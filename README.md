# Numerai Python API
Automatically download and upload data for the Numerai machine learning
competition.

This library is a Python client to the Numerai API. The interface is programmed
in Python and allows downloading the training data, uploading predictions, and
accessing user, submission and competitions information.

If you encounter a problem or have suggestions, feel free to open an issue.

# Installation
`pip install git+https://github.com/numerai/NumerAPI.git`

# Usage
See `example.py`.  You can run it as `./example.py`

Some actions (like uploading predictions or staking) requires a token to verify
that it is really you interacting with Numerai's API. These tokens consists of
a `public_id` and `secret_key`. Both can be obtained by login in to Numer.ai and
going to Account -> Custom API Keys.

# Documentation
## Layout
Parameters and return values are given with Python types. Dictionary keys are
given in quotes; other names to the left of colons are for reference
convenience only. In particular, `list`s of `dict`s have names for the `dict`s;
these names will not show up in the actual data, only the actual `dict` data
itself.

## `download_current_dataset`
### Parameters
* `dest_path` (`str`, optional, default: `.`): destination folder for the
  dataset
* `unzip` (`bool`, optional, default: `True`): indication of whether the
  training data should be unzipped
### Return Values
* `path` (`string`): location of the downloaded dataset

## `get_leaderboard`
retrieves the leaderboard for the given round
### Parameters
* `round_num` (`int`) The round you are interested in.
### Return Values
* `participants` (`list`): information about all competitors
  * `participants` (`dict`)
    * `concordance` (`dict`)
      * `pending` (`bool`)
      * `value` (`bool`)
    * `originality` (`dict`)
      * `pending` (`bool`)
      * `value` (`bool`)
    * `consistency` (`float`)
    * `liveLogloss` (`float` or `None`)
    * `validationLogloss` (`float`)
    * `paymentGeneral` (`dict` or `None`)
      * `nmrAmount` (`float`)
      * `usdAmount` (`float`)
    * `paymentStaking` (`dict` or `None`)
      * `nmrAmount` (`float`)
      * `usdAmount` (`float`)
    * `submissionId` (`str`)
    * `totalPayments` (`dict`)
      * `nmrAmount` (`float`)
      * `usdAmount` (`float`)
    * `username` (`str`)

## `get_competitions`
### Return Values
* `all_competitions` (`list`): information about all competitions
  * `competition` (`dict`)
    * `datasetId` (`str`)
    * `number` (`int`)
    * `openTime` (`str (datetime)`)
    * `resolveTime` (`str (datetime)`)
    * `resolvedGeneral` (`bool`)
    * `resolvedStaking` (`bool`)

## `get_current_round`
### Return Values
* `number` (`int`): number of the current round

## `get_submission_ids`
get dict with username->submission_id mapping
### Return Values
* `submission_ids` (`dict`)
  * `username` (`str`)
  * `submissionId` (`str`): ID of submission

## `submission_status`
submission status of the given submission_id or the last submission done
within the same session.
### Parameters
* `submission_id` (`str`, optional, default: `None`):
### Return Values
* `status` (`dict`)
  * `concordance` (`dict`):
    * `pending` (`bool`)
    * `value` (`bool`): whether the submission is concordant
  * `originality` (`dict`)
    * `pending` (`bool`)
    * `value` (`bool`): whether the submission is original
  * `consistency` (`float`): consistency of the submission
  * `validation_logloss` (`float`): amount of logloss for the submission

## `upload_predictions`
  ### Parameters
  * `file_path` (`str`): path to CSV of predictions (e.g. `"path/to/file/prediction.csv"`)
  ### Return Values
  * `submission_id`: ID of submission


TODO


## `get_earnings_per_round`
### Parameters
* `username`: user for which earnings are requested
### Return Values
* `round_ids` (`np.ndarray(int)`): IDs of each round for which there are
  earnings
* `earnings` (`np.ndarray(float)`): earnings for each round

## `get_scores_for_user`
### Parameters
* `username`: user for which scores are being requested
### Return Values
* `validation_scores` (`np.ndarray(float)`): logloss validation scores
* `consistency_scoress` (`np.ndarray(float)`): logloss consistency scores
* `round_ids` (`np.ndarray(int`): IDs of the rounds for which there are scores

## `get_user`
### Parameters
* `username`: `str` - name of requested user
### Return Values
* `user` (`dict`): information about the requested user
  * `"_id"` (`str`)
  * `"username"` (`str`)
  * `"assignedEthAddress"` (`str`)
  * `"created"` (`str (datetime)`)
  * `"earnings"` (`float`)
  * `"followers"` (`int`)
  * `"rewards"` (`list`)
    * `reward` (`dict`)
      * `"_id"` (`int`)
      * `"amount"` (`float`)
      * `"earned"` (`float`)
      * `"nmr_earned"` (`str`)
      * `"start_date"` (`str (datetime)`)
      * `"end_date"` (`str (datetime)`)
  * `"submissions"` (`dict`)
    * `"results"` (`list`)
      * `result` (`dict`)
        * `"_id"` (`str`)
        * `"competition"` (`dict`)
          * `"_id"` (`str`)
          * `"start_date"` (`str (datetime)`)
          * `"end_date"` (`str (datetime)`)
        * `"competition_id"` (`int`)
        * `"created"` (`str (datetime)`)
        * `"id"` (`str`)
        * `"username"` (`str`)
