[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Require-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Command '$Name' tidak ditemukan. Lihat prasyarat di README.md."
    }
}

Push-Location $RepoRoot
try {
    Require-Command "uv"
    Require-Command "pnpm"

    if (-not (Test-Path -LiteralPath ".env")) {
        Copy-Item -LiteralPath ".env.example" -Destination ".env"
        Write-Host "Membuat .env dari .env.example (khusus lokal)."
    }

    & uv sync --project apps/api --extra dev
    if ($LASTEXITCODE -ne 0) { throw "uv sync gagal." }

    & pnpm install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw "pnpm install gagal." }

    if (-not (Test-Path -LiteralPath "apps/android/gradlew.bat")) {
        throw "Gradle Wrapper Android tidak ditemukan. Pulihkan file wrapper dari repository."
    }

    if (-not (Get-Command "java" -ErrorAction SilentlyContinue)) {
        Write-Warning "Java tidak ditemukan. Gunakan JDK 17 atau JBR Android Studio untuk build Android."
    }

    & uv run --project apps/api python scripts/check_structure.py
    if ($LASTEXITCODE -ne 0) { throw "Validasi struktur gagal." }

    Write-Host "Bootstrap KASTA selesai."
}
finally {
    Pop-Location
}
