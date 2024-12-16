from fastapi.testclient import TestClient

from config import Settings
from main import app, get_settings

import json
from pathlib import Path
from typing import Any, Type, TypeVar, Union

import httpx
import pytest

from githubkit import GitHub
from githubkit.utils import UNSET
from githubkit.response import Response
from githubkit.typing import URLTypes, UnsetType

client = TestClient(app)


def get_settings_override():
    return Settings(github_api_secret="very_secret_very_secure")


app.dependency_overrides[get_settings] = get_settings_override

STARRED_REPO_COUNT_BY_USERS = json.loads(
    Path("fake_response_data/starred_repo_count_by_users.json").read_text()
)
STARRED_REPO_BY_USER_IDS = json.loads(
    Path("fake_response_data/starred_repo_by_user_ids.json").read_text()
)
STARRED_REPO_BY_USER_ID = json.loads(
    Path("fake_response_data/starred_repos_by_user_id.json").read_text()
)

T = TypeVar("T")


def mock_request(
    g: GitHub,
    method: str,
    url: URLTypes,
    *,
    response_model: Union[Type[Any], UnsetType] = UNSET,
    **kwargs: Any,
) -> Response[Any]:
    if method == "POST" and url == "/graphql":
        if "StarredRepoCountByUsers" in kwargs["json"]["query"]:
            return Response[T](
                httpx.Response(status_code=200, json=STARRED_REPO_COUNT_BY_USERS),
                Any if response_model is UNSET else response_model,
            )
        elif "StarredRepoByUserIds" in kwargs["json"]["query"]:
            return Response[T](
                httpx.Response(status_code=200, json=STARRED_REPO_BY_USER_IDS),
                Any if response_model is UNSET else response_model,
            )
        elif "StarredRepoByUserId" in kwargs["json"]["query"]:
            return Response[T](
                httpx.Response(status_code=200, json=STARRED_REPO_BY_USER_ID),
                Any if response_model is UNSET else response_model,
            )
    raise RuntimeError(f"Unexpected request: {method} {url}")


def test_read_main():
    with pytest.MonkeyPatch.context() as m:
        # Patch the request method with the mock
        m.setattr(GitHub, "request", mock_request)

        response = client.get("/repos/octocat/Hello-World/starneighbours")
        assert response.status_code == 200
        assert response.json() == [
            {
                "repo": "Renari/Fate-Grand-Order-Translation",
                "stargazers": ["kevintongg"],
            },
            {"repo": "kubernetes/kubernetes", "stargazers": ["another"]},
            {"repo": "microsoft/vscode", "stargazers": ["another"]},
        ]
