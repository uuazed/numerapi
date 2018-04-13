# -*- coding: utf-8 -*-

from __future__ import absolute_import

# System
import zipfile
import os
import logging
import datetime

# Third Party
import requests
import pytz

from numerapi import utils

API_TOURNAMENT_URL = 'https://api-tournament.numer.ai'


class NumerAPI(object):

    """Wrapper around the Numerai API"""

    def __init__(self, public_id=None, secret_key=None, verbosity="INFO",
                 show_progress_bars=True):
        """
        initialize Numerai API wrapper for Python

        public_id: first part of your token generated at
                   Numer.ai->Account->Custom API keys
        secret_key: second part of your token generated at
                    Numer.ai->Account->Custom API keys
        verbosity: indicates what level of messages should be displayed
            valid values: "debug", "info", "warning", "error", "critical"
        show_progress_bars: flag to turn of progress bars
        """

        # set up logging
        self.logger = logging.getLogger(__name__)
        numeric_log_level = getattr(logging, verbosity.upper())
        log_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
        logging.basicConfig(format=log_format, level=numeric_log_level)

        if public_id and secret_key:
            self.token = (public_id, secret_key)
        elif not public_id and not secret_key:
            self.token = None
        else:
            self.logger.warning(
                "You need to supply both a public id and a secret key.")
            self.token = None

        self.submission_id = None
        self.show_progress_bars = show_progress_bars

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

        tournament: ID of the tournament (optional, defaults to 1)

        Returns:
            str: url of the current dataset
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
        """download dataset for current round

        dest_path: desired location of dataset file (optional)
        dest_filename: desired filename of dataset file (optional)
        unzip: indicates whether to unzip dataset (optional)
        tournament: ID of the tournament (optional, defaults to 1)
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
        """send a raw request to the Numerai's GraphQL API

        query (str): the query
        variables (dict): dict of variables
        authorization (bool): does the request require authorization
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
        """ retrieves the leaderboard for the given round and tournament

        round_num: The round you are interested in, defaults to current round
        tournament: ID of the tournament (optional, defaults to 1)
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
                  originality {
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
        return leaderboard

    def get_staking_leaderboard(self, round_num=0, tournament=1):
        """ retrieves the leaderboard of the staking competition for the given
        round

        round_num: The round you are interested in, defaults to current round.
        tournament: ID of the tournament (optional, defaults to 1)
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
        # convert strings to pyton objects
        for s in stakes:
            utils.replace(s["stake"], "insertedAt",
                          utils.parse_datetime_string)
            utils.replace(s["stake"], "confidence", utils.parse_float_string)
            utils.replace(s["stake"], "soc", utils.parse_float_string)
            utils.replace(s["stake"], "value", utils.parse_float_string)
        return stakes

    def get_competitions(self, tournament=1):
        """ get information about tournament rounds

        tournament: ID of the tournament (optional, defaults to 1)
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

    def get_current_round(self, tournament=1):
        """get information about the current active round

        tournament: ID of the tournament (optional, defaults to 1)
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

    def get_submission_ids(self, tournament=1):
        """get dict with username->submission_id mapping

        tournament: ID of the tournament (optional, defaults to 1)
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
        """get all information about you! """
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
        """all your payments"""
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
        """all deposits and withdrawals"""
        query = """
          query {
            user {
              nmrDeposits {
                from
                id
                posted
                status
                to
                txHash
                value
              }
              nmrWithdrawals {
                from
                id
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
        """all your stakes"""
        query = """
          query {
            user {
              stakeTxs {
                confidence
                insertedAt
                roundNumber
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
        """display submission status of the last submission associated with
        the account

        submission_id: submission of interest, defaults to the last submission
            done with the account
        """
        if submission_id is None:
            submission_id = self.submission_id

        if submission_id is None:
            raise ValueError('You need to submit something first or provide\
                              a submission ID')

        query = '''
            query($submission_id: String!) {
              submissions(id: $submission_id) {
                originality {
                  pending
                  value
                }
                concordance {
                  pending
                  value
                }
                consistency
                validation_logloss
              }
            }
            '''
        variable = {'submission_id': submission_id}
        data = self.raw_query(query, variable, authorization=True)
        status = data['data']['submissions'][0]
        return status

    def upload_predictions(self, file_path, tournament=1):
        """uploads predictions from file

        file_path: CSV file with predictions that will get uploaded
        tournament: ID of the tournament (optional, defaults to 1)
        """
        self.logger.info("uploading prediction...")

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
        """ participate in the staking competition

        confidence: your confidence (C) value
        value: amount of NMR you are willing to stake
        tournament: ID of the tournament (optional, defaults to 1)
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
                id
                status
                txHash
                value
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
        return stake

    def check_new_round(self, hours=24, tournament=1):
        """ checks wether a new round has started within the last `hours`

        hours: timeframe to consider (optional, defaults to 24)
        tournament: ID of the tournament (optional, defaults to 1)
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
        """Check if the last submission passes concordance and
        consistency tests

        submission_id: submission of interest, defaults to the last submission
            done with the account
        """
        status = self.submission_status(submission_id)
        # need to cast to bool to not return None in some cases.
        success = bool(status['consistency'] >= 58 and
                       status["concordance"]["value"])
        return success
