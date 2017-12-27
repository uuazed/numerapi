# Changelog
Notable changes to this project.


## [unreleased]
- setup travis to run test automatically
- run tests on different Python versions (2.7, 3.5 and 3.6)
- test coverage reports via codecov.io
- only append .zip to downloaded dataset if zip=True


## [0.6.3] - 2017-12-20
- complete rewrite to adapt to Numerai's API swich to GraphQL
- update documentation and example
- added staking via API - `stake`
- added `get_staking_leaderboard`
- allow passing desired filename to data download
- allow custom API calls - 'raw_query'
- started a test suite
