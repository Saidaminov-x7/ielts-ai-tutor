import pytest

from app.database.session import Base, make_engine


@pytest.fixture
def session():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        yield db
    engine.dispose()
