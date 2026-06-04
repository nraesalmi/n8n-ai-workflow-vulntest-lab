# ============================================
# n8n Research Lab Setup (PowerShell)
# ============================================
# Run this AFTER starting Docker:
#   docker compose up -d
#   .\scripts\setup.ps1
# ============================================

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

# Load .env
Get-Content "$ProjectDir\.env" | ForEach-Object {
    if ($_ -match "^\s*([^#=]+)=(.*)$") {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        Set-Item -Path "env:$name" -Value $value
    }
}

Write-Host "========================================"
Write-Host " n8n Lab Setup: Credentials & Workflows"
Write-Host "========================================"

# ── Step 1: Wait for n8n ───────────────────
Write-Host ""
Write-Host "1. Waiting for n8n..."
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:5678/healthz" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 2
}
if (-not $ready) {
    Write-Host "   ERROR: n8n did not become ready. Check: docker compose logs n8n"
    exit 1
}
Write-Host "   n8n is ready."

# ── Step 2: Check owner user ─────────────────
Write-Host ""
Write-Host "2. Checking owner user..."
$userId = docker exec n8n-postgres psql -U n8n -d n8n -t -A -c "SELECT id FROM public.user LIMIT 1;" 2>&1
if (-not $userId -or $userId.Trim() -eq "") {
    Write-Host "   No user found. Open http://localhost:5678 in your browser,"
    Write-Host "   complete the setup wizard to create your account, then re-run this script."
    exit 1
}
$userId = $userId.Trim()
Write-Host "   Owner user: $userId"

# ── Step 3: Generate & import credentials ──
Write-Host ""
Write-Host "3. Importing credentials..."
docker exec n8n-app sh -c "mkdir -p /tmp/credentials"

# Generate UUIDs for credential IDs
$tgId = (docker exec n8n-app node -e "console.log(require('crypto').randomUUID())" 2>&1).Trim()
$pgId = (docker exec n8n-app node -e "console.log(require('crypto').randomUUID())" 2>&1).Trim()
$ollamaId = (docker exec n8n-app node -e "console.log(require('crypto').randomUUID())" 2>&1).Trim()

# Write credential JSONs with IDs
$tgJson = @{
    id = $tgId
    name = "Telegram Bot"
    type = "telegramApi"
    data = @{
        accessToken = $env:TELEGRAM_BOT_TOKEN
    }
}
$tgJson | ConvertTo-Json | docker exec -i n8n-app sh -c "cat > /tmp/credentials/telegram-bot.json"

$pgJson = @{
    id = $pgId
    name = "PostgreSQL Database"
    type = "postgres"
    data = @{
        host = "postgres"
        database = $env:POSTGRES_DB
        user = $env:POSTGRES_USER
        password = $env:POSTGRES_PASSWORD
        port = 5432
        maxConnections = 10
        allowUnauthorizedCerts = $true
        ssl = "disable"
    }
}
$pgJson | ConvertTo-Json | docker exec -i n8n-app sh -c "cat > /tmp/credentials/postgres-database.json"

$ollamaJson = @{
    id = $ollamaId
    name = "Ollama API"
    type = "ollamaApi"
    data = @{
        baseUrl = "http://ollama:11434"
    }
}
$ollamaJson | ConvertTo-Json | docker exec -i n8n-app sh -c "cat > /tmp/credentials/ollama-api.json"

# Import them
docker exec n8n-app n8n import:credentials --separate --input=/tmp/credentials --userId $userId
Write-Host "   Credentials imported."

# ── Step 4: Import workflows ───────────────
Write-Host ""
Write-Host "4. Importing workflows..."
docker exec n8n-app n8n import:workflow --separate --input=/tmp/workflows --userId $userId
Write-Host "   Workflows imported."

Write-Host ""
Write-Host "========================================"
Write-Host " Setup complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Open http://localhost:5678"
Write-Host "  2. Open each workflow and click Active"
Write-Host "  3. If credentials need re-linking, edit each"
Write-Host "     workflow and re-select them from the dropdown"
Write-Host ""
