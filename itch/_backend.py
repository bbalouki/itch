"""Optional native (C++) backend selection.

When the `itchcpp <https://pypi.org/project/itchcpp/>`_ package is installed,
``itch.parser`` and ``itch.messages`` transparently use it instead of the
pure-Python implementation. ``itchcpp`` mirrors this package's public API (the same
message classes, attributes, ``MarketMessage`` helpers, ``MessageParser`` semantics,
``create_message``, ``messages`` registry and ``AllMessages``) but parses in C++ at
gigabytes per second, so existing code keeps working unchanged while running much
faster.

Set the environment variable ``ITCH_NO_CPP=1`` to force the pure-Python
implementation (this package's own test-suite does so to exercise the Python code).
"""

import os


def cpp_backend_enabled() -> bool:
    """Return True when the native ``itchcpp`` backend should be used."""
    if os.environ.get("ITCH_NO_CPP"):
        return False
    try:
        import itchcpp  # noqa: F401
    except ImportError:
        return False
    return True


# Resolved once at import time. Read it as ``itch.USING_CPP_BACKEND``.
USING_CPP_BACKEND = cpp_backend_enabled()
