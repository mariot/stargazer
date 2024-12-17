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


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str


class UserCreate(User):
    password: str
    disabled: bool = False
