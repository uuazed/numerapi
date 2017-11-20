# -*- coding: utf-8 -*-

# System
import zipfile
import json
import os
import datetime
import errno
import logging

# Third Party
import requests

API_TOURNAMENT_URL = 'https://api-tournament.numer.ai'


class NumerAPI(object):

    """Wrapper around the Numerai API"""

    def __init__(self, public_id=None, secret_key=None, verbosity="INFO"):
        """
        initialize Numerai API wrapper for Python

        verbosity: indicates what level of messages should be displayed
            valid values: "debug", "info", "warning", "error", "critical"
        """
        if public_id and secret_key:
            self.token = (public_id, secret_key)
        elif not public_id and not secret_key:
            self.token = None
        else:
            print("You need to supply both a public id and a secret key.")
            self.token = None

        self.logger = logging.getLogger(__name__)

        # set up logging
        numeric_log_level = getattr(logging, verbosity.upper())
        if not isinstance(numeric_log_level, int):
            raise ValueError('invalid verbosity: %s' % verbosity)
        log_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
        logging.basicConfig(format=log_format, level=numeric_log_level)
        self.submission_id = None

    def _unzip_file(self, src_path, dest_path, filename):
        """unzips file located at src_path into destination_path"""
        self.logger.info("unzipping file...")

        # construct full path (including file name) for unzipping
        unzip_path = "{0}/{1}".format(dest_path, filename)

        # create parent directory for unzipped data
        try:
            os.makedirs(unzip_path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

        # extract data
        with zipfile.ZipFile(src_path, "r") as z:
            z.extractall(unzip_path)

        return True

    def download_current_dataset(self, dest_path=".", unzip=True):
        """download dataset for current round

        dest_path: desired location of dataset file
        unzip: indicates whether to unzip dataset
        """
        self.logger.info("downloading current dataset...")

        # set up download path
        now = datetime.datetime.now().strftime("%Y%m%d")
        dataset_name = "numerai_dataset_{0}".format(now)
        file_name = "{0}.zip".format(dataset_name)
        dataset_path = "{0}/{1}".format(dest_path, file_name)

        if os.path.exists(dataset_path):
            self.logger.info("target file already exists")
            return dataset_path

        # get data for current dataset
        url = 'https://api.numer.ai/competitions/current/dataset'
        dataset_res = requests.get(url, stream=True)
        dataset_res.raise_for_status()

        # create parent folder if necessary
        try:
            os.makedirs(dest_path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

        # write dataset to file
        with open(dataset_path, "wb") as f:
            for chunk in dataset_res.iter_content(1024):
                f.write(chunk)

        # unzip dataset
        if unzip:
            self._unzip_file(dataset_path, dest_path, dataset_name)

        return dataset_path

    def _handle_call_error(self, errors):
        if isinstance(errors, list):
            for error in errors:
                if "message" in error:
                    self.logger.error(error['message'])
        elif isinstance(errors, dict):
            if "detail" in errors:
                self.logger.error(errors['detail'])

    def _call(self, query, variables=None, authorization=False):
        body = {'query': query,
                'variables': variables}
        headers = {'Content-type': 'application/json',
                   'Accept': 'application/json'}
        if authorization and self.token:
            public_id, secret_key = self.token
            headers['Authorization'] = \
                'Token {}${}'.format(public_id, secret_key)
        r = requests.post(API_TOURNAMENT_URL, json=body, headers=headers)
        result = r.json()
        if "errors" in result:
            self._handle_call_error(result['errors'])
            # fail!
            raise ValueError

        return result

    def get_leaderboard(self, round_num):
        self.logger.info("getting leaderboard for round {}".format(round_num))
        query = '''
            query simpleRoundsRequest($number: Int!) {
              rounds(number: $number) {
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
                    tournament
                    usdAmount
                  }
                  paymentStaking {
                    nmrAmount
                    tournament
                    usdAmount
                  }
                  totalPayments {
                    nmrAmount
                    tournament
                    usdAmount
                  }
                }
              }
            }
        '''
        arguments = {'number': round_num}
        result = self._call(query, arguments)
        return result['data']['rounds'][0]['leaderboard']

    def get_current_leaderboard(self):
        return self.get_leaderboard(0)

    def get_competitions(self):
        """ get information about rounds """
        self.logger.info("getting rounds...")

        query = '''
            query rounds {
              rounds {
                number
                resolveTime
                datasetId
                openTime
                resolvedGeneral
                resolvedStaking
              }
            }
        '''
        result = self._call(query)
        return result['data']['rounds']

    def get_current_round(self):
        # zero is an alias for the current round!
        query = '''
            query simpleRoundsRequest {
              rounds(number: 0) {
                number
              }
            }
        '''
        data = self._call(query)
        round_num = data['data']['rounds'][0]["number"]
        return round_num

    def submission_status(self):
        """display submission status"""
        if self.submission_id is None:
            raise ValueError('You need to submit something first')

        query = '''
            query submissions($submission_id: String!) {
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
        variable = {'submission_id': self.submission_id}
        status_raw = self._call(query, variable, authorization=True)
        status_raw = status_raw['data']['submissions'][0]
        status = {}
        for key, value in status_raw.items():
            if isinstance(value, dict):
                value = value['value']
            status[key] = value
        return status

    def upload_predictions(self, file_path):
        """uploads predictions from file"""
        self.logger.info("uploading prediction...")

        auth_query = \
            '''
            query($filename: String!) {
                submission_upload_auth(filename: $filename) {
                    filename
                    url
                }
            }
            '''
        variable = {'filename': os.path.basename(file_path)}
        submission_resp = self._call(auth_query, variable, authorization=True)
        submission_auth = submission_resp['data']['submission_upload_auth']
        with open(file_path, 'rb') as fh:
            requests.put(submission_auth['url'], data=fh.read())
        create_query = \
            '''
            mutation($filename: String!) {
                create_submission(filename: $filename) {
                    id
                }
            }
            '''
        variables = {'filename': submission_auth['filename']}
        create = self._call(create_query, variables, authorization=True)
        self.submission_id = create['data']['create_submission']['id']
        return self.submission_id

    def stake(self, confidence, value):
        query = '''
            mutation stake($code: String,
            $confidence: String!
            $password: String
            $round: Int!
            $value: String!) {
              stake(code: $code
                    confidence: $confidence
                    password: $password
                    round: $round
                    value: $value) {
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
                     'value': str(value)}
        result = self._call(query, arguments, authorization=True)
        return result
