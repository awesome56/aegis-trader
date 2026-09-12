"""Export the OpenAPI specification to `api/docs/openapi.yaml`.

Run from the backend directory:

    python -m scripts.export_openapi

The generated file is committed so the API contract is reviewable without
starting the server. The running app also serves it at
`/api/docs/openapi.yaml` and renders it at `/api/docs`.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from app.main import app


def build_spec() -> dict:
    return app.openapi()


def main() -> None:
    output = Path(__file__).resolve().parents[2] / "api" / "docs" / "openapi.yaml"
    output.parent.mkdir(parents=True, exist_ok=True)
    spec = build_spec()
    output.write_text(
        yaml.safe_dump(spec, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    paths = len(spec.get("paths", {}))
    print(f"wrote {output} ({paths} paths, version {spec['info']['version']})")


if __name__ == "__main__":
    main()
