from __future__ import annotations

import logging
from typing import Any

from flask import Flask

from app.config import load_config
from app.logging_setup import configure_logging
from app.routes import health

logger = logging.getLogger(__name__)


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    configure_logging()
    config = test_config if test_config is not None else load_config()

    app = Flask(__name__)
    app.config["QUOTE_BOX"] = config
    app.register_blueprint(health.bp)

    return app
