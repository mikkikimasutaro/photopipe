import unittest
import warnings

from warnings_config import (
    GOOGLE_PYTHON_VERSION_SUPPORT_MODULE,
    configure_warning_filters,
)


class WarningFilterTests(unittest.TestCase):
    def test_configure_warning_filters_adds_google_version_filter(self):
        configure_warning_filters()

        matches = [
            f
            for f in warnings.filters
            if f[0] == "ignore"
            and f[2] is FutureWarning
            and getattr(f[3], "pattern", None) == GOOGLE_PYTHON_VERSION_SUPPORT_MODULE
        ]
        self.assertTrue(matches, "Expected FutureWarning filter for google api_core module")


if __name__ == "__main__":
    unittest.main()
