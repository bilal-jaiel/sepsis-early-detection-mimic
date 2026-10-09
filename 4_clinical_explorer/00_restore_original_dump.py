from pathlib import Path
import subprocess
import time

BASE_DIR = Path(__file__).resolve().parent

# ============================================================
# CONFIG
# ============================================================

PG_BIN = r"C:\Program Files\PostgreSQL\18\bin"

DB_NAME = "mimic_iv_clinical_hosp"
DB_USER = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"

DUMP_FILE = BASE_DIR / "mimic_iv_final.sql"
DROP_EXISTING_DATABASE = False


# ============================================================
# HELPERS
# ============================================================

def pg_tool(name):
    path = Path(PG_BIN) / f"{name}.exe"
    if not path.exists():
        raise FileNotFoundError(f"Cannot find {name}:\n{path}")
    return str(path)


def run_command(cmd, title):
    print()
    print(f"▶ {title}")
    start = time.perf_counter()

    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise RuntimeError(f"{title} failed with exit code {result.returncode}")

    elapsed = time.perf_counter() - start
    print(f"Done in {elapsed:.1f}s")


def database_exists(psql):
    cmd = [
        psql,
        "-h", DB_HOST,
        "-p", DB_PORT,
        "-U", DB_USER,
        "-d", "postgres",
        "-tAc",
        f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}';",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    return result.stdout.strip() == "1"


# ============================================================
# MAIN
# ============================================================

def main():
    psql = pg_tool("psql")
    createdb = pg_tool("createdb")
    dropdb = pg_tool("dropdb")

    if not DUMP_FILE.exists():
        raise FileNotFoundError(f"Cannot find dump file:\n{DUMP_FILE}")

    print("PostgreSQL restore script")
    print(f"Database: {DB_NAME}")
    print(f"Dump file: {DUMP_FILE}")

    exists = database_exists(psql)

    if exists and DROP_EXISTING_DATABASE:
        run_command(
            [
                dropdb,
                "-h", DB_HOST,
                "-p", DB_PORT,
                "-U", DB_USER,
                DB_NAME,
            ],
            f"Dropping existing database {DB_NAME}",
        )
        exists = False

    if not exists:
        run_command(
            [
                createdb,
                "-h", DB_HOST,
                "-p", DB_PORT,
                "-U", DB_USER,
                DB_NAME,
            ],
            f"Creating database {DB_NAME}",
        )
    else:
        print()
        print(f"✓ Database {DB_NAME} already exists")
        print("  Restore will be executed into the existing database.")

    run_command(
        [
            psql,
            "-h", DB_HOST,
            "-p", DB_PORT,
            "-U", DB_USER,
            "-d", DB_NAME,
            "-f", str(DUMP_FILE),
        ],
        "Restoring original SQL dump",
    )

    print()
    print("Restore completed.")
    print()
    print("Next step:")
    print("python run_omop_explorer.py")


if __name__ == "__main__":
    main()