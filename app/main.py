from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from flask import Flask

from app.config import load_config
from app.db import close_db, init_db
from app.logging_setup import configure_logging
from app.routes import authors, health, notes, profiles, quotes, tags
from app.seed import seed_if_empty

logger = logging.getLogger(__name__)


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    configure_logging()
    config = test_config if test_config is not None else load_config()

    app = Flask(__name__)
    app.config["QUOTE_BOX"] = config

    db_path = Path(config["db_path"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    init_db(db_path)

    counts = seed_if_empty(db_path, Path(config["seed_json_path"]))
    if counts is None:
        logger.info("seed skipped, db already populated or seed file missing")
    else:
        logger.info(
            "seeded",
            extra={
                "quotes": counts.quotes,
                "tags": counts.tags,
                "quote_tags": counts.quote_tags,
            },
        )

    app.teardown_appcontext(close_db)
    app.register_blueprint(health.bp)
    app.register_blueprint(quotes.bp)
    app.register_blueprint(tags.bp)
    app.register_blueprint(authors.bp)
    app.register_blueprint(profiles.bp)
    app.register_blueprint(notes.bp)

    return app
