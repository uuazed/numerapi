"""Parts of the API that is shared between Signals and Classic"""

import os
import logging
from typing import Dict, List
from io import BytesIO

import pandas as pd
import requests

from numerapi import utils

API_TOURNAMENT_URL = 'https://api-tournament.numer.ai'


class Api:
    """Wrapper around the Numerai API"""

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
        self.tournament_id = 0
        self.diagnostics_id = None

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
        self.logger.debug(body)
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

    def get_models(self, tournament: int = None) -> Dict:
        """Get mapping of account model names to model ids for convenience

        Args:
            tournament (int): ID of the tournament (optional)

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
                tournament
              }
            }
          }
        """
        if tournament is None:
            tournament = self.tournament_id
        data = self.raw_query(
            query, authorization=True)['data']['account']['models']
        mapping = {
            model['name']: model['id'] for model in data
            if model['tournament'] == tournament
        }
        return mapping

    def get_current_round(self, tournament: int = None) -> int:
        """Get number of the current active round.

        Args:
            tournament (int): ID of the tournament (optional)

        Returns:
            int: number of the current active round

        Example:
            >>> NumerAPI().get_current_round()
            104
        """
        if tournament is None:
            tournament = self.tournament_id
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

    def get_account_transactions(self) -> List:
        """Get all your account deposits and withdrawals.

        DEPRECATED - please use `wallet_transactions` instead"
        """
        self.logger.warning(
            "DEPRECATED - please use `wallet_transactions` instead")
        return self.wallet_transactions()

    def wallet_transactions(self) -> List:
        """Get all transactions in your wallet.

        Returns:
            list: List of dicts with the following structure:

                 * from (`str`)
                 * posted (`bool`)
                 * status (`str`)
                 * to (`str`)
                 * txHash (`str`)
                 * amount (`decimal.Decimal`)
                 * time (`datetime`)
                 * tournament (`int`)

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> api.wallet_transactions()
            [{'amount': Decimal('1.000000000000000000'),
              'from': '0x000000000000000000000000000000000000313bc',
              'status': 'confirmed',
              'time': datetime.datetime(2023, 4, 19, 13, 28, 45),
              'to': '0x000000000000000000000000000000000006621',
              'tournament': None,
              'txHash': '0xeasdfkjaskljf314451234',
              'type': 'withdrawal'},

              ...
              ]
        """
        query = """
          query {
            account {
              walletTxns {
                amount
                from
                status
                to
                time
                tournament
                txHash
                type
              }
            }
          }
        """
        txs = self.raw_query(
            query, authorization=True)['data']['account']['walletTxns']
        # convert strings to python objects
        for transaction in txs:
            utils.replace(transaction, "time", utils.parse_datetime_string)
            utils.replace(transaction, "amount", utils.parse_float_string)
        return txs

    def set_submission_webhook(self, model_id: str,
                               webhook: str = None) -> bool:
        """Set a model's submission webhook used in Numerai Compute.
        Read More: https://docs.numer.ai/tournament/compute

        Args:
            model_id (str): Target model UUID

            webhook (str): The compute webhook to trigger this model

        Returns:
            bool: confirmation that your webhook has been set

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> api.set_submission_webhook(model_id="..", webhook="..")
            True
        """
        query = '''
          mutation (
            $modelId: String!
            $newSubmissionWebhook: String
          ) {
            setSubmissionWebhook(
              modelId: $modelId
              newSubmissionWebhook: $newSubmissionWebhook
            )
          }
        '''
        arguments = {'modelId': model_id, 'newSubmissionWebhook': webhook}
        res = self.raw_query(query, arguments, authorization=True)
        return res['data']['setSubmissionWebhook'] == "true"

    def _upload_auth(self, endpoint: str, file_path: str, tournament: int,
                     model_id: str) -> Dict[str, str]:
        auth_query = f'''
            query($filename: String!
                  $tournament: Int!
                  $modelId: String) {{
                {endpoint}(filename: $filename
                                       tournament: $tournament
                                       modelId: $modelId) {{
                    filename
                    url
                }}
            }}
        '''
        arguments = {'filename': os.path.basename(file_path),
                     'tournament': tournament,
                     'modelId': model_id}
        return self.raw_query(
            auth_query, arguments,
            authorization=True)['data'][endpoint]

    def upload_diagnostics(self, file_path: str = "predictions.csv",
                           tournament: int = None,
                           model_id: str = None,
                           df: pd.DataFrame = None) -> str:
        """Upload predictions to diagnostics from file.

        Args:
            file_path (str): CSV file with predictions that will get uploaded
            tournament (int): ID of the tournament (optional, defaults to None)
                -- DEPRECATED there is only one tournament nowadays
            model_id (str): Target model UUID (required for accounts with
                multiple models)
            df (pandas.DataFrame): pandas DataFrame to upload, if function is
                given df and file_path, df will be uploaded.

        Returns:
            str: diagnostics_id

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model_id = api.get_models()['uuazed']
            >>> api.upload_diagnostics("prediction.cvs", model_id=model_id)
            '93c46857-fed9-4594-981e-82db2b358daf'
            >>> # upload from pandas DataFrame directly:
            >>> api.upload_diagnostics(df=predictions_df, model_id=model_id)
        """
        self.logger.info("uploading diagnostics...")

        # write the pandas DataFrame as a binary buffer if provided
        buffer_csv = None
        if tournament is None:
            tournament = self.tournament_id

        if df is not None:
            buffer_csv = BytesIO(df.to_csv(index=False).encode())
            buffer_csv.name = file_path

        upload_auth = self._upload_auth(
            'diagnosticsUploadAuth', file_path, tournament, model_id)

        with open(file_path, 'rb') if df is None else buffer_csv as file:
            requests.put(upload_auth['url'], data=file.read())
        create_query = '''
            mutation($filename: String!
                     $tournament: Int!
                     $modelId: String) {
                createDiagnostics(filename: $filename
                                  tournament: $tournament
                                  modelId: $modelId) {
                    id
                }
            }'''
        arguments = {'filename': upload_auth['filename'],
                     'tournament': tournament,
                     'modelId': model_id}
        create = self.raw_query(create_query, arguments, authorization=True)
        self.diagnostics_id = create['data']['createDiagnostics']['id']
        return self.diagnostics_id

    def diagnostics(self, model_id: str, diagnostics_id: str = None) -> Dict:
        """Fetch results of diagnostics run

        Args:
            model_id (str): Target model UUID (required for accounts with
                multiple models)
            diagnostics_id (str): id returned by "upload_diagnostics", defaults
                to last diagnostic upload done within the same session

        Returns:
            dict: diagnostic results with the following content:

                * validationCorrMean (`float`)
                * validationCorrSharpe (`float`)
                * examplePredsCorrMean (`float`)
                * validationMmcStd (`float`)
                * validationMmcSharpe (`float`)
                * validationCorrPlusMmcSharpeDiff (`float`)
                * validationMmcStdRating (`float`)
                * validationMmcMeanRating (`float`)
                * validationCorrPlusMmcSharpeDiffRating (`float`)
                * perEraDiagnostics (`list`) each with the following fields:
                    * era (`int`)
                    * examplePredsCorr (`float`)
                    * validationCorr (`float`)
                    * validationFeatureCorrMax (`float`)
                    * validationFeatureNeutralCorr (`float`)
                    * validationMmc (`float`)
                * validationCorrPlusMmcStd (`float`)
                * validationMmcMean (`float`)
                * validationCorrStdRating (`float`)
                * validationCorrPlusMmcSharpe (`float`)
                * validationMaxDrawdownRating (`float`)
                * validationFeatureNeutralCorrMean (`float`)
                * validationCorrPlusMmcMean (`float`)
                * validationFeatureCorrMax (`float`)
                * status (`string`),
                * validationCorrMeanRating (`float`)
                * validationFeatureNeutralCorrMeanRating (`float`)
                * validationCorrSharpeRating (`float`)
                * validationCorrPlusMmcMeanRating (`float`)
                * message (`string`)
                * validationMmcSharpeRating (`float`)
                * updatedAt (`datetime`)
                * validationFeatureCorrMaxRating (`float`)
                * validationCorrPlusMmcSharpeRating (`float`)
                * trainedOnVal (`bool`)
                * validationCorrStd (`float`)
                * erasAcceptedCount (`int`)
                * validationMaxDrawdown (`float`)
                * validationCorrPlusMmcStdRating (`float`)

        Example:
            >>> napi = NumerAPI(secret_key="..", public_id="..")
            >>> model_id = napi.get_models()['uuazed']
            >>> api.upload_diagnostics("prediction.cvs", model_id=model_id)
            '93c46857-fed9-4594-981e-82db2b358daf'
            >>> napi.diagnostic(model_id)
            {"validationCorrMean": 0.53231,
            ...
            }

        """
        if diagnostics_id is None and self.diagnostics_id is None:
            raise ValueError("You need to provide a 'diagnostics_id'",
                             " or upload to diagnostics again.")
        if diagnostics_id is None:
            diagnostics_id = self.diagnostics_id

        query = '''
            query($id: String!
                  $modelId: String) {
              diagnostics(id: $id
                          modelId: $modelId) {
                erasAcceptedCount
                examplePredsCorrMean
                message
                perEraDiagnostics {
                    era
                    examplePredsCorr
                    validationCorr
                    validationFeatureCorrMax
                    validationFeatureNeutralCorr
                    validationMmc
                }
                status
                trainedOnVal
                updatedAt
                validationCorrMean
                validationCorrMeanRating
                validationCorrPlusMmcMean
                validationCorrPlusMmcMeanRating
                validationCorrPlusMmcSharpe
                validationCorrPlusMmcSharpeDiff
                validationCorrPlusMmcSharpeDiffRating
                validationCorrPlusMmcSharpeRating
                validationCorrPlusMmcStd
                validationCorrPlusMmcStdRating
                validationCorrSharpe
                validationCorrSharpeRating
                validationCorrStd
                validationCorrStdRating
                validationFeatureCorrMax
                validationFeatureCorrMaxRating
                validationFeatureNeutralCorrMean
                validationFeatureNeutralCorrMeanRating
                validationMaxDrawdown
                validationMaxDrawdownRating
                validationMmcMean
                validationMmcMeanRating
                validationMmcSharpe
                validationMmcSharpeRating
                validationMmcStd
                validationMmcStdRating
              }
            }
        '''
        args = {'modelId': model_id, 'id': diagnostics_id}
        results = self.raw_query(
            query, args, authorization=True)['data']['diagnostics']
        utils.replace(results, "updatedAt", utils.parse_datetime_string)
        return results
