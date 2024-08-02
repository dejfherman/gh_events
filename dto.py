from pydantic import BaseModel, Field


class Repo(BaseModel):
    name: str
    owner: str
    remote_id: int | None = None


class RepoList(BaseModel):
    repositories: list[Repo] = Field(..., max_items=5)
