"""API for Numerai Crypto"""

from typing import List, Dict
from numerapi import base_api
from numerapi import utils


class CryptoAPI(base_api.Api):
    """"API for Numerai Crypto"""

    def __init__(self, *args, **kwargs):
        base_api.Api.__init__(self, *args, **kwargs)
        self.tournament_id = 12

    def get_leaderboard(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get the current Numerai Crypto leaderboard with a reduced set of fields.

        Returns:
            list of dicts: each dict contains only the requested fields:
                - nmrStaked
                - rank
                - username
                - corrRep
                - mmcRep
                - return_1_day
                - return_52_weeks
                - return_13_weeks
        """
        query = '''
            query($limit: Int!
                  $offset: Int!) {
              cryptosignalsLeaderboard(limit: $limit
                            offset: $offset) {
                nmrStaked
                rank
                username
                corrRep
                mmcRep
                return_1_day
                return_52_weeks
                return_13_weeks
              }
            }
        '''
        arguments = {'limit': limit, 'offset': offset}
        data = self.raw_query(query, arguments)['data']['cryptosignalsLeaderboard']
        for item in data:
            utils.replace(item, "nmrStaked", utils.parse_float_string)
        return data
