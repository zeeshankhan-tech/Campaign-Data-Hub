"""CLI entrypoint for running ingestion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.ingestion.pipeline import run_ingestion


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Campaign Data Hub ingestion")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Path to assessment data directory containing deliveries/ and exchange_rates.json",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(settings.log_level)

    data_dir = args.data_dir
    if data_dir is None:
        data_dir = (Path.cwd() / settings.assessment_data_dir).resolve()
    else:
        data_dir = data_dir.resolve()

    with SessionLocal() as session:
        result = run_ingestion(session, data_dir=data_dir)

    print(json.dumps(result.summary, indent=2, default=str))
    return 0 if result.status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
