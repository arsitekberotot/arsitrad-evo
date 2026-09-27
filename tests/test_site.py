"""Tests for arsitrad_evo.site module."""
import unittest
import tempfile
import json
import os

from arsitrad_evo.site import (
    SiteMode, create_legacy_site, load_site, point_in_polygon,
    nearest_edge, edge_classification, ProvenanceTag, Annotation
)


class TestSite(unittest.TestCase):
    def test_legacy_site(self):
        site = create_legacy_site()
        self.assertEqual(site.mode, SiteMode.LEGACY_RECT)
        self.assertEqual(site.width_m, 90.0)
        self.assertEqual(site.height_m, 61.5)
        self.assertAlmostEqual(site.area_m2, 5535.0)
        self.assertEqual(len(site.edges), 4)
    
    def test_point_in_polygon(self):
        site = create_legacy_site()
        # Center should be inside
        self.assertTrue(point_in_polygon((45, 30), site.boundary_polygon))
        # Corner should be on boundary (implementation dependent)
        # Outside should be outside
        self.assertFalse(point_in_polygon((100, 100), site.boundary_polygon))
        self.assertFalse(point_in_polygon((-1, -1), site.boundary_polygon))
    
    def test_nearest_edge(self):
        site = create_legacy_site()
        idx, dist = nearest_edge((45, 30), site.boundary_polygon)
        self.assertGreaterEqual(dist, 0)
        self.assertLess(dist, 50)  # should be reasonably close
    
    def test_edge_classification(self):
        site = create_legacy_site()
        classes = edge_classification(site.boundary_polygon)
        self.assertIn("N", classes)
        self.assertIn("S", classes)
        self.assertIn("E", classes)
        self.assertIn("W", classes)
    
    def test_load_geojson(self):
        # Create a temporary GeoJSON file
        geojson = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]
                }
            }]
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False) as f:
            json.dump(geojson, f)
            path = f.name
        
        try:
            site = load_site(path)
            self.assertEqual(site.mode, SiteMode.GEOJSON)
            self.assertGreater(site.area_m2, 0)
        finally:
            os.unlink(path)
    
    def test_annotation_schema(self):
        ann = Annotation(
            feature_type="frontage",
            geometry={"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
            provenance=ProvenanceTag.DESIGN_HYPOTHESIS,
            verified=False,
            notes="Test annotation"
        )
        self.assertEqual(ann.feature_type, "frontage")
        self.assertFalse(ann.verified)


if __name__ == "__main__":
    unittest.main()
