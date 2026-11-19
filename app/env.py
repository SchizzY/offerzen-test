"""Load settings from a .env file in the project root, if there is one.

Real environment variables win over .env, so `FOO=1 poetry run ...` still works.
Create your .env with ./scripts/init-env.sh (it copies .env.example).
"""

from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

load_dotenv(ENV_FILE, override=False)
