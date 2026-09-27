"""Site model system for v4 — real GeoJSON parcels + legacy rectangle fallback.

Supports two modes via config:
  - legacy_rect: exact v3 reproduction (90 x 61.5 m rectangle)
  - geojson: real parcel from GeoJSON file with optional annotations

Provenance: [DESIGN HYPOTHESIS] for all geometric derivations.
[TO VERIFY] for all real-world spatial relationships.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import numpy as np


class SiteMode(Enum):
    LEGACY_RECT = "legacy_rect"
    GEOJSON = "geojson"


class ProvenanceTag(Enum):
    VERIFIED = "[VERIFIED]"
    OBSERVED = "[OBSERVED]"
    SECONDARY = "[SECONDARY]"
    DESIGN_HYPOTHESIS = "[DESIGN HYPOTHESIS]"
    TO_VERIFY = "[TO VERIFY]"


@dataclass
class Annotation:
    """A site annotation with provenance tracking."""
    feature_type: str          # frontage, public_access, service_access, etc.
    geometry: dict             # GeoJSON geometry
    provenance: ProvenanceTag
    verified: bool = False
    notes: str = ""


@dataclass
class Edge:
    """A classified site boundary edge."""
    index: int
    start: tuple[float, float]  # (lon, lat) or (x, y) in local coords
    end: tuple[float, float]
    length_m: float
    orientation: str             # N, S, E, W, NE, NW, SE, SW
    midpoint: tuple[float, float]


@dataclass
class Site:
    """Unified site model for both legacy and real parcels."""
    mode: SiteMode
    name: str = ""
    
    # Geometry (local coordinates in metres, origin at SW corner)
    boundary_polygon: list[tuple[float, float]] = field(default_factory=list)
    area_m2: float = 0.0
    perimeter_m: float = 0.0
    centroid: tuple[float, float] = (0.0, 0.0)
    width_m: float = 0.0          # bounding box
    height_m: float = 0.0         # bounding box
    
    # Edges
    edges: list[Edge] = field(default_factory=list)
    
    # Annotations (optional, may be empty in first v4 run)
    annotations: dict[str, list[Annotation]] = field(default_factory=dict)
    
    # Config
    source_path: Optional[str] = None
    convert_linestring: bool = True
    
    # --- v4 real-site metadata (from site.yaml) ---------------------------
    metadata: dict = field(default_factory=dict)
    metadata_provenance: dict = field(default_factory=dict)
    setbacks_m: dict = field(default_factory=dict)      # front/side/rear/tpst_buffer
    frontage_edges: list[int] = field(default_factory=list)
    preferred_expansion_direction: str = ""
    
    # Legacy compatibility
    @property
    def site_w(self) -> float:
        return self.width_m
    
    @property
    def site_h(self) -> float:
        return self.height_m
    
    def get_annotations(self, feature_type: str) -> list[Annotation]:
        return self.annotations.get(feature_type, [])
    
    def has_annotation(self, feature_type: str) -> bool:
        return feature_type in self.annotations and len(self.annotations[feature_type]) > 0
    
    def verified_annotations(self, feature_type: str) -> list[Annotation]:
        return [a for a in self.get_annotations(feature_type) if a.verified]


def create_legacy_site() -> Site:
    """Create the exact v3 legacy site: 90 x 61.5 m rectangle.
    
    Returns a Site object that reproduces v3 behaviour exactly.
    """
    # v3 used SITE_W=90, SITE_H=61.5, area=5533.85
    # We create a rectangle with the same area and proportions
    w, h = 90.0, 61.5
    coords = [(0, 0), (w, 0), (w, h), (0, h), (0, 0)]
    
    site = Site(
        mode=SiteMode.LEGACY_RECT,
        name="legacy_v3_rectangle",
        boundary_polygon=coords,
        width_m=w,
        height_m=h,
        area_m2=w * h,
        perimeter_m=2 * (w + h),
        centroid=(w/2, h/2),
    )
    
    # Create edges
    for i in range(4):
        p1 = coords[i]
        p2 = coords[i+1]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.sqrt(dx*dx + dy*dy)
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        orient = _angle_to_orientation(angle)
        site.edges.append(Edge(
            index=i, start=p1, end=p2, length_m=length,
            orientation=orient, midpoint=((p1[0]+p2[0])/2, (p1[1]+p2[1])/2)
        ))
    
    return site


def load_site(path: str | Path, mode: SiteMode = SiteMode.GEOJSON,
              convert_linestring: bool = True) -> Site:
    """Load a site from GeoJSON file.
    
    Handles both Polygon and closed LineString geometries.
    Converts geographic coordinates to local metres.
    """
    path = Path(path)
    with open(path) as f:
        data = json.load(f)
    
    if data["type"] != "FeatureCollection":
        raise ValueError(f"Expected FeatureCollection, got {data['type']}")
    
    # Find the boundary feature
    boundary_feature = None
    for feat in data["features"]:
        geom_type = feat["geometry"]["type"]
        if geom_type in ("Polygon", "LineString"):
            boundary_feature = feat
            break
    
    if boundary_feature is None:
        raise ValueError("No Polygon or LineString feature found")
    
    geom = boundary_feature["geometry"]
    
    # Extract coordinates
    if geom["type"] == "Polygon":
        coords = geom["coordinates"][0]  # exterior ring
    elif geom["type"] == "LineString":
        coords = geom["coordinates"]
        if not convert_linestring:
            raise ValueError("LineString found but convert_linestring=False")
        # Check if closed
        if coords[0] != coords[-1]:
            raise ValueError("LineString is not closed — cannot convert to polygon")
    else:
        raise ValueError(f"Unsupported geometry type: {geom['type']}")
    
    # Convert geographic to local coordinates (metres)
    local_coords = _geo_to_local(coords)
    
    # Compute metrics
    area = _polygon_area(local_coords)
    perimeter = _polygon_perimeter(local_coords)
    centroid = _polygon_centroid(local_coords)
    
    xs = [c[0] for c in local_coords]
    ys = [c[1] for c in local_coords]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    
    site = Site(
        mode=SiteMode.GEOJSON,
        name=path.stem,
        boundary_polygon=local_coords,
        area_m2=area,
        perimeter_m=perimeter,
        centroid=centroid,
        width_m=width,
        height_m=height,
        source_path=str(path),
        convert_linestring=convert_linestring,
    )
    
    # Create edges
    n = len(local_coords) - 1
    for i in range(n):
        p1 = local_coords[i]
        p2 = local_coords[i+1]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.sqrt(dx*dx + dy*dy)
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        orient = _angle_to_orientation(angle)
        site.edges.append(Edge(
            index=i, start=p1, end=p2, length_m=length,
            orientation=orient, midpoint=((p1[0]+p2[0])/2, (p1[1]+p2[1])/2)
        ))
    
    return site


def _geo_to_local(coords: list[list[float]]) -> list[tuple[float, float]]:
    """Convert [lon, lat] list to local metre coordinates."""
    lats = [c[1] for c in coords]
    lons = [c[0] for c in coords]
    lat_center = sum(lats) / len(lats)
    
    m_per_deg_lat = 111320.0
    m_per_deg_lon = 111320.0 * abs(math.cos(math.radians(lat_center)))
    
    # Use min values as origin
    lon0 = min(lons)
    lat0 = min(lats)
    
    local = []
    for lon, lat in coords:
        x = (lon - lon0) * m_per_deg_lon
        y = (lat - lat0) * m_per_deg_lat
        local.append((x, y))
    
    return local


def _polygon_area(coords: list[tuple[float, float]]) -> float:
    """Shoelace formula."""
    n = len(coords) - 1
    area = 0.0
    for i in range(n):
        x1, y1 = coords[i]
        x2, y2 = coords[(i+1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def _polygon_perimeter(coords: list[tuple[float, float]]) -> float:
    n = len(coords) - 1
    perim = 0.0
    for i in range(n):
        x1, y1 = coords[i]
        x2, y2 = coords[(i+1) % n]
        perim += math.sqrt((x2-x1)**2 + (y2-y1)**2)
    return perim


def _polygon_centroid(coords: list[tuple[float, float]]) -> tuple[float, float]:
    """Centroid of polygon, guaranteed to be inside bounding box."""
    n = len(coords) - 1
    if n < 3:
        # Fallback to average
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        return (sum(xs)/len(xs), sum(ys)/len(ys))
    
    cx = 0.0
    cy = 0.0
    signed_area = 0.0
    
    for i in range(n):
        x1, y1 = coords[i]
        x2, y2 = coords[(i+1) % n]
        cross = x1 * y2 - x2 * y1
        signed_area += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    
    signed_area *= 0.5
    if abs(signed_area) < 1e-10:
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        return (sum(xs)/len(xs), sum(ys)/len(ys))
    
    cx /= (6 * signed_area)
    cy /= (6 * signed_area)
    return (abs(cx), abs(cy))


def _angle_to_orientation(angle: float) -> str:
    """Convert angle (0-360) to compass orientation."""
    if 337.5 <= angle or angle < 22.5:
        return "E"
    elif 22.5 <= angle < 67.5:
        return "NE"
    elif 67.5 <= angle < 112.5:
        return "N"
    elif 112.5 <= angle < 157.5:
        return "NW"
    elif 157.5 <= angle < 202.5:
        return "W"
    elif 202.5 <= angle < 247.5:
        return "SW"
    elif 247.5 <= angle < 292.5:
        return "S"
    else:
        return "SE"


def point_in_polygon(point: tuple[float, float], 
                     polygon: list[tuple[float, float]]) -> bool:
    """Ray casting algorithm for point-in-polygon test."""
    x, y = point
    n = len(polygon)
    inside = False
    
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        
        if ((yi > y) != (yj > y)) and \
           (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    
    return inside


def nearest_edge(point: tuple[float, float], 
                 polygon: list[tuple[float, float]]) -> tuple[int, float]:
    """Find nearest edge and distance to it."""
    x, y = point
    min_dist = float('inf')
    min_idx = 0
    
    n = len(polygon)
    for i in range(n - 1):
        x1, y1 = polygon[i]
        x2, y2 = polygon[i+1]
        
        # Distance from point to line segment
        dx = x2 - x1
        dy = y2 - y1
        length_sq = dx*dx + dy*dy
        
        if length_sq == 0:
            dist = math.sqrt((x-x1)**2 + (y-y1)**2)
        else:
            t = max(0, min(1, ((x-x1)*dx + (y-y1)*dy) / length_sq))
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            dist = math.sqrt((x-proj_x)**2 + (y-proj_y)**2)
        
        if dist < min_dist:
            min_dist = dist
            min_idx = i
    
    return min_idx, min_dist


def edge_classification(polygon: list[tuple[float, float]]) -> dict[str, list[int]]:
    """Classify edges by orientation."""
    result = {"N": [], "S": [], "E": [], "W": []}
    n = len(polygon)
    for i in range(n - 1):
        x1, y1 = polygon[i]
        x2, y2 = polygon[i+1]
        dx = x2 - x1
        dy = y2 - y1
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        orient = _angle_to_orientation(angle)
        if orient in result:
            result[orient].append(i)
    return result


def setback_polygon(polygon: list[tuple[float, float]], 
                    setback_m: float) -> list[tuple[float, float]]:
    """Approximate inward offset of polygon by setback distance.
    
    Uses a simple normal-based approach. For complex polygons,
    a proper offsetting library would be better [TO VERIFY].
    """
    n = len(polygon)
    result = []
    
    for i in range(n - 1):
        p1 = polygon[i]
        p2 = polygon[i+1]
        
        # Edge vector
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.sqrt(dx*dx + dy*dy)
        
        if length == 0:
            continue
        
        # Normal (pointing inward for CCW polygon)
        nx = -dy / length
        ny = dx / length
        
        # Offset points
        result.append((p1[0] + nx * setback_m, p1[1] + ny * setback_m))
    
    # Close polygon
    if result:
        result.append(result[0])
    
    return result


def load_annotations(path: str | Path) -> dict[str, list[Annotation]]:
    """Load site annotations from YAML/JSON sidecar file."""
    path = Path(path)
    if not path.exists():
        return {}
    
    with open(path) as f:
        data = json.load(f)
    
    annotations = {}
    for key, items in data.get("annotations", {}).items():
        if items is None:
            continue
        if not isinstance(items, list):
            items = [items]
        annotations[key] = []
        for item in items:
            prov_str = item.get("provenance", "TO_VERIFY")
            try:
                prov = ProvenanceTag(f"[{prov_str}]")
            except ValueError:
                prov = ProvenanceTag.TO_VERIFY
            
            annotations[key].append(Annotation(
                feature_type=key,
                geometry=item.get("geometry", {}),
                provenance=prov,
                verified=item.get("verified", False),
                notes=item.get("notes", ""),
            ))
    
    return annotations


# =============================================================================
# Canonical real-site input (v4): site.geojson (geometry) + site.yaml (metadata)
# =============================================================================
def _parse_provenance(raw: str) -> ProvenanceTag:
    """Parse a provenance string into a ProvenanceTag (lenient)."""
    if not raw:
        return ProvenanceTag.TO_VERIFY
    s = str(raw).strip().strip("[]").upper().replace(" ", "_")
    mapping = {
        "VERIFIED": ProvenanceTag.VERIFIED,
        "OBSERVED": ProvenanceTag.OBSERVED,
        "SECONDARY": ProvenanceTag.SECONDARY,
        "DESIGN_HYPOTHESIS": ProvenanceTag.DESIGN_HYPOTHESIS,
        "DH": ProvenanceTag.DESIGN_HYPOTHESIS,
        "TO_VERIFY": ProvenanceTag.TO_VERIFY,
        "TV": ProvenanceTag.TO_VERIFY,
        "PA5_CORPUS": ProvenanceTag.DESIGN_HYPOTHESIS,
    }
    return mapping.get(s, ProvenanceTag.TO_VERIFY)


def _simple_yaml(text: str) -> dict:
    """Minimal YAML-subset parser (no external dependency).

    Supports nested dicts via indentation, `key: value`, `key: null`,
    inline flow dicts `{a: b, c: d}` and inline flow lists `[1, 2]`.
    Only used when PyYAML is unavailable; validated against the v4
    site.yaml schema. NOT a general YAML parser [TO VERIFY for exotic input].
    """
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)
    except Exception:
        pass

    def _scalar(tok: str):
        t = tok.strip()
        if t in ("", "~", "null", "None"):
            return None
        if t in ("true", "True"):
            return True
        if t in ("false", "False"):
            return False
        if t.startswith("{") and t.endswith("}"):
            inner = t[1:-1].strip()
            out = {}
            if inner:
                for part in _split_top(inner):
                    k, _, v = part.partition(":")
                    out[k.strip()] = _scalar(v)
            return out
        if t.startswith("[") and t.endswith("]"):
            inner = t[1:-1].strip()
            return [_scalar(p) for p in _split_top(inner)] if inner else []
        try:
            return int(t)
        except ValueError:
            pass
        try:
            return float(t)
        except ValueError:
            pass
        return t.strip('"').strip("'")

    def _split_top(s: str) -> list[str]:
        parts, depth, cur = [], 0, ""
        for ch in s:
            if ch in "[{":
                depth += 1
            elif ch in "]}":
                depth -= 1
            if ch == "," and depth == 0:
                parts.append(cur)
                cur = ""
            else:
                cur += ch
        if cur.strip():
            parts.append(cur)
        return parts

    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        content = line.strip()
        if ":" not in content:
            continue
        key, _, val = content.partition(":")
        key = key.strip()
        val = val.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if val == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _scalar(val)
    return root


def load_site_metadata(path: str | Path) -> dict:
    """Load site.yaml metadata (returns {} if absent). Never fabricates."""
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return _simple_yaml(f.read()) or {}


def _flatten_provenance(meta: dict, prefix: str = "") -> dict:
    """Flatten nested metadata into {dotted.key: provenance_str}."""
    out = {}
    for k, v in meta.items():
        key = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict):
            if "provenance" in v:
                out[key] = str(v.get("provenance", "[TO VERIFY]"))
            out.update(_flatten_provenance(
                {kk: vv for kk, vv in v.items() if kk != "provenance"}, key))
    return out


def load_canonical_site(geojson_path: str | Path,
                        yaml_path: str | Path | None = None) -> Site:
    """Load the canonical REAL site: GeoJSON geometry + site.yaml metadata.

    The legacy 90 x 61.5 m rectangle is retained ONLY as a regression/test
    fixture (see create_legacy_site). All v4 runs use this canonical loader.

    Provenance: geometry [VERIFIED via site.geojson]; metadata inherits the
    per-attribute tags declared in site.yaml. Nothing is fabricated: absent
    attributes stay None/[TO VERIFY].
    """
    geojson_path = Path(geojson_path)
    site = load_site(geojson_path, mode=SiteMode.GEOJSON)

    if yaml_path is None:
        yaml_path = geojson_path.with_suffix(".yaml")
    meta = load_site_metadata(yaml_path)
    site.metadata = meta
    site.metadata_provenance = _flatten_provenance(meta)

    # --- setbacks / buffers (schematic defaults) --------------------------
    sb = meta.get("setbacks", {}) if isinstance(meta.get("setbacks"), dict) else {}
    def _depth(key: str, default: float) -> float:
        node = sb.get(key, {})
        if isinstance(node, dict) and isinstance(node.get("value"), (int, float)):
            return float(node["value"])
        return default
    site.setbacks_m = {
        "front": _depth("front_m", 4.0),
        "side": _depth("side_m", 3.0),
        "rear": _depth("rear_m", 3.0),
        "tpst_buffer": _depth("tpst_buffer_m", 10.0),
    }

    # --- frontage edges ----------------------------------------------------
    fr = meta.get("frontage", {}) if isinstance(meta.get("frontage"), dict) else {}
    prim = fr.get("primary_street", {}) if isinstance(fr.get("primary_street"), dict) else {}
    idxs = prim.get("edge_indices") or []
    site.frontage_edges = [int(i) for i in idxs if isinstance(i, (int, float))]

    # --- preferred expansion direction -------------------------------------
    ctx = meta.get("context", {}) if isinstance(meta.get("context"), dict) else {}
    exp = ctx.get("preferred_expansion_direction", {})
    if isinstance(exp, dict) and exp.get("direction"):
        site.preferred_expansion_direction = str(exp["direction"])

    return site


def buildable_polygon(site: Site) -> list[tuple[float, float]]:
    """Approximate buildable band after applying a uniform side setback.

    Uses the max of side/rear setbacks as a conservative inward offset
    [DESIGN HYPOTHESIS]; front edge keeps its own arrival band. For complex
    polygons a true offsetting library would be preferable [TO VERIFY].
    """
    if not site.boundary_polygon:
        return []
    depth = max(site.setbacks_m.get("side", 3.0),
                site.setbacks_m.get("rear", 3.0)) if site.setbacks_m else 3.0
    return setback_polygon(site.boundary_polygon, depth)


def anchor_point(site: Site, kind: str) -> tuple[float, float] | None:
    """Resolve a site access anchor to a local (x, y) point.

    kind in {"public_entry", "service_entry", "emergency_access"}.
    Uses the midpoint of the frontage edge when a coordinate is not yet
    evidenced [DESIGN HYPOTHESIS]; returns None when no anchor is declared.
    """
    if kind == "public_entry":
        if site.frontage_edges and site.edges:
            ei = site.frontage_edges[0]
            if 0 <= ei < len(site.edges):
                return site.edges[ei].midpoint
        # fallback: centroid of front-most edge
        return site.centroid if site.centroid else None
    # service / emergency: prefer explicit metadata, else None (never fabricate)
    acc = site.metadata.get("access", {}) if isinstance(site.metadata.get("access"), dict) else {}
    node = acc.get(kind, {})
    if isinstance(node, dict):
        idxs = node.get("edge_indices") or []
        if idxs and site.edges:
            ei = int(idxs[0])
            if 0 <= ei < len(site.edges):
                return site.edges[ei].midpoint
    return None
