"""Run regression tests in the LNbits runtime; zero tests is a failure."""

import sys
import unittest
from pathlib import Path

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent / "unit"))
    if suite.countTestCases() == 0:
        sys.exit("No regression tests discovered")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
