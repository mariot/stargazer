from pydantic import BaseModel
from typing import List


class Stargazer(BaseModel):
    id: str
    login: str


class StargazerWithStarredReposCount(Stargazer):
    starred_repos_count: int


class StarredRepoCount(BaseModel):
    less_than_100_stars_stargazers: List[StargazerWithStarredReposCount]
    more_than_100_stars_stargazers: List[StargazerWithStarredReposCount]


class ResponseItem(BaseModel):
    repo: str
    stargazers: List[str]


class FastAPIException(BaseModel):
    detail: str
