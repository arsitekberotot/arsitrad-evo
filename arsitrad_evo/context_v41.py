"""Evidence-gated site fields and dynamic architectural zoning for V4.1."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .site import Site, arrival_segments, distance_to_arrival, distance_to_segment


ZONE_ORDER = ("public_civic", "controlled_care", "shared_everyday", "domestic", "personal")
SERVICE_ZONE = "service"


def _area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    return abs(sum(points[i][0] * points[(i + 1) % len(points)][1]
                   - points[(i + 1) % len(points)][0] * points[i][1]
                   for i in range(len(points)))) / 2.0


def _clip_halfplane(points, normal, limit, keep_greater):
    """Clip polygon against dot(point, normal) >=/<= limit."""
    if not points:
        return []
    result = []
    previous = points[-1]
    pv = previous[0] * normal[0] + previous[1] * normal[1] - limit
    for current in points:
        cv = current[0] * normal[0] + current[1] * normal[1] - limit
        p_ok = pv >= -1e-9 if keep_greater else pv <= 1e-9
        c_ok = cv >= -1e-9 if keep_greater else cv <= 1e-9
        if p_ok != c_ok:
            t = pv / (pv - cv)
            result.append((previous[0] + t * (current[0] - previous[0]),
                           previous[1] + t * (current[1] - previous[1])))
        if c_ok:
            result.append(current)
        previous, pv = current, cv
    return result


@dataclass(frozen=True)
class SiteContext:
    site: Site
    arrival_start: tuple[float, float] | None
    arrival_end: tuple[float, float] | None
    inward: tuple[float, float]
    max_depth_m: float
    layers: dict

    @classmethod
    def from_site(cls, site: Site) -> "SiteContext":
        segments = arrival_segments(site)
        if not segments:
            raise ValueError("V4.1 needs an evidenced public-arrival segment")
        if len(segments) != 1:
            raise ValueError("V4.1 currently expects one continuous arrival segment")
        start, end = segments[0]
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        nx, ny = -dy / length, dx / length
        mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        if (site.centroid[0] - mid[0]) * nx + (site.centroid[1] - mid[1]) * ny < 0:
            nx, ny = -nx, -ny
        vertices = site.boundary_polygon[:-1]
        depth = max((p[0] - mid[0]) * nx + (p[1] - mid[1]) * ny for p in vertices)
        declared = site.metadata.get("context_layers", {})
        layers = {}
        for name, raw in declared.items():
            present = raw.get("present") is True
            provenance = raw.get("provenance", "[TO VERIFY]")
            needs_edges = name in {"public_frontage", "public_arrival", "possible_service_access",
                                   "settlement_facing_edges", "tpst_facing_edges", "noise", "odour", "dust"}
            enabled = present and provenance != "[TO VERIFY]" and (not needs_edges or bool(raw.get("edge_indices")))
            layers[name] = {"enabled": enabled, "provenance": provenance,
                            "edge_indices": raw.get("edge_indices", []),
                            "notes": raw.get("notes", "")}
        required = {"public_frontage", "public_arrival", "possible_service_access",
                    "settlement_facing_edges", "tpst_facing_edges", "road_hierarchy",
                    "solar_orientation", "prevailing_wind", "noise", "odour", "dust",
                    "drainage_flooding", "vegetation", "existing_obstacles",
                    "landscape_opportunity", "future_expansion"}
        if not required.issubset(layers):
            raise ValueError(f"Missing contextual layers: {sorted(required - set(layers))}")
        return cls(site, start, end, (nx, ny), depth, layers)

    def depth_m(self, point: tuple[float, float]) -> float:
        mid = ((self.arrival_start[0] + self.arrival_end[0]) / 2,
               (self.arrival_start[1] + self.arrival_end[1]) / 2)
        return max(0.0, (point[0] - mid[0]) * self.inward[0]
                   + (point[1] - mid[1]) * self.inward[1])

    def depth_fraction(self, point: tuple[float, float]) -> float:
        return min(1.0, self.depth_m(point) / self.max_depth_m)

    def along_frontage_fraction(self, point: tuple[float, float]) -> float:
        ax, ay = self.arrival_start
        bx, by = self.arrival_end
        dx, dy = bx - ax, by - ay
        return ((point[0] - ax) * dx + (point[1] - ay) * dy) / (dx * dx + dy * dy)

    def at_depth(self, point: tuple[float, float], fraction: float) -> tuple[float, float]:
        delta = fraction * self.max_depth_m - self.depth_m(point)
        return point[0] + delta * self.inward[0], point[1] + delta * self.inward[1]

    def sample(self, field: str, point: tuple[float, float]) -> float | None:
        """Continuous 0-1 site field. None means no evidenced optimization input."""
        if field == "public_access_attraction":
            distance = distance_to_arrival(self.site, point)
            return max(0.0, 1.0 - distance / self.max_depth_m) if distance is not None else None
        if field == "domestic_protection_depth":
            return self.depth_fraction(point)
        if field == "community_interface_suitability":
            return self.sample("public_access_attraction", point)
        edge_layer = {
            "service_access_attraction": "possible_service_access",
            "environmental_exposure": "tpst_facing_edges",
        }.get(field)
        if edge_layer:
            layer = self.layers[edge_layer]
            if not layer["enabled"] or not layer["edge_indices"]:
                return None
            distance = min(distance_to_segment(point, (self.site.edges[i].start, self.site.edges[i].end))
                           for i in layer["edge_indices"])
            proximity = max(0.0, 1.0 - distance / self.max_depth_m)
            return proximity
        if field in {"landscape_suitability", "expansion_potential"}:
            layer = self.layers["landscape_opportunity" if field == "landscape_suitability" else "future_expansion"]
            if not layer["enabled"]:
                return None
            # A verified layer still needs a spatial geometry before it may act.
            return None
        raise KeyError(field)

    def field_manifest(self) -> dict:
        return {
            "public_access_attraction": {"enabled": True, "source": "public_arrival", "provenance": "[VERIFIED]"},
            "domestic_protection_depth": {"enabled": True, "source": "public_arrival", "provenance": "[DESIGN HYPOTHESIS]"},
            "community_interface_suitability": {"enabled": True, "source": "public_arrival", "provenance": "[DESIGN HYPOTHESIS]"},
            "service_access_attraction": {"enabled": self.layers["possible_service_access"]["enabled"], "source": "possible_service_access", "provenance": self.layers["possible_service_access"]["provenance"]},
            "environmental_exposure": {"enabled": self.layers["tpst_facing_edges"]["enabled"], "source": "tpst_facing_edges", "provenance": self.layers["tpst_facing_edges"]["provenance"]},
            "landscape_suitability": {"enabled": False, "source": "landscape_opportunity", "provenance": "[TO VERIFY]"},
            "expansion_potential": {"enabled": False, "source": "future_expansion", "provenance": "[TO VERIFY]"},
        }


def zoning_state(context: SiteContext, scales: list[float]) -> dict:
    """Evolved depth bands clipped to the exact parcel polygon."""
    if len(scales) != len(ZONE_ORDER):
        raise ValueError("Need one scale gene per ordered zone")
    positive = [max(0.05, float(v)) for v in scales]
    total = sum(positive)
    limits = [0.0]
    for value in positive:
        limits.append(limits[-1] + value / total)
    polygon = context.site.boundary_polygon[:-1]
    normal = context.inward
    origin_dot = context.arrival_start[0] * normal[0] + context.arrival_start[1] * normal[1]
    areas = {}
    for index, name in enumerate(ZONE_ORDER):
        low = origin_dot + limits[index] * context.max_depth_m
        high = origin_dot + limits[index + 1] * context.max_depth_m
        clipped = _clip_halfplane(polygon, normal, low, True)
        clipped = _clip_halfplane(clipped, normal, high, False)
        areas[name] = _area(clipped)
    shares = [a / context.site.area_m2 for a in areas.values()]
    largest = max(shares)
    if largest >= 0.65:
        zone_type = "total_zone"
    elif largest >= 0.40:
        zone_type = "dominated_zone"
    else:
        zone_type = "balanced_zone"
    return {"order": list(ZONE_ORDER), "service_network": "parallel_controlled",
            "boundaries_fraction": limits, "area_m2": areas,
            "type": zone_type,
            "definition": "Balanced: largest zone <40% of parcel; dominated: 40-65%; total: >=65%. Service is a parallel controlled network.",
            "provenance": "[DESIGN HYPOTHESIS]"}


def zone_at(context: SiteContext, state: dict, point: tuple[float, float]) -> str:
    depth = context.depth_fraction(point)
    for index, upper in enumerate(state["boundaries_fraction"][1:]):
        if depth <= upper + 1e-9:
            return ZONE_ORDER[index]
    return ZONE_ORDER[-1]


def target_depth(state: dict, zone: str, offset: float = 0.0) -> float:
    if zone == SERVICE_ZONE:
        # The service route runs across the public/controlled/shared bands.
        return max(0.08, min(0.55, 0.5 * state["boundaries_fraction"][3] + offset))
    i = ZONE_ORDER.index(zone)
    lo, hi = state["boundaries_fraction"][i:i + 2]
    return max(lo + 0.02, min(hi - 0.02, (lo + hi) / 2 + offset * (hi - lo)))
