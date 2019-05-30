import dateutil.parser
import requests
import tqdm
import os
import errno
import decimal
import logging


# work-around needed for Python2
try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError


logger = logging.getLogger(__name__)


def parse_datetime_string(s):
    if s is None:
        return None
    dt = dateutil.parser.parse(s)
    return dt


def parse_float_string(s):
    if s is None:
        return None
    try:
        f = decimal.Decimal(s.replace(",", ""))
    except decimal.InvalidOperation:
        f = None
    return f


def replace(dictionary, key, function):
    if dictionary is not None and key in dictionary:
        dictionary[key] = function(dictionary[key])


def download_file(url, dest_path, show_progress_bars=True):
    r = requests.get(url, stream=True)
    r.raise_for_status()
    # Total size in bytes.
    total_size = int(r.headers.get('content-length', 0))

    # write dataset to file and show progress bar
    pbar = tqdm.tqdm(total=total_size, unit='B', unit_scale=True,
                     desc=dest_path, disable=not show_progress_bars)
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(1024):
            f.write(chunk)
            pbar.update(1024)


def ensure_directory_exists(path):
    try:
        # `exist_ok` option is only available in Python 3.2+
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


def post_with_err_handling(url, body, headers, timeout=None):
    try:
        r = requests.post(url, json=body, headers=headers, timeout=timeout)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error("Http Error: {}".format(e))
    except requests.exceptions.ConnectionError as e:
        logger.error("Error Connecting: {}".format(e))
    except requests.exceptions.Timeout as e:
        logger.error("Timeout Error: {}".format(e))
    except requests.exceptions.RequestException as e:
        logger.error("Oops, something went wrong: {}".format(e))

    try:
        return r.json()
    except UnboundLocalError as e:
        # `r` isn't available, probably because the try/except above failed
        pass
    except JSONDecodeError as e:
        logger.error("Did not receive a valid JSON: {}".format(e))
        return {}
