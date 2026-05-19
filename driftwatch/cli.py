"""Command-line interface for driftwatch."""

import argparse
import sys
import logging
from pathlib import Path

from driftwatch.config import load_config, ConfigError
from driftwatch.runner import run_once
from driftwatch.scheduler import run_loop

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=level,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="driftwatch",
        description="Monitor local config files against a remote source of truth.",
    )
    parser.add_argument(
        "-c", "--config",
        default="driftwatch.toml",
        metavar="FILE",
        help="Path to the driftwatch TOML config file (default: driftwatch.toml).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check", help="Run a single drift check and exit.")
    sub.add_parser("daemon", help="Run continuously on a schedule (default).")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    config_path = Path(args.config)
    try:
        cfg = load_config(config_path)
    except (ConfigError, FileNotFoundError) as exc:
        logger.error("Failed to load config: %s", exc)
        return 1

    command = args.command or "daemon"

    if command == "check":
        summary = run_once(cfg)
        logger.info(
            "Check complete — targets: %d, drifted: %d, errors: %d",
            len(summary.results),
            sum(1 for r in summary.results if r.drift_result.drifted),
            sum(1 for r in summary.results if r.drift_result.error),
        )
        return 1 if summary.has_drift else 0

    # daemon
    try:
        run_loop(cfg)
    except KeyboardInterrupt:
        logger.info("Interrupted — shutting down.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
