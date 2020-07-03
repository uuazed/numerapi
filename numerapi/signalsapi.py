from typing import List, Dict
import os
import csv
import codecs

import requests

from numerapi import base_api
from numerapi import utils


class SignalsAPI(base_api.Api):

    def get_leaderboard(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get the current Numerai Signals leaderboard
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
            >>> numerapi.SignalsAPI().get_leaderboard(1)
            [{'prevRank': 1,
              'rank': 1,
              'sharpe': 2.3,
              'today': 0.01321,
              'username': 'floury_kerril_moodle'}]
        """
        query = '''
            query($limit: Int!
                  $offset: Int!) {
              signalsLeaderboard(limit: $limit
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
        data = self.raw_query(query, arguments)['data']['signalsLeaderboard']
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
            >>> api = SignalsAPI(secret_key="..", public_id="..")
            >>> model_id = api.get_models()['uuazed']
            >>> api.upload_predictions("prediction.cvs", model_id=model_id)
            '93c46857-fed9-4594-981e-82db2b358daf'
        """
        self.logger.info("uploading predictions...")

        auth_query = '''
            query($filename: String!
                  $modelId: String) {
              submissionUploadSignalsAuth(filename: $filename
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
        auth = submission_resp['data']['submissionUploadSignalsAuth']
        with open(file_path, 'rb') as fh:
            requests.put(auth['url'], data=fh.read())
        create_query = '''
            mutation($filename: String!
                     $modelId: String) {
                createSignalsSubmission(filename: $filename
                                  modelId: $modelId) {
                    id
                    firstEffectiveDate
                }
            }
            '''
        arguments = {'filename': auth['filename'], 'modelId': model_id}
        create = self.raw_query(create_query, arguments, authorization=True)
        return create['data']['createSignalsSubmission']['id']

    def submission_status(self, model_id: str = None) -> Dict:
        """submission status of the last submission associated with the account

        Args:
            model_id (str)

        Returns:
            dict: submission status with the following content:

                * firstEffectiveDate (`datetime.datetime`):
                * userId (`string`)
                * filename (`string`)
                * id (`string`)
                * submissionIp (`string`)
                * submittedCount (`int`)
                * filteredCount (`int`)

        Example:
            >>> api = SignalsAPI(secret_key="..", public_id="..")
            >>> model_id = api.get_models()['uuazed']
            >>> api.submission_status(model_id)
            {'firstEffectiveDate': datetime.datetime(2020, 5, 12, 1, 23),
             'userId': "slyfox",
             'filename': 'model57-HPzOyr56TPaD.csv',
             'id': '1234'
             'submissionIp': "102.142.12.12",
             'submittedCount': 112,
             'filteredCount': 12}
        """

        query = '''
            query($modelId: String) {
                  account {
                    models(modelId: $modelId) {
                      latestSignalsSubmission {
                        id
                        filename
                        firstEffectiveDate
                        userId
                        submissionIp
                        submittedCount
                        filteredCount
                        }
                     }
                  }
            '''
        arguments = {'modelId': model_id}
        data = self.raw_query(query, arguments, authorization=True)
        status = data['data']['account']['models']['latestSignalsSubmission']
        return status

    def public_user_profile(self, username: str) -> Dict:
        """Fetch the public Numerai Signals profile of a user.

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
            >>> api = SignalsAPI()
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
            signalsUserProfile(username: $username) {
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
        data = self.raw_query(query, arguments)['data']['signalsUserProfile']
        # convert strings to python objects
        utils.replace(data, "startDate", utils.parse_datetime_string)
        return data

    def daily_user_performances(self, username: str) -> List[Dict]:
        """Fetch daily Numerai Signals performance of a user.

        Args:
            username (str)

        Returns:
            list of dicts: list of daily user performance entries

            For each entry in the list, there is a dict with the following
            content:

                * rank (`int`)
                * date (`datetime`)
                * sharpe (`float`)

        Example:
            >>> api = SignalsAPI()
            >>> api.daily_user_performances("floury_kerril_moodle")
            [{'date': datetime.datetime(2020, 5, 16, 0, 0,
              'rank': 1,
              'sharpe': 2.35},
             ...]
        """
        query = """
          query($username: String!) {
            signalsUserProfile(username: $username) {
              dailyUserPerformances {
                rank
                date
                sharpe
              }
            }
          }
        """
        arguments = {'username': username}
        data = self.raw_query(query, arguments)['data']['signalsUserProfile']
        performances = data['dailyUserPerformances']
        # convert strings to python objects
        for perf in performances:
            utils.replace(perf, "date", utils.parse_datetime_string)
        return performances

    def daily_submissions_performances(self, username: str) -> List[Dict]:
        """Fetch daily Numerai Signals performance of a user's submissions.

        Args:
            username (str)

        Returns:
            list of dicts: list of daily submission performance entries

            For each entry in the list, there is a dict with the following
            content:

                * date (`datetime`)
                * returns (`float`)
                * submission_time (`datetime`)

        Example:
            >>> api = SignalsAPI()
            >>> api.daily_submissions_performances("floury_kerril_moodle")
            [{'date': datetime.datetime(2020, 5, 16, 0, 0),
              'returns': 1.256,
              'submissionTime': datetime.datetime(2020, 5, 12, 1, 23)},
             ...
        """
        query = """
          query($username: String!) {
            signalsUserProfile(username: $username) {
              dailySubmissionPerformances {
                date
                returns
                submissionTime
              }
            }
          }
        """
        arguments = {'username': username}
        data = self.raw_query(query, arguments)['data']['signalsUserProfile']
        performances = data['dailySubmissionPerformances']
        # convert strings to python objects
        for perf in performances:
            utils.replace(perf, "date", utils.parse_datetime_string)
            utils.replace(perf, "submissionTime", utils.parse_datetime_string)
        return performances

    def ticker_universe(self) -> List[str]:
        """fetch universe of accepted tickers

        Returns:
            list of strings: list of currently accepted tickers

        Example:
            >>> SignalsAPI().ticker_universe()
            ["MSFT", "AMZN", "APPL", ...]
        """
        domain = 'https://numerai-quant-public-data.s3-us-west-2.amazonaws.com'
        url = f"{domain}/example_predictions/latest.csv"
        result = requests.get(url, stream=True)
        iterator = codecs.iterdecode(result.iter_lines(), 'utf-8')
        reader = csv.reader(iterator, delimiter=',', quotechar='"')
        tickers = [t for t, _ in reader]
        return tickers
