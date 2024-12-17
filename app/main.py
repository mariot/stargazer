from datetime import timedelta
from functools import lru_cache
from typing import Annotated, List

from fastapi.security import OAuth2PasswordRequestForm
from githubkit import GitHub
from fastapi import FastAPI, HTTPException, status, Depends

from fastapi.middleware.gzip import GZipMiddleware
from githubkit.exception import AuthCredentialError, GraphQLFailed

from .config import Settings
from .models import SessionDep, create_db_and_tables, User as UserModel
from .schema import FastAPIException, ResponseItem, Token, User, UserCreate
from .services import (
    group_stargazer_ids_by_star_count,
    starred_repos_by_batched_user_ids,
    starred_repos_by_user_ids,
    starred_repos_count_by_stargazers_of_repo,
    transform_dict_to_list_of_dicts,
)
from .utils import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_password_hash,
)

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@lru_cache
def get_settings():
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]


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
def get_repo_star_neighbours(
    user: str,
    repo: str,
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[User, Depends(get_current_active_user)],
):
    try:
        github = GitHub(settings.github_api_secret)
        all_stargazers = starred_repos_count_by_stargazers_of_repo(
            github=github,
            user=user,
            repo=repo,
            stargazers_per_page=settings.stargazers_per_page,
        )
        batched_stargazers_ids = group_stargazer_ids_by_star_count(
            stargazers=all_stargazers.less_than_100_stars_stargazers,
            max_sublist_length=settings.max_sublist_length,
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
            max_stars_per_stargazer=settings.max_stars_per_stargazer,
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


@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
    settings: SettingsDep,
) -> Token:
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username},
        secret_key=settings.secret_key,
        algorithm=settings.algorithm,
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


@app.get("/users/me/", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user


@app.post("/users/", response_model=User)
async def create_user(user: UserCreate, session: SessionDep):
    hashed_password = get_password_hash(user.password)
    new_user = UserModel(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        disabled=user.disabled,
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user
