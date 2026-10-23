"""Load local configuration before importing application modules."""
import os
from pathlib import Path
from dotenv import dotenv_values, load_dotenv

env_path = Path(__file__).resolve().parents[1] / '.env'
load_dotenv(env_path, override=False)

# An empty variable in the launching shell should not mask a configured .env value.
for name, value in dotenv_values(env_path).items():
    if value is not None and not os.getenv(name, '').strip():
        os.environ[name] = value
