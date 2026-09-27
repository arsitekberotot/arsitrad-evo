"""Tests for arsitrad_evo.genotype_v4 module."""
import unittest
import numpy as np

from arsitrad_evo.site import create_legacy_site, SiteMode
from arsitrad_evo.genotype_v4 import (
    gene_bounds_v4, random_genome_v4, decode_v4, decode_v3_compat,
    N_GENES_V4, PhenotypeV4, InstanceV4, validate_placement_v4
)


class TestGenotypeV4(unittest.TestCase):
    def setUp(self):
        self.site = create_legacy_site()
        self.rng = np.random.default_rng(42)
    
    def test_gene_bounds(self):
        lo, hi, is_int = gene_bounds_v4(self.site)
        self.assertEqual(len(lo), N_GENES_V4)
        self.assertEqual(len(hi), N_GENES_V4)
        self.assertEqual(len(is_int), N_GENES_V4)
        self.assertTrue(np.all(lo <= hi))
    
    def test_random_genome(self):
        genes = random_genome_v4(self.rng, self.site)
        self.assertEqual(len(genes), N_GENES_V4)
        lo, hi, _ = gene_bounds_v4(self.site)
        self.assertTrue(np.all(genes >= lo))
        self.assertTrue(np.all(genes <= hi))
    
    def test_decode(self):
        genes = random_genome_v4(self.rng, self.site)
        ph = decode_v4(genes, self.site, "test", 0)
        
        self.assertIsInstance(ph, PhenotypeV4)
        self.assertEqual(ph.site, self.site)
        self.assertGreaterEqual(len(ph.instances), 0)
        
        for inst in ph.instances:
            self.assertIsInstance(inst, InstanceV4)
            self.assertGreaterEqual(inst.x, 0)
            self.assertGreaterEqual(inst.y, 0)
            self.assertLessEqual(inst.x, self.site.width_m)
            self.assertLessEqual(inst.y, self.site.height_m)
    
    def test_metrics_computed(self):
        genes = random_genome_v4(self.rng, self.site)
        ph = decode_v4(genes, self.site, "test", 0)
        
        self.assertGreaterEqual(ph.gfa, 0)
        self.assertGreaterEqual(ph.footprint, 0)
        self.assertGreaterEqual(ph.landscape_frac, 0)
        self.assertLessEqual(ph.landscape_frac, 1)
        self.assertGreaterEqual(ph.floor_count, 1)
    
    def test_phases(self):
        genes = random_genome_v4(self.rng, self.site)
        ph = decode_v4(genes, self.site, "test", 0)
        
        self.assertGreaterEqual(len(ph.phases), 1)
        for phase in ph.phases:
            self.assertIn("phase", phase)
            self.assertIn("modules", phase)
            self.assertIn("gfa", phase)
    
    def test_validate_placement(self):
        genes = random_genome_v4(self.rng, self.site)
        ph = decode_v4(genes, self.site, "test", 0)
        
        if ph.instances:
            result = validate_placement_v4(ph.instances[0], self.site)
            self.assertIn("valid", result)
            self.assertIn("issues", result)
    
    def test_v3_compat(self):
        # Create a short v3-length genome
        v3_genes = np.random.rand(60)  # v3 was shorter
        ph = decode_v3_compat(v3_genes, self.site, "v3_test", 0)
        self.assertIsInstance(ph, PhenotypeV4)


if __name__ == "__main__":
    unittest.main()
