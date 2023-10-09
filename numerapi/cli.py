""" Access the numerai API via command line"""

import json
import datetime
import decimal

import click

import numerapi

napi = numerapi.NumerAPI()


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
@click.option('--round_num',
              help='round you are interested in.defaults to the current round')
def list_datasets(round_num):
    """List of available data files"""
    click.echo(prettify(napi.list_datasets(round_num=round_num)))


@cli.command()
@click.option(
    '--round_num',
    help='round you are interested in.defaults to the current round')
@click.option(
    '--filename', help='file to be downloaded')
@click.option(
    '--dest_path',
    help='complate destination path, defaults to the name of the source file')
def download_dataset(round_num, filename="numerai_live_data.parquet",
                     dest_path=None):
    """Download specified file for the given round"""
    click.echo("WARNING to download the old data use `download-dataset-old`")
    click.echo(napi.download_dataset(
        round_num=round_num, filename=filename, dest_path=dest_path))


@cli.command()
@click.option('--tournament', default=8,
              help='The ID of the tournament, defaults to 8')
def competitions(tournament=8):
    """Retrieves information about all competitions"""
    click.echo(prettify(napi.get_competitions(tournament=tournament)))


@cli.command()
@click.option('--tournament', default=8,
              help='The ID of the tournament, defaults to 8')
def current_round(tournament=8):
    """Get number of the current active round."""
    click.echo(napi.get_current_round(tournament=tournament))


@cli.command()
@click.option('--limit', default=20,
              help='Number of items to return, defaults to 20')
@click.option('--offset', default=0,
              help='Number of items to skip, defaults to 0')
def leaderboard(limit=20, offset=0):
    """Get the leaderboard."""
    click.echo(prettify(napi.get_leaderboard(limit=limit, offset=offset)))


@cli.command()
@click.option('--tournament', type=int, default=None,
              help='filter by ID of the tournament, defaults to None')
@click.option('--round_num', type=int, default=None,
              help='filter by round number, defaults to None')
@click.option(
    '--model_id', type=str, default=None,
    help="An account model UUID (required for accounts with multiple models")
def submission_filenames(round_num, tournament, model_id):
    """Get filenames of your submissions"""
    click.echo(prettify(
        napi.get_submission_filenames(tournament, round_num, model_id)))


@cli.command()
@click.option('--tournament', default=8,
              help='The ID of the tournament, defaults to 8')
@click.option('--hours', default=12,
              help='timeframe to consider, defaults to 12')
def check_new_round(hours=12, tournament=8):
    """Check if a new round has started within the last `hours`."""
    click.echo(int(napi.check_new_round(hours=hours, tournament=tournament)))


@cli.command()
@click.option(
    '--model_id', type=str, default=None,
    help="An account model UUID (required for accounts with multiple models")
def user(model_id):
    """Get all information about you! DEPRECATED - use account"""
    click.echo(prettify(napi.get_user(model_id)))


@cli.command()
def account():
    """Get all information about your account!"""
    click.echo(prettify(napi.get_account()))


@cli.command()
@click.option('--tournament', default=8,
              help='The ID of the tournament, defaults to 8')
def models(tournament):
    """Get map of account models!"""
    click.echo(prettify(napi.get_models(tournament)))


@cli.command()
@click.argument("username")
def profile(username):
    """Fetch the public profile of a user."""
    click.echo(prettify(napi.public_user_profile(username)))


@cli.command()
@click.argument("username")
def daily_model_performances(username):
    """Fetch daily performance of a model."""
    click.echo(prettify(napi.daily_model_performances(username)))


@cli.command()
def transactions():
    """List all your deposits and withdrawals."""
    click.echo(prettify(napi.wallet_transactions()))


@cli.command()
@click.option('--tournament', default=8,
              help='The ID of the tournament, defaults to 8')
@click.option(
    '--model_id', type=str, default=None,
    help="An account model UUID (required for accounts with multiple models")
@click.argument('path', type=click.Path(exists=True))
def submit(path, tournament, model_id):
    """Upload predictions from file."""
    click.echo(napi.upload_predictions(
        path, tournament, model_id))


@cli.command()
@click.argument("username")
def stake_get(username):
    """Get stake value of a user."""
    click.echo(napi.stake_get(username))


@cli.command()
@click.option(
    '--model_id', type=str, default=None,
    help="An account model UUID (required for accounts with multiple models")
def stake_drain(model_id):
    """Completely remove your stake."""
    click.echo(napi.stake_drain(model_id))


@cli.command()
@click.argument("nmr")
@click.option(
    '--model_id', type=str, default=None,
    help="An account model UUID (required for accounts with multiple models")
def stake_decrease(nmr, model_id):
    """Decrease your stake by `value` NMR."""
    click.echo(napi.stake_decrease(nmr, model_id))


@cli.command()
@click.argument("nmr")
@click.option(
    '--model_id', type=str, default=None,
    help="An account model UUID (required for accounts with multiple models")
def stake_increase(nmr, model_id):
    """Increase your stake by `value` NMR."""
    click.echo(napi.stake_increase(nmr, model_id))


@cli.command()
def version():
    """Installed numerapi version."""
    print(numerapi.__version__)


if __name__ == "__main__":
    cli()
