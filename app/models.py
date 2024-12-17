from typing import Annotated

from fastapi import Depends
from sqlmodel import Field, Session, SQLModel, create_engine


class User(SQLModel, table=True):
    username: str = Field(primary_key=True)
    email: str = Field(index=True)
    full_name: str | None = Field(default=None)
    hashed_password: str
    disabled: bool = Field(default=False)


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
