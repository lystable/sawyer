import re
import requests
import logging

from .pull_request import PullRequest

API_URI = 'https://api.github.com/repos/{owner}/{repo}'

PR_MESSAGE_FORMAT = re.compile('^Merge pull request #(\d+) from (.*)')


_log = logging.getLogger(__name__)


class GithubFetcher:
    def __init__(self, user, password, owner, repo):
        self.auth = user, password
        self.uri = API_URI.format(owner=owner, repo=repo) + self.endpoint

    @property
    def endpoint(self):
        """Endpoint to visit in the API."""
        raise NotImplementedError

    def fetch(self):
        """Method to fetch the API endpoint."""
        return requests.get(self.uri, auth=self.auth).json()


class PullRequestFetcher(GithubFetcher):
    endpoint = '/pulls'

    def _fetch_recursive(self, page, raw_prs=[], stop_at=None):
        params = {
            'state': 'all',
            'page': page,
            'direction': 'desc'
        }

        response = requests.get(
            self.uri, params=params, auth=self.auth
        )

        if response.status_code == 401:
            raise ValueError('Wrong password')

        raw = response.json()

        # Until no content is returned, get more PRs
        if not raw:
            return raw_prs

        should_stop = False

        for item in raw:
            raw_prs.append(item)
            if item['number'] <= stop_at:
                should_stop = True

        _log.info('Got {} pull requests'.format(len(raw_prs)))

        if should_stop:
            return raw_prs

        return self._fetch_recursive(
            page=page + 1, raw_prs=raw_prs, stop_at=stop_at
        )

    def fetch(self, pr_numbers=None):
        if pr_numbers:
            earliest_pr = sorted(pr_numbers)[0]
        else:
            earliest_pr = 1

        raw_prs = self._fetch_recursive(1, stop_at=earliest_pr)
        pull_requests = []
        for pr in raw_prs:
            if pr_numbers and pr['number'] not in pr_numbers:
                continue

            pull_requests.append(PullRequest(pr))

        return pull_requests


class DiffFetcher(GithubFetcher):
    endpoint = '/compare/{base}...{head}'

    def fetch(self, base, head):
        response = requests.get(
            self.uri.format(base=base, head=head), auth=self.auth
        ).json()

        return response['commits']

    def merged_pr_numbers(self, base, head):
        commits = self.fetch(base, head)

        # Iterate through commits and identify merge commits

        merged_pr_numbers = []

        for commit in commits:
            pr_message = PR_MESSAGE_FORMAT.match(commit['commit']['message'])
            if pr_message:
                merged_pr_numbers.append(int(pr_message.group(1)))

        return merged_pr_numbers
