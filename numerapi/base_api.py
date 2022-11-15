"""Parts of the API that is shared between Signals and Classic"""

import os
import datetime
import logging
from typing import Dict, List
from io import BytesIO
import pytz

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

        self.show_progress_bars = show_progress_bars
        self.tournament_id = 0

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

    def raw_query(self, query: str, variables: Dict = None,
                  authorization: bool = False,
                  retries: int = 3, delay: int = 5, backoff: int = 2):
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
            retries (int): for 5XX errors, how often should numerapi retry
            delay (int): in case of retries, how many seconds to wait between tries
            backoff (int): in case of retries, multiplier to increase the delay between retries

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
            API_TOURNAMENT_URL, body, headers,
            retries=retries, delay=delay, backoff=backoff)

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

    def set_bio(self, model_id: str, bio: str) -> bool:
        """Set bio field for a model id.

        Args:
            model_id (str): Target model UUID
            bio (str)

        Returns:
            bool: if the bio was changed successfully

        Example:
            >>> napi = numerapi.NumerAPI()
            >>> model_id = napi.get_models()["uuazed"]
            >>> napi.set_bio(model_id, "This model stinks.")
            True
        """
        mutation = '''
            mutation($value: String!
                  $modelId: String) {
                setUserBio(value: $value
                           modelId: $modelId)
            }
        '''
        arguments = {'value': bio, 'modelId': model_id}
        res = self.raw_query(mutation, arguments, authorization=True)
        return res["data"]["setUserBio"]

    def set_link(self, model_id: str, link_text: str, link: str) -> bool:
        """Set link field for a model id.

        Args:
            model_id (str): Target model UUID
            link_test (str)
            link (str)

        Returns:
            bool: if the bio was changed successfully

        Example:
            >>> napi = numerapi.NumerAPI()
            >>> model_id = napi.get_models()["uuazed"]
            >>> napi.set_link(model_id, "buy my predictions", "numerbay.ai")
            True
        """
        mutation = '''
            mutation($linkUrl: String!
                     $linkText: String
                     $modelId: String) {
                setUserLink(linkText: $linkText
                            linkUrl: $linkUrl
                            modelId: $modelId)
            }
        '''
        args = {'linkUrl': link, "linkText": link_text, 'modelId': model_id}
        res = self.raw_query(mutation, args, authorization=True)
        return res["data"]["setUserLink"]

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
            requests.put(upload_auth['url'], data=file.read(), timeout=600)
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
        diagnostics_id = create['data']['createDiagnostics']['id']
        return diagnostics_id

    def diagnostics(self, model_id: str, diagnostics_id: str = None) -> Dict:
        """Fetch results of diagnostics run

        Args:
            model_id (str): Target model UUID (required for accounts with
                multiple models)
            diagnostics_id (str, optional): id returned by "upload_diagnostics"

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
        query = '''
            query($id: String
                  $modelId: String!) {
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

    def round_model_performances(self, username: str) -> List[Dict]:
        """Fetch round model performance of a user.

        Args:
            username (str)

        Returns:
            list of dicts: list of round model performance entries

            For each entry in the list, there is a dict with the following
            content:

                * corr (`float`)
                * corr20d (`float` or None)
                * corr20dPercentile (`float` or None)
                * corrMultiplier (`float`)
                * corrPercentile (`float`)
                * corrWMetamodel (`float`)
                * tc (`float`)
                * tcPercentile (`float`)
                * ic (`float`)
                * icPercentile (`float`)
                * fnc (`float`)
                * fncPercentile (`float`)
                * fncV3 (`float`)
                * fncV3Percentile (`float`)
                * mmc (`float`)
                * mmc20d (`float` or None)
                * mmc20dPercentile (`float` or None)
                * mmcMultiplier (`float`)
                * mmcPercentile (`float`)
                * payout (`Decimal`)
                * roundNumber (`int`)
                * roundOpenTime (`datetime`)
                * roundPayoutFactor (`Decimal`)
                * roundResolveTime (`datetime`)
                * roundResolved (`bool`)
                * roundTarget (`str` or None)
                * selectedStakeValue (`Decimal`)

        Example:
            >>> api = NumerAPI()
            >>> api.round_model_performances("uuazed")
            [{'corr': -0.01296840448965,
             'corr20d': None,
             'corr20dPercentile': None,
             'corrMultiplier': 1.0,
             'corrPercentile': 0.0411107104219257,
             'corrWMetamodel': 0.51542251407092,
             'tc': 0.1415973344,
             'tcPercentile': 0.115398485394879,
             'ic': 0.1415973344,
             'icPercentile': 0.115398485394879,
             'fnc': 0.000437631996046271,
             'fncPercentile': 0.115398485394879,
             'fncV3': 0.000437631996046271,
             'fncV3Percentile': 0.115398485394879,
             'mmc': -0.0152125841680981,
             'mmc20d': None,
             'mmc20dPercentile': None,
             'mmcMultiplier': 2.0,
             'mmcPercentile': 0.0443562928236567,
             'payout': Decimal('-5.687406578133045'),
             'roundNumber': 281,
             'roundOpenTime': datetime.datetime(2021, 9, 11, 18, 0),
             'roundPayoutFactor': Decimal('0.578065736524773470'),
             'roundResolveTime': datetime.datetime(2021, 10, 13, 20, 0),
             'roundResolved': False,
             'roundTarget': None,
             'selectedStakeValue': Decimal('226.73138356930343')},
             ...
            ]
        """
        if self.tournament_id == 8:
            endpoint = "v3UserProfile"
        elif self.tournament_id == 11:
            endpoint = "v2SignalsProfile"
        else:
            raise ValueError("round_model_performances is not available for ",
                             f"tournament {self.tournament_id}")

        query = f"""
          query($username: String!) {{
            {endpoint}(modelName: $username) {{
              roundModelPerformances {{
                corr
                corr20d
                corr20dPercentile
                corrMultiplier
                corrPercentile
                corrWMetamodel
                tc
                tcPercentile
                ic
                icPercentile
                fnc
                fncPercentile
                fncV3
                fncV3Percentile
                mmc
                mmc20d
                mmc20dPercentile
                mmcMultiplier
                mmcPercentile
                payout
                roundNumber
                roundOpenTime
                roundPayoutFactor
                roundResolveTime
                roundResolved
                roundTarget
                selectedStakeValue
              }}
            }}
          }}
        """
        arguments = {'username': username}
        data = self.raw_query(query, arguments)['data'][endpoint]
        performances = data['roundModelPerformances']
        # convert strings to python objects
        for perf in performances:
            utils.replace(perf, "roundOpenTime", utils.parse_datetime_string)
            utils.replace(perf, "roundResolveTime", utils.parse_datetime_string)
            utils.replace(perf, "payout", utils.parse_float_string)
            utils.replace(perf, "roundPayoutFactor", utils.parse_float_string)
            utils.replace(perf, "selectedStakeValue", utils.parse_float_string)
        return performances

    def stake_change(self, nmr, action: str = "decrease",
                     model_id: str = None) -> Dict:
        """Change stake by `value` NMR.

        Args:
            nmr (float or str): amount of NMR you want to increase/decrease
            action (str): `increase` or `decrease`
            model_id (str): Target model UUID (required for accounts with
                multiple models)

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
                     'tournamentNumber': self.tournament_id}
        result = self.raw_query(query, arguments, authorization=True)
        stake = result['data']['v2ChangeStake']
        utils.replace(stake, "requestedAmount", utils.parse_float_string)
        utils.replace(stake, "dueDate", utils.parse_datetime_string)
        return stake

    def stake_drain(self, model_id: str = None) -> Dict:
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
        return self.stake_decrease(11000000, model_id)

    def stake_decrease(self, nmr, model_id: str = None) -> Dict:
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
        return self.stake_change(nmr, 'decrease', model_id)

    def stake_increase(self, nmr, model_id: str = None) -> Dict:
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
        return self.stake_change(nmr, 'increase', model_id)

    def set_stake_type(self, model_id: str = None,
                       corr_multiplier: int = 0,
                       tc_multiplier: float = 0,
                       take_profit: bool = False) -> Dict:
        """Change stake type by model.

        Args:
            model_id (str): Target model UUID (required for accounts with
                multiple models)
            corrMultiplier (int): multiplier of correlation for returns
            tcMultiplier (float): multiplier of TC for returns
            takeProfit (bool): determines whether payouts are returned to usr
                wallet or automatically staked to next round.

        Returns:
           dict with confirmation that payout selection has been updated

        Example:
            >>> api = NumerAPI(secret_key="..", public_id="..")
            >>> model = api.get_models()['uuazed']
            >>> api.set_stake_type(model, 1, 3)
            {'data': {'v2ChangePayoutSelection': 'payout selection updated'}}
        """
        query = """mutation ($corrMultiplier: Float!
                             $modelId: String!
                             $takeProfit: Boolean!
                             $tcMultiplier: Float!
                             $tournamentNumber: Int!) {
                        v2ChangePayoutSelection(corrMultiplier: $corrMultiplier
                                                modelId: $modelId
                                                takeProfit: $takeProfit
                                                tcMultiplier: $tcMultiplier
                                                tournamentNumber: $tournamentNumber)}
        """
        args = {'modelId':  model_id,
                'corrMultiplier': corr_multiplier,
                'tcMultiplier': tc_multiplier,
                'takeProfit': take_profit,
                'tournamentNumber': self.tournament_id}
        result = self.raw_query(query, args, authorization=True)

        return result

    def check_round_open(self) -> bool:
        """Check if a round is currently open.

        Returns:
            bool: True if a round is currently open for submissions, False otherwise.

        Example:
            >>> NumerAPI().check_round_open()
            False
        """
        query = '''
            query($tournament: Int!) {
              rounds(tournament: $tournament
              number: 0) {
                number
                openTime
                closeStakingTime
              }
            }
        '''
        arguments = {'tournament': self.tournament_id}
        raw = self.raw_query(query, arguments)['data']['rounds'][0]
        if raw is None:
            return False
        open_time = utils.parse_datetime_string(raw['openTime'])
        deadline = utils.parse_datetime_string(raw["closeStakingTime"])
        now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        is_open = open_time < now < deadline
        return is_open

    def check_new_round(self, hours: int = 12, tournament: int = None) -> bool:
        """Check if a new round has started within the last `hours`.

        Args:
            hours (int, optional): timeframe to consider, defaults to 12
            tournament (int): ID of the tournament (optional)
                -- DEPRECATED this is now automatically filled

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
        tournament = self.tournament_id if tournament is None else tournament
        arguments = {'tournament': tournament}
        raw = self.raw_query(query, arguments)['data']['rounds'][0]
        if raw is None:
            return False
        open_time = utils.parse_datetime_string(raw['openTime'])
        now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        is_new_round = open_time > now - datetime.timedelta(hours=hours)
        return is_new_round
