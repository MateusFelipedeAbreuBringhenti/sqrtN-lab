import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_results import describe, percentile


class AnalysisTests(unittest.TestCase):
    def test_percentiles(self):
        self.assertEqual(percentile([1.0], 0.99), 1.0)
        self.assertEqual(percentile([1.0, 3.0], 0.5), 2.0)

    def test_describe(self):
        result = describe([1.0, 2.0, 3.0])
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["mean"], 2.0)
        self.assertEqual(result["minimum"], 1.0)
        self.assertEqual(result["maximum"], 3.0)


if __name__ == "__main__":
    unittest.main()
