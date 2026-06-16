#!/usr/bin/env bash
#
# Boot a local Odoo 18 Community instance with SA Fleet & Logistics installed.
# Installing the umbrella module pulls in all 16 platform modules.
#
# Open in your browser when ready:
#     http://localhost:8069
#
# Default login (set on first run):
#     Email:    admin
#     Password: admin
#
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed. Install Docker Desktop first: https://docs.docker.com/get-docker/"
  exit 1
fi

COMPOSE="docker compose"
if ! docker compose version >/dev/null 2>&1; then
  COMPOSE="docker-compose"
fi

case "${1:-up}" in
  up)
    echo "Starting Odoo 18 + Postgres..."
    $COMPOSE up -d
    echo
    echo "First boot installs the platform. Tail logs with:"
    echo "    $COMPOSE logs -f odoo"
    echo
    echo "When you see 'Modules loaded.' open: http://localhost:8069"
    echo "Login: admin / admin"
    ;;
  logs)
    $COMPOSE logs -f odoo
    ;;
  stop)
    $COMPOSE stop
    ;;
  restart)
    $COMPOSE restart odoo
    ;;
  update)
    # Apply XML/model changes without rebuilding the DB.
    $COMPOSE exec odoo odoo -c /etc/odoo/odoo.conf -d sa_demo -u sa_fleet_logistics --stop-after-init
    $COMPOSE restart odoo
    ;;
  test)
    # Run the included unit tests against a fresh DB.
    $COMPOSE exec odoo odoo -c /etc/odoo/odoo.conf -d sa_tests -i sa_fleet_logistics --test-enable --stop-after-init --log-level=test
    ;;
  reset)
    echo "WARNING: this deletes the database and uploaded files."
    read -r -p "Continue? (y/N) " ans
    [[ "$ans" == "y" || "$ans" == "Y" ]] || exit 0
    $COMPOSE down -v
    ;;
  tunnel)
    if ! command -v cloudflared >/dev/null 2>&1; then
      echo "cloudflared not installed. Install with: brew install cloudflared"
      exit 1
    fi
    echo "Exposing http://localhost:8069 via Cloudflare Tunnel..."
    echo "Share the *.trycloudflare.com URL it prints."
    cloudflared tunnel --url http://localhost:8069
    ;;
  *)
    echo "Usage: $0 {up|logs|stop|restart|update|test|reset|tunnel}"
    exit 1
    ;;
esac
