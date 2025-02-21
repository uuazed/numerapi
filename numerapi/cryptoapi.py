"""API for Numerai Crypto"""

from numerapi import base_api

class CryptoAPI(base_api.Api):
    """"API for Numerai Crypto"""

    def __init__(self, *args, **kwargs):
        base_api.Api.__init__(self, *args, **kwargs)
        self.tournament_id = 12
