#!/usr/bin/env python

from numerapi.numerapi import NumerAPI

# Most API calls don't require logging in:
napi = NumerAPI()

print("Downloading the current dataset...")
napi.download_current_dataset(dest_path='.', unzip=True)

username = 'xanderai'
print("Getting information about user {}...".format(username))
print(napi.get_user(username))
print(napi.get_scores(username))
print(napi.get_earnings_per_round(username))

# Uploading predicitons to your account require your credentials:
# napi.credentials = ("YOUR_EMAIL", "YOUR_PASSWORD")
# napi.upload_prediction('./numerai_datasets/example_predictions.csv')
