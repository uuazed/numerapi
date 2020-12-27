import pkg_resources

try:
    __version__ = pkg_resources.get_distribution(__name__).version
except pkg_resources.DistributionNotFound:
    __version__ = 'unknown'


from numerapi.numerapi import NumerAPI  # noqa
from numerapi.signalsapi import SignalsAPI  # noqa
