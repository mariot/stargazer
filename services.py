from typing import List

from githubkit import GitHub

from config import settings
from schema import StargazerWithStarredReposCount, StarredRepoCount


def starred_repos_count_by_stargazers_of_repo(
    github: GitHub, user: str, repo: str
) -> StarredRepoCount:
    query = f"""
    query ($user: String!, $repo: String!, $cursor: String) {{
        repository(owner: $user, name: $repo) {{
            stargazers(first: {settings.stargazers_per_page}, after: $cursor) {{
                nodes {{
                    id
                    login
                    starredRepositories {{
                        totalCount
                    }}
                }}
                pageInfo {{
                    endCursor
                    hasNextPage
                }}
            }}
        }}
    }}
    """
    less_than_100_stars_stargazers = []
    more_than_100_stars_stargazers = []
    for result in github.graphql.paginate(
        query, variables={"user": user, "repo": repo}
    ):
        for stargazer in result["repository"]["stargazers"]["nodes"]:
            starred_repos_count = stargazer["starredRepositories"]["totalCount"]
            stargazer_with_starred_repos_count = {
                "id": stargazer["id"],
                "login": stargazer["login"],
                "starred_repos_count": starred_repos_count,
            }
            if starred_repos_count < 100:
                less_than_100_stars_stargazers.append(
                    stargazer_with_starred_repos_count
                )
            else:
                more_than_100_stars_stargazers.append(
                    stargazer_with_starred_repos_count
                )
    return StarredRepoCount(
        less_than_100_stars_stargazers=less_than_100_stars_stargazers,
        more_than_100_stars_stargazers=more_than_100_stars_stargazers,
    )


def starred_repos_by_batched_user_ids(
    github: GitHub, user_ids_list: list[list[str]], ignore_repo: str
) -> dict[str, list[str]]:
    query = """
    query StarredRepoByUserIds($ids: [ID!]!) {
      nodes(ids: $ids) {
        ... on User {
          login
          starredRepositories {
            nodes {
              owner {
                login
              }
              name
            }
          }
        }
      }
    }
    """
    batched_user_ids = {}
    for user_ids in user_ids_list:
        result = github.graphql(query, variables={"ids": user_ids})
        for user in result["nodes"]:
            batched_user_ids[user["login"]] = [
                f"{repo['owner']['login']}/{repo['name']}"
                for repo in user["starredRepositories"]["nodes"]
                if f"{repo['owner']['login']}/{repo['name']}" != ignore_repo
            ]
    return batched_user_ids


def starred_repos_by_user_ids(
    github: GitHub, users_list: List[StargazerWithStarredReposCount], ignore_repo: str
) -> dict:
    query = """
    query StarredRepoByUserId($id: ID!, $cursor: String) {
      node(id: $id) {
        ... on User {
          login
          starredRepositories(first: 100, after: $cursor) {
            nodes {
              owner {
                login
              }
              name
            }
            pageInfo {
                endCursor
                hasNextPage
            }
          }
        }
      }
    }
    """
    starred_repos_counts = {}
    for user in users_list:
        user_stars = 0
        starred_repos_counts[user.login] = []
        for result in github.graphql.paginate(query, variables={"id": user.id}):
            starred_repos_counts[result["node"]["login"]].extend(
                [
                    f"{repo['owner']['login']}/{repo['name']}"
                    for repo in result["node"]["starredRepositories"]["nodes"]
                    if f"{repo['owner']['login']}/{repo['name']}" != ignore_repo
                ]
            )
            user_stars += 100
            if user_stars >= settings.max_stars_per_stargazer:
                break
    return starred_repos_counts


def group_stargazer_ids_by_star_count(
    stargazers: List[StargazerWithStarredReposCount],
) -> list[list[str]]:
    """
    Groups stargazer IDs into sublists where each sublist's total number of stars
    does not exceed 100, each sublist contains no more than 50 elements, and ignores
    stargazers with 0 stars.

    Args:
        stargazers (List[StargazerWithStarredReposCount]): A list of dictionaries,
        each containing 'id' and 'starred_repos_count' keys.

    Returns:
        list[list[str]]: A list of lists, where each inner list contains stargazer IDs.
    """
    grouped_ids = []
    current_group = []
    current_star_count = 0

    for stargazer in stargazers:
        starred_repos_count = stargazer.starred_repos_count
        if starred_repos_count == 0:
            continue
        if (
            current_star_count + starred_repos_count > 100
            or len(current_group) >= settings.max_sublist_length
        ):
            grouped_ids.append(current_group)
            current_group = []
            current_star_count = 0
        current_group.append(stargazer.id)
        current_star_count += starred_repos_count

    if current_group:
        grouped_ids.append(current_group)

    return grouped_ids


def transform_dict_to_list_of_dicts(input_dict):
    repo_dict = {}
    for stargazer, repos in input_dict.items():
        for repo in repos:
            if repo not in repo_dict:
                repo_dict[repo] = []
            repo_dict[repo].append(stargazer)

    result = [
        {"repo": repo, "stargazers": stargazers}
        for repo, stargazers in repo_dict.items()
    ]
    return result
