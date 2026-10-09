"""Command-line entry point."""

from __future__ import annotations

import argparse
import asyncio

from .config import load_config
from .engine import LoadGenerator


def main() -> None:
    parser = argparse.ArgumentParser(prog="loadgen", description="HTTP load-generation engine")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config file")
    args = parser.parse_args()

    config = load_config(args.config)
    summary = asyncio.run(LoadGenerator(config).run())
    print(summary.render())


if __name__ == "__main__":
    main()
