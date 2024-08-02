import model                            # model import required for db initialization
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from dto import RepoList
from database import init_db, get_db, exists_statement
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session
from model import Repository, Event
from adapter import GitHubAdapter
from httpx import HTTPError
from logger import logger
from util import avg_created_diff

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Use lifespan events to initialize db on startup.
    """
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/set-repos")
async def set_up_repositories(repolist: RepoList, db: Session = Depends(get_db)):
    """Accepts a list of up to five GitHub repositories, checks if they exist and saves their identifiers for local use.
    """
    response_msg = {}
    repositories = []

    for repo in repolist.repositories:
        try:
            if db.execute(exists_statement(Repository, {"owner": repo.owner, "name": repo.name})).scalar():
                response_msg[f'{repo.owner}/{repo.name}'] = "Already monitored"
                continue
            repo = GitHubAdapter.ping_repo(repo)
            repositories.append(Repository(**repo.model_dump()))
        except HTTPError as e:
            response_msg[f'{repo.owner}/{repo.name}'] = "Error: cannot reach repository"
            continue
        response_msg[f'{repo.owner}/{repo.name}'] = "Monitoring set up OK"

        db.add_all(repositories)

    return response_msg


@app.get("/event-stats")
async def calculate_repo_statistics(db: Session = Depends(get_db)):
    """Returns the average time diff in seconds between consecutive events split by type for each monitored repository.
    """
    # load up repository objects
    repositories = db.execute(select(Repository)).scalars().all()

    logger.info("Initiating event download routine")
    for repo in repositories:
        last_known_event = repo.get_last_event(db)
        events = GitHubAdapter.fetch_events(repo, last_known_event)

        if events:
            # sometimes the events from GH API don't come perfectly time-ordered down to seconds,
            # so we ignore any duplicate events coming through
            statement = insert(Event).values(events).on_conflict_do_nothing(index_elements=['remote_id'])
            db.execute(statement)

    # commit newfound events before calculations
    logger.info("Saving all newfound events")
    db.commit()

    # calculate statistics and send
    response_msg = {}
    for repo in repositories:
        window_events = repo.get_recent_events_by_type(db)
        response_msg[f'{repo.owner}/{repo.name}'] = {
            event_type: avg_created_diff(event_list) for event_type, event_list in window_events.items()
        }

    return response_msg
