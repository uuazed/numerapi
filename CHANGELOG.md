# Changelog
Notable changes to this project.


## [unreleased]
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
- allow custom API calls - 'raw_query'
- started a test suite
- moved numerapi to it's new home (https://github.com/uuazed/numerapi)
- make numerapi available on pypi (https://pypi.org/project/numerapi)
- rename package from NumerAPI to all-lowercase numerapi
