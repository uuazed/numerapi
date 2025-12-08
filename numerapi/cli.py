"""Access the numerai API via command line"""

import datetime
import decimal
import json

import click

import numerapi

DEFAULT_TOURNAMENT = 8


def _get_api(tournament: int):
    """
    Return the correct API implementation for a tournament.

    Classic (and any tournament other than Signals/Crypto) uses NumerAPI,
    Signals (11) uses SignalsAPI, and Crypto (12) uses CryptoAPI.
    """
    if tournament == 11:
        return numerapi.SignalsAPI()
    if tournament == 12:
        return numerapi.CryptoAPI()
    api = numerapi.NumerAPI()
    api.tournament_id = tournament
    return api


def _require_method(api, method_name: str, command_name: str):
    """Ensure the requested command is supported for the selected tournament."""
    if not hasattr(api, method_name):
        raise click.ClickException(
            f"The '{command_name}' command is not available for tournament "
            f"{api.tournament_id}."
        )
    return getattr(api, method_name)


def tournament_option(func):
    """Reusable Click option for selecting a tournament."""
    return click.option(
        "--tournament",
        type=int,
        default=DEFAULT_TOURNAMENT,
        show_default=True,
        help="Tournament to target (8 classic, 11 signals, 12 crypto).",
    )(func)


class CommonJSONEncoder(json.JSONEncoder):
    """
    Common JSON Encoder
    json.dumps(jsonString, cls=CommonJSONEncoder)
    """

    def default(self, o):
        # Encode: Decimal
        if isinstance(o, decimal.Decimal):
            return str(o)
        # Encode: Date & Datetime
        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()

        return None


def prettify(stuff):
    """prettify json"""
    return json.dumps(stuff, cls=CommonJSONEncoder, indent=4)


@click.group()
def cli():
    """Wrapper around the Numerai API"""


@cli.command()
@click.option(
    "--round_num",
    type=int,
    help="round you are interested in. defaults to the current round",
)
@tournament_option
def list_datasets(round_num, tournament):
    """List of available data files"""
    api = _get_api(tournament)
    click.echo(prettify(api.list_datasets(round_num=round_num)))


@cli.command()
@click.option(
    "--round_num",
    type=int,
    help="round you are interested in. defaults to the current round",
)
@click.option(
    "--filename",
    default="numerai_live_data.parquet",
    show_default=True,
    help="file to be downloaded",
)
@click.option(
    "--dest_path",
    help="complete destination path, defaults to the name of the source file",
)
@tournament_option
def download_dataset(
    round_num,
    filename="numerai_live_data.parquet",
    dest_path=None,
    tournament=DEFAULT_TOURNAMENT,
):
    """Download specified file for the given round"""
    api = _get_api(tournament)
    click.echo(
        api.download_dataset(
            round_num=round_num, filename=filename, dest_path=dest_path
        )
    )


@cli.command()
@tournament_option
def competitions(tournament=DEFAULT_TOURNAMENT):
    """Retrieves information about all competitions"""
    api = _get_api(tournament)
    method = _require_method(api, "get_competitions", "competitions")
    click.echo(prettify(method(tournament=tournament)))


@cli.command()
@tournament_option
def current_round(tournament=DEFAULT_TOURNAMENT):
    """Get number of the current active round."""
    api = _get_api(tournament)
    click.echo(api.get_current_round(tournament=tournament))


@cli.command()
@click.option("--limit", default=20, help="Number of items to return, defaults to 20")
@click.option("--offset", default=0, help="Number of items to skip, defaults to 0")
@tournament_option
def leaderboard(limit=20, offset=0, tournament=DEFAULT_TOURNAMENT):
    """Get the leaderboard."""
    api = _get_api(tournament)
    method = _require_method(api, "get_leaderboard", "leaderboard")
    click.echo(prettify(method(limit=limit, offset=offset)))


