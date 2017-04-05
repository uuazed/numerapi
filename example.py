#!/usr/bin/env python

from numerapi.numerapi import NumerAPI

# Most API calls don't require logging in:
napi = NumerAPI()

print("Downloading the current dataset...")
napi.download_current_dataset(dest_path='.', unzip=True)

# User-specific information
username = 'xanderai'
print("Getting information about user {}...".format(username))
print(napi.get_user(username))
print(napi.get_scores(username))
print(napi.get_earnings_per_round(username))

# Get the leaderboard for the current round of the competition
print(napi.get_new_leaderboard())

# Get the leaderboard for previous rounds of the competition
print(napi.get_new_leaderboard(40))

# Uploading predicitons to your account require your credentials:
# napi.credentials = ("YOUR_EMAIL", "YOUR_PASSWORD")
# napi.upload_prediction('./numerai_datasets/example_predictions.csv')
