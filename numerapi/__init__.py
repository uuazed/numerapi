""" Numerai Python API"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("package-name")
except PackageNotFoundError:
    __version__ = 'unknown'


# pylint: disable=wrong-import-position
from numerapi.numerapi import NumerAPI
from numerapi.signalsapi import SignalsAPI
from numerapi.cryptoapi import CryptoAPI
# pylint: enable=wrong-import-position


__all__ = ["NumerAPI", "SignalsAPI", "CryptoAPI"]
