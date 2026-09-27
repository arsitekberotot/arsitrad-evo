"""Tests for the v4 canonical real-site input (site.geojson + site.yaml)."""
import unittest
from pathlib import Path

from arsitrad_evo.site import (
    SiteMode, load_canonical_site, load_site_metadata, buildable_polygon,
    anchor_point, point_in_polygon, ProvenanceTag,
)

DATA = Path(__file__).resolve().parent.parent / "data"
GEOJSON = DATA / "site.geojson"
YAML = DATA / "site.yaml"


class TestCanonicalSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not GEOJSON.exists():
            raise unittest.SkipTest("data/site.geojson not present")
        cls.site = load_canonical_site(GEOJSON, YAML)

    def test_geometry_loaded(self):
        s = self.site
        self.assertEqual(s.mode, SiteMode.GEOJSON)
        self.assertGreater(s.area_m2, 5400)
        self.assertLess(s.area_m2, 5800)
        self.assertGreater(len(s.edges), 4)   # irregular polygon, not rectangle
        self.assertGreater(s.perimeter_m, 250)

    def test_metadata_loaded_not_fabricated(self):
        s = self.site
        self.assertIn("site", s.metadata)
        self.assertEqual(s.metadata["site"]["id"], "bantargebang_threshold_site")
        # provenance flattened
        self.assertTrue(any("setbacks" in k for k in s.metadata_provenance))
        # TO VERIFY attributes stay None, never invented
        self.assertIsNone(s.metadata["frontage"]["secondary_street"]["present"])
        self.assertIsNone(s.metadata["access"]["service_entry"]["present"])

    def test_setbacks_and_frontage(self):
        s = self.site
        self.assertEqual(s.setbacks_m["front"], 4.0)
        self.assertEqual(s.setbacks_m["tpst_buffer"], 10.0)
        self.assertIn(0, s.frontage_edges)
        self.assertEqual(s.preferred_expansion_direction, "S")

    def test_buildable_polygon(self):
        bp = buildable_polygon(self.site)
        self.assertGreater(len(bp), 0)
        # buildable band centroid should lie inside the parcel
        xs = [p[0] for p in bp]; ys = [p[1] for p in bp]
        cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
        self.assertTrue(point_in_polygon((cx, cy), self.site.boundary_polygon))

    def test_anchor_point(self):
        # public entry resolves to frontage edge midpoint
        pe = anchor_point(self.site, "public_entry")
        self.assertIsNotNone(pe)
        assert pe is not None
        self.assertTrue(point_in_polygon(pe, self.site.boundary_polygon))
        # service entry not evidenced -> None (never fabricated)
        se = anchor_point(self.site, "service_entry")
        self.assertIsNone(se)

    def test_no_yaml_still_loads(self):
        s = load_canonical_site(GEOJSON, DATA / "nonexistent.yaml")
        self.assertEqual(s.metadata, {})
        # defaults still applied
        self.assertEqual(s.setbacks_m["front"], 4.0)


if __name__ == "__main__":
    unittest.main()
