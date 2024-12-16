from typing import List

from githubkit import GitHub
from fastapi import FastAPI, HTTPException, status

from fastapi.middleware.gzip import GZipMiddleware
from githubkit.exception import AuthCredentialError, GraphQLFailed

from config import settings
from schema import FastAPIException, ResponseItem
from services import (
    group_stargazer_ids_by_star_count,
    starred_repos_by_batched_user_ids,
    starred_repos_by_user_ids,
    starred_repos_count_by_stargazers_of_repo,
    transform_dict_to_list_of_dicts,
)

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
github = GitHub(settings.github_api_secret)


@app.get(
    "/repos/{user}/{repo}/starneighbours",
    response_model=List[ResponseItem],
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": FastAPIException,
            "description": "Invalid request or GitHub API error",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": FastAPIException,
            "description": "Invalid GitHub API secret",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": FastAPIException,
            "description": "Invalid GitHub API secret",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": FastAPIException,
            "description": "Repository not found",
        },
    },
)
def get_repo_star_neighbours(user: str, repo: str):
    try:
        all_stargazers = starred_repos_count_by_stargazers_of_repo(github, user, repo)
        batched_stargazers_ids = group_stargazer_ids_by_star_count(
            stargazers=all_stargazers.less_than_100_stars_stargazers,
        )
        less_popular_stargazers = starred_repos_by_batched_user_ids(
            github=github,
            user_ids_list=batched_stargazers_ids,
            ignore_repo=f"{user}/{repo}",
        )
        more_popular_stargazers = starred_repos_by_user_ids(
            github=github,
            users_list=all_stargazers.more_than_100_stars_stargazers,
            ignore_repo=f"{user}/{repo}",
        )
        merged_stargazers = less_popular_stargazers | more_popular_stargazers
        return transform_dict_to_list_of_dicts(merged_stargazers)
    except GraphQLFailed as e:
        for error in e.response.errors:
            if error.type == "NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=error.message
                )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AuthCredentialError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
