from __future__ import annotations

import warnings

GOOGLE_PYTHON_VERSION_SUPPORT_MODULE = r"google\.api_core\._python_version_support"


def configure_warning_filters() -> None:
    warnings.filterwarnings(
        "ignore",
        category=FutureWarning,
        module=GOOGLE_PYTHON_VERSION_SUPPORT_MODULE,
    )
