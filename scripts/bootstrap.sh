#!/usr/bin/env sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

command -v uv >/dev/null 2>&1 || { echo "uv tidak ditemukan; lihat README.md" >&2; exit 1; }
command -v pnpm >/dev/null 2>&1 || { echo "pnpm tidak ditemukan; lihat README.md" >&2; exit 1; }

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Membuat .env dari .env.example (khusus lokal)."
fi

uv sync --project apps/api --extra dev
pnpm install --frozen-lockfile

if [ ! -f apps/android/gradlew ]; then
  echo "Gradle Wrapper Android tidak ditemukan. Pulihkan file wrapper dari repository." >&2
  exit 1
fi

chmod +x apps/android/gradlew

if ! command -v java >/dev/null 2>&1; then
  echo "Java tidak ditemukan. Gunakan JDK 17 atau JBR Android Studio untuk build Android." >&2
fi

uv run --project apps/api python scripts/check_structure.py
echo "Bootstrap KASTA selesai."
