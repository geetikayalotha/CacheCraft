import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cachecraft.config import default_config  # noqa: E402
from cachecraft.strategy import available  # noqa: E402


class DefaultConfigTests(unittest.TestCase):
    def test_every_available_strategy_is_compared(self):
        cfg = default_config()
        kinds = [spec.kind for spec in cfg.strategies]
        self.assertEqual(sorted(kinds), sorted(available()))

    def test_every_strategy_builds(self):
        for spec in default_config().strategies:
            self.assertIsNotNone(spec.build())


if __name__ == "__main__":
    unittest.main()
