#!/usr/bin/env bash

set -Eeuo pipefail

# Always run from the project root, regardless of where the script is called.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Ensure this script uses the project's dedicated dbt environment.
DBT_BIN="$PROJECT_ROOT/.dbt-venv/bin/dbt"

if [[ ! -x "$DBT_BIN" ]]; then
    echo "ERROR: dbt executable not found at $DBT_BIN"
    echo "Activate or repair the .dbt-venv environment first."
    exit 1
fi

echo "==> Checking dbt and database connection"
"$DBT_BIN" debug --target dev

echo "==> Loading development seed data"
"$DBT_BIN" seed --target dev

echo "==> Building staging and intermediate models"
"$DBT_BIN" build --target dev --select stg_orders int_orders

echo "==> Building the fact model and its associated tests"
"$DBT_BIN" build --target dev --select fct_orders

echo "==> Development dbt workflow completed successfully"
