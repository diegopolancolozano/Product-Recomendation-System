# ============================================================
#  Script de inicio — Supermarket Analytics (desarrollo local)
#  Levanta el backend FastAPI y el frontend Next.js en paralelo.
# ============================================================

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV = Join-Path $ROOT ".venv\Scripts\Activate.ps1"
$FRONTEND = Join-Path $ROOT "frontend"

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Supermarket Analytics — Inicio local" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Verificar entorno virtual ──────────────────────────────────────────
if (-not (Test-Path $VENV)) {
    Write-Host "⚠️  No se encontró el entorno virtual .venv" -ForegroundColor Yellow
    Write-Host "   Crea uno con:  python -m venv .venv" -ForegroundColor Yellow
    Write-Host "   Luego instala: .venv\Scripts\Activate.ps1; pip install -r requirements.txt"
    exit 1
}

# ── 2. Verificar node_modules del frontend ────────────────────────────────
$nodeModules = Join-Path $FRONTEND "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "📦  Instalando dependencias de Node.js..." -ForegroundColor Yellow
    Push-Location $FRONTEND
    npm install
    Pop-Location
}

# ── 3. Lanzar FastAPI en una nueva ventana PowerShell ─────────────────────
Write-Host "🚀  Iniciando FastAPI en http://localhost:8000 ..." -ForegroundColor Green
$backendCmd = "cd '$ROOT'; .venv\Scripts\Activate.ps1; uvicorn api.main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Start-Sleep -Seconds 2   # Dar tiempo al backend para arrancar

# ── 4. Lanzar Next.js en una nueva ventana PowerShell ────────────────────
Write-Host "🎨  Iniciando Next.js en http://localhost:3000 ..." -ForegroundColor Green
$frontendCmd = "cd '$FRONTEND'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host ""
Write-Host "  ✅  Backend:   http://localhost:8000/docs"  -ForegroundColor Green
Write-Host "  ✅  Frontend:  http://localhost:3000"       -ForegroundColor Green
Write-Host ""
Write-Host "  Cierra las ventanas de PowerShell para detener los servicios."
Write-Host ""
