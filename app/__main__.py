from __future__ import annotations

import logging
import os

from app.main import create_app

logger = logging.getLogger(__name__)


def main() -> None:
    app = create_app()
    config = app.config["QUOTE_BOX"]
    host: str = config["bind_host"]
    port: int = config["port"]
    debug = os.environ.get("FLASK_DEBUG") == "1"
    logger.info("server starting", extra={"host": host, "port": port, "debug": debug})
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
