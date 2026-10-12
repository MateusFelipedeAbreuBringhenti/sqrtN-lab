import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from canonical_config import config_hash, semantic_config


class CanonicalConfigTests(unittest.TestCase):
    def test_key_order_does_not_change_hash(self):
        self.assertEqual(config_hash({"b": 2, "a": 1}), config_hash({"a": 1, "b": 2}))

    def test_nonsemantic_fields_do_not_change_hash(self):
        base = {"mode": "smoke", "cases": [{"bits": 20}]}
        decorated = dict(
            base,
            experiment_id="different",
            generated_at="tomorrow",
            config_hash_algorithm="sha256",
        )
        self.assertEqual(config_hash(base), config_hash(decorated))

    def test_all_modes_disable_external_targets(self):
        for path in (ROOT / "modes").glob("*.json"):
            config = json.loads(path.read_text())
            self.assertFalse(config["accept_external_targets"])
            self.assertEqual(config["target_origin"], "locally_generated_synthetic")
            self.assertFalse(config["store_private_keys"])

    def test_semantic_config_removes_nested_telemetry(self):
        value = {"fixed": 1, "nested": {"telemetry": {"temp": 80}, "dp": 10}}
        self.assertEqual(semantic_config(value), {"fixed": 1, "nested": {"dp": 10}})


if __name__ == "__main__":
    unittest.main()
