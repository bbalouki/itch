"""
Nasdaq TotalView-ITCH 5.0 Parser
"""

__author__ = "Bertin Balouki SIMYELI"
__copyright__ = "2025 Bertin Balouki SIMYELI"
__email__ = "bertin@bbstrader.com"
__license__ = "MIT"

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("itchfeed")
except PackageNotFoundError:
    __version__ = "unknown"


