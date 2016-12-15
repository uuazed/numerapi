# NumerAPI
automatically download and upload data for the numer.ai machine learning competition

This API provides access to the unofficial numer.ai API. The interface is programmed in Python and allows to simply download the training data, upload predictions and access some user information. Some parts of the code were taken from [numerflow](https://github.com/ChristianSch/numerflow) by ChristianSch. Visit his [wiki](https://github.com/ChristianSch/numerflow/wiki/API-Reverse-Engineering), if you need further information on the reverse engineering process.

If you encounter a problem or have suggestions, feel free to open an issue.

Requirements: 
* Python 2.7
* numpy

# Documentation
### `download_current_dataset`
#### Parameters
* `dest_path`: Optional parameter. Destination folder for the dataset. Default: currrent working directory.
* `unzip`: Optional parameter. Decide if you wish to unzip the downloaded training data. Default: True

#### Return values
* `status_code`: Status code of the requests operation.

### `upload_prediction`
#### Parameters
* `file_path`: Path to the prediction. It should already contain the file name ('path/to/file/prediction.csv')

#### Return values
* `status_code`: Status code of the requests operation.

#### Notes
Uploading a prediction shortly before a new dataset is released may result in a <400 Bad Request>. If this happen just wait for the new dataset and upload new predictions then.

### `get_user`
### Parameters
* `username`: Name of the user you want to request.

### Return values
* `array-like`: Tuple of size five containing the `username`, `logloss`, `rank`, `carerr earnings` and the status code of the requests operation. If it fails all values except the status code will be `None`.

### `get_scores`
### Parameters
* `username`: Name of the user you want to request.

### Return values
* `array-like`: Tuple of size 2 containing a `numpy.ndarray` containing the scores of all uploaded predictions with the newest first and the status code of the requests operation. If it fails all values except the status code will be `None`.

### `get_earnings_per_round`
### Parameters
* `username`: Name of the user you want to request.

### Return values
* `array-like`: Tuple of size 2 containing a `numpy.ndarray` containing the earnings of each round with the oldest first and the status code of the requests operation. If it fails all values except the status code will be `None`.

### `login`
#### Return values
* `array-like`: Tuple of size four containing the `accessToken`, `refreshToken`, `id`, and the status code of the requests operation. If it fails all values except the status code will be `None`.

### `authorize`
#### Parameters
* `file_path`: Path to the prediction. It should already contain the file name ('path/to/file/prediction.csv')

#### Return values
* `array-like`: Tuple of size four containing the `filename`, `signedRequest`, `headers`, and the status code of the requests operation. If it fails all values except the status code will be `None`.

### `get_current_competition`
#### Return values
* `array-like`: Tuple of size three containing the `dataset_id`, `_id` and the status code of the requests operation. If it fails all values except the status code will be `None`.

# Usage
```
import numerapi

napi = numerapi.NumerAPI('email', 'password')
napi.download_current_dataset(dest_path='.', unzip=True)
napi.upload_prediction('path/to/prediction.csv')
napi.get_user('username')
napi.get_scores('username')
napi.get_earnings_per_round('username')
```
