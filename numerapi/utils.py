import dateutil.parser
import requests
import tqdm
import os
import errno
import decimal
import logging
import json


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
    file_size = 0
    req = requests.get(url, stream=True)
    req.raise_for_status()
    # Total size in bytes.
    total_size = int(req.headers.get('content-length', 0))

    if os.path.exists(dest_path):
        logger.info("target file already exists")
        file_size = os.stat(dest_path).st_size  # File size in bytes
        if file_size < total_size:
            # Download incomplete
            logger.info("resuming download")
            resume_header = {'Range': 'bytes=%d-' % file_size}
            req = requests.get(url, headers=resume_header, stream=True,
                               verify=False, allow_redirects=True)
        elif file_size == total_size:
            # Download complete
            logger.info("download complete")
            return
        else:
            # Error, delete file and restart download
            logger.error("deleting file and restarting")
            os.remove(dest_path)
            file_size = 0
    else:
        # File does not exist, starting download
        logger.info("starting download")

    # write dataset to file and show progress bar
    pbar = tqdm.tqdm(total=total_size, unit='B', unit_scale=True,
                     desc=dest_path, disable=not show_progress_bars)
    # Update progress bar to reflect how much of the file is already downloaded
    pbar.update(file_size)
    with open(dest_path, "ab") as dest_file:
        for chunk in req.iter_content(1024):
            dest_file.write(chunk)
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
    except UnboundLocalError:
        # `r` isn't available, probably because the try/except above failed
        pass
    except json.decoder.JSONDecodeError as e:
        logger.error("Did not receive a valid JSON: {}".format(e))
        return {}
