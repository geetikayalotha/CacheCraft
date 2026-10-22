import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cachecraft.config import ConfigError, default_config, parse_config  # noqa: E402


class ConfigValidationTests(unittest.TestCase):
    def test_default_config_builds_every_strategy(self):
        cfg = default_config()
        self.assertTrue(cfg.strategies)
        self.assertEqual(len(cfg.build_all()), len(cfg.strategies))

    def test_hit_cost_must_be_finite_and_positive(self):
        for bad in (None, "NaN", float("inf"), -1, "x"):
            with self.assertRaises(ConfigError) as ctx:
                parse_config({"strategies": [{"kind": "exact"}], "hit_cost_ms": bad})
            self.assertIn("hit_cost_ms", str(ctx.exception))

    def test_unknown_kind_names_the_accepted_set(self):
        with self.assertRaises(ConfigError) as ctx:
            parse_config({"strategies": [{"kind": "exat"}]})
        self.assertIn("exact", str(ctx.exception))

    def test_params_must_be_a_mapping(self):
        with self.assertRaises(ConfigError) as ctx:
            parse_config({"strategies": [{"kind": "exact", "params": []}]})
        self.assertIn("strategies[0]", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
