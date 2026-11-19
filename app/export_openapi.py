"""Write the OpenAPI spec to openapi.json: poetry run python -m app.export_openapi"""

import json
from pathlib import Path

from app.main import app

OUTPUT = Path(__file__).resolve().parent.parent / "openapi.json"


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(app.openapi(), indent=2) + "\n")
    print(f"Wrote {OUTPUT}")
