# -*- coding: utf-8 -*-

# System
import zipfile
import os
import logging
import datetime
import decimal
from typing import List, Dict

# Third Party
import requests
import pytz

from numerapi import utils

API_TOURNAMENT_URL = 'https://api-tournament.numer.ai'


class NumerAPI(object):
    """Wrapper around the Numerai API

    Automatically download and upload data for the Numerai machine learning
    competition.

    This library is a Python client to the Numerai API. The interface is
    implemented in Python and allows downloading the training data, uploading
    predictions, accessing user, submission and competitions information and
    much more.
    """

    def __init__(self, public_id=None, secret_key=None, verbosity="INFO",
                 show_progress_bars=True):
        """
        initialize Numerai API wrapper for Python

        Args:
            public_id (str): first part of your token generated at
                Numer.ai->Account->Custom API keys
            secret_key (str): second part of your token generated at
                Numer.ai->Account->Custom API keys
            verbosity (str): indicates what level of messages should be
                displayed. valid values are "debug", "info", "warning",
                "error" and "critical"
            show_progress_bars (bool): flag to turn of progress bars
        """

        # set up logging
        self.logger = logging.getLogger(__name__)
        numeric_log_level = getattr(logging, verbosity.upper())
        log_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
        logging.basicConfig(format=log_format, level=numeric_log_level)

        self._login(public_id, secret_key)

        self.submission_id = None
        self.show_progress_bars = show_progress_bars

    def _login(self, public_id=None, secret_key=None):
        # check env variables if not set
        if not public_id:
            public_id = os.getenv("NUMERAI_PUBLIC_ID")
        if not secret_key:
            secret_key = os.getenv("NUMERAI_SECRET_KEY")

        if public_id and secret_key:
            self.token = (public_id, secret_key)
        elif not public_id and not secret_key:
            self.token = None
        else:
            self.logger.warning(
                "You need to supply both a public id and a secret key.")
            self.token = None

    def _unzip_file(self, src_path, dest_path, filename):
        """unzips file located at src_path into destination_path"""
        self.logger.info("unzipping file...")

        # construct full path (including file name) for unzipping
        unzip_path = os.path.join(dest_path, filename)
        utils.ensure_directory_exists(unzip_path)

        # extract data
        with zipfile.ZipFile(src_path, "r") as z:
            z.extractall(unzip_path)

        return True

    def get_dataset_url(self, tournament=8):
        """Fetch url of the current dataset.

        Args:
            tournament (int, optional): ID of the tournament, defaults to 8

        Returns:
            str: url of the current dataset

        Example:
            >>> NumerAPI().get_dataset_url()
            https://numerai-datasets.s3.amazonaws.com/t1/104/numerai_datasets.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAIYNVLTPMU6QILOHA%2F20180424%2Fus-west-1%2Fs3%2Faws4_request&X-Amz-Date=20180424T084911Z&X-Amz-Expires=900&X-Amz-SignedHeaders=host&X-Amz-Signature=83863db44689c9907da6d3c8ac28160cd5e2d17aa90f12c7eee6811810e4b8d3
        """
        query = """
            query($tournament: Int!) {
                dataset(tournament: $tournament)
            }"""
        arguments = {'tournament': tournament}
        url = self.raw_query(query, arguments)['data']['dataset']
        return url

    def download_current_dataset(self, dest_path=".", dest_filename=None,
                                 unzip=True, tournament=8):
        """Download dataset for the current active round.

        Args:
            dest_path (str, optional): destination folder, defaults to `.`
            dest_filename (str, optional): desired filename of dataset file,
                defaults to `numerai_dataset_<round number>.zip`
            unzip (bool, optional): indication of whether the training data
                should be unzipped, defaults to `True`
            tournament (int, optional): ID of the tournament, defaults to 8

        Returns:
            str: Path to the downloaded dataset

        Example:
            >>> NumerAPI().download_current_dataset()
            ./numerai_dataset_104.zip
        """
        # set up download path
        if dest_filename is None:
            try:
                round_number = self.get_current_round(tournament)
            except ValueError:
                round_number = "x"
            dest_filename = f"numerai_dataset_{round_number}.zip"
        else:
            # ensure it ends with ".zip"
            if unzip and not dest_filename.endswith(".zip"):
                dest_filename += ".zip"
        dataset_path = os.path.join(dest_path, dest_filename)

        if os.path.exists(dataset_path):
            self.logger.info("target file already exists")
            return dataset_path

        # create parent folder if necessary
        utils.ensure_directory_exists(dest_path)

        url = self.get_dataset_url(tournament)
        utils.download_file(url, dataset_path, self.show_progress_bars)

        # unzip dataset
        if unzip:
            # remove the ".zip" in the end
            dataset_name = dest_filename[:-4]
            self._unzip_file(dataset_path, dest_path, dataset_name)

        return dataset_path

    def _handle_call_error(self, errors):
        if isinstance(errors, list):
            for error in errors:
                if "message" in error:
                    msg = error['message']
                    self.logger.error(msg)
        elif isinstance(errors, dict):
            if "detail" in errors:
                msg = errors['detail']
                self.logger.error(msg)
        return msg

    def raw_query(self, query, variables=None, authorization=False):
        """Send a raw request to the Numerai's GraphQL API.

        This function allows to build your own queries and fetch results from
        Numerai's GraphQL API. Checkout
        https://medium.com/numerai/getting-started-with-numerais-new-tournament-api-77396e895e72
        for an introduction and https://api-tournament.numer.ai/ for the
        documentation.

        Args:
            query (str): your query
            variables (dict, optional): dict of variables
            authorization (bool, optional): does the request require
                authorization, defaults to `False`

        Returns:
            dict: Result of the request

        Raises:
            ValueError: if something went wrong with the requests. For example,
                this could be a wrongly formatted query or a problem at
                Numerai's end. Have a look at the error messages, in most cases
                the problem is obvious.

        Example:
            >>> query = '''query($tournament: Int!)
                           {rounds(tournament: $tournament number: 0)
                            {number}}'''
            >>> args = {'tournament': 1}
            >>> NumerAPI().raw_query(query, args)
            {'data': {'rounds': [{'number': 104}]}}
        """
        body = {'query': query,
                'variables': variables}
        headers = {'Content-type': 'application/json',
                   'Accept': 'application/json'}
        if authorization:
            if self.token:
                public_id, secret_key = self.token
                headers['Authorization'] = f'Token {public_id}${secret_key}'
            else:
                raise ValueError("API keys required for this action.")

        result = utils.post_with_err_handling(
            API_TOURNAMENT_URL, body, headers)

        if result and "errors" in result:
            err = self._handle_call_error(result['errors'])
            # fail!
            raise ValueError(err)
        return result

    def get_v1_leaderboard(self, round_num=0, tournament=8):
        """Retrieves the leaderboard for the given round.

        Args:
            round_num (int, optional): The round you are interested in,
                defaults to current round.
            tournament (int, optional): ID of the tournament, defaults to 8

        Returns:
            list of dicts: list of participants

            For each user in the list, there is a dict with the following
            content:

                * concordance (`dict`)
                 * pending (`bool`)
                 * value (`bool`)
                * consistency (`float`)
                * liveLogloss (`float` or `None`)
                * liveAuroc (`float` or `None`)
                * liveCorrelation (`float` or `None`)
                * validationLogloss (`float`)
                * validationAuroc (`float` or `None`)
                * validationCorrelation (`float` or `None`)
                * paymentGeneral (`dict` or `None`)
                 * nmrAmount (`decimal.Decimal`)
                 * usdAmount (`decimal.Decimal`)
                * paymentStaking (`dict` or `None`)
                 * nmrAmount (`decimal.Decimal`)
                 * usdAmount (`decimal.Decimal`)
                * submissionId (`str`)
                * username (`str`)
                * stakeResolution (`dict`)
                 * destroyed (`bool`)
                 * paid (`decimal.Decimal`)
                 * successful ('bool')
                * return (`dict`)
                 * nmrAmount (`decimal.Decimal`)
                 * status (`str`)

        Example:
            >>> NumerAPI().get_v1_leaderboard(99)
            [{'concordance': {'pending': False, 'value': True},
              'consistency': 83.33333333333334,
              'liveLogloss': 0.6941153941722517,
              'liveAuroc': 0.5368847103148798,
              'liveCorrelation': 0.536898,
              'paymentGeneral': None,
              'paymentStaking': None,
              'submissionId': '4459d3df-0a4b-4996-ad44-41abb7c45336',
              'stakeResolution': {'destroyed': False,
                                  'paid': Decimal('19.86'),
                                  'successful': True},
              'return': {'nmrAmount': Decimal('0.3'),
                         'status': ''}
              'username': 'ci_wp',
              'validationLogloss': 0.692269984475575},
              'validationAuroc': 0.6368847103148798,
              'validationCorrelation': 0.54342
             ...
            ]
        """
        query = '''
            query($number: Int!
                  $tournament: Int!) {
              rounds(number: $number
                     tournament: $tournament) {
                leaderboard {
                  consistency
                  concordance {
                    pending
                    value
                  }
                  liveLogloss
                  liveAuroc
                  liveCorrelation
                  submissionId
                  username
                  validationLogloss
                  validationAuroc
                  validationCorrelation
                  paymentGeneral {
                    nmrAmount
                    usdAmount
                  }
                  paymentStaking {
                    nmrAmount
                    usdAmount
                  }
                  stakeResolution {
                    destroyed
                    paid
                    successful
                  }
                  return {
                    nmrAmount
                    status
                  }
                }
              }
            }
        '''
        arguments = {'number': round_num, 'tournament': tournament}
        result = self.raw_query(query, arguments)['data']['rounds']

        if len(result) == 0:
            msg = f"no entries for round {round_num} & tournament {tournament}"
            self.logger.warning(msg)
            raise ValueError

        leaderboard = result[0]['leaderboard']
        # parse to correct data types
        for item in leaderboard:
            for p in ["paymentGeneral", "paymentStaking"]:
                utils.replace(item[p], "nmrAmount", utils.parse_float_string)
                utils.replace(item[p], "usdAmount", utils.parse_float_string)
            utils.replace(item['stakeResolution'], "paid",
                          utils.parse_float_string)
            utils.replace(item['return'], "nmrAmount",
                          utils.parse_float_string)
        return leaderboard

    def get_competitions(self, tournament=8):
        """Retrieves information about all competitions

        Args:
            tournament (int, optional): ID of the tournament, defaults to 8

        Returns:
            list of dicts: list of rounds

            Each round's dict contains the following items:

                * datasetId (`str`)
                * number (`int`)
                * openTime (`datetime`)
                * resolveTime (`datetime`)
                * participants (`int`): number of participants
                * prizePoolNmr (`decimal.Decimal`)
                * prizePoolUsd (`decimal.Decimal`)
                * resolvedGeneral (`bool`)
                * resolvedStaking (`bool`)
                * ruleset (`string`)

        Example:
            >>> NumerAPI().get_competitions()
            [
             {'datasetId': '59a70840ca11173c8b2906ac',
              'number': 71,
              'openTime': datetime.datetime(2017, 8, 31, 0, 0),
              'resolveTime': datetime.datetime(2017, 9, 27, 21, 0),
              'participants': 1287,
              'prizePoolNmr': Decimal('0.00'),
              'prizePoolUsd': Decimal('6000.00'),
              'resolvedGeneral': True,
              'resolvedStaking': True,
              'ruleset': 'p_auction'
             },
              ..
            ]
        """
        self.logger.info("getting rounds...")

        query = '''
            query($tournament: Int!) {
              rounds(tournament: $tournament) {
                number
                resolveTime
                datasetId
                openTime
                resolvedGeneral
                resolvedStaking
                participants
                prizePoolNmr
                prizePoolUsd
                ruleset
              }
            }
        '''
        arguments = {'tournament': tournament}
        result = self.raw_query(query, arguments)
        rounds = result['data']['rounds']
        # convert datetime strings to datetime.datetime objects
        for r in rounds:
            utils.replace(r, "openTime", utils.parse_datetime_string)
            utils.replace(r, "resolveTime", utils.parse_datetime_string)
            utils.replace(r, "prizePoolNmr", utils.parse_float_string)
            utils.replace(r, "prizePoolUsd", utils.parse_float_string)
        return rounds

    def get_current_round(self, tournament=8):
        """Get number of the current active round.

        Args:
            tournament (int): ID of the tournament (optional, defaults to 8)

        Returns:
            int: number of the current active round

        Example:
            >>> NumerAPI().get_current_round()
            104
        """
        # zero is an alias for the current round!
        query = '''
            query($tournament: Int!) {
              rounds(tournament: $tournament
                     number: 0) {
                number
              }
            }
        '''
        arguments = {'tournament': tournament}
        data = self.raw_query(query, arguments)['data']['rounds'][0]
        if data is None:
            return None
        round_num = data["number"]
        return round_num

    def get_tournaments(self, only_active=True):
        """Get all tournaments

        Args:
            only_active (bool): Flag to indicate of only active tournaments
                                should be returned or all of them. Defaults
                                to True.

        Returns:
            list of dicts: list of tournaments

            Each tournaments' dict contains the following items:

                * id (`str`)
                * name (`str`)
                * tournament (`int`)
                * active (`bool`)

        Example:
            >>> NumerAPI().get_tournaments()
            [ { 'id': '2ecf30f4-4b4f-42e9-8e72-cc5bd61c2733',
                'name': 'alpha',
                'tournament': 1,
                'active': True},
              { 'id': '6ff44cca-263d-40bd-b029-a1ab8f42798f',
                'name': 'bravo',
                'tournament': 2,
                'active': True},
              { 'id': 'ebf0d62b-0f60-4550-bcec-c737b168c65d',
                'name': 'charlie',
                'tournament': 3
                'active': False},
              { 'id': '5fac6ece-2726-4b66-9790-95866b3a77fc',
                'name': 'delta',
                'tournament': 4,
                'active': True}]
        """
        query = """
            query {
              tournaments {
                id
                name
                tournament
                active
            }
        }
        """
        data = self.raw_query(query)['data']['tournaments']
        if only_active:
            data = [d for d in data if d['active']]
        return data

    def get_account(self) -> Dict:
        """Get all information about your account!

        Returns:
            dict: user information including the following fields:

                * assignedEthAddress (`str`)
                * availableNmr (`decimal.Decimal`)
                * availableUsd (`decimal.Decimal`)
                * email (`str`)
                * id (`str`)
                * insertedAt (`datetime`)
                * mfaEnabled (`bool`)
                * status (`str`)
                * username (`str`)
                * apiTokens (`list`) each with the following fields:
                 * name (`str`)
                 * public_id (`str`)
                 * scopes (`list of str`)
                * models
                  * username
                  * id
                  * submissions
                  * v2Stake
                   * status (`str`)
                   * txHash (`str`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> api.get_account()
            {'apiTokens': [
                    {'name': 'tokenname',
                     'public_id': 'BLABLA',
                     'scopes': ['upload_submission', 'stake', ..]
                     }, ..],
             'assignedEthAddress': '0x0000000000000000000000000001',
             'availableNmr': Decimal('99.01'),
             'email': 'username@example.com',
             'id': '1234-ABC..',
             'insertedAt': datetime.datetime(2018, 1, 1, 2, 16, 48),
             'mfaEnabled': False,
             'status': 'VERIFIED',
             'username': 'cool username',
             }
        """
        query = """
          query {
            account {
              username
              walletAddress
              availableNmr
              email
              id
              mfaEnabled
              status
              insertedAt
              models {
                id
                name
                submissions {
                  id
                  filename
                }
                v2Stake {
                  status
                  txHash
                }
              }
              apiTokens {
                name
                public_id
                scopes
              }
            }
          }
        """
        data = self.raw_query(query, authorization=True)['data']['account']
        # convert strings to python objects
        utils.replace(data, "insertedAt", utils.parse_datetime_string)
        utils.replace(data, "availableNmr", utils.parse_float_string)
        return data

    def get_models(self) -> Dict:
        """Get mapping of account model names to model ids for convenience

        Returns:
            dict: modelname->model_id mapping, string->string

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model = api.get_models()
            {'uuazed': '9b157d9b-ce61-4ab5-9413-413f13a0c0a6'}
        """
        query = """
          query {
            account {
              models {
                id
                name
              }
            }
          }
        """
        data = self.raw_query(query, authorization=True)['data']['account']['models']
        mapping = {model['name']: model['id'] for model in data}
        return mapping

    def get_user_activities(self, username, tournament=8):
        """Get user activities (works for all users!).

        Args:
            username (str): name of the user
            tournament (int): ID of the tournament (optional, defaults to 8)

        Returns:
            list: list of user activities (`dict`)

            Each activity in the list as the following structure:

                * resolved (`bool`)
                * roundNumber (`int`)
                * tournament (`int`)
                * submission (`dict`)
                 * concordance (`bool`)
                 * consistency (`float`)
                 * date (`datetime`)
                 * liveLogloss (`float`)
                 * liveAuroc (`float`)
                 * liveCorrelation (`float`)
                 * validationLogloss (`float`)
                 * validationAuroc (`float`)
                 * validationCorrelation (`float`)
                * stake (`dict`)
                 * confidence (`decimal.Decimal`)
                 * date (`datetime`)
                 * nmrEarned (`decimal.Decimal`)
                 * staked (`bool`)
                 * usdEarned (`decimal.Decimal`)
                 * burned (`bool`)

        Example:
            >>> NumerAPI().get_user_activities("slyfox", 5)
            [{'tournament': 5,
              'submission': {
               'validationLogloss': 0.6928141372700635,
               'validationAuroc': 0.52,
               'validationCorrelation': 0.52,
               'liveLogloss': None,
               'liveAuroc': None,
               'liveCorrelation': None,
               'date': datetime.datetime(2018, 7, 14, 17, 5, 27, 206042),
               'consistency': 83.33333333333334,
               'concordance': True},
              'stake': {'value': Decimal('0.10'),
               'usdEarned': None,
               'staked': True,
               'nmrEarned': None,
               'date': datetime.datetime(2018, 7, 14, 17, 7, 7, 877845),
               'confidence': Decimal('0.100000000000000000')},
               'burned': False
              'roundNumber': 116,
              'resolved': False},
             {'tournament': 5,
              'submission': {'validationLogloss': 0.6928141372700635,

               ...

               ]

        """
        query = '''
            query($tournament: Int!
                  $username: String!) {
              userActivities(tournament: $tournament
                     username: $username) {
                resolved
                roundNumber
                tournament
                submission {
                    concordance
                    consistency
                    date
                    liveLogloss
                    liveAuroc
                    liveCorrelation
                    validationLogloss
                    validationAuroc
                    validationCorrelation
                }
                stake {
                    confidence
                    date
                    nmrEarned
                    staked
                    usdEarned
                    value
                    burned
                }
              }
            }
        '''
        arguments = {'tournament': tournament, 'username': username}
        data = self.raw_query(query, arguments)['data']['userActivities']
        # filter rounds with no activity
        data = [item for item in data
                if item['submission']['date'] is not None]
        for item in data:
            # remove stakes with all values set to None
            if item['stake'] is None or item['stake']['date'] is None:
                del item['stake']
            # parse
            else:
                utils.replace(item['stake'], "date",
                              utils.parse_datetime_string)
                for col in ['confidence', 'value', 'nmrEarned', 'usdEarned']:
                    utils.replace(item['stake'], col, utils.parse_float_string)
        # parse
        for item in data:
            utils.replace(item['submission'], "date",
                          utils.parse_datetime_string)
        return data

    def get_submission_filenames(self, tournament=None, round_num=None,
                                 model_id=None) -> List[Dict]:
        """Get filenames of the submission of the user.

        Args:
            tournament (int): optionally filter by ID of the tournament
            round_num (int): optionally filter round number
            model_id (str): Target model UUID (required for accounts with multiple models)

        Returns:
            list: list of user filenames (`dict`)

            Each filenames in the list as the following structure:

                * filename (`str`)
                * round_num (`int`)
                * tournament (`int`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model = api.get_models()['uuazed']
            >>> api.get_submission_filenames(3, 111, model)
            [{'filename': 'model57-dMpHpYMPIUAF.csv',
              'round_num': 111,
              'tournament': 3}]

        """
        query = """
          query($modelId: String) {
            model(modelId: $modelId) {
              submissions {
                filename
                selected
                round {
                   tournament
                   number
                }
              }
            }
          }
        """
        arguments = {'modelId': model_id}
        data = self.raw_query(query, arguments, authorization=True)['data']['model']

        filenames = [{"round_num": item['round']['number'],
                      "tournament": item['round']['tournament'],
                      "filename": item['filename']}
                     for item in data['submissions'] if item['selected']]

        if round_num is not None:
            filenames = [f for f in filenames if f['round_num'] == round_num]
        if tournament is not None:
            filenames = [f for f in filenames if f['tournament'] == tournament]
        filenames.sort(key=lambda f: (f['round_num'], f['tournament']))
        return filenames

    def get_submission_ids(self, tournament=8):
        """Get dict with username->submission_id mapping.

        Args:
            tournament (int): ID of the tournament (optional, defaults to 8)

        Returns:
            dict: username->submission_id mapping, string->string

        Example:
            >>> NumerAPI().get_submission_ids()
            {'1337ai': '93c46857-fed9-4594-981e-82db2b358daf',
             '1x0r': '108c7601-822c-4910-835d-241da93e2e24',
             ...
             }
        """
        query = """
            query($tournament: Int!) {
              rounds(tournament: $tournament
                     number: 0) {
                leaderboard {
                  username
                  submissionId
                }
            }
        }
        """
        arguments = {'tournament': tournament}
        data = self.raw_query(query, arguments)['data']['rounds'][0]
        if data is None:
            return None
        mapping = {item['username']: item['submissionId']
                   for item in data['leaderboard']}
        return mapping

    def get_user(self, model_id: str = None) -> Dict:
        """Get all information about you! DEPRECATED

        Args:
            model_id (str): Target model UUID (required for accounts with multiple models)

        Returns:
            dict: user information including the following fields:

                * assignedEthAddress (`str`)
                * availableNmr (`decimal.Decimal`)
                * availableUsd (`decimal.Decimal`)
                * banned (`bool`)
                * email (`str`)
                * id (`str`)
                * insertedAt (`datetime`)
                * mfaEnabled (`bool`)
                * status (`str`)
                * username (`str`)
                * country (`str)
                * apiTokens (`list`) each with the following fields:
                 * name (`str`)
                 * public_id (`str`)
                 * scopes (`list of str`)
                * v2Stake
                 * status (`str`)
                 * txHash (`str`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model = api.get_models()['uuazed']
            >>> api.get_user(model)
            {'apiTokens': [
                    {'name': 'tokenname',
                     'public_id': 'BLABLA',
                     'scopes': ['upload_submission', 'stake', ..]
                     }, ..],
             'assignedEthAddress': '0x0000000000000000000000000001',
             'availableNmr': Decimal('99.01'),
             'availableUsd': Decimal('9.47'),
             'banned': False,
             'email': 'username@example.com',
             'country': 'US',
             'id': '1234-ABC..',
             'insertedAt': datetime.datetime(2018, 1, 1, 2, 16, 48),
             'mfaEnabled': False,
             'status': 'VERIFIED',
             'username': 'cool username',
             'v2Stake': None
             }
        """
        self.logger.warning("Method get_user is DEPRECATED, use get_account")
        query = """
          query($modelId: String) {
            user(modelId: $modelId) {
              username
              banned
              assignedEthAddress
              availableNmr
              availableUsd
              email
              id
              mfaEnabled
              status
              country
              insertedAt
              apiTokens {
                name
                public_id
                scopes
              }
              v2Stake {
                status
                txHash
              }
            }
          }
        """
        arguments = {'modelId': model_id}
        data = self.raw_query(query, arguments, authorization=True)['data']['user']
        # convert strings to python objects
        utils.replace(data, "insertedAt", utils.parse_datetime_string)
        utils.replace(data, "availableUsd", utils.parse_float_string)
        utils.replace(data, "availableNmr", utils.parse_float_string)
        return data

    def get_payments(self, model_id: str = None) -> Dict:
        """Get all your payments.

        Args:
            model_id (str): Target model UUID (required for accounts with multiple models)

        Returns:
            dict of lists: payments & reputationPayments

            A dict containing the following items:
               * payments (`list`)
                 * nmrAmount (`decimal.Decimal`)
                 * usdAmount (`decimal.Decimal`)
                 * tournament (`str`)
                 * round (`dict`)
                   * number (`int`)
                   * openTime (`datetime`)
                   * resolveTime (`datetime`)
                   * resolvedGeneral (`bool`)
                   * resolvedStaking (`bool`)
               * reputationPayment (`list`)
                 * nmrAmount (`decimal.Decimal`)
                 * insertedAt (`datetime`)


        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model = api.get_models()['uuazed']
            >>> api.get_payments(model)
            {'payments': [
                {'nmrAmount': Decimal('0.00'),
                 'round': {'number': 84,
                 'openTime': datetime.datetime(2017, 12, 2, 18, 0),
                 'resolveTime': datetime.datetime(2018, 1, 1, 18, 0),
                 'resolvedGeneral': True,
                 'resolvedStaking': True},
                 'tournament': 'staking',
                 'usdAmount': Decimal('17.44')},
                 ...
                ],
             'reputationPayments': [
               {'nmrAmount': Decimal('0.1'),
                'insertedAt': datetime.datetime(2017, 12, 2, 18, 0)},
                ...
                ],
             'otherUsdIssuances': [
                {'usdAmount': Decimal('0.1'),
                 'insertedAt': datetime.datetime(2017, 12, 2, 18, 0)},
                 ...
             ]
            }
        """
        query = """
          query($modelId: String) {
            model(modelId: $modelId) {
              reputationPayments {
                insertedAt
                nmrAmount
              }
              otherUsdIssuances {
                insertedAt
                usdAmount
              }
              payments {
                nmrAmount
                usdAmount
                tournament
                round {
                  number
                  openTime
                  resolveTime
                  resolvedGeneral
                  resolvedStaking
                }
              }
            }
          }
        """
        arguments = {'modelId': model_id}
        data = self.raw_query(query, arguments, authorization=True)['data']
        payments = data['model']
        # convert strings to python objects
        for p in payments['payments']:
            utils.replace(p['round'], "openTime", utils.parse_datetime_string)
            utils.replace(p['round'], "resolveTime",
                          utils.parse_datetime_string)
            utils.replace(p, "usdAmount", utils.parse_float_string)
            utils.replace(p, "nmrAmount", utils.parse_float_string)
        for p in payments['reputationPayments']:
            utils.replace(p, "nmrAmount", utils.parse_float_string)
            utils.replace(p, "insertedAt", utils.parse_datetime_string)
        for p in payments['otherUsdIssuances']:
            utils.replace(p, "usdAmount", utils.parse_float_string)
            utils.replace(p, "insertedAt", utils.parse_datetime_string)
        return payments

    def get_account_transactions(self) -> Dict:
        """Get all your account deposits and withdrawals.

        Returns:
            dict: lists of your tournament wallet NMR transactions

            The returned dict has the following structure:

                * nmrDeposits (`list`) contains items with fields:
                 * from (`str`)
                 * posted (`bool`)
                 * status (`str`)
                 * to (`str`)
                 * txHash (`str`)
                 * value (`decimal.Decimal`)
                 * insertedAt (`datetime`)
                * nmrWithdrawals"` (`list`) contains items with fields:
                 * from"` (`str`)
                 * posted"` (`bool`)
                 * status"` (`str`)
                 * to"` (`str`)
                 * txHash"` (`str`)
                 * value"` (`decimal.Decimal`)
                  * insertedAt (`datetime`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> api.get_account_transactions()
            {'nmrDeposits': [
                {'from': '0x54479..9ec897a',
                 'posted': True,
                 'status': 'confirmed',
                 'to': '0x0000000000000000000001',
                 'txHash': '0x52..e2056ab',
                 'value': Decimal('9.0'),
                 'insertedAt: datetime.datetime((2018, 2, 11, 17, 54, 2)},
                 .. ],
             'nmrWithdrawals': [
                {'from': '0x0000000000000000..002',
                 'posted': True,
                 'status': 'confirmed',
                 'to': '0x00000000000..001',
                 'txHash': '0x1278..266c',
                 'value': Decimal('2.0'),
                 'insertedAt: datetime.datetime((2018, 2, 11, 17, 54, 2)},},
                 .. ]}
        """
        query = """
          query {
            account {
              nmrDeposits {
                from
                posted
                status
                to
                txHash
                value
                insertedAt
              }
              nmrWithdrawals {
                from
                posted
                status
                to
                txHash
                value
                insertedAt
              }
            }
          }
        """
        txs = self.raw_query(query, authorization=True)['data']['account']
        # convert strings to python objects
        for t in txs["nmrWithdrawals"]:
            utils.replace(t, "value", utils.parse_float_string)
            utils.replace(t, "insertedAt", utils.parse_datetime_string)
        for t in txs["nmrDeposits"]:
            utils.replace(t, "value", utils.parse_float_string)
            utils.replace(t, "insertedAt", utils.parse_datetime_string)
        return txs

    def get_transactions(self, model_id: str = None) -> Dict:
        """Get all your deposits and withdrawals.

        Args:
            model_id (str): Target model UUID (required for accounts with multiple models)

        Returns:
            dict: lists of your NMR and USD transactions

            The returned dict has the following structure:

                * nmrDeposits (`list`) contains items with fields:
                 * from (`str`)
                 * posted (`bool`)
                 * status (`str`)
                 * to (`str`)
                 * txHash (`str`)
                 * value (`decimal.Decimal`)
                 * insertedAt (`datetime`)
                * nmrWithdrawals"` (`list`) contains items with fields:
                 * from"` (`str`)
                 * posted"` (`bool`)
                 * status"` (`str`)
                 * to"` (`str`)
                 * txHash"` (`str`)
                 * value"` (`decimal.Decimal`)
                  * insertedAt (`datetime`)
                * usdWithdrawals"` (`list`) contains items with fields:
                 * confirmTime"` (`datetime` or `None`)
                 * ethAmount"` (`str`)
                 * from"` (`str`)
                 * posted"` (`bool`)
                 * sendTime"` (`datetime`)
                 * status"` (`str`)
                 * to (`str`)
                 * txHash (`str`)
                 * usdAmount (`decimal.Decimal`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model = api.get_models()['uuazed']
            >>> api.get_transactions(model)
            {'nmrDeposits': [
                {'from': '0x54479..9ec897a',
                 'posted': True,
                 'status': 'confirmed',
                 'to': '0x0000000000000000000001',
                 'txHash': '0x52..e2056ab',
                 'value': Decimal('9.0'),
                 'insertedAt: datetime.datetime((2018, 2, 11, 17, 54, 2)},
                 .. ],
             'nmrWithdrawals': [
                {'from': '0x0000000000000000..002',
                 'posted': True,
                 'status': 'confirmed',
                 'to': '0x00000000000..001',
                 'txHash': '0x1278..266c',
                 'value': Decimal('2.0'),
                 'insertedAt: datetime.datetime((2018, 2, 11, 17, 54, 2)},},
                 .. ],
             'usdWithdrawals': [
                {'confirmTime': datetime.datetime(2018, 2, 11, 17, 54, 2, 785430),
                 'ethAmount': '0.295780674909307710',
                 'from': '0x11.....',
                 'posted': True,
                 'sendTime': datetime.datetime(2018, 2, 11, 17, 53, 25, 235035),
                 'status': 'confirmed',
                 'to': '0x81.....',
                 'txHash': '0x3c....',
                 'usdAmount': Decimal('10.07')},
                 ..]}
        """
        self.logger.warning("Method get_transactions is DEPRECATED, use get_account_transactions")
        query = """
          query($modelId: String) {
            user(modelId: $modelId) {
              nmrDeposits {
                from
                posted
                status
                to
                txHash
                value
                insertedAt
              }
              nmrWithdrawals {
                from
                posted
                status
                to
                txHash
                value
                insertedAt
              }
              usdWithdrawals {
                ethAmount
                confirmTime
                from
                posted
                sendTime
                status
                to
                txHash
                usdAmount
              }
            }
          }
        """
        arguments = {'modelId': model_id}
        txs = self.raw_query(query, arguments, authorization=True)['data']['user']
        # convert strings to python objects
        for t in txs['usdWithdrawals']:
            utils.replace(t, "confirmTime", utils.parse_datetime_string)
            utils.replace(t, "sendTime", utils.parse_datetime_string)
            utils.replace(t, "usdAmount", utils.parse_float_string)
        for t in txs["nmrWithdrawals"]:
            utils.replace(t, "value", utils.parse_float_string)
            utils.replace(t, "insertedAt", utils.parse_datetime_string)
        for t in txs["nmrDeposits"]:
            utils.replace(t, "value", utils.parse_float_string)
            utils.replace(t, "insertedAt", utils.parse_datetime_string)
        return txs

    def get_stakes(self, model_id: str = None) -> List[Dict]:
        """List all your stakes.

        Args:
            model_id (str): Target model UUID (required for accounts with multiple models)

        Returns:
            list of dicts: stakes

            Each stake is a dict with the following fields:

                * confidence (`decimal.Decimal`)
                * roundNumber (`int`)
                * tournamentId (`int`)
                * soc (`decimal.Decimal`)
                * insertedAt (`datetime`)
                * staker (`str`): NMR adress used for staking
                * status (`str`)
                * txHash (`str`)
                * value (`decimal.Decimal`)

        Example:

            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model = api.get_models()['uuazed']
            >>> api.get_stakes(model)
            [{'confidence': Decimal('0.053'),
              'insertedAt': datetime.datetime(2017, 9, 26, 8, 18, 36, 709000),
              'roundNumber': 74,
              'soc': Decimal('56.60'),
              'staker': '0x0000000000000000000000000000000000003f9e',
              'status': 'confirmed',
              'tournamentId': 1,
              'txHash': '0x1cbb985629552a0f57b98a1e30acef02e02aaf0e91c95',
              'value': Decimal('3.00')},
              ..
             ]
        """
        query = """
          query($modelId: String) {
            model(modelId: $modelId) {
              stakeTxs {
                confidence
                insertedAt
                roundNumber
                tournamentId
                soc
                staker
                status
                txHash
                value
              }
            }
          }
        """
        arguments = {'modelId': model_id}
        data = self.raw_query(query, arguments, authorization=True)['data']
        stakes = data['model']['stakeTxs']
        # convert strings to python objects
        for s in stakes:
            utils.replace(s, "insertedAt", utils.parse_datetime_string)
            utils.replace(s, "soc", utils.parse_float_string)
            utils.replace(s, "confidence", utils.parse_float_string)
            utils.replace(s, "value", utils.parse_float_string)
        return stakes

    def submission_status(self, submission_id: str = None) -> Dict:
        """submission status of the last submission associated with the account

        Args:
            submission_id (str): submission of interest, defaults to the last
                submission done with the account

        Returns:
            dict: submission status with the following content:

                * concordance (`dict`):
                 * pending (`bool`)
                 * value (`bool`): whether the submission is concordant
                * consistency (`float`): consistency of the submission
                * validationCorrelation (`float`)
                * filename (`string`)
                * corrWithExamplePreds (`float`)
                * validationFeatureExposure (`float`)
                * validationSharpe (`float`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> api.upload_predictions()
            >>> api.submission_status()
            {'concordance': None,
             'consistency': None,
             'corrWithExamplePreds': 0.3811635610849811,
             'filename': 'model57-HPzOyr56TPaD.csv',
             'validationCorrelation': 0.02967954913128146,
             'validationFeatureExposure': 0.09736206063204657,
             'validationSharpe': 1.5567641700803665}
        """
        if submission_id is None:
            submission_id = self.submission_id

        if submission_id is None:
            raise ValueError('You need to submit something first or provide\
                              a submission ID')

        query = '''
            query($submission_id: String!) {
              submissions(id: $submission_id) {
                concordance {
                  pending
                  value
                }
                consistency
                validationCorrelation
                validationFeatureExposure
                validationSharpe
                corrWithExamplePreds
                filename
              }
            }
            '''
        variable = {'submission_id': submission_id}
        data = self.raw_query(query, variable, authorization=True)
        status = data['data']['submissions'][0]
        return status

    def upload_predictions(self, file_path: str, tournament: int = 8, model_id: str = None) -> str:
        """Upload predictions from file.

        Args:
            file_path (str): CSV file with predictions that will get uploaded
            tournament (int): ID of the tournament (optional, defaults to 8)
            model_id (str): Target model UUID (required for accounts with multiple models)

        Returns:
            str: submission_id

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model = api.get_models()['uuazed']
            >>> api.upload_predictions(model)
            '93c46857-fed9-4594-981e-82db2b358daf'
        """
        self.logger.info("uploading predictions...")

        auth_query = '''
            query($filename: String!
                  $tournament: Int!
                  $modelId: String) {
                submission_upload_auth(filename: $filename
                                       tournament: $tournament
                                       modelId: $modelId) {
                    filename
                    url
                }
            }
            '''
        arguments = {'filename': os.path.basename(file_path),
                     'tournament': tournament,
                     'modelId': model_id}
        submission_resp = self.raw_query(auth_query, arguments,
                                         authorization=True)
        submission_auth = submission_resp['data']['submission_upload_auth']
        with open(file_path, 'rb') as fh:
            requests.put(submission_auth['url'], data=fh.read())
        create_query = '''
            mutation($filename: String!
                     $tournament: Int!
                     $modelId: String) {
                create_submission(filename: $filename
                                  tournament: $tournament
                                  modelId: $modelId) {
                    id
                }
            }
            '''
        arguments = {'filename': submission_auth['filename'],
                     'tournament': tournament,
                     'modelId': model_id}
        create = self.raw_query(create_query, arguments, authorization=True)
        self.submission_id = create['data']['create_submission']['id']
        return self.submission_id

    def check_new_round(self, hours: int = 24, tournament: int = 8) -> bool:
        """Check if a new round has started within the last `hours`.

        Args:
            hours (int, optional): timeframe to consider, defaults to 24
            tournament (int): ID of the tournament (optional, defaults to 8)

        Returns:
            bool: True if a new round has started, False otherwise.

        Example:
            >>> NumerAPI().check_new_round()
            False
        """
        query = '''
            query($tournament: Int!) {
              rounds(tournament: $tournament
                     number: 0) {
                number
                openTime
              }
            }
        '''
        arguments = {'tournament': tournament}
        raw = self.raw_query(query, arguments)['data']['rounds'][0]
        if raw is None:
            return False
        open_time = utils.parse_datetime_string(raw['openTime'])
        now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        is_new_round = open_time > now - datetime.timedelta(hours=hours)
        return is_new_round

    def tournament_number2name(self, number: int) -> str:
        """Translate tournament number to tournament name.

        Args:
            number (int): tournament number to translate

        Returns:
            name (str): name of the tournament or `None` if unknown.

        Examples:
            >>> NumerAPI().tournament_number2name(4)
            'delta'
            >>> NumerAPI().tournament_number2name(99)
            None
        """
        tournaments = self.get_tournaments()
        d = {t['tournament']: t['name'] for t in tournaments}
        return d.get(number, None)

    def tournament_name2number(self, name: str) -> int:
        """Translate tournament name to tournament number.

        Args:
            name (str): tournament name to translate

        Returns:
            number (int): number of the tournament or `None` if unknown.

        Examples:
            >>> NumerAPI().tournament_name2number('delta')
            4
            >>> NumerAPI().tournament_name2number('foo')
            None
        """
        tournaments = self.get_tournaments()
        d = {t['name']: t['tournament'] for t in tournaments}
        return d.get(name, None)

    #  ################# V2 #####################################

    def get_leaderboard(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get the current leaderboard

        Args:
            limit (int): number of items to return (optional, defaults to 50)
            offset (int): number of items to skip (optional, defaults to 0)

        Returns:
            list of dicts: list of leaderboard entries

            Each dict contains the following items:

                * username (`str`)
                * tier (`str`)
                * reputation (`float`) -- DEPRECATED since 2020-04-05
                * rolling_score_rep (`float`)
                * rank (`int`)
                * prevRank (`int`)
                * stakedRank (`int`)
                * prevStakedRank (`int`)
                * nmrStaked (`decimal.Decimal`)
                * oldStakeValue (`decimal.Decimal`)
                * leaderboardBonus (`decimal.Decimal`)
                * averageCorrelationPayout (`decimal.Decimal`)
                * payoutPending (`decimal.Decimal`)
                * payoutSettled (`decimal.Decimal`)
                * bonusPerc (`float`)
                * badges (`list of str`)

        Example:
            >>> numerapi.NumerAPI().get_leaderboard(1)
            [{'username': 'anton',
              'tier': 'C',
              'reputation': -0.00499721,
              'rolling_score_rep': -0.00499721,
              'rank': 143,
              'prevRank': 116,
              'stakedRank': 103,
              'prevStakedRank': 102,
              'nmrStaked': Decimal('12'),
              'oldStakeValue': Decimal('12'),
              `leaderboardBonus`: Decimal('0.1')
              `averageCorrelationPayout`: Decimal('0.1')
              `payoutPending`: Decimal('0.1')
              `payoutSettled`: Decimal('0.1')
              'bonusPerc': 0.5,
              'badges': ['submission-streak_1', 'burned_2']}]

        """
        query = '''
            query($limit: Int!
                  $offset: Int!) {
              v2Leaderboard(limit: $limit
                            offset: $offset) {
                bonusPerc
                nmrStaked
                oldStakeValue
                prevRank
                prevStakedRank
                rank
                stakedRank
                reputation
                rolling_score_rep
                tier
                username
                leaderboardBonus
                averageCorrelationPayout
                payoutPending
                payoutSettled
                badges
              }
            }
        '''

        arguments = {'limit': limit, 'offset': offset}
        data = self.raw_query(query, arguments)['data']['v2Leaderboard']
        for item in data:
            utils.replace(item, "nmrStaked", utils.parse_float_string)
        return data

    def stake_set(self, nmr) -> Dict:
        """Set stake to value by decreasing or increasing your current stake

        Args:
            nmr (float or str): amount of NMR you want to stake

        Returns:
            dict: stake information with the following content:

              * insertedAt (`datetime`)
              * status (`str`)
              * txHash (`str`)
              * value (`decimal.Decimal`)
              * source (`str`)
              * to (`str`)
              * from (`str`)
              * posted (`bool`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> api.stake_set(10)
            {'from': None,
             'insertedAt': None,
             'status': None,
             'txHash': '0x76519...2341ca0',
             'from': '',
             'to': '',
             'posted': True,
             'value': '10'}
        """
        # get username of logged in user
        username = self.get_account()['username']
        # fetch current stake
        current = self.stake_get(username)
        # convert everything to decimals
        if current is None:
            current = decimal.Decimal(0)
        else:
            current = decimal.Decimal(str(current))
        if not isinstance(nmr, decimal.Decimal):
            nmr = decimal.Decimal(str(nmr))
        # update stake!
        if nmr == current:
            self.logger.info("Stake already at desired value. Nothing to do.")
            return None
        elif nmr < current:
            return self.stake_decrease(current - nmr)
        elif nmr > current:
            return self.stake_increase(nmr - current)

    def stake_get(self, username: str) -> float:
        """Get your current stake amount.

        Args:
            username (str)

        Returns:
            float: current stake

        Example:
            >>> api = NumerAPI()
            >>> api.stake_get("uuazed")
            1.1
        """
        query = """
          query($username: String!) {
            v2UserProfile(username: $username) {
              dailyUserPerformances {
                stakeValue
              }
            }
          }
        """
        arguments = {'username': username}
        data = self.raw_query(query, arguments)['data']['v2UserProfile']
        # be convention, the first is the latest one
        stake = data['dailyUserPerformances'][0]['stakeValue']
        return stake

    def stake_change(self, nmr, action: str = "decrease", model_id: str = None) -> Dict:
        """Change stake by `value` NMR.

        Args:
            nmr (float or str): amount of NMR you want to reduce
            action (str): `increase` or `decrease`
            model_id (str): Target model UUID (required for accounts with multiple models)

        Returns:
            dict: stake information with the following content:

              * dueDate (`datetime`)
              * status (`str`)
              * requestedAmount (`decimal.Decimal`)
              * type (`str`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model = api.get_models()['uuazed']
            >>> api.stake_decrease(10, model)
            {'dueDate': None,
             'requestedAmount': decimal.Decimal('10'),
             'type': 'decrease',
             'status': ''}
        """
        query = '''
          mutation($value: String!
                   $type: String!
                   $modelId: String) {
              v2ChangeStake(value: $value
                            type: $type
                            modelId: $modelId) {
                dueDate
                requestedAmount
                status
                type
              }
        }
        '''
        arguments = {'value': str(nmr), 'type': action, 'modelId': model_id}
        result = self.raw_query(query, arguments, authorization=True)
        stake = result['data']['v2ChangeStake']
        utils.replace(stake, "requestedAmount", utils.parse_float_string)
        utils.replace(stake, "dueDate", utils.parse_datetime_string)
        return stake

    def stake_drain(self, model_id: str = None) -> Dict:
        """Completely remove your stake.

        Args:
            model_id (str): Target model UUID (required for accounts with multiple models)

        Returns:
            dict: stake information with the following content:

              * dueDate (`datetime`)
              * status (`str`)
              * requestedAmount (`decimal.Decimal`)
              * type (`str`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model = api.get_models()['uuazed']
            >>> api.stake_drain(model)
            {'dueDate': None,
             'requestedAmount': decimal.Decimal('11000000'),
             'type': 'decrease',
             'status': ''}
        """
        return self.stake_decrease(11000000, model_id)

    def stake_decrease(self, nmr, model_id: str = None) -> Dict:
        """Decrease your stake by `value` NMR.

        Args:
            nmr (float or str): amount of NMR you want to reduce
            model_id (str): Target model UUID (required for accounts with multiple models)

        Returns:
            dict: stake information with the following content:

              * dueDate (`datetime`)
              * status (`str`)
              * requestedAmount (`decimal.Decimal`)
              * type (`str`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model = api.get_models()['uuazed']
            >>> api.stake_decrease(10, model)
            {'dueDate': None,
             'requestedAmount': decimal.Decimal('10'),
             'type': 'decrease',
             'status': ''}
        """
        return self.stake_change(nmr, 'decrease', model_id)

    def stake_increase(self, nmr, model_id: str = None) -> Dict:
        """Increase your stake by `value` NMR.

        Args:
            nmr (float or str): amount of additional NMR you want to stake
            model_id (str): Target model UUID (required for accounts with multiple models)

        Returns:
            dict: stake information with the following content:

              * dueDate (`datetime`)
              * status (`str`)
              * requestedAmount (`decimal.Decimal`)
              * type (`str`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model = api.get_models()['uuazed']
            >>> api.stake_increase(10, model)
            {'dueDate': None,
             'requestedAmount': decimal.Decimal('10'),
             'type': 'increase',
             'status': ''}
        """
        return self.stake_change(nmr, 'increase', model_id)

    def public_user_profile(self, username: str) -> Dict:
        """Fetch the public profile of a user.

        Args:
            username (str)

        Returns:
            dict: user profile including the following fields:

                * username (`str`)
                * startDate (`datetime`)
                * netEarnings (`float`)
                * id (`string`)
                * historicalNetUsdEarnings (`float`)
                * historicalNetNmrEarnings (`float`)
                * badges (`list of str`)
                * bio (`str`)
                * totalStake (`float`)

        Example:
            >>> api = NumerAPI()
            >>> api.public_user_profile("niam")
            {'username': 'niam',
             'startDate': datetime.datetime(2018, 6, 14, 22, 58, 2, 186221),
             'netEarnings': None,
             'id': '024c9bb9-77af-4b3f-91c7-63062fce2b80',
             'historicalNetUsdEarnings': '3669.41',
             'historicalNetNmrEarnings': '1094.247665827645663410',
             'badges': ['burned_3', 'compute_0', 'submission-streak_1'],
             'bio': 'blabla',
             'totalStake': 12.2}
        """
        query = """
          query($username: String!) {
            v2UserProfile(username: $username) {
              badges
              historicalNetNmrEarnings
              historicalNetUsdEarnings
              id
              netEarnings
              startDate
              username
              bio
              totalStake
            }
          }
        """
        arguments = {'username': username}
        data = self.raw_query(query, arguments)['data']['v2UserProfile']
        # convert strings to python objects
        utils.replace(data, "startDate", utils.parse_datetime_string)
        return data

    def daily_user_performances(self, username: str) -> List[Dict]:
        """Fetch daily performance of a user.

        Args:
            username (str)

        Returns:
            list of dicts: list of daily user performance entries

            For each entry in the list, there is a dict with the following
            content:

                * tier (`str`)
                * stakeValue (`float` or none)
                * reputation (`float`) -- DEPRECATED since 2020-04-05
                * rolling_score_rep (`float`)
                * rank (`int`)
                * leaderboardBonus (`float` or None)
                * date (`datetime`)
                * averageCorrelationPayout (`float` or None)
                * averageCorrelation (`float`)
                * sumDeltaCorrelation (`float`)
                * finalCorrelation (`float`)
                * payoutPending (`float` or None)
                * payoutSettled (`float` or None)

        Example:
            >>> api = NumerAPI()
            >>> api.daily_user_performances("uuazed")
            [{'tier': 'A',
              'stakeValue': None,
              'reputation': 0.0017099,
              'rolling_score_rep': 0.0111,
              'rank': 32,
              'leaderboardBonus': None,
              'date': datetime.datetime(2019, 10, 16, 0, 0),
              'averageCorrelationPayout': None,
              'averageCorrelation': -0.000983637,
              'sumDeltaCorrelation': -0.000983637,
              'finalCorrelation': -0.000983637,
              'payoutPending': None,
              'payoutSettled': None},
              ...
            ]
        """
        query = """
          query($username: String!) {
            v2UserProfile(username: $username) {
              dailyUserPerformances {
                averageCorrelation
                averageCorrelationPayout
                sumDeltaCorrelation
                finalCorrelation
                payoutPending
                payoutSettled
                date
                leaderboardBonus
                rank
                reputation
                rolling_score_rep
                stakeValue
                tier
              }
            }
          }
        """
        arguments = {'username': username}
        data = self.raw_query(query, arguments)['data']['v2UserProfile']
        performances = data['dailyUserPerformances']
        # convert strings to python objects
        for perf in performances:
            utils.replace(perf, "date", utils.parse_datetime_string)
        return performances

    def round_details(self, round_num: int) -> List[Dict]:
        """Fetch all correlation scores of a round.

        Args:
            round_num (int)

        Returns:
            list of dicts: list containing scores for each user

            For each entry in the list, there is a dict with the following
            content:

                * date (`datetime`)
                * correlation (`float`)
                * username (`str`)

        Example:
            >>> api = NumerAPI()
            >>> api.round_details(180)
            [{'username': 'abcd',
              'date': datetime.datetime(2019, 11, 15, 0, 0),
              'correlation': 0.02116131087},
              ...
            ]
        """
        query = """
          query($roundNumber: Int!) {
            v2RoundDetails(roundNumber: $roundNumber) {
              userPerformances {
                date
                correlation
                username
              }
            }
          }
        """
        arguments = {'roundNumber': round_num}
        data = self.raw_query(query, arguments)['data']['v2RoundDetails']
        performances = data['userPerformances']
        # convert strings to python objects
        for perf in performances:
            utils.replace(perf, "date", utils.parse_datetime_string)
        return performances

    def daily_submissions_performances(self, username: str) -> List[Dict]:
        """Fetch daily performance of a user's submissions.

        Args:
            username (str)

        Returns:
            list of dicts: list of daily submission performance entries

            For each entry in the list, there is a dict with the following
            content:

                * date (`datetime`)
                * correlation (`float`)
                * roundNumber (`int`)
                * mmc (`float`)
                * correlationWithMetamodel (`float`)

        Example:
            >>> api = NumerAPI()
            >>> api.daily_user_performances("uuazed")
            [{'roundNumber': 181,
              'correlation': -0.011765912,
              'date': datetime.datetime(2019, 10, 16, 0, 0),
              'mmc': 0.3,
              'correlationWithMetamodel': 0.87},
              ...
            ]
        """
        query = """
          query($username: String!) {
            v2UserProfile(username: $username) {
              dailySubmissionPerformances {
                date
                correlation
                roundNumber
                mmc
                correlationWithMetamodel
              }
            }
          }
        """
        arguments = {'username': username}
        data = self.raw_query(query, arguments)['data']['v2UserProfile']
        performances = data['dailySubmissionPerformances']
        # convert strings to python objects
        for perf in performances:
            utils.replace(perf, "date", utils.parse_datetime_string)
        return performances
