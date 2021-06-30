# -*- coding: utf-8 -*-

# System
import zipfile
import os
import datetime
import decimal
from typing import List, Dict
from io import BytesIO

# Third Party
import requests
import pytz
import pandas as pd

from numerapi import utils
from numerapi import base_api


class NumerAPI(base_api.Api):
    """Wrapper around the Numerai API

    Automatically download and upload data for the Numerai machine learning
    competition.

    This library is a Python client to the Numerai API. The interface is
    implemented in Python and allows downloading the training data, uploading
    predictions, accessing user, submission and competitions information and
    much more.
    """

    PUBLIC_DATASETS_URL = \
        "https://numerai-public-datasets.s3-us-west-2.amazonaws.com"

    def __init__(self, *args, **kwargs):
        base_api.Api.__init__(self, *args, **kwargs)
        self.tournament_id = 8

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
              -- DEPRECATED there is only one tournament nowadays

        Returns:
            str: url of the current dataset

        Example:
            >>> NumerAPI().get_dataset_url()
            https://numerai-datasets.s3.amazonaws.com/t1/104/n.........
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
                -- DEPRECATED there is only one tournament nowadays

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

    def get_latest_data_url(self, data_type: str,
                            extension: str = "csv") -> str:
        """Fetch url of the latest data url for a specified data type

        Args:
            data_type (str): type of data to return
            extension (str): file extension to get (optional, defaults to csv)

        Returns:
            str: url of the requested dataset

        Example:
            >>> url = NumerAPI().get_latest_data_url("live", "csv")
            >>> numerapi.utils.download_file(url, ".")
        """
        valid_extensions = ["csv", "csv.xz", "parquet"]
        valid_data_types = [
            "live",
            "training",
            "validation",
            "test",
            "max_test_era",
            "tournament",
            "tournament_ids",
            "example_predictions",
        ]

        # Allow extension to have a "." as the first character
        extension = extension.lstrip(".")

        # Validate arguments
        if extension not in valid_extensions:
            msg = f"extension must be set to one of {valid_extensions}"
            raise ValueError(msg)

        if data_type not in valid_data_types:
            raise ValueError(
                f"data_type must be set to one of {valid_data_types}")

        url = (f"{self.PUBLIC_DATASETS_URL}/"
               f"latest_numerai_{data_type}_data.{extension}")

        return url

    def download_latest_data(self, data_type: str, extension: str = "csv",
                             dest_path: str = ".", dest_filename: str = None):
        # set up download path
        if dest_filename is None:
            dest_filename = f"latest_numerai_{data_type}_data.{extension}"

        dataset_path = os.path.join(dest_path, dest_filename)

        # create parent folder if necessary
        utils.ensure_directory_exists(dest_path)

        url = self.get_latest_data_url(data_type, extension)
        utils.download_file(url, dataset_path, self.show_progress_bars)

    def get_competitions(self, tournament=8):
        """Retrieves information about all competitions

        Args:
            tournament (int, optional): ID of the tournament, defaults to 8
                -- DEPRECATED there is only one tournament nowadays

        Returns:
            list of dicts: list of rounds

            Each round's dict contains the following items:

                * number (`int`)
                * openTime (`datetime`)
                * resolveTime (`datetime`)
                * resolvedGeneral (`bool`)
                * resolvedStaking (`bool`)

        Example:
            >>> NumerAPI().get_competitions()
            [
             {'number': 71,
              'openTime': datetime.datetime(2017, 8, 31, 0, 0),
              'resolveTime': datetime.datetime(2017, 9, 27, 21, 0),
              'resolvedGeneral': True,
              'resolvedStaking': True,
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
                openTime
                resolvedGeneral
                resolvedStaking
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
        return rounds

    def get_submission_filenames(self, tournament=None, round_num=None,
                                 model_id=None) -> List[Dict]:
        """Get filenames of the submission of the user.

        Args:
            tournament (int): optionally filter by ID of the tournament
                -- DEPRECATED there is only one tournament nowadays
            round_num (int): optionally filter round number
            model_id (str): Target model UUID (required for accounts with
                multiple models)

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
        data = self.raw_query(
            query, arguments, authorization=True)['data']['model']

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

    def get_user(self, model_id: str = None) -> Dict:
        """Get all information about you! DEPRECATED

        Args:
            model_id (str): Target model UUID (required for accounts with
                multiple models)

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
        data = self.raw_query(
            query, arguments, authorization=True)['data']['user']
        # convert strings to python objects
        utils.replace(data, "insertedAt", utils.parse_datetime_string)
        utils.replace(data, "availableUsd", utils.parse_float_string)
        utils.replace(data, "availableNmr", utils.parse_float_string)
        return data

    def submission_status(self, model_id: str = None) -> Dict:
        """submission status of the last submission associated with the account

        Args:
            model_id (str)

        Returns:
            dict: submission status with the following content:

                * filename (`string`)
                * corrWithExamplePreds (`float`)
                * validationCorrelation (`float`)
                * validationCorrelationRating (`float`)
                * validationSharpe (`float`)
                * validationSharpeRating  (`float`)
                * validationFeatureNeutralMean (`float`)
                * validationFeatureNeutralMeanRating (`float`)
                * validationStd (`float`)
                * validationStdRating (`float`)
                * validationMaxFeatureExposure (`float`)
                * validationMaxFeatureExposureRating (`float`)
                * validationMaxDrawdown (`float`)
                * validationMaxDrawdownRating (`float`)
                * validationCorrPlusMmcSharpe (`float`)
                * validationCorrPlusMmcSharpeRating (`float`)
                * validationMmcMean (`float`)
                * validationMmcMeanRating (`float`)
                * validationCorrPlusMmcSharpeDiff (`float`)
                * validationCorrPlusMmcSharpeDiffRating (`float`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model_id = api.get_models()['uuazed']
            >>> api.submission_status(model_id)
            {'corrWithExamplePreds': 0.7217288907243551,
             'filename': 'model57-HPzOyr56TPaD.csv',
             'validationCorrPlusMmcSharpe': 1.0583461013814541,
             'validationCorrPlusMmcSharpeDiff': -0.23505145970149166,
             'validationCorrPlusMmcSharpeDiffRating': 0.02989708059701668,
             'validationCorrPlusMmcSharpeRating': 0.7123167873588739,
             'validationCorrelation': 0.023244452475027225,
             'validationCorrelationRating': 0.6026148514721896,
             'validationFeatureExposure': None,
             'validationFeatureNeutralMean': 0.019992061095211483,
             'validationFeatureNeutralMeanRating': 0.7689254267389032,
             'validationMaxDrawdown': -0.03710774157542396,
             'validationMaxDrawdownRating': 0.8099139824952893,
             'validationMaxFeatureExposure': 0.17339716040222303,
             'validationMaxFeatureExposureRating': 0.9200079988669775,
             'validationMmcMean': 0.0027797270044420106,
             'validationMmcMeanRating': 0.615821958518417,
             'validationSharpe': 1.2933975610829458,
             'validationSharpeRating': 0.9921399536701735,
             'validationStd': 0.017971622318171787,
             'validationStdRating': 0.9842992879669488}
        """
        query = '''
            query($modelId: String) {
                model(modelId: $modelId) {
                  latestSubmission {
                    filename
                    corrWithExamplePreds
                    validationCorrelation
                    validationSharpe
                    validationFeatureExposure
                    validationCorrelation
                    validationCorrelationRating
                    validationSharpe
                    validationSharpeRating
                    validationFeatureNeutralMean
                    validationFeatureNeutralMeanRating
                    validationStd
                    validationStdRating
                    validationMaxFeatureExposure
                    validationMaxFeatureExposureRating
                    validationMaxDrawdown
                    validationMaxDrawdownRating
                    validationCorrPlusMmcSharpe
                    validationCorrPlusMmcSharpeRating
                    validationMmcMean
                    validationMmcMeanRating
                    validationCorrPlusMmcSharpeDiff
                    validationCorrPlusMmcSharpeDiffRating
                  }
                }
              }
            '''

        args = {'modelId': model_id}
        data = self.raw_query(query, args, authorization=True)
        status = data['data']['model']['latestSubmission'][0]
        return status

    def upload_predictions(self, file_path: str = "predictions.csv",
                           tournament: int = 8,
                           model_id: str = None,
                           df: pd.DataFrame = None) -> str:
        """Upload predictions from file.
        Will read TRIGGER_ID from the environment if this model is enabled with
        a Numerai Compute cluster setup by Numerai CLI.

        Args:
            file_path (str): CSV file with predictions that will get uploaded
            tournament (int): ID of the tournament (optional, defaults to 8)
                -- DEPRECATED there is only one tournament nowadays
            model_id (str): Target model UUID (required for accounts with
                multiple models)
            df (pandas.DataFrame): pandas DataFrame to upload, if function is
                given df and file_path, df will be uploaded.

        Returns:
            str: submission_id

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model_id = api.get_models()['uuazed']
            >>> api.upload_predictions("prediction.cvs", model_id=model_id)
            '93c46857-fed9-4594-981e-82db2b358daf'
            >>> # upload from pandas DataFrame directly:
            >>> api.upload_predictions(df=predictions_df, model_id=model_id)
        """
        self.logger.info("uploading predictions...")

        # write the pandas DataFrame as a binary buffer if provided
        buffer_csv = None

        if df is not None:
            buffer_csv = BytesIO(df.to_csv(index=False).encode())
            buffer_csv.name = file_path

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

        # get compute id if available and pass it along
        headers = {"x_compute_id": os.getenv("NUMERAI_COMPUTE_ID")}
        with open(file_path, 'rb') if df is None else buffer_csv as fh:
            requests.put(
                submission_auth['url'], data=fh.read(), headers=headers)
        create_query = '''
            mutation($filename: String!
                     $tournament: Int!
                     $modelId: String
                     $triggerId: String) {
                create_submission(filename: $filename
                                  tournament: $tournament
                                  modelId: $modelId
                                  triggerId: $triggerId) {
                    id
                }
            }
            '''
        arguments = {'filename': submission_auth['filename'],
                     'tournament': tournament,
                     'modelId': model_id,
                     'triggerId': os.getenv('TRIGGER_ID', None)}
        create = self.raw_query(create_query, arguments, authorization=True)
        submission_id = create['data']['create_submission']['id']
        return submission_id

    def check_new_round(self, hours: int = 24, tournament: int = 8) -> bool:
        """Check if a new round has started within the last `hours`.

        Args:
            hours (int, optional): timeframe to consider, defaults to 24
            tournament (int): ID of the tournament (optional, defaults to 8)
                -- DEPRECATED there is only one tournament nowadays

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
            float: current stake (including projected NMR earnings from open
                   rounds)

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

    def stake_change(self, nmr, action: str = "decrease",
                     model_id: str = None, tournament: int = 8) -> Dict:
        """Change stake by `value` NMR.

        Args:
            nmr (float or str): amount of NMR you want to increase/decrease
            action (str): `increase` or `decrease`
            model_id (str): Target model UUID (required for accounts with
                multiple models)
            tournament (int): ID of the tournament (optional, defaults to 8)
                -- DEPRECATED there is only one tournament nowadays

        Returns:
            dict: stake information with the following content:

              * dueDate (`datetime`)
              * status (`str`)
              * requestedAmount (`decimal.Decimal`)
              * type (`str`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model = api.get_models()['uuazed']
            >>> api.stake_change(10, "decrease", model)
            {'dueDate': None,
             'requestedAmount': decimal.Decimal('10'),
             'type': 'decrease',
             'status': ''}
        """
        query = '''
          mutation($value: String!
                   $type: String!
                   $tournamentNumber: Int!
                   $modelId: String) {
              v2ChangeStake(value: $value
                            type: $type
                            modelId: $modelId
                            tournamentNumber: $tournamentNumber) {
                dueDate
                requestedAmount
                status
                type
              }
        }
        '''
        arguments = {'value': str(nmr),
                     'type': action,
                     'modelId': model_id,
                     'tournamentNumber': tournament}
        result = self.raw_query(query, arguments, authorization=True)
        stake = result['data']['v2ChangeStake']
        utils.replace(stake, "requestedAmount", utils.parse_float_string)
        utils.replace(stake, "dueDate", utils.parse_datetime_string)
        return stake

    def stake_drain(self, model_id: str = None, tournament: int = 8) -> Dict:
        """Completely remove your stake.

        Args:
            model_id (str): Target model UUID (required for accounts with
                multiple models)
            tournament (int): ID of the tournament (optional, defaults to 8)
                -- DEPRECATED there is only one tournament nowadays

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
        return self.stake_decrease(11000000, model_id, tournament)

    def stake_decrease(self, nmr, model_id: str = None,
                       tournament: int = 8) -> Dict:
        """Decrease your stake by `value` NMR.

        Args:
            nmr (float or str): amount of NMR you want to reduce
            model_id (str): Target model UUID (required for accounts with
                multiple models)
            tournament (int): ID of the tournament (optional, defaults to 8)
                -- DEPRECATED there is only one tournament nowadays

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
        return self.stake_change(nmr, 'decrease', model_id, tournament)

    def stake_increase(self, nmr, model_id: str = None,
                       tournament: int = 8) -> Dict:
        """Increase your stake by `value` NMR.

        Args:
            nmr (float or str): amount of additional NMR you want to stake
            model_id (str): Target model UUID (required for accounts with
                multiple models)
            tournament (int): ID of the tournament (optional, defaults to 8)
                -- DEPRECATED there is only one tournament nowadays

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
        return self.stake_change(nmr, 'increase', model_id, tournament)

    def public_user_profile(self, username: str) -> Dict:
        """Fetch the public profile of a user.

        Args:
            username (str)

        Returns:
            dict: user profile including the following fields:
                * username (`str`)
                * startDate (`datetime`)
                * id (`string`)
                * bio (`str`)
                * totalStake (`float`)

        Example:
            >>> api = NumerAPI()
            >>> api.public_user_profile("integration_test")
            {'bio': 'The official example model. Submits example predictions.',
             'id': '59de8728-38e5-45bd-a3d5-9d4ad649dd3f',
             'startDate': datetime.datetime(
                2018, 6, 6, 17, 33, 21, tzinfo=tzutc()),
             'totalStake': '57.582371875005243780',
             'username': 'integration_test'}

        """
        query = """
          query($username: String!) {
            v2UserProfile(username: $username) {
              id
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

                * stakeValue (`float` or none)
                * rank (`int`)
                * date (`datetime`)
                * payoutPending (`float` or None)
                * payoutSettled (`float` or None)
                * corrRep (`float` or None)
                * mmcRep (`float` or None)
                * fncRep (`float` or None)

        Example:
            >>> api = NumerAPI()
            >>> api.daily_user_performances("uuazed")
            [{'corrRep': 0.04989791277211584,
             'date': datetime.datetime(2021, 6, 29, 0, 0, tzinfo=tzutc()),
             'fncRep': 0.013364783709176759,
             'mmcRep': 0.006799019156483222,
             'payoutPending': '5.979926674348371782',
             'payoutSettled': None,
             'rank': 559,
             'stakeValue': '226.746596100340180000'},
             ...
            ]
        """
        query = """
          query($username: String!) {
            v2UserProfile(username: $username) {
              dailyUserPerformances {
                corrRep
                date
                fncRep
                mmcRep
                payoutPending
                payoutSettled
                rank
                stakeValue
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
                * mmc (`float`): metamodel contribution
                * fnc (`float`): feature neutral correlation
                * correlationWithMetamodel (`float`)

        Example:
            >>> api = NumerAPI()
            >>> api.daily_user_performances("uuazed")
            [{'roundNumber': 181,
              'correlation': -0.011765912,
              'date': datetime.datetime(2019, 10, 16, 0, 0),
              'mmc': 0.3,
              'fnc': 0.1,
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
                fnc
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
        # remove useless items
        performances = [p for p in performances
                        if any([p['correlation'], p['fnc'], p['mmc']])]
        return performances
