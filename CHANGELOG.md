# Changelog
Notable changes to this project.


## [dev] - unreleased

## [0.8.1] - 2018-01-27
- import NumerAPI class to toplevel. now `from numerapi import NumerAPI` works
- added `get_dataset_url`
- more & improved tests

## [0.8.0] - 2018-01-06
- added `check_new_round` to check if a new round has started
- added `check_submission_successful` to check if the last submission passes
  concordance, originality and consistency
- return proper Python data types, for example the NMR amounts are now
  floats and no longer strings
- show progress bar while downloading dataset
- general code cleanup & more tests

## [0.7.1] - 2017-12-29
- fix import issues (py2 vs py3)

## [0.7.0] - 2017-12-29
- convert datetime strings to proper Python datetime objects
- only append .zip to downloaded dataset if zip=True
- use round_number instead of date in default download filename
- setup travis to run test automatically
- run tests with different Python versions (2.7, 3.5 and 3.6)
- test coverage reports via codecov.io

## [0.6.3] - 2017-12-20
- complete rewrite to adapt to Numerai's API swich to GraphQL
- update documentation and example
- added staking via API - `stake`
- added `get_staking_leaderboard`
- allow passing desired filename to data download
- allow custom API calls - `raw_query`
- started a test suite
- moved numerapi to it's new home (https://github.com/uuazed/numerapi)
- make numerapi available on pypi (https://pypi.org/project/numerapi)
- rename package from NumerAPI to all-lowercase numerapi
