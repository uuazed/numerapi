# -*- coding: utf-8 -*-

from __future__ import absolute_import

# System
import zipfile
import os
import logging
import datetime
import decimal

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

    def get_dataset_url(self, tournament=1):
        """Fetch url of the current dataset.

        Args:
            tournament (int, optional): ID of the tournament, defaults to 1

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
                                 unzip=True, tournament=1):
        """Download dataset for the current active round.

        Args:
            dest_path (str, optional): destination folder, defaults to `.`
            dest_filename (str, optional): desired filename of dataset file,
                defaults to `numerai_dataset_<round number>.zip`
            unzip (bool, optional): indication of whether the training data
                should be unzipped, defaults to `True`
            tournament (int, optional): ID of the tournament, defaults to 1

        Returns:
            str: Path to the downloaded dataset

        Example:
            >>> NumerAPI().download_current_dataset()
            ./numerai_dataset_104.zip
        """
        # set up download path
        if dest_filename is None:
            round_number = self.get_current_round()
            dest_filename = "numerai_dataset_{0}.zip".format(round_number)
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
                headers['Authorization'] = \
                    'Token {}${}'.format(public_id, secret_key)
            else:
                raise ValueError("API keys required for this action.")
        r = requests.post(API_TOURNAMENT_URL, json=body, headers=headers)
        result = r.json()
        if "errors" in result:
            err = self._handle_call_error(result['errors'])
            # fail!
            raise ValueError(err)

        return result

    def get_leaderboard(self, round_num=0, tournament=1):
        """Retrieves the leaderboard for the given round.

        Args:
            round_num (int, optional): The round you are interested in,
                defaults to current round.
            tournament (int, optional): ID of the tournament, defaults to 1

        Returns:
            list of dicts: list of participants

            For each user in the list, there is a dict with the following
            content:

                * concordance (`dict`)
                 * pending (`bool`)
                 * value (`bool`)
                * consistency (`float`)
                * liveLogloss (`float` or `None`)
                * validationLogloss (`float`)
                * paymentGeneral (`dict` or `None`)
                 * nmrAmount (`decimal.Decimal`)
                 * usdAmount (`decimal.Decimal`)
                * paymentStaking (`dict` or `None`)
                 * nmrAmount (`decimal.Decimal`)
                 * usdAmount (`decimal.Decimal`)
                * submissionId (`str`)
                * totalPayments (`dict`)
                 * nmrAmount (`decimal.Decimal`)
                 * usdAmount (`decimal.Decimal`)
                * username (`str`)
                * stakeResolution (`dict`)
                 * destroyed (`bool`)
                 * paid (`decimal.Decimal`)
                 * successful ('bool')

        Example:
            >>> NumerAPI().get_leaderboard(99)
            [{'concordance': {'pending': False, 'value': True},
              'consistency': 83.33333333333334,
              'liveLogloss': 0.6941153941722517,
              'paymentGeneral': None,
              'paymentStaking': None,
              'submissionId': '4459d3df-0a4b-4996-ad44-41abb7c45336',
              'totalPayments': {'nmrAmount': Decimal('163.05'),
                                'usdAmount': Decimal('40.75')},
              'stakeResolution': {'destroyed': False,
                                  'paid': Decimal('19.86'),
                                  'successful': True},
              'username': 'ci_wp',
              'validationLogloss': 0.692269984475575},
             ...
            ]
        """
        msg = "getting leaderboard for tournament {} round {}"
        self.logger.info(msg.format(tournament, round_num))
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
                  submissionId
                  username
                  validationLogloss
                  paymentGeneral {
                    nmrAmount
                    usdAmount
                  }
                  paymentStaking {
                    nmrAmount
                    usdAmount
                  }
                  totalPayments {
                    nmrAmount
                    usdAmount
                  }
                  stakeResolution {
                    destroyed
                    paid
                    successful
                  }
                }
              }
            }
        '''
        arguments = {'number': round_num, 'tournament': tournament}
        result = self.raw_query(query, arguments)['data']['rounds'][0]
        # happens for non-existent tournament IDs
        if result is None:
            return None
        leaderboard = result['leaderboard']
        # parse to correct data types
        for item in leaderboard:
            for p in ["totalPayments", "paymentGeneral", "paymentStaking"]:
                utils.replace(item[p], "nmrAmount", utils.parse_float_string)
                utils.replace(item[p], "usdAmount", utils.parse_float_string)
            utils.replace(item['stakeResolution'], "paid",
                          utils.parse_float_string)
        return leaderboard

    def get_staking_leaderboard(self, round_num=0, tournament=1):
        """Retrieves the leaderboard of the staking competition for the given
        round.

        Args:
            round_num (int, optional): The round you are interested in,
                defaults to current round.
            tournament (int, optional): ID of the tournament, defaults to 1

        Returns:
            list: list of stakers (`dict`)

            Each stake in the list as the following structure:

                * username (`str`)
                * consistency (`float`)
                * liveLogloss (`float` or `None`)
                * validationLogloss (`float`)
                * stake (`dict`)
                 * confidence (`decimal.Decimal`)
                 * insertedAt (`datetime`)
                 * soc (`decimal.Decimal`)
                 * txHash (`str`)
                 * value (`decimal.Decimal`)

        Example:
            >>> NumerAPI().get_staking_leaderboard(99)
            [{'consistency': 83.33333333333334,
              'liveLogloss': 0.6941153941722517,
              'stake': {'confidence': Decimal('0.055'),
               'insertedAt': datetime.datetime(2018, 3, 18, 0, 20, 31, 724728, tzinfo=tzutc()),
               'soc': Decimal('18.18'),
               'txHash': '0xf1460c7fe08e7920d3e61492501337db5c89bff22af9fd88b9ff1ad604939f61',
               'value': Decimal('1.00')},
              'username': 'ci_wp',
              'validationLogloss': 0.692269984475575},
              ..
            ]
        """
        msg = "getting stakes for tournament {} round {}"
        self.logger.info(msg.format(tournament, round_num))
        query = '''
            query($number: Int!
                  $tournament: Int!) {
              rounds(number: $number
                     tournament: $tournament) {
                leaderboard {
                  consistency
                  liveLogloss
                  username
                  validationLogloss
                  stake {
                    insertedAt
                    soc
                    confidence
                    value
                    txHash
                  }
                }
              }
            }
        '''
        arguments = {'number': round_num, 'tournament': tournament}
        result = self.raw_query(query, arguments)['data']['rounds'][0]
        if result is None:
            return None
        stakes = result['leaderboard']
        # filter those with actual stakes
        stakes = [item for item in stakes if item["stake"]["soc"] is not None]
        # convert strings to python objects
        for s in stakes:
            utils.replace(s["stake"], "insertedAt",
                          utils.parse_datetime_string)
            utils.replace(s["stake"], "confidence", utils.parse_float_string)
            utils.replace(s["stake"], "soc", utils.parse_float_string)
            utils.replace(s["stake"], "value", utils.parse_float_string)
        return stakes

    def get_nmr_prize_pool(self, round_num=0, tournament=1):
        """Get NMR prize pool for the given round and tournament.

        Args:
            round_num (int, optional): The round you are interested in,
                defaults to current round.
            tournament (int, optional): ID of the tournament, defaults to 1

        Returns:
            decimal.Decimal: prize pool in NMR

        Raises:
            Value Error: in case of invalid round number
        """
        tournaments = self.get_competitions(tournament)
        tournaments.sort(key=lambda t: t['number'])
        if round_num == 0:
            t = tournaments[-1]
        else:
            tournaments = [t for t in tournaments if t['number'] == round_num]
            if len(tournaments) == 0:
                raise ValueError("invalid round number")
            t = tournaments[0]
        return t['prizePoolNmr']

    def get_staking_cutoff(self, round_num=0, tournament=1):
        """Compute staking cutoff for the given round and tournament.

        Args:
            round_num (int, optional): The round you are interested in,
                defaults to current round.
            tournament (int, optional): ID of the tournament, defaults to 1

        Returns:
            decimal.Decimal: cutoff probability

        Raises:
            ValueError: in case of missing prize pool information
        """
        stakes = [item['stake'] for item
                  in self.get_staking_leaderboard(
                      tournament=tournament, round_num=round_num)]
        stakes.sort(
            key=lambda stake: (stake['confidence'], stake['insertedAt']),
            reverse=True)
        prize_pool = self.get_nmr_prize_pool(round_num, tournament)
        if prize_pool == 0:
            raise ValueError("prize pool = 0 in that round")
        cumsum = 0
        for stake in stakes:
            confidence = stake['confidence']
            cumsum += stake['value']
            payout = cumsum * (1- confidence) / confidence
            if payout <= prize_pool:
                cutoff = confidence
                cutoff_cumsum = cumsum
            else:
                break
        # lower cutoff even if there are no stakes at that confidence
        while cutoff_cumsum * (1- cutoff) / cutoff <= prize_pool:
            cutoff -= decimal.Decimal('0.001')
        return cutoff

    def get_competitions(self, tournament=1):
        """Retrieves information about all competitions

        Args:
            tournament (int, optional): ID of the tournament, defaults to 1

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
              'resolvedStaking': True
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

    def get_current_round(self, tournament=1):
        """Get number of the current active round.

        Args:
            tournament (int): ID of the tournament (optional, defaults to 1)

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

    def get_tournaments(self):
        """Get all active tournaments

        Returns:
            list of dicts: list of tournaments

            Each tournaments' dict contains the following items:

                * id (`str`)
                * name (`str`)
                * tournament (`int`)

        Example:
            >>> NumerAPI().get_tournaments()
            [ { 'id': '2ecf30f4-4b4f-42e9-8e72-cc5bd61c2733',
                'name': 'alpha',
                'tournament': 1},
              { 'id': '6ff44cca-263d-40bd-b029-a1ab8f42798f',
                'name': 'bravo',
                'tournament': 2},
              { 'id': 'ebf0d62b-0f60-4550-bcec-c737b168c65d',
                'name': 'charlie',
                'tournament': 3},
              { 'id': '5fac6ece-2726-4b66-9790-95866b3a77fc',
                'name': 'delta',
                'tournament': 4},
              { 'id': 'f993b7db-83ce-4efd-ae26-10900d422e72',
                'name': 'echo',
                'tournament': 5}]
        """
        query = """
            query {
              tournaments {
                id
                name
                tournament
            }
        }
        """
        data = self.raw_query(query)['data']['tournaments']
        return data

    def get_user_activities(self, username, tournament=1):
        """Get user activities (works for all users!).

        Args:
            username (str): name of the user
            tournament (int): ID of the tournament (optional, defaults to 1)

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
                 * validationLogloss (`float`)
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
              'submission': {'validationLogloss': 0.6928141372700635,
               'liveLogloss': None,
               'date': datetime.datetime(2018, 7, 14, 17, 5, 27, 206042, tzinfo=tzutc()),
               'consistency': 83.33333333333334,
               'concordance': True},
              'stake': {'value': Decimal('0.10'),
               'usdEarned': None,
               'staked': True,
               'nmrEarned': None,
               'date': datetime.datetime(2018, 7, 14, 17, 7, 7, 877845, tzinfo=tzutc()),
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
                    validationLogloss
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
            if item['stake']['date'] is None:
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

    def get_submission_filenames(self, tournament=None, round_num=None):
        """Get filenames of the submission of the user.

        Args:
            tournament (int): optionally filter by ID of the tournament
            round_num (int): optionally filter round number

        Returns:
            list: list of user filenames (`dict`)

            Each filenames in the list as the following structure:

                * filename (`str`)
                * round_num (`int`)
                * tournament (`int`)

        Example:
            >>> NumerAPI().get_submission_filenames(3, 111)
            [{'filename': 'model57-dMpHpYMPIUAF.csv',
              'round_num': 111,
              'tournament': 3}]

        """
        query = '''
          query {
            user {
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
        '''
        data = self.raw_query(query, authorization=True)['data']['user']

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

    def get_rankings(self, limit=50, offset=0):
        """Get the overall ranking

        Args:
            limit (int): number of items to return (optional, defaults to 50)
            offset (int): number of items to skip (optional, defaults to 0)

        Returns:
            list of dicts: list of ranking items

            Each dict contains the following items:

                * id (`str`)
                * username (`str`)
                * nmrBurned (`decimal.Decimal`)
                * nmrPaid (`decimal.Decimal`)
                * nmrStaked (`decimal.Decimal`)
                * rep (`int`)
                * stakeCount (`int`)
                * usdEarned (`decimal.Decimal`)

        Example:
            >>> numerapi.NumerAPI().get_rankings(1)
            [{'username': 'glasperlenspiel',
              'usdEarned': Decimal('16347.12'),
              'stakeCount': 41,
              'rep': 14,
              'nmrStaked': Decimal('250.000000000000000000'),
              'nmrPaid': Decimal('16061.37'),
              'nmrBurned': Decimal('295.400000000000000000'),
              'id': 'bbee4f0e-f238-4d8a-8f1b-5eb384cdcbfc'}]
        """
        query = '''
            query($limit: Int!
                  $offset: Int!) {
              rankings(limit: $limit
                       offset: $offset) {
                username
                id
                nmrBurned
                nmrPaid
                nmrStaked
                rep
                stakeCount
                usdEarned
              }
            }
        '''
        arguments = {'limit': limit, 'offset': offset}
        data = self.raw_query(query, arguments)['data']['rankings']
        for item in data:
            for p in ["nmrBurned", "nmrPaid", "nmrStaked", "usdEarned"]:
                utils.replace(item, p, utils.parse_float_string)
        return data

    def get_submission_ids(self, tournament=1):
        """Get dict with username->submission_id mapping.

        Args:
            tournament (int): ID of the tournament (optional, defaults to 1)

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

    def get_user(self):
        """Get all information about you!

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
                * apiTokens (`list`) each with the following fields:
                 * name (`str`)
                 * public_id (`str`)
                 * scopes (`list of str`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> api.get_user()
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
             'id': '1234-ABC..',
             'insertedAt': datetime.datetime(2018, 1, 1, 2, 16, 48),
             'mfaEnabled': False,
             'status': 'VERIFIED',
             'username': 'cool username'
             }
        """
        query = """
          query {
            user {
              username
              banned
              assignedEthAddress
              availableNmr
              availableUsd
              email
              id
              mfaEnabled
              status
              insertedAt
              apiTokens {
                name
                public_id
                scopes
              }
            }
          }
        """
        data = self.raw_query(query, authorization=True)['data']['user']
        # convert strings to python objects
        utils.replace(data, "insertedAt", utils.parse_datetime_string)
        utils.replace(data, "availableUsd", utils.parse_float_string)
        utils.replace(data, "availableNmr", utils.parse_float_string)
        return data

    def get_payments(self):
        """Get all your payments.

        Returns:
            list of dicts: payments

            For each payout in the list, a dict contains the following items:

                * nmrAmount (`decimal.Decimal`)
                * usdAmount (`decimal.Decimal`)
                * tournament (`str`)
                * round (`dict`)
                 * number (`int`)
                 * openTime (`datetime`)
                 * resolveTime (`datetime`)
                 * resolvedGeneral (`bool`)
                 * resolvedStaking (`bool`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> api.get_payments()
            [{'nmrAmount': Decimal('0.00'),
              'round': {'number': 84,
               'openTime': datetime.datetime(2017, 12, 2, 18, 0, tzinfo=tzutc()),
               'resolveTime': datetime.datetime(2018, 1, 1, 18, 0, tzinfo=tzutc()),
               'resolvedGeneral': True,
               'resolvedStaking': True},
              'tournament': 'staking',
              'usdAmount': Decimal('17.44')},
              ...
             ]
    """
        query = """
          query {
            user {
              payments {
                nmrAmount
                round {
                  number
                  openTime
                  resolveTime
                  resolvedGeneral
                  resolvedStaking
                }
                tournament
                usdAmount
              }
            }
          }
        """
        data = self.raw_query(query, authorization=True)['data']
        payments = data['user']['payments']
        # convert strings to python objects
        for p in payments:
            utils.replace(p['round'], "openTime", utils.parse_datetime_string)
            utils.replace(p['round'], "resolveTime",
                          utils.parse_datetime_string)
            utils.replace(p, "usdAmount", utils.parse_float_string)
            utils.replace(p, "nmrAmount", utils.parse_float_string)
        return payments

    def get_transactions(self):
        """Get all your deposits and withdrawals.

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
                * nmrWithdrawals"` (`list`) contains items with fields:
                 * from"` (`str`)
                 * posted"` (`bool`)
                 * status"` (`str`)
                 * to"` (`str`)
                 * txHash"` (`str`)
                 * value"` (`decimal.Decimal`)
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
            >>> api.get_transactions()
            {'nmrDeposits': [
                {'from': '0x54479..9ec897a',
                 'posted': True,
                 'status': 'confirmed',
                 'to': '0x0000000000000000000001',
                 'txHash': '0x52..e2056ab',
                 'value': Decimal('9.0')},
                 .. ],
             'nmrWithdrawals': [
                {'from': '0x0000000000000000..002',
                 'posted': True,
                 'status': 'confirmed',
                 'to': '0x00000000000..001',
                 'txHash': '0x1278..266c',
                 'value': Decimal('2.0')},
                 .. ],
             'usdWithdrawals': [
                {'confirmTime': datetime.datetime(2018, 2, 11, 17, 54, 2, 785430, tzinfo=tzutc()),
                 'ethAmount': '0.295780674909307710',
                 'from': '0x11.....',
                 'posted': True,
                 'sendTime': datetime.datetime(2018, 2, 11, 17, 53, 25, 235035, tzinfo=tzutc()),
                 'status': 'confirmed',
                 'to': '0x81.....',
                 'txHash': '0x3c....',
                 'usdAmount': Decimal('10.07')},
                 ..]}
        """
        query = """
          query {
            user {
              nmrDeposits {
                from
                posted
                status
                to
                txHash
                value
              }
              nmrWithdrawals {
                from
                posted
                status
                to
                txHash
                value
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
        txs = self.raw_query(query, authorization=True)['data']['user']
        # convert strings to python objects
        for t in txs['usdWithdrawals']:
            utils.replace(t, "confirmTime", utils.parse_datetime_string)
            utils.replace(t, "sendTime", utils.parse_datetime_string)
            utils.replace(t, "usdAmount", utils.parse_float_string)
        for t in txs["nmrWithdrawals"]:
            utils.replace(t, "value", utils.parse_float_string)
        for t in txs["nmrDeposits"]:
            utils.replace(t, "value", utils.parse_float_string)
        return txs

    def get_stakes(self):
        """List all your stakes.

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
            >>> api.get_stakes()
            [{'confidence': Decimal('0.053'),
              'insertedAt': datetime.datetime(2017, 9, 26, 8, 18, 36, 709000, tzinfo=tzutc()),
              'roundNumber': 74,
              'soc': Decimal('56.60'),
              'staker': '0x0000000000000000000000000000000000003f9e',
              'status': 'confirmed',
              'tournamentId': 1,
              'txHash': '0x1cbb985629552a0f57b98a1e30a5e7f101a992121db318cef02e02aaf0e91c95',
              'value': Decimal('3.00')},
              ..
             ]
        """
        query = """
          query {
            user {
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
        data = self.raw_query(query, authorization=True)['data']
        stakes = data['user']['stakeTxs']
        # convert strings to python objects
        for s in stakes:
            utils.replace(s, "insertedAt", utils.parse_datetime_string)
            utils.replace(s, "soc", utils.parse_float_string)
            utils.replace(s, "confidence", utils.parse_float_string)
            utils.replace(s, "value", utils.parse_float_string)
        return stakes

    def submission_status(self, submission_id=None):
        """submission status of the last submission associated with the account.

        Args:
            submission_id (str): submission of interest, defaults to the last
                submission done with the account

        Returns:
            dict: submission status with the following content:

                * concordance (`dict`):
                 * pending (`bool`)
                 * value (`bool`): whether the submission is concordant
                * consistency (`float`): consistency of the submission
                * validationLogloss (`float`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> api.upload_predictions()
            >>> api.submission_status()
            {'concordance': {'pending': False, 'value': True},
             'consistency': 91.66666666666666,
             'validationLogloss': 0.691733023121}
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
                validationLogloss
              }
            }
            '''
        variable = {'submission_id': submission_id}
        data = self.raw_query(query, variable, authorization=True)
        status = data['data']['submissions'][0]
        return status

    def upload_predictions(self, file_path, tournament=1):
        """Upload predictions from file.

        Args:
            file_path (str): CSV file with predictions that will get uploaded
            tournament (int): ID of the tournament (optional, defaults to 1)

        Returns:
            str: submission_id

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> api.upload_predictions()
            '93c46857-fed9-4594-981e-82db2b358daf'
        """
        self.logger.info("uploading predictions...")

        auth_query = '''
            query($filename: String!
                  $tournament: Int!) {
                submission_upload_auth(filename: $filename
                                       tournament: $tournament) {
                    filename
                    url
                }
            }
            '''
        arguments = {'filename': os.path.basename(file_path),
                     'tournament': tournament}
        submission_resp = self.raw_query(auth_query, arguments,
                                         authorization=True)
        submission_auth = submission_resp['data']['submission_upload_auth']
        with open(file_path, 'rb') as fh:
            requests.put(submission_auth['url'], data=fh.read())
        create_query = '''
            mutation($filename: String!
                     $tournament: Int!) {
                create_submission(filename: $filename
                                  tournament: $tournament) {
                    id
                }
            }
            '''
        arguments = {'filename': submission_auth['filename'],
                     'tournament': tournament}
        create = self.raw_query(create_query, arguments, authorization=True)
        self.submission_id = create['data']['create_submission']['id']
        return self.submission_id

    def stake(self, confidence, value, tournament=1):
        """Participate in the staking competition.

        Args:
            confidence (float or str): your confidence (C) value
            value (float or str): amount of NMR you are willing to stake
            tournament (int): ID of the tournament (optional, defaults to 1)

        Returns:
            dict: stake information with the following content:

              * insertedAt (`datetime`)
              * status (`str`)
              * txHash (`str`)
              * value (`decimal.Decimal`)
              * from (`str`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> api.stake(0.1, 10)
            {'stake':
              {'from': None,
               'insertedAt': None,
               'status': None,
               'txHash': '0x76519...2341ca0',
               'value': '10'}
             }
        """

        query = '''
          mutation($code: String
            $confidence: String!
            $password: String
            $round: Int!
            $value: String!
            $tournament: Int!) {
              stake(code: $code
                    confidence: $confidence
                    password: $password
                    round: $round
                    value: $value
                    tournament: $tournament) {
                insertedAt
                status
                txHash
                value
                from
              }
        }
        '''
        arguments = {'code': 'somecode',
                     'confidence': str(confidence),
                     'password': "somepassword",
                     'round': self.get_current_round(),
                     'value': str(value),
                     'tournament': tournament}
        result = self.raw_query(query, arguments, authorization=True)
        stake = result['data']
        utils.replace(stake, "value", utils.parse_float_string)
        utils.replace(stake, "insertedAt", utils.parse_datetime_string)
        return stake

    def check_new_round(self, hours=24, tournament=1):
        """Check if a new round has started within the last `hours`.

        Args:
            hours (int, optional): timeframe to consider, defaults to 24
            tournament (int): ID of the tournament (optional, defaults to 1)

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

    def check_submission_successful(self, submission_id=None):
        """Check if the last submission passes submission criteria.

        Args:
            submission_id (str, optional): submission of interest, defaults to
                the last submission done with the account

        Return:
            bool: True if the submission passed all checks, False otherwise.

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> api.upload_predictions("predictions.csv")
            >>> api.check_submission_successful()
            True
        """
        status = self.submission_status(submission_id)
        # need to cast to bool to not return None in some cases.
        success = bool(status['consistency'] >= 58 and
                       status["concordance"]["value"])
        return success

    def tournament_number2name(self, number):
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

    def tournament_name2number(self, name):
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
