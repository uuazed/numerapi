from __future__ import absolute_import
import pkg_resources
import logging

try:
    __version__ = pkg_resources.get_distribution(__name__).version
except:
    __version__ = 'unknown'


from numerapi.numerapi import NumerAPI

logging.getLogger(__name__).addHandler(logging.NullHandler())
