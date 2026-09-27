"""Spatial analysis v4 — privacy fields, enclosure, light, sightlines.

Extends v3's simple module-level privacy with spatial gradients, real
enclosure analysis, and geometric sightline casting.

Provenance: [DESIGN HYPOTHESIS] for all spatial derivations.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .site import Site, point_in_polygon, nearest_edge
from .genotype_v4 import PhenotypeV4, InstanceV4


@dataclass
class PrivacyField:
    """Grid-based privacy gradient across the site."""
    grid: np.ndarray           # 2D array of privacy levels (0-4)
    resolution: float          # metres per cell
    site_width: float
    site_height: float
    
    def privacy_at(self, x: float, y: float) -> float:
        """Get privacy level at a point."""
        i = int(y / self.resolution)
        j = int(x / self.resolution)
        if 0 <= i < self.grid.shape[0] and 0 <= j < self.grid.shape[1]:
            return float(self.grid[i, j])
        return 0.0
    
    def gradient_at(self, x: float, y: float) -> tuple[float, float]:
        """Get privacy gradient direction."""
        i = int(y / self.resolution)
        j = int(x / self.resolution)
        if 1 <= i < self.grid.shape[0]-1 and 1 <= j < self.grid.shape[1]-1:
            dx = float(self.grid[i, j+1] - self.grid[i, j-1]) / (2 * self.resolution)
            dy = float(self.grid[i+1, j] - self.grid[i-1, j]) / (2 * self.resolution)
            return (dx, dy)
        return (0.0, 0.0)


@dataclass
class EnclosureAnalysis:
    """Enclosure analysis for an open space."""
    space_id: str
    enclosure_ratio: float      # 0.0 = open, 1.0 = fully enclosed
    enclosure_sides: int        # 0-4
    sky_view_factor: float      # approximate
    adjacent_modules: list[str] # module codes
    space_type: str             # COURTYARD, POCKET_COURT, THRESHOLD_EDGE, OPEN_LANDSCAPE
    provenance: str = "[DESIGN HYPOTHESIS]"


@dataclass
class LightAccess:
    """Approximate daylight potential."""
    point: tuple[float, float]
    unobstructed_sky: float     # 0-1
    shadow_length: float        # metres
    orientation: str            # N, S, E, W
    light_score: float          # composite 0-1
    provenance: str = "[DESIGN HYPOTHESIS]"


@dataclass
class SightlineV4:
    """A sightline with occlusion analysis."""
    observer: tuple[float, float, float]   # x, y, height
    target: tuple[float, float, float]     # x, y, height
    exposed: bool
    occluding_modules: list[str] # module codes that block
    length_m: float
    privacy_violation: bool
    provenance: str = "[DESIGN HYPOTHESIS]"


def compute_privacy_field(ph: PhenotypeV4, resolution: float = 2.0) -> PrivacyField:
    """Compute a spatial privacy gradient across the site.
    
    Factors:
    - Module privacy levels (higher = more private)
    - Distance to module edges
    - Distance to site boundary
    - Sightline exposure
    """
    site = ph.site
    w = int(site.width_m / resolution) + 1
    h = int(site.height_m / resolution) + 1
    grid = np.zeros((h, w))
    
    # Base privacy from modules
    for inst in ph.instances:
        # Module bounds
        x0 = inst.x - inst.w / 2
        x1 = inst.x + inst.w / 2
        y0 = inst.y - inst.d / 2
        y1 = inst.y + inst.d / 2
        
        # Module privacy level
        priv = inst.privacy_level
        
        # Fill grid cells within module
        i0 = max(0, int(y0 / resolution))
        i1 = min(h, int(y1 / resolution) + 1)
        j0 = max(0, int(x0 / resolution))
        j1 = min(w, int(x1 / resolution) + 1)
        
        for i in range(i0, i1):
            for j in range(j0, j1):
                grid[i, j] = max(grid[i, j], priv)
    
    # Distance decay: privacy increases with distance from public modules
    public_modules = [i for i in ph.instances if i.privacy_level <= 1]
    for inst in public_modules:
        x0 = inst.x - inst.w / 2
        x1 = inst.x + inst.w / 2
        y0 = inst.y - inst.d / 2
        y1 = inst.y + inst.d / 2
        
        for i in range(h):
            for j in range(w):
                cx = j * resolution + resolution / 2
                cy = i * resolution + resolution / 2
                
                # Distance to module edge
                dx = max(x0 - cx, 0, cx - x1)
                dy = max(y0 - cy, 0, cy - y1)
                dist = math.sqrt(dx*dx + dy*dy)
                
                # Privacy increases with distance (up to 10m)
                boost = min(dist / 10.0, 1.0) * 2.0
                grid[i, j] = min(4.0, grid[i, j] + boost)
    
    # Boundary effect: edges near boundary are more public
    for i in range(h):
        for j in range(w):
            cx = j * resolution + resolution / 2
            cy = i * resolution + resolution / 2
            _, dist = nearest_edge((cx, cy), site.boundary_polygon)
            if dist < 5.0:
                grid[i, j] = max(0.0, grid[i, j] - 1.0)
    
    return PrivacyField(
        grid=grid, resolution=resolution,
        site_width=site.width_m, site_height=site.height_m
    )


def compute_enclosure(space_center: tuple[float, float], 
                      space_radius: float,
                      modules: list[InstanceV4]) -> EnclosureAnalysis:
    """Compute enclosure ratio for an open space.
    
    Casts rays in 4 cardinal directions and checks for module occlusion.
    """
    cx, cy = space_center
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # N, E, S, W
    enclosed_sides = 0
    adjacent = []
    
    for dx, dy in directions:
        # Cast ray
        ray_len = 0.0
        max_len = space_radius * 3
        step = 0.5
        
        while ray_len < max_len:
            px = cx + dx * ray_len
            py = cy + dy * ray_len
            
            # Check if inside any module
            for inst in modules:
                x0 = inst.x - inst.w / 2
                x1 = inst.x + inst.w / 2
                y0 = inst.y - inst.d / 2
                y1 = inst.y + inst.d / 2
                
                if x0 <= px <= x1 and y0 <= py <= y1:
                    enclosed_sides += 1
                    adjacent.append(inst.code)
                    ray_len = max_len  # stop
                    break
            else:
                ray_len += step
                continue
            break
    
    ratio = enclosed_sides / 4.0
    
    # Classify
    if enclosed_sides >= 3:
        stype = "COURTYARD"
    elif enclosed_sides == 2:
        stype = "POCKET_COURT"
    elif enclosed_sides == 1:
        stype = "THRESHOLD_EDGE"
    else:
        stype = "OPEN_LANDSCAPE"
    
    # Sky view factor (simplified)
    svf = 1.0 - (enclosed_sides * 0.2)
    
    return EnclosureAnalysis(
        space_id=f"space_{cx:.0f}_{cy:.0f}",
        enclosure_ratio=ratio,
        enclosure_sides=enclosed_sides,
        sky_view_factor=svf,
        adjacent_modules=adjacent,
        space_type=stype,
    )


def compute_light_access(point: tuple[float, float],
                         modules: list[InstanceV4],
                         site: Site) -> LightAccess:
    """Approximate daylight access at a point.
    
    Simplified: checks for shadows cast by modules to the north
    (assuming northern hemisphere sun from south).
    """
    x, y = point
    
    # Check for modules to the south (casting shadows north)
    shadow_length = 0.0
    for inst in modules:
        # Module to the south?
        if inst.y < y:
            dist = y - inst.y
            # Shadow length ~ module height * cot(sun_angle)
            # Simplified: assume 45° sun, shadow = height
            shadow = inst.d  # rough proxy
            if dist < shadow:
                shadow_length = max(shadow_length, shadow - dist)
    
    unobstructed = 1.0 - min(shadow_length / 10.0, 1.0)
    
    # Orientation score (south-facing is best in northern hemisphere)
    _, edge_dist = nearest_edge(point, site.boundary_polygon)
    orientation = "S"  # simplified
    
    # Composite score
    score = unobstructed * 0.7 + (1.0 if orientation == "S" else 0.5) * 0.3
    
    return LightAccess(
        point=point,
        unobstructed_sky=unobstructed,
        shadow_length=shadow_length,
        orientation=orientation,
        light_score=score,
    )


def cast_sightline(observer: tuple[float, float, float],
                   target: tuple[float, float, float],
                   modules: list[InstanceV4]) -> SightlineV4:
    """Cast a sightline and check for module occlusion.
    
    Simple 2D line-of-sight with module rectangles as occluders.
    """
    ox, oy, oh = observer
    tx, ty, th = target
    
    # Line parametric: P = O + t*(T-O), t in [0,1]
    dx = tx - ox
    dy = ty - oy
    length = math.sqrt(dx*dx + dy*dy)
    
    if length == 0:
        return SightlineV4(
            observer=observer, target=target,
            exposed=False, occluding_modules=[], length_m=0.0,
            privacy_violation=False,
        )
    
    occluders = []
    
    for inst in modules:
        # Module rectangle
        x0 = inst.x - inst.w / 2
        x1 = inst.x + inst.w / 2
        y0 = inst.y - inst.d / 2
        y1 = inst.y + inst.d / 2
        
        # Check if line intersects rectangle
        # Using Liang-Barsky algorithm (simplified)
        t0, t1 = 0.0, 1.0
        
        # X clipping
        if dx == 0:
            if ox < x0 or ox > x1:
                continue
        else:
            t_x0 = (x0 - ox) / dx
            t_x1 = (x1 - ox) / dx
            t0 = max(t0, min(t_x0, t_x1))
            t1 = min(t1, max(t_x0, t_x1))
        
        # Y clipping
        if dy == 0:
            if oy < y0 or oy > y1:
                continue
        else:
            t_y0 = (y0 - oy) / dy
            t_y1 = (y1 - oy) / dy
            t0 = max(t0, min(t_y0, t_y1))
            t1 = min(t1, max(t_y0, t_y1))
        
        if t0 < t1 and t0 < 1.0 and t1 > 0.0:
            # Intersection within line segment
            occluders.append(inst.code)
    
    exposed = len(occluders) == 0
    
    # Privacy violation: sightline into domestic/personal space
    privacy_violation = False
    if exposed:
        for inst in modules:
            if inst.privacy_level >= 3:
                # Check if target is inside this module
                x0 = inst.x - inst.w / 2
                x1 = inst.x + inst.w / 2
                y0 = inst.y - inst.d / 2
                y1 = inst.y + inst.d / 2
                if x0 <= tx <= x1 and y0 <= ty <= y1:
                    privacy_violation = True
                    break
    
    return SightlineV4(
        observer=observer, target=target,
        exposed=exposed, occluding_modules=occluders,
        length_m=length, privacy_violation=privacy_violation,
    )


def compute_exposure_grid(ph: PhenotypeV4, 
                          resolution: float = 5.0) -> np.ndarray:
    """Compute visual exposure across the site.
    
    For each open grid cell, count sightlines from public modules.
    """
    site = ph.site
    w = int(site.width_m / resolution) + 1
    h = int(site.height_m / resolution) + 1
    grid = np.zeros((h, w))
    
    # Public modules as observers
    public_mods = [i for i in ph.instances if i.privacy_level <= 1]
    
    for i in range(h):
        for j in range(w):
            cx = j * resolution + resolution / 2
            cy = i * resolution + resolution / 2
            
            # Skip if inside a module
            inside = False
            for inst in ph.instances:
                x0 = inst.x - inst.w / 2
                x1 = inst.x + inst.w / 2
                y0 = inst.y - inst.d / 2
                y1 = inst.y + inst.d / 2
                if x0 <= cx <= x1 and y0 <= cy <= y1:
                    inside = True
                    break
            
            if inside:
                grid[i, j] = -1  # N/A
                continue
            
            # Count sightlines from public modules
            exposure = 0
            for pub in public_mods:
                sl = cast_sightline(
                    (pub.x, pub.y, 1.5),
                    (cx, cy, 1.5),
                    ph.instances
                )
                if sl.exposed:
                    exposure += 1
            
            grid[i, j] = exposure
    
    return grid
