from __future__ import annotations

from collections.abc import Iterator

import pytest
from flask.testing import FlaskClient

from app.config import DEFAULT_CONFIG
from app.main import create_app

# TODO: in-memory SQLite fixture lands here when app/db.py is added.


@pytest.fixture
def client() -> Iterator[FlaskClient]:
    app = create_app(dict(DEFAULT_CONFIG))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
