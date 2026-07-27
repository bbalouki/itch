"""
Nasdaq TotalView-ITCH 5.0 Parser
"""

__author__ = "Bertin Balouki SIMYELI"
__copyright__ = "2025 Bertin Balouki SIMYELI"
__email__ = "bertin@bbs-trading.com"
__license__ = "MIT"

from importlib.metadata import version, PackageNotFoundError

from itch._backend import USING_CPP_BACKEND

try:
    __version__ = version("itchfeed")
except PackageNotFoundError:
    __version__ = "unknown"

# True when the optional native `itchcpp` backend is active (see itch._backend).
__all__ = ["USING_CPP_BACKEND"]


