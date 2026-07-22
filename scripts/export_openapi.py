from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
API_SOURCE = REPOSITORY_ROOT / "apps/api/src"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "packages/contracts/openapi/generated-kasta-api.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the FastAPI OpenAPI document.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    os.environ.setdefault("KASTA_ENVIRONMENT", "test")
    sys.path.insert(0, str(API_SOURCE))

    from kasta_api.main import app

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"OpenAPI diekspor ke {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
