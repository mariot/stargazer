from githubkit import GitHub
from fastapi import FastAPI

from config import settings
from services import (
    group_stargazer_ids_by_star_count,
    starred_repos_by_batched_user_ids,
    starred_repos_by_user_ids,
    starred_repos_count_by_stargazers_of_repo,
    transform_dict_to_list_of_dicts,
)

app = FastAPI()
github = GitHub(settings.github_api_secret)


@app.get("/repos/{user}/{repo}/starneighbours")
def get_repo_star_neighbours(user: str, repo: str):
    all_stargazers = starred_repos_count_by_stargazers_of_repo(github, user, repo)
    batched_stargazers_ids = group_stargazer_ids_by_star_count(
        all_stargazers["less_than_100_stars_stargazers"],
    )
    less_popular_stargazers = starred_repos_by_batched_user_ids(
        github, batched_stargazers_ids, f"{user}/{repo}"
    )
    more_popular_stargazers = starred_repos_by_user_ids(
        github, all_stargazers["more_than_100_stars_stargazers"], f"{user}/{repo}"
    )
    merged_stargazers = less_popular_stargazers | more_popular_stargazers
    return transform_dict_to_list_of_dicts(merged_stargazers)
