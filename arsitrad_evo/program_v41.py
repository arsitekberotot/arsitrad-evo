"""Program composition and occupancy contracts for the V4.1 module library.

The existing V4 footprints and grammar remain the geometric base. These
records give each variant a distinct room/component composition. Component
counts are schematic design hypotheses, even where a baseline function comes
from the PA5 corpus. They are not measured as-built room schedules.
"""
from __future__ import annotations

from collections import Counter

from .modules_v4 import MODULE_LIBRARY_V4, ModularityCategory


# Counts are schematic. Components present in the canonical PA5 module receive
# PA5 functional provenance, while their proposed quantity remains a hypothesis.
_COMPOSITION: dict[str, dict[str, int]] = {
    "R4-S": {"personal_territory": 2, "wash": 1, "shared_domestic": 1, "porch": 1},
    "R4-M": {"personal_territory": 2, "wash": 2, "shared_domestic": 1, "retreat_edge": 1, "porch": 1},
    "R4-L": {"personal_territory": 3, "wash": 2, "shared_domestic": 2, "retreat_edge": 2, "porch": 2},
    "A0-S": {"screened_reception": 1, "waiting_bay": 1, "orientation_point": 1},
    "A0": {"screened_reception": 1, "waiting_bay": 2, "orientation_point": 1, "private_pause": 1},
    "B0-S": {"intake": 1, "counselling": 1},
    "B0": {"intake": 1, "counselling": 2, "safeguarding": 1, "staff_response": 1},
    "B0-L": {"intake": 2, "counselling": 2, "safeguarding": 1, "staff_response": 1, "quiet_room": 1},
    "C0-S": {"domestic_dining": 1, "shared_everyday": 1, "kitchen_interface": 1},
    "C0": {"shared_dining": 1, "shared_everyday": 2, "kitchen_interface": 1, "outdoor_commons": 1},
    "C0-L": {"shared_dining": 2, "shared_everyday": 2, "kitchen_interface": 2, "outdoor_commons": 1},
    "H0-S": {"tutorial_room": 1, "quiet_study": 1},
    "H0": {"learning_room": 1, "quiet_study": 1, "resource_store": 1},
    "H0-L": {"learning_room": 2, "quiet_study": 2, "resource_store": 1},
    "J0-S": {"craft_workshop": 1, "tool_store": 1},
    "J0": {"workshop": 1, "production_bay": 1, "market_interface": 1},
    "J0-L": {"workshop": 2, "production_bay": 2, "dedicated_store": 1, "market_interface": 1},
    "K0-S": {"neighbourhood_room": 1, "flexible_event_edge": 1},
    "K0": {"gathering_hall": 1, "event_support": 1, "community_edge": 1},
    "K0-L": {"gathering_hall": 2, "event_support": 2, "community_edge": 1},
    "I0-S": {"individual_reflection": 1, "quiet_edge": 1},
    "I0": {"reflection_room": 1, "quiet_edge": 1, "nature_interface": 1},
    "I0-L": {"communal_prayer": 1, "individual_reflection": 2, "nature_interface": 1},
    "L0": {"decompression_threshold": 1, "orientation_point": 1},
    "L0-L": {"decompression_threshold": 2, "orientation_gallery": 1, "screened_wait": 1},
    "F0": {"kitchen": 1, "food_store": 1, "service_interface": 1},
    "F0-L": {"kitchen": 2, "food_store": 2, "service_interface": 1, "staff_prep": 1},
    "M0": {"maintenance": 1, "waste_hold": 1, "utility": 1},
    "M0-L": {"maintenance": 2, "waste_hold": 1, "utility": 2, "service_yard": 1},
}

_BASELINE = {"R4-M", "A0", "B0", "C0", "H0", "J0", "K0", "I0", "L0", "F0", "M0"}
_SPECIALIZED = {"B0", "I0"}  # care/safeguarding and reflection-specific space
_PUBLIC_FAMILIES = {"A0", "B0", "C0", "H0", "J0", "K0", "I0", "L0"}


