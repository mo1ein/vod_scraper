#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for database and Redis to be ready..."

sleep 10

while [ "${SCRAPER_ENABLED:-true}" = "true" ]; do
  echo "Starting scrapers at $(date)"
  if python run_scrapers.py; then
    echo "Scrapers completed successfully at $(date)"
  else
    echo "Scrapers failed at $(date). Retrying after interval..."
  fi

  INTERVAL=${SCRAPER_INTERVAL:-3600}
  echo "Waiting for next run in ${INTERVAL} seconds..."
  sleep "${INTERVAL}"
done

echo "Scraper service stopped"
