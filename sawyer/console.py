import argparse
import getpass
import re
import sawyer
import logging

from .changelog import render_changelog
from .github import PullRequestFetcher, DiffFetcher

PR_MESSAGE_FORMAT = re.compile('^Merge pull request #(\d+) from (.*)')


def configure_logging(quiet):
    log_level = logging.ERROR if quiet else logging.INFO
    logging.basicConfig(
        format='%(message)s', level=log_level
    )
    logging.getLogger("requests").setLevel(logging.WARNING)


def merged_pr_numbers(commits):
    """ Iterate through commits and identify merge commits
    """

    merged_pr_numbers = []

    for commit in commits:
        pr_message = PR_MESSAGE_FORMAT.match(commit['commit']['message'])
        if pr_message:
            merged_pr_numbers.append(int(pr_message.group(1)))

    return merged_pr_numbers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', dest='github-user', action='store')
    parser.add_argument('-t', dest='github-token', action='store')
    parser.add_argument('-q', dest='quiet', action='store_true', default=False)
    parser.add_argument('--all-prs', dest='all-prs', action='store_const',
                        const=True, default=False)
    parser.add_argument('--head', default='develop')
    parser.add_argument('repo')
    parser.add_argument('previous-tag')
    parser.add_argument('current-tag')

    args = vars(parser.parse_args())

    user = args['github-user']
    token = args['github-token']
    owner, repo = args['repo'].split('/')
    all_prs = args['all-prs']
    head = args['head']
    previous_tag = args['previous-tag']
    current_tag = args['current-tag']
    quiet = args['quiet']

    configure_logging(quiet)

    if not token:
        token = getpass.getpass()

    pr_fetcher = PullRequestFetcher(user, token, owner, repo)
    diff_fetcher = DiffFetcher(user, token, owner, repo)

    if not all_prs:
        commits = diff_fetcher.fetch(previous_tag, head)
        pr_numbers = merged_pr_numbers(commits)
    else:
        pr_numbers = None

    prs = pr_fetcher.fetch(pr_numbers=pr_numbers)

    context = {
        'current_tag': current_tag,
        'previous_tag': previous_tag,
        'owner': owner,
        'repo': repo,
        'pull_requests': prs
    }

    print(render_changelog(context))
