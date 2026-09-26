"""arsitrad-evo — AI-native evolutionary spatial programming for The Threshold."""
from . import (config, modules, genotype, constraints, objectives, nsga2,
               clustering, analyze, visualize)

__all__ = ["config", "modules", "genotype", "constraints", "objectives",
           "nsga2", "clustering", "analyze", "visualize"]
__version__ = "0.2.0"
