import pprint
import click

import numerapi

napi = numerapi.NumerAPI()


def prettify(stuff):
    pp = pprint.PrettyPrinter(indent=4)
    return pp.pformat(stuff)


@click.group()
def cli():
    """Wrapper around the Numerai API"""
    pass


@cli.command()
@click.option('--tournament', default=1,
              help='The ID of the tournament, defaults to 1')
@click.option('--unzip', is_flag=True, default=True,
              help='indication of whether the data should be unzipped')
def download_dataset(tournament, unzip):
    """Download dataset for the current active round."""
    click.echo(napi.download_current_dataset(tournament=tournament, unzip=unzip))


@cli.command()
@click.option('--tournament', default=1,
              help='The ID of the tournament, defaults to 1')
def dataset_url(tournament):
    """Fetch url of the current dataset."""
    click.echo(prettify(napi.get_dataset_url(tournament=tournament)))


@cli.command()
@click.option('--tournament', default=1,
              help='The ID of the tournament, defaults to 1')
@click.option('--round_num', default=0,
              help='The round you are interested in, defaults to current round')
def leaderboard(round_num=0, tournament=1):
    """Retrieves the leaderboard for the given round."""
    click.echo(prettify(napi.get_leaderboard(tournament=tournament,
                                             round_num=round_num)))


@cli.command()
@click.option('--tournament', default=1,
              help='The ID of the tournament, defaults to 1')
@click.option('--round_num', default=0,
              help='The round you are interested in, defaults to current round')
def staking_leaderboard(round_num=0, tournament=1):
    """Retrieves the staking competition leaderboard for the given round."""
    click.echo(prettify(napi.get_staking_leaderboard(tournament=tournament,
                                                     round_num=round_num)))


@cli.command()
@click.option('--tournament', default=1,
              help='The ID of the tournament, defaults to 1')
def competitions(tournament=1):
    """Retrieves information about all competitions"""
    click.echo(prettify(napi.get_competitions(tournament=tournament)))


@cli.command()
@click.option('--tournament', default=1,
              help='The ID of the tournament, defaults to 1')
def current_round(tournament=1):
    """Get number of the current active round."""
    click.echo(napi.get_current_round(tournament=tournament))


@cli.command()
@click.option('--tournament', default=1,
              help='The ID of the tournament, defaults to 1')
def submission_ids(tournament=1):
    """Get dict with username->submission_id mapping."""
    click.echo(prettify(napi.get_submission_ids(tournament=tournament)))


@cli.command()
@click.option('--limit', default=20,
              help='Number of items to return, defaults to 20')
@click.option('--offset', default=0,
              help='Number of items to skip, defaults to 0')
def rankings(limit=20, offset=0):
    """Get the overall rankings."""
    click.echo(prettify(napi.get_rankings(limit=limit, offset=offset)))


@cli.command()
@click.argument("username")
@click.option('--tournament', default=1,
              help='The ID of the tournament, defaults to 1')
def user_activities(username, tournament=1):
    """Get user activities (works for all users!)"""
    click.echo(prettify(napi.get_user_activities(username, tournament)))


@cli.command()
@click.option('--tournament', type=int,
              help='filter by ID of the tournament, defaults to None')
@click.option('--round_num', type=int,
              help='filter by round number, defaults to None')
def submission_filenames(round_num=None, tournament=None):
    """Get filenames of your submissions"""
    click.echo(prettify(
        napi.get_submission_filenames(tournament, round_num)))


@cli.command()
@click.option('--tournament', type=int, default=1,
              help='ID of the tournament, defaults to 1')
@click.option('--round_num', type=int, default=0,
              help='round number, defaults to the current round')
def staking_cutoff(round_num, tournament):
    """Compute staking cutoff for the given round and tournament."""
    click.echo(prettify(napi.get_staking_cutoff(round_num, tournament)))


@cli.command()
@click.option('--tournament', default=1,
              help='The ID of the tournament, defaults to 1')
@click.option('--hours', default=24,
              help='timeframe to consider, defaults to 24')
def check_new_round(hours=24, tournament=1):
    """Check if a new round has started within the last `hours`."""
    click.echo(int(napi.check_new_round(hours=hours, tournament=tournament)))


@cli.command()
def user():
    """Get all information about you!"""
    click.echo(prettify(napi.get_user()))


@cli.command()
def payments():
    """List all your payments"""
    click.echo(prettify(napi.get_payments()))


@cli.command()
def transactions():
    """List all your deposits and withdrawals."""
    click.echo(prettify(napi.get_transactions()))


@cli.command()
def stakes():
    """List all your stakes."""
    click.echo(prettify(napi.get_stakes()))


@cli.command()
def tournaments():
    """Get all active tournaments."""
    click.echo(prettify(napi.get_tournaments()))


@cli.command()
@click.argument("number", type=int)
def tournament_number2name(number):
    """Translate tournament number to tournament name."""
    click.echo(prettify(napi.tournament_number2name(number)))


@cli.command()
@click.argument("name", type=str)
def tournament_name2number(name):
    """Translate tournament name to tournament number."""
    click.echo(prettify(napi.tournament_name2number(name)))


@cli.command()
@click.argument("submission_id")
def submission_status(submission_id):
    """checks the submission status"""
    click.echo(prettify(napi.submission_status(submission_id)))


@cli.command()
@click.argument("submission_id")
def submission_successful(submission_id):
    """Check if the last submission passes submission criteria."""
    click.echo(int(napi.check_submission_successful(submission_id)))


@cli.command()
@click.argument("confidence")
@click.argument("value")
@click.option('--tournament', default=1,
              help='The ID of the tournament, defaults to 1')
def stake(confidence, value, tournament):
    """Participate in the staking competition."""
    click.echo(napi.stake(confidence, value, tournament))


@cli.command()
@click.option('--tournament', default=1,
              help='The ID of the tournament, defaults to 1')
@click.argument('path', type=click.Path(exists=True))
def submit(path, tournament):
    """Upload predictions from file."""
    click.echo(napi.upload_predictions(path, tournament))


@cli.command()
def version():
    """Installed numerapi version."""
    print(numerapi.__version__)


if __name__ == "__main__":
    cli()
