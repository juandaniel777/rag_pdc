#!/usr/bin/env bash
set -euo pipefail

# Minimal build script — installs dependencies and runs Django collectstatic/migrate
# Prefer packages.txt (exact pinned versions); fall back to requirements.txt.

echo "==> Installing Python packages"
if [ -f packages.txt ]; then
  python -m pip install -r packages.txt

else
  echo "No packages.txt or requirements.txt found — skipping package install"
fi

echo "==> Collecting static files"
python manage.py collectstatic --noinput

echo "==> Applying migrations"
python manage.py migrate --noinput

echo "Build finished."