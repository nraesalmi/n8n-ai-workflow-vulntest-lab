#!/bin/sh

echo "========================================"
echo " n8n Workflow Import Script"
echo "========================================"

MARKER="/home/node/.n8n/.workflows-imported"

# Skip if already imported
if [ -f "$MARKER" ]; then
    echo "Workflows already imported. Skipping."
    exec /docker/docker-entrypoint.sh
fi

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
MAX_RETRIES=60
RETRY_COUNT=0
until node -e "require('net').connect(5432,'postgres',c=>{c.destroy();process.exit(0)}).on('error',()=>process.exit(1))" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "ERROR: PostgreSQL did not become ready."
        echo "Starting n8n anyway. Workflows will need manual import."
        exec /docker/docker-entrypoint.sh
    fi
    sleep 2
done
echo "PostgreSQL is ready."

# Import workflows
echo "Importing workflows from /tmp/workflows..."
IMPORT_OUTPUT=$(n8n import:workflow --input=/tmp/workflows 2>&1)
IMPORT_EXIT=$?

if [ $IMPORT_EXIT -eq 0 ]; then
    echo "Workflows imported successfully."
else
    echo "Note: Import returned non-zero exit code (may indicate existing workflows)."
    echo "Output: $IMPORT_OUTPUT"
fi

# Create marker
mkdir -p /home/node/.n8n
touch "$MARKER"

echo "Starting n8n..."
exec /docker/docker-entrypoint.sh
