from typing import List, Dict

from numerapi import base_api
from numerapi import utils


class QuantAPI(base_api.Api):

    def get_leaderboard(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get the current numerai–quant leaderboard
        Args:
            limit (int): number of items to return (optional, defaults to 50)
            offset (int): number of items to skip (optional, defaults to 0)
        Returns:
            list of dicts: list of leaderboard entries
            Each dict contains the following items:
                * username (`str`)
                * sharpe (`float`)
                * rank (`int`)
                * prevRank (`int`)
                * today (`float`)
        Example:
            >>> numerapi.QuantAPI().get_leaderboard(1)
            [{'prevRank': 1,
              'rank': 1,
              'sharpe': 2.3,
              'today': 0.01321,
              'username': 'floury_kerril_moodle'}]
        """
        query = '''
            query($limit: Int!
                  $offset: Int!) {
              quantLeaderboard(limit: $limit
                            offset: $offset) {
                prevRank
                rank
                sharpe
                today
                username
              }
            }
        '''

        arguments = {'limit': limit, 'offset': offset}
        data = self.raw_query(query, arguments)['data']['quantLeaderboard']
        return data

    def upload_predictions(self, file_path: str, model_id: str = None) -> str:
        """Upload predictions from file.

        Args:
            file_path (str): CSV file with predictions that will get uploaded
            model_id (str): Target model UUID (required for accounts
                            with multiple models)

        Returns:
            str: submission_id

        Example:
            >>> api = QuantAPI(secret_key="..", public_id="..")
            >>> model_id = api.get_models()['uuazed']
            >>> api.upload_predictions("prediction.cvs", model_id=model_id)
            '93c46857-fed9-4594-981e-82db2b358daf'
        """
        self.logger.info("uploading predictions...")

        auth_query = '''
            query($filename: String!
                  $modelId: String) {
              submissionUploadQuantAuth(filename: $filename
                                        modelId: $modelId) {
                    filename
                    url
                }
            }
            '''
        arguments = {'filename': os.path.basename(file_path),
                     'modelId': model_id}
        submission_resp = self.raw_query(auth_query, arguments,
                                         authorization=True)
        auth = submission_resp['data']['submission_upload_quant_auth']
        with open(file_path, 'rb') as fh:
            requests.put(auth['url'], data=fh.read())
        create_query = '''
            mutation($filename: String!
                     $modelId: String) {
                createQuantSubmission(filename: $filename
                                  tournament: $tournament
                                  modelId: $modelId) {
                    id
                    firstEffectiveDate
                }
            }
            '''
        arguments = {'filename': auth['filename'], 'modelId': model_id}
        create = self.raw_query(create_query, arguments, authorization=True)
        self.submission_id = create['data']['create_quant_submission']['id']
        return self.submission_id

    def public_user_profile(self, username: str) -> Dict:
        """Fetch the public quant profile of a user.

        Args:
            username (str)

        Returns:
            dict: user profile including the following fields:

                * username (`str`)
                * startDate (`datetime`)
                * id (`string`)
                * rank (`int`)
                * bio (`str`)
                * sharpe (`float`)

        Example:
            >>> api = QuantAPI()
            >>> api.public_user_profile("floury_kerril_moodle")
            {'bio': None,
             'id': '635db2a4-bdc6-4e5d-b515-f5120392c8c9',
             'rank': 1,
             'sharpe': 2.35,
             'startDate': datetime.datetime(2019, 3, 26, 0, 43),
             'username': 'floury_kerril_moodle'}

        """
        query = """
          query($username: String!) {
            quantUserProfile(username: $username) {
              rank
              id
              startDate
              username
              bio
              sharpe
            }
          }
        """
        arguments = {'username': username}
        data = self.raw_query(query, arguments)['data']['quantUserProfile']
        # convert strings to python objects
        utils.replace(data, "startDate", utils.parse_datetime_string)
        return data
