"""Pytest configuration for the itchfeed test-suite.

These tests exercise the pure-Python parser and message internals (struct formats,
``__new__``-based construction, etc.), so the optional native ``itchcpp`` backend is
disabled here even if it happens to be installed in the environment. Set
``ITCH_NO_CPP`` before pytest imports ``itch`` so the selection in ``itch._backend``
resolves to the pure implementation.
"""

import os

os.environ["ITCH_NO_CPP"] = "1"
