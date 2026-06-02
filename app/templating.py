from fastapi.templating import Jinja2Templates
from pathlib import Path

VERSION = Path("/app/VERSION").read_text().strip() if Path("/app/VERSION").exists() else "dev"

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["version"] = VERSION
