"""vanilla_diff checks on fixtures: python3 tests/test_vanilla_diff.py"""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kvlib as kv  # noqa: E402
import vanilla_diff as vd  # noqa: E402

FIXTURES = os.path.join(ROOT, "tools", "fixtures", "vanilla_diff")


def fixture(name):
    root, _ = kv.parse_file(os.path.join(FIXTURES, name))
    return kv.entries(root)


class DeadRefs(unittest.TestCase):
    def test_reports_only_the_dead_name(self):
        fails = vd.dead_refs("npc_units_custom.txt", fixture("npc_units_custom.txt"), {"live_ability"})
        self.assertEqual(fails, [
            "npc_units_custom.txt npc_fixture_unit: LinkedAbility dead_ability is defined neither in vanilla nor in our KV",
        ])


class DeadOverrides(unittest.TestCase):
    def test_reports_only_the_removed_key(self):
        name = "npc_abilities_override.txt"
        fails = vd.dead_overrides(name, fixture(name), {"live_ability"})
        self.assertEqual(fails, [f"{name} removed_talent: overridden name is not defined in vanilla"])


if __name__ == "__main__":
    unittest.main()
