#!/usr/bin/env python

from numerapi.numerapi import NumerAPI


def main():
    # set example username and round
    example_public_id = "somepublicid"
    example_secret_key = "somesecretkey"

    # some API calls do not require logging in
    napi = NumerAPI(verbosity="info")
    # download current dataset
    napi.download_current_dataset(unzip=True)
    # get competitions
    all_competitions = napi.get_competitions()
    competition_67 = napi.get_competition(round_id=67)

    # provide api tokens
    napi = NumerAPI(example_public_id, example_secret_key)

    # upload predictions
    submission_id = napi.upload_predictions("mypredictions.csv")
    # check submission status
    napi.submission_status()


if __name__ == "__main__":
    main()
