"""Production entry point: `gunicorn wsgi:app`.

Deployments default to public mode (stricter rate limits, no local-only UI); set
READMEFORGE_MODE=local to opt out.
"""

import os

from readme_forge.web.app import create_app

app = create_app({"MODE": os.environ.get("READMEFORGE_MODE", "public")})
