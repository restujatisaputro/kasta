"""Convenience entry point for the deterministic KASTA demo seed.

Run with ``uv run --project apps/api python scripts/seed_demo.py`` after the
database migrations have been applied.  The implementation lives in the API
package so it can also be imported by tests and application tooling.
"""

from __future__ import annotations

import asyncio

from kasta_api.seed_demo import run

if __name__ == "__main__":
    asyncio.run(run())
