from __future__ import annotations

import argparse
import logging
import threading
import time

import uvicorn
from pathlib import Path

from .api import create_app
from .config import load_site
from .runtime import Runtime
from .bootstrap import run_setup
from .setup_store import SetupStore


def build_runtime(site_path: str, plugin_dir: str = "plugins", data_dir: str = "data") -> Runtime:
    site = load_site(site_path)
    runtime = Runtime(
        site,
        plugin_dir=plugin_dir,
        historian_path=f"{data_dir}/{site.site.id}/historian.sqlite3",
    )
    runtime.configure()
    runtime.start()
    runtime.collect_once()
    return runtime


def _background_loop(runtime: Runtime, interval_seconds: float, stop: threading.Event) -> None:
    while not stop.wait(interval_seconds):
        runtime.collect_once()
        runtime.evaluate_strategy()
        runtime.evaluate_outcomes()
        runtime.learning.fit_passive_baselines()
        runtime.learning.fit_thermal_context_baseline()
        runtime.learning.fit_dhw_baseline()
        runtime.learning.fit_electrical_baseline()
        runtime.learning.fit_pv_orientation_baseline()


def main() -> None:
    parser = argparse.ArgumentParser(description="INS-EI standalone runtime")
    parser.add_argument("--site", default="config/site.example.yaml")
    parser.add_argument("--plugins", default="plugins")
    parser.add_argument("--data", default="data")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8080, type=int)
    parser.add_argument("--interval", default=10.0, type=float)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    requested_site = Path(args.site)
    local_store = SetupStore(args.data)
    if not requested_site.is_file():
        if local_store.exists():
            requested_site = local_store.site_path
        else:
            logging.info("No Site configuration found; starting INS-EI Setup Wizard")
            run_setup(args.host, args.port, args.plugins, args.data)
            return

    try:
        runtime = build_runtime(str(requested_site), args.plugins, args.data)
    except Exception:
        logging.exception("Stored Site configuration is invalid; returning to Setup Wizard")
        run_setup(args.host, args.port, args.plugins, args.data)
        return
    stop = threading.Event()
    worker = threading.Thread(
        target=_background_loop,
        args=(runtime, max(1.0, args.interval), stop),
        daemon=True,
        name="ins-ei-runtime",
    )
    worker.start()
    try:
        uvicorn.run(create_app(runtime), host=args.host, port=args.port)
    finally:
        stop.set()
        worker.join(timeout=5)
        runtime.stop()


if __name__ == "__main__":
    main()
