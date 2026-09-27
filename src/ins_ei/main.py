from __future__ import annotations

import argparse
import logging

import uvicorn

from .api import create_app
from .config import load_site
from .runtime import Runtime


def build_runtime(site_path: str) -> Runtime:
    site = load_site(site_path)
    runtime = Runtime(site)
    runtime.configure()
    runtime.start()
    runtime.collect_once()
    return runtime


def main() -> None:
    parser = argparse.ArgumentParser(description="INS-EI standalone runtime")
    parser.add_argument("--site", default="config/site.example.yaml")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    runtime = build_runtime(args.site)
    try:
        uvicorn.run(create_app(runtime), host=args.host, port=args.port)
    finally:
        runtime.stop()


if __name__ == "__main__":
    main()