def module_record(code: str) -> dict:
    """V4.1 record with explicit function/size/modularity/composition axes."""
    m = MODULE_LIBRARY_V4[code]
    composition = _COMPOSITION[code]
    return {
        "code": code,
        "function": m.family,
        "size": m.size_class.value,
        "modularity_category": (
            "developmental" if m.modularity == ModularityCategory.REPEATABLE
            else m.modularity.value
        ),
        "repeatable": m.repeatable,
        "specialized_function": m.family in _SPECIALIZED,
        "program_composition": [
            {"component": name, "count": count,
             "function_provenance": "[PA5 CORPUS]" if code in _BASELINE else "[DESIGN HYPOTHESIS]",
             "count_provenance": "[DESIGN HYPOTHESIS]"}
            for name, count in composition.items()
        ],
        "nominal_room_capacity": m.capacity_day_users,
        "resident_capacity": m.capacity_residents,
        "nominal_staff_capacity": m.capacity_staff,
        "width_m": m.w,
        "depth_m": m.d,
        "area_m2": m.area,
        "zone": zone_for_family(m.family),
        "site_relation": "[TO VERIFY]" if m.family in {"F0", "M0"} else "[DESIGN HYPOTHESIS]",
        "provenance": m.provenance,
    }


def catalogue() -> dict:
    if set(_COMPOSITION) != set(MODULE_LIBRARY_V4):
        raise ValueError("V4.1 composition is missing or inventing module codes")
    return {code: module_record(code) for code in MODULE_LIBRARY_V4}


def zone_for_family(family: str) -> str:
    return {
        "A0": "public_civic", "K0": "public_civic",
        "B0": "controlled_care", "L0": "controlled_care",
        "C0": "shared_everyday", "H0": "shared_everyday", "J0": "shared_everyday",
        "R4": "domestic", "I0": "personal",
        "F0": "service", "M0": "service",
    }[family]


def population_summary(instances) -> dict:
    """Report function/variant populations and two independent ratios."""
    by_function = Counter(i.family for i in instances)
    by_code = Counter(i.code for i in instances)
    by_modularity = Counter(module_record(i.code)["modularity_category"] for i in instances)
    total = len(instances)
    specialized = sum(i.family in _SPECIALIZED for i in instances)
    return {
        "total": total,
        "by_function": dict(sorted(by_function.items())),
        "by_variant": dict(sorted(by_code.items())),
        "developmental_population": by_modularity.get("developmental", 0),
        "variational_population": by_modularity.get("variational", 0),
        "developmental_ratio": by_modularity.get("developmental", 0) / total if total else 0.0,
        "variational_ratio": by_modularity.get("variational", 0) / total if total else 0.0,
        "specialized_function_population": specialized,
        "specialized_function_ratio": specialized / total if total else 0.0,
        "definition": "Specialized = care/safeguarding B0 plus reflection I0; modularity ratios count units, not area.",
    }


def allocate_concurrent_occupancy(instances, requested_day_users: int) -> dict:
    """Allocate one concurrent day-user population among available rooms.

    The capacity of each room is a limit, not a different person added to the
    project population. An explicit snapshot is allocated proportionally to
    nominal capacity, with deterministic remainder assignment.
    """
    rooms = [(i.code, i.capacity_day_users) for i in instances
             if i.family in _PUBLIC_FAMILIES and i.capacity_day_users > 0]
    nominal = sum(cap for _, cap in rooms)
    alloc = [0] * len(rooms)
    remaining = min(requested_day_users, nominal)
    if nominal:
        raw = [remaining * cap / nominal for _, cap in rooms]
        alloc = [min(cap, int(x)) for x, (_, cap) in zip(raw, rooms)]
        left = remaining - sum(alloc)
        order = sorted(range(len(rooms)), key=lambda j: (raw[j] - alloc[j], rooms[j][1], -j), reverse=True)
        for j in order:
            if not left:
                break
            if alloc[j] < rooms[j][1]:
                alloc[j] += 1
                left -= 1
    by_function: dict[str, int] = {}
    for (code, _), count in zip(rooms, alloc):
        fam = MODULE_LIBRARY_V4[code].family
        by_function[fam] = by_function.get(fam, 0) + count
    return {
        "requested_concurrent_day_users": requested_day_users,
        "allocated_concurrent_day_users": sum(alloc),
        "unmet_day_users": max(0, requested_day_users - sum(alloc)),
        "nominal_room_capacity_sum": nominal,
        "by_function": by_function,
        "method": "single simultaneous snapshot allocated among enabled functions by capacity share",
        "provenance": "[DESIGN HYPOTHESIS]",
    }
