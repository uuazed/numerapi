""" Numerai Python API"""

import pkg_resources

try:
    __version__ = pkg_resources.get_distribution(__name__).version
except pkg_resources.DistributionNotFound:
    __version__ = 'unknown'


# pylint: disable=wrong-import-position
from numerapi.numerapi import NumerAPI
from numerapi.signalsapi import SignalsAPI
# pylint: enable=wrong-import-position
