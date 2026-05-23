from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.config import DEFAULT_CONFIG
from app.db import _connect, init_db
from app.main import create_app
from app.seed import seed_if_empty


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def seed_json() -> Path:
    return Path(__file__).parent / "fixtures" / "quotes_sample.json"


@pytest.fixture
def empty_db(db_path: Path) -> Iterator[sqlite3.Connection]:
    init_db(db_path)
    conn = _connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def seeded_db(db_path: Path, seed_json: Path) -> Iterator[sqlite3.Connection]:
    init_db(db_path)
    seed_if_empty(db_path, seed_json)
    conn = _connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def app(db_path: Path, seed_json: Path) -> Flask:
    cfg = dict(DEFAULT_CONFIG)
    cfg["db_path"] = str(db_path)
    cfg["seed_json_path"] = str(seed_json)
    return create_app(cfg)


@pytest.fixture
def client(app: Flask) -> Iterator[FlaskClient]:
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
