#!/usr/bin/env python3
from __future__ import annotations

import sys

import config
from data_sources import collect_dashboard_data
from render_dashboard import render_dashboard


def main() -> int:
    try:
        data = collect_dashboard_data()
        output = render_dashboard(data, config.OUTPUT_FILE)
        print(f"Dashboard saved to {output}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
