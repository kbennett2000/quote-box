from __future__ import annotations

import shutil
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
def seed_json() -> Path:
    return Path(__file__).parent / "fixtures" / "quotes_sample.json"


@pytest.fixture(scope="session")
def _seeded_db_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a fully-seeded SQLite file once per test session.

    Per-test fixtures copy this file into ``tmp_path``, skipping the schema
    init + seed cost (~80–100ms each) on every test that needs a populated DB.
    """
    template = tmp_path_factory.mktemp("seed") / "template.db"
    init_db(template)
    seed_if_empty(
        template,
        Path(__file__).parent / "fixtures" / "quotes_sample.json",
    )
    return template


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def empty_db(db_path: Path) -> Iterator[sqlite3.Connection]:
    init_db(db_path)
    conn = _connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def seeded_db_path(_seeded_db_template: Path, tmp_path: Path) -> Path:
    dest = tmp_path / "test.db"
    shutil.copy(_seeded_db_template, dest)
    return dest


@pytest.fixture
def seeded_db(seeded_db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = _connect(seeded_db_path)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def app(seeded_db_path: Path, seed_json: Path) -> Flask:
    # create_app will see the DB is already seeded and skip the seed step,
    # so this path is fast.
    cfg = dict(DEFAULT_CONFIG)
    cfg["db_path"] = str(seeded_db_path)
    cfg["seed_json_path"] = str(seed_json)
    return create_app(cfg)


@pytest.fixture
def client(app: Flask) -> Iterator[FlaskClient]:
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
