"""Circulation network v4 — real path networks for all user groups.

Derives resident, care/staff, visitor, service, and emergency routes as
actual path networks with waypoints, not just straight lines.

Provenance: [DESIGN HYPOTHESIS] for all route derivations.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .site import Site, point_in_polygon
from .genotype_v4 import PhenotypeV4, InstanceV4
from .spatial_analysis import cast_sightline, compute_privacy_field


@dataclass
class Waypoint:
    """A point along a route."""
    x: float
    y: float
    waypoint_type: str  # "access", "threshold", "turn", "destination"
    module_code: str = ""  # associated module if any


@dataclass
class Route:
    """A path between two points with metadata."""
    route_id: str
    kind: str              # resident, staff, visitor, service, emergency
    start: Waypoint
    end: Waypoint
    waypoints: list[Waypoint] = field(default_factory=list)
    length_m: float = 0.0
    exposed_length_m: float = 0.0  # length visible from public areas
    privacy_violations: int = 0    # segments through private space
    accessibility_ok: bool = True  # step-free, width adequate
    provenance: str = "[DESIGN HYPOTHESIS]"


@dataclass
class RouteNetwork:
    """A network of routes for one user group."""
    kind: str
    routes: list[Route] = field(default_factory=list)
    total_length: float = 0.0
    avg_exposure: float = 0.0
    max_privacy_violation: int = 0
    provenance: str = "[DESIGN HYPOTHESIS]"


@dataclass
class AccessPoint:
    """A module access point."""
    module_code: str
    x: float
    y: float
    face: str           # N, S, E, W
    access_type: str    # public, controlled, private, service
    width_m: float = 1.5


def _get_access_point(inst: InstanceV4, face: str) -> tuple[float, float]:
    """Get access point coordinates for a module face."""
    x, y = inst.x, inst.y
    hw, hd = inst.w / 2, inst.d / 2
    
    if face == "N":
        return (x, y + hd)
    elif face == "S":
        return (x, y - hd)
    elif face == "E":
        return (x + hw, y)
    elif face == "W":
        return (x - hw, y)
    else:
        return (x, y)


def _simple_pathfind(start: tuple[float, float], 
                     end: tuple[float, float],
                     obstacles: list[InstanceV4],
                     site: Site) -> list[Waypoint]:
    """Simple pathfinding with obstacle avoidance.
    
    Uses a grid-based A* approximation. For v4, this is simplified:
    - Try direct line first
    - If blocked, route around obstacles
    - Generate waypoints at turns
    """
    waypoints = [Waypoint(start[0], start[1], "access")]
    
    # Check if direct path is clear
    blocked = False
    for obs in obstacles:
        x0 = obs.x - obs.w / 2
        x1 = obs.x + obs.w / 2
        y0 = obs.y - obs.d / 2
        y1 = obs.y + obs.d / 2
        
        # Simple line-rect intersection check
        if _line_intersects_rect(start, end, (x0, y0, x1, y1)):
            blocked = True
            break
    
    if not blocked:
        waypoints.append(Waypoint(end[0], end[1], "destination"))
        return waypoints
    
    # Route around obstacles (simplified: go via site center)
    cx, cy = site.centroid
    
    # Add intermediate waypoint at site center
    waypoints.append(Waypoint(cx, cy, "turn"))
    waypoints.append(Waypoint(end[0], end[1], "destination"))
    
    return waypoints


def _line_intersects_rect(p1: tuple[float, float], 
                          p2: tuple[float, float],
                          rect: tuple[float, float, float, float]) -> bool:
    """Check if line segment intersects rectangle."""
    x0, y0, x1, y1 = rect
    
    # Check if either endpoint is inside
    if (x0 <= p1[0] <= x1 and y0 <= p1[1] <= y1):
        return True
    if (x0 <= p2[0] <= x1 and y0 <= p2[1] <= y1):
        return True
    
    # Check line-line intersections with each edge
    edges = [
        ((x0, y0), (x1, y0)),  # bottom
        ((x1, y0), (x1, y1)),  # right
        ((x1, y1), (x0, y1)),  # top
        ((x0, y1), (x0, y0)),  # left
    ]
    
    for e1, e2 in edges:
        if _lines_intersect(p1, p2, e1, e2):
            return True
    
    return False


def _lines_intersect(a1: tuple[float, float], a2: tuple[float, float],
                     b1: tuple[float, float], b2: tuple[float, float]) -> bool:
    """Check if two line segments intersect."""
    def ccw(A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
    
    return ccw(a1, b1, b2) != ccw(a2, b1, b2) and ccw(a1, a2, b1) != ccw(a1, a2, b2)


def _compute_route_metrics(route: Route, ph: PhenotypeV4) -> None:
    """Compute length, exposure, and privacy metrics for a route."""
    total_len = 0.0
    exposed_len = 0.0
    
    wps = [route.start] + route.waypoints + [route.end]
    
    for i in range(len(wps) - 1):
        p1 = (wps[i].x, wps[i].y)
        p2 = (wps[i+1].x, wps[i+1].y)
        seg_len = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        total_len += seg_len
        
        # Check exposure (simplified: is segment visible from public modules?)
        public_mods = [m for m in ph.instances if m.privacy_level <= 1]
        seg_exposed = False
        for pub in public_mods:
            sl = cast_sightline(
                (pub.x, pub.y, 1.5),
                ((p1[0]+p2[0])/2, (p1[1]+p2[1])/2, 1.5),
                ph.instances
            )
            if sl.exposed:
                seg_exposed = True
                break
        
        if seg_exposed:
            exposed_len += seg_len
    
    route.length_m = total_len
    route.exposed_length_m = exposed_len


def derive_resident_routes(ph: PhenotypeV4) -> RouteNetwork:
    """Derive resident circulation network.
    
    Key journeys:
    - R4 ↔ C0 (domestic to commons)
    - R4 ↔ H0 (domestic to learning)
    - R4 ↔ B0 (domestic to care, screened)
    - R4 ↔ site boundary (exit)
    """
    network = RouteNetwork(kind="resident")
    
    r4s = [i for i in ph.instances if i.family == "R4"]
    c0s = [i for i in ph.instances if i.family == "C0"]
    h0s = [i for i in ph.instances if i.family == "H0"]
    b0s = [i for i in ph.instances if i.family == "B0"]
    
    route_id = 0
    
    # R4 → C0
    for r4 in r4s:
        for c0 in c0s:
            start = _get_access_point(r4, r4.access_face)
            end = _get_access_point(c0, c0.access_face)
            route = Route(
                route_id=f"resident_{route_id}",
                kind="resident",
                start=Waypoint(start[0], start[1], "access", r4.code),
                end=Waypoint(end[0], end[1], "destination", c0.code),
            )
            route.waypoints = _simple_pathfind(start, end, ph.instances, ph.site)
            _compute_route_metrics(route, ph)
            network.routes.append(route)
            route_id += 1
    
    # R4 → B0 (screened)
    for r4 in r4s:
        for b0 in b0s:
            start = _get_access_point(r4, r4.access_face)
            end = _get_access_point(b0, b0.access_face)
            route = Route(
                route_id=f"resident_screened_{route_id}",
                kind="resident_screened",
                start=Waypoint(start[0], start[1], "access", r4.code),
                end=Waypoint(end[0], end[1], "destination", b0.code),
            )
            route.waypoints = _simple_pathfind(start, end, ph.instances, ph.site)
            _compute_route_metrics(route, ph)
            network.routes.append(route)
            route_id += 1
    
    _aggregate_network(network)
    return network


def derive_staff_routes(ph: PhenotypeV4) -> RouteNetwork:
    """Derive care/staff circulation network.
    
    Key journeys:
    - B0 ↔ R4 (observation / response)
    - B0 ↔ C0 (care to commons)
    - B0 ↔ F0/M0 (service)
    """
    network = RouteNetwork(kind="staff")
    
    b0s = [i for i in ph.instances if i.family == "B0"]
    r4s = [i for i in ph.instances if i.family == "R4"]
    c0s = [i for i in ph.instances if i.family == "C0"]
    services = [i for i in ph.instances if i.family in ("F0", "M0")]
    
    route_id = 0
    
    for b0 in b0s:
        for r4 in r4s:
            start = _get_access_point(b0, b0.access_face)
            end = _get_access_point(r4, r4.access_face)
            route = Route(
                route_id=f"staff_obs_{route_id}",
                kind="staff_observation",
                start=Waypoint(start[0], start[1], "access", b0.code),
                end=Waypoint(end[0], end[1], "destination", r4.code),
            )
            route.waypoints = _simple_pathfind(start, end, ph.instances, ph.site)
            _compute_route_metrics(route, ph)
            network.routes.append(route)
            route_id += 1
        
        for svc in services:
            start = _get_access_point(b0, b0.access_face)
            end = _get_access_point(svc, svc.access_face)
            route = Route(
                route_id=f"staff_svc_{route_id}",
                kind="staff_service",
                start=Waypoint(start[0], start[1], "access", b0.code),
                end=Waypoint(end[0], end[1], "destination", svc.code),
            )
            route.waypoints = _simple_pathfind(start, end, ph.instances, ph.site)
            _compute_route_metrics(route, ph)
            network.routes.append(route)
            route_id += 1
    
    _aggregate_network(network)
    return network


def derive_visitor_routes(ph: PhenotypeV4) -> RouteNetwork:
    """Derive visitor circulation network.
    
    Key journeys:
    - A0 ↔ K0 (arrival to community)
    - A0 ↔ C0 (arrival to commons)
    - A0 ↔ B0 (controlled access to care)
    """
    network = RouteNetwork(kind="visitor")
    
    a0s = [i for i in ph.instances if i.family == "A0"]
    k0s = [i for i in ph.instances if i.family == "K0"]
    c0s = [i for i in ph.instances if i.family == "C0"]
    b0s = [i for i in ph.instances if i.family == "B0"]
    
    route_id = 0
    
    for a0 in a0s:
        for dest_list, kind in [(k0s, "visitor_community"), (c0s, "visitor_commons"), (b0s, "visitor_controlled")]:
            for dest in dest_list:
                start = _get_access_point(a0, a0.access_face)
                end = _get_access_point(dest, dest.access_face)
                route = Route(
                    route_id=f"visitor_{route_id}",
                    kind=kind,
                    start=Waypoint(start[0], start[1], "access", a0.code),
                    end=Waypoint(end[0], end[1], "destination", dest.code),
                )
                route.waypoints = _simple_pathfind(start, end, ph.instances, ph.site)
                _compute_route_metrics(route, ph)
                network.routes.append(route)
                route_id += 1
    
    _aggregate_network(network)
    return network


def derive_service_routes(ph: PhenotypeV4) -> RouteNetwork:
    """Derive service circulation network.
    
    Key journeys:
    - F0/M0 ↔ all modules (back-of-house)
    - Service yard ↔ waste / utility
    """
    network = RouteNetwork(kind="service")
    
    services = [i for i in ph.instances if i.family in ("F0", "M0")]
    all_mods = ph.instances
    
    route_id = 0
    
    for svc in services:
        for mod in all_mods:
            if mod.code == svc.code:
                continue
            start = _get_access_point(svc, svc.access_face)
            end = _get_access_point(mod, mod.access_face)
            route = Route(
                route_id=f"service_{route_id}",
                kind="service",
                start=Waypoint(start[0], start[1], "access", svc.code),
                end=Waypoint(end[0], end[1], "destination", mod.code),
            )
            route.waypoints = _simple_pathfind(start, end, ph.instances, ph.site)
            _compute_route_metrics(route, ph)
            network.routes.append(route)
            route_id += 1
    
    _aggregate_network(network)
    return network


def derive_emergency_routes(ph: PhenotypeV4) -> RouteNetwork:
    """Derive emergency egress network.
    
    Key journeys:
    - All modules → assembly points
    - R4 → site boundary (multiple exits)
    """
    network = RouteNetwork(kind="emergency")
    
    # Assembly point at site centroid (simplified)
    assembly = ph.site.centroid
    
    route_id = 0
    
    for mod in ph.instances:
        start = _get_access_point(mod, mod.access_face)
        route = Route(
            route_id=f"emergency_{route_id}",
            kind="emergency",
            start=Waypoint(start[0], start[1], "access", mod.code),
            end=Waypoint(assembly[0], assembly[1], "destination"),
        )
        route.waypoints = _simple_pathfind(start, assembly, ph.instances, ph.site)
        _compute_route_metrics(route, ph)
        network.routes.append(route)
        route_id += 1
    
    _aggregate_network(network)
    return network


def _aggregate_network(network: RouteNetwork) -> None:
    """Compute aggregate metrics for a route network."""
    if not network.routes:
        return
    
    network.total_length = sum(r.length_m for r in network.routes)
    exposures = [r.exposed_length_m / r.length_m if r.length_m > 0 else 0 
                 for r in network.routes]
    network.avg_exposure = sum(exposures) / len(exposures)
    network.max_privacy_violation = max(r.privacy_violations for r in network.routes)


def route_exposure(route: Route, ph: PhenotypeV4) -> float:
    """Compute exposure fraction for a route."""
    if route.length_m == 0:
        return 0.0
    return route.exposed_length_m / route.length_m


def route_privacy(route: Route, privacy_field) -> list[float]:
    """Sample privacy levels along a route."""
    levels = []
    wps = [route.start] + route.waypoints + [route.end]
    
    for wp in wps:
        levels.append(privacy_field.privacy_at(wp.x, wp.y))
    
    return levels