@cli.command()
@click.option(
    "--round_num",
    type=int,
    default=None,
    help="filter by round number, defaults to None",
)
@click.option(
    "--model_id",
    type=str,
    default=None,
    help="An account model UUID (required for accounts with multiple models",
)
@tournament_option
def submission_filenames(round_num, tournament, model_id):
    """Get filenames of your submissions"""
    api = _get_api(tournament)
    method = _require_method(api, "get_submission_filenames", "submission-filenames")
    click.echo(
        prettify(method(tournament=tournament, round_num=round_num, model_id=model_id))
    )


@cli.command()
@click.option("--hours", default=12, help="timeframe to consider, defaults to 12")
@tournament_option
def check_new_round(hours=12, tournament=DEFAULT_TOURNAMENT):
    """Check if a new round has started within the last `hours`."""
    api = _get_api(tournament)
    click.echo(int(api.check_new_round(hours=hours)))


@cli.command()
@tournament_option
def account(tournament=DEFAULT_TOURNAMENT):
    """Get all information about your account!"""
    api = _get_api(tournament)
    click.echo(prettify(api.get_account()))


@cli.command()
@tournament_option
def models(tournament=DEFAULT_TOURNAMENT):
    """Get map of account models!"""
    api = _get_api(tournament)
    click.echo(prettify(api.get_models(tournament)))


@cli.command()
@click.argument("username")
@tournament_option
def profile(username, tournament=DEFAULT_TOURNAMENT):
    """Fetch the public profile of a user."""
    api = _get_api(tournament)
    method = _require_method(api, "public_user_profile", "profile")
    click.echo(prettify(method(username)))


@cli.command()
@click.argument("username")
@tournament_option
def daily_model_performances(username, tournament=DEFAULT_TOURNAMENT):
    """Fetch daily performance of a model."""
    api = _get_api(tournament)
    method = _require_method(
        api, "daily_model_performances", "daily-model-performances"
    )
    click.echo(prettify(method(username)))


@cli.command()
@tournament_option
def transactions(tournament=DEFAULT_TOURNAMENT):
    """List all your deposits and withdrawals."""
    api = _get_api(tournament)
    click.echo(prettify(api.wallet_transactions()))


@cli.command()
@click.option(
    "--model_id",
    type=str,
    default=None,
    help="An account model UUID (required for accounts with multiple models",
)
@click.argument("path", type=click.Path(exists=True))
@tournament_option
def submit(path, model_id, tournament=DEFAULT_TOURNAMENT):
    """Upload predictions from file."""
    api = _get_api(tournament)
    click.echo(api.upload_predictions(path, model_id=model_id))


@cli.command()
@click.argument("username")
@tournament_option
def stake_get(username, tournament=DEFAULT_TOURNAMENT):
    """Get stake value of a user."""
    api = _get_api(tournament)
    method = _require_method(api, "stake_get", "stake-get")
    click.echo(method(username))


@cli.command()
@click.option(
    "--model_id",
    type=str,
    default=None,
    help="An account model UUID (required for accounts with multiple models",
)
@tournament_option
def stake_drain(model_id, tournament=DEFAULT_TOURNAMENT):
    """Completely remove your stake."""
    api = _get_api(tournament)
    click.echo(api.stake_drain(model_id))


@cli.command()
@click.argument("nmr")
@click.option(
    "--model_id",
    type=str,
    default=None,
    help="An account model UUID (required for accounts with multiple models",
)
@tournament_option
def stake_decrease(nmr, model_id, tournament=DEFAULT_TOURNAMENT):
    """Decrease your stake by `value` NMR."""
    api = _get_api(tournament)
    click.echo(api.stake_decrease(nmr, model_id))


@cli.command()
@click.argument("nmr")
@click.option(
    "--model_id",
    type=str,
    default=None,
    help="An account model UUID (required for accounts with multiple models",
)
@tournament_option
def stake_increase(nmr, model_id, tournament=DEFAULT_TOURNAMENT):
    """Increase your stake by `value` NMR."""
    api = _get_api(tournament)
    click.echo(api.stake_increase(nmr, model_id))


@cli.command()
def version():
    """Installed numerapi version."""
    print(numerapi.__version__)


if __name__ == "__main__":
    cli()
