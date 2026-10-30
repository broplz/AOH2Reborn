"""vanilla_diff.dead_refs on a fixture: python3 tests/test_vanilla_diff.py"""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kvlib as kv  # noqa: E402
import vanilla_diff as vd  # noqa: E402

FIXTURE = os.path.join(ROOT, "tools", "fixtures", "vanilla_diff", "npc_units_custom.txt")


class DeadRefs(unittest.TestCase):
    def test_reports_only_the_dead_name(self):
        root, _ = kv.parse_file(FIXTURE)
        fails = vd.dead_refs("npc_units_custom.txt", kv.entries(root), {"live_ability"})
        self.assertEqual(fails, [
            "npc_units_custom.txt npc_fixture_unit: LinkedAbility dead_ability is defined neither in vanilla nor in our KV",
        ])


if __name__ == "__main__":
    unittest.main()
