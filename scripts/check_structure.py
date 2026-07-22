from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = (
    ".env.example",
    ".gitignore",
    "README.md",
    "apps/api/pyproject.toml",
    "apps/api/src/kasta_api/main.py",
    "apps/web/package.json",
    "apps/web/src/routes/+page.svelte",
    "apps/android/app/build.gradle.kts",
    "apps/android/app/src/main/AndroidManifest.xml",
    "apps/android/gradle/wrapper/gradle-wrapper.jar",
    "apps/android/gradle/wrapper/gradle-wrapper.properties",
    "apps/android/gradlew",
    "apps/android/gradlew.bat",
    "packages/contracts/openapi/kasta-api.yaml",
    "packages/shared/config/environments.json",
    "infrastructure/docker/compose.yaml",
    "infrastructure/caddy/Caddyfile",
    "documentation/repository-structure.md",
    "documentation/database/kasta-postgresql-v0.1.sql",
    "tests/README.md",
    "documentation/testing/test-plan.md",
    "documentation/testing/test-cases.md",
    "documentation/testing/actual-result-template.md",
    "scripts/check_test_catalog.py",
)

REQUIRED_MODULES = (
    "auth",
    "users",
    "businesses",
    "accounting",
    "transactions",
    "receipts",
    "ocr",
    "inventory",
    "receivables",
    "payables",
    "mentors",
    "reports",
    "notifications",
    "sync",
    "audit",
)


def main() -> int:
    missing = [path for path in REQUIRED_PATHS if not (REPOSITORY_ROOT / path).exists()]
    module_root = REPOSITORY_ROOT / "apps/api/src/kasta_api/modules"
    missing.extend(
        str(path.relative_to(REPOSITORY_ROOT))
        for name in REQUIRED_MODULES
        if not (path := module_root / name / "__init__.py").exists()
    )

    android_build = (REPOSITORY_ROOT / "apps/android/app/build.gradle.kts").read_text(
        encoding="utf-8"
    )
    if 'applicationId = "id.kasta.app"' not in android_build:
        missing.append("Android applicationId id.kasta.app")

    if missing:
        print("Struktur KASTA belum lengkap:")
        for path in missing:
            print(f"- {path}")
        return 1

    print(f"Struktur KASTA valid: {len(REQUIRED_PATHS)} path dan {len(REQUIRED_MODULES)} modul.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
