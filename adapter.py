import httpx
from dto import Repo
from model import Event, Repository
from logger import logger
from datetime import datetime, timedelta


type EventDict = dict[str, str | datetime]
"""
{
    'type': str,
    'created_at': datetime,
    'remote_id': str (represents int),
    'repository_id': str (represents int),   
}
"""


class GitHubAdapter:

    BASE_URL = 'https://api.github.com/'
    HEADERS = {'Accept': 'application/vnd.github.v3+json'}
    PARAMS = {"per_page": 100}
    DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

    @staticmethod
    def ping_repo(repo: Repo) -> Repo:
        """Sends request to a github repo to check if it exists.

        Fills in missing data to the Repo parameter if needed.
        """
        response = httpx.get(f'{GitHubAdapter.BASE_URL}repos/{repo.owner}/{repo.name}', timeout=10)

        response.raise_for_status()

        repository_data = response.json()
        repo.remote_id = repository_data['id']

        return repo

    @staticmethod
    def fetch_events(repo: Repository, last_known_event: Event = None) -> list[EventDict]:
        """Downloads recent event data related to a single repository via GitHub Events API. Limits the amount of events
        by 500 or a time cutoff of one week or last_known_event.created_at, whichever is later.

        Returns a list of EventDict items (as opposed to some more powerful Event model) in order to be immediately
        usable in an sqlite-specific insert statement.
        """
        events_url = f'{GitHubAdapter.BASE_URL}repos/{repo.owner}/{repo.name}/events'
        events_total = []
        logger.info(f'Fetching events from {repo.owner}/{repo.name}')

        week_ago = datetime.now() - timedelta(days=7)
        cutoff_datetime = week_ago if not last_known_event or week_ago > last_known_event.created_at \
            else last_known_event.created_at
        earliest_found_event = None

        # the datetime cutoff is also handled within fetch_event_batch,
        # but I like to leave it here for completeness and readability
        while events_url \
                and len(events_total) < 500 \
                and (not earliest_found_event or earliest_found_event['created_at'] > cutoff_datetime):
            events_batch, events_url = GitHubAdapter.fetch_event_batch(events_url, last_known_event)

            earliest_found_event = events_batch[-1] if events_batch else None
            events_total.extend(events_batch)

        return events_total

    @staticmethod
    def fetch_event_batch(url: str, last_known_event: Event = None) -> (list[EventDict], str):
        """Downloads event data from a single page of the GitHub Events API.

        :param url: url leading to a page of GitHub Events API
        :param last_known_event: an Event object whose created_at property serves as download limit
        :return: events: list of found data packaged into EventDict items
                 next_url: url to next page of the Events API
        """
        response = httpx.get(url, headers=GitHubAdapter.HEADERS, params=GitHubAdapter.PARAMS, timeout=30)
        response.raise_for_status()

        next_url = response.links.get('next')
        next_url = next_url.get('url') if next_url else None

        events = []
        for event in response.json():
            if last_known_event and int(event['id']) == last_known_event.remote_id:
                # events returned by GH API should be ordered by date_created, so the unambiguity of id comparison
                # is preferable to datetime comparison
                next_url = None
                break

            events.append({
                'type': event['type'],
                'created_at': datetime.strptime(event['created_at'], GitHubAdapter.DATETIME_FORMAT),
                'remote_id': event['id'],
                'repository_id': event['repo']['id']
            })

        log_msg = f'Found {len(events)} new events'
        log_msg = f'{log_msg} dating {events[0]['created_at']} - {events[-1]['created_at']}' \
            if len(events) > 0 else log_msg
        logger.info(log_msg)

        return events, next_url

