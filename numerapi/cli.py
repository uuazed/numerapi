import click
import json
import datetime
import decimal

import numerapi

napi = numerapi.NumerAPI()


class CommonJSONEncoder(json.JSONEncoder):
    """
    Common JSON Encoder
    json.dumps(jsonString, cls=CommonJSONEncoder)
    """
    def default(self, obj):
        """Encode: Decimal"""
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        """Encode: Date & Datetime"""
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        pass


def prettify(stuff):
    return json.dumps(stuff, cls=CommonJSONEncoder, indent=4)


@click.group()
def cli():
    """Wrapper around the Numerai API"""
    pass


@cli.command()
@click.option('--tournament', default=8,
              help='The ID of the tournament, defaults to 8')
@click.option('--unzip', is_flag=True, default=True,
              help='indication of whether the data should be unzipped')
def download_dataset(tournament, unzip):
    """Download dataset for the current active round."""
    click.echo(napi.download_current_dataset(
        tournament=tournament, unzip=unzip))


@cli.command()
@click.option('--tournament', default=8,
              help='The ID of the tournament, defaults to 8')
def dataset_url(tournament):
    """Fetch url of the current dataset."""
    click.echo(prettify(napi.get_dataset_url(tournament=tournament)))


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
@click.option('--hours', default=24,
              help='timeframe to consider, defaults to 24')
def check_new_round(hours=24, tournament=8):
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
def daily_user_performances(username):
    """Fetch daily performance of a user."""
    click.echo(prettify(napi.daily_user_performances(username)))


@cli.command()
@click.argument("username")
def daily_submissions_performances(username):
    """Fetch daily performance of a user's submissions."""
    click.echo(prettify(napi.daily_submissions_performances(username)))


@cli.command()
@click.option(
    '--model_id', type=str, default=None,
    help="An account model UUID (required for accounts with multiple models")
def transactions(model_id):
    """List all your deposits and withdrawals."""
    click.echo(prettify(napi.get_transactions(model_id)))


@cli.command()
@click.option(
    '--model_id', type=str, default=None,
    help="An account model UUID (required for accounts with multiple models")
def stakes(model_id):
    """List all your stakes."""
    click.echo(prettify(napi.get_stakes(model_id)))


@cli.command()
@click.argument("model_id")
def submission_status(model_id):
    """checks the submission status"""
    click.echo(prettify(napi.submission_status(model_id)))


@cli.command()
@click.option('--tournament', default=8,
              help='The ID of the tournament, defaults to 8')
@click.option(
    '--model_id', type=str, default=None,
    help="An account model UUID (required for accounts with multiple models")
@click.argument('path', type=click.Path(exists=True))
def submit(path, tournament, model_id):
    """Upload predictions from file."""
    click.echo(napi.upload_predictions(path, tournament, model_id))


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
