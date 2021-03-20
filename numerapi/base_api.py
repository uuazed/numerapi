# -*- coding: utf-8 -*-

# System
import os
import logging
from typing import Dict

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
            model_id (str): Target model UUID (required for accounts
                            with multiple models)

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
                {'confirmTime': datetime.datetime(2018, 2, 11, 17, 54, 2),
                 'ethAmount': '0.295780674909307710',
                 'from': '0x11.....',
                 'posted': True,
                 'sendTime': datetime.datetime(2018, 2, 11, 17, 53, 25),
                 'status': 'confirmed',
                 'to': '0x81.....',
                 'txHash': '0x3c....',
                 'usdAmount': Decimal('10.07')},
                 ..]}
        """
        self.logger.warning(
            "get_transactions is DEPRECATED, use get_account_transactions")
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
        txs = self.raw_query(
            query, arguments, authorization=True)['data']['user']
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
