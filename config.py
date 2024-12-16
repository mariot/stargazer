from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    github_api_secret: str
    max_sublist_length: int = 50  # The maximum number of elements in each sublist.
    # Should be between 30 and 80.
    stargazers_per_page: int = 10  # The number of stargazers to fetch per page.
    max_stars_per_stargazer: int = 150


settings = Settings()
