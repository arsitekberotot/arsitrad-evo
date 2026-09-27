"""Tests for arsitrad_evo.modules_v4 module."""
import unittest

from arsitrad_evo.modules_v4 import (
    MODULE_LIBRARY_V4, get_module, get_family_modules, SizeClass,
    allowed_rotations, ground_required_modules, domestic_modules,
    service_modules, care_modules, v3_code_to_v4, ModuleTypeV4,
    ModularityCategory, RotationPolicy
)


class TestModulesV4(unittest.TestCase):
    def test_library_populated(self):
        self.assertGreater(len(MODULE_LIBRARY_V4), 0)
        self.assertIn("R4-M", MODULE_LIBRARY_V4)
        self.assertIn("A0", MODULE_LIBRARY_V4)
    
    def test_r4_variants(self):
        r4s = get_family_modules("R4")
        self.assertEqual(len(r4s), 3)  # S, M, L
        codes = [m.code for m in r4s]
        self.assertIn("R4-S", codes)
        self.assertIn("R4-M", codes)
        self.assertIn("R4-L", codes)
    
    def test_module_properties(self):
        m = get_module("R4-M")
        self.assertEqual(m.family, "R4")
        self.assertEqual(m.size_class, SizeClass.MEDIUM)
        self.assertEqual(m.capacity_residents, 4)
        self.assertTrue(m.ground_required)
        self.assertFalse(m.stackable_above)
    
    def test_rotation_policy(self):
        m = get_module("R4-M")
        self.assertEqual(m.rotation_policy, RotationPolicy.ORTHOGONAL)
        self.assertIn(0, m.allowed_rotations)
        self.assertIn(90, m.allowed_rotations)
        
        w, d = m.rotated_dimensions(0)
        self.assertEqual((w, d), (m.w, m.d))
        
        w, d = m.rotated_dimensions(90)
        self.assertEqual((w, d), (m.d, m.w))
    
    def test_grammar_attached(self):
        m = get_module("R4-M")
        self.assertIsNotNone(m.grammar)
        self.assertIn("entry", m.grammar.description.lower())
    
    def test_queries(self):
        self.assertGreater(len(ground_required_modules()), 0)
        self.assertGreater(len(domestic_modules()), 0)
        self.assertGreater(len(service_modules()), 0)
        self.assertGreater(len(care_modules()), 0)
    
    def test_v3_compat(self):
        self.assertEqual(v3_code_to_v4("R4"), "R4-M")
        self.assertEqual(v3_code_to_v4("A0"), "A0")


if __name__ == "__main__":
    unittest.main()
