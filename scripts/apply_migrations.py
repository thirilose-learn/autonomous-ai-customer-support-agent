"""
Applies all SQL schema migrations from supabase/migrations/ in sequential order to Supabase PostgreSQL.
"""

import os
import sys
import glob
import psycopg2
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRATIONS_DIR = os.path.join(BASE_DIR, "supabase", "migrations")


def apply_migrations():
    load_dotenv(os.path.join(BASE_DIR, "backend", ".env"))
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set in backend/.env or environment.")
        sys.exit(1)

    migration_files = sorted(glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql")))
    if not migration_files:
        print(f"No SQL migration files found in {MIGRATIONS_DIR}")
        sys.exit(1)

    print(f"Found {len(migration_files)} migration files in {MIGRATIONS_DIR}:")
    for mf in migration_files:
        print(f"  - {os.path.basename(mf)}")

    print("\nConnecting to PostgreSQL...")
    conn = psycopg2.connect(db_url, connect_timeout=15)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        for mf in migration_files:
            filename = os.path.basename(mf)
            print(f"\nApplying migration: {filename}...")
            with open(mf, "r", encoding="utf-8") as f:
                sql = f.read()
            cur.execute(sql)
            print(f"✓ Successfully applied {filename}")

        # Notify PostgREST to reload schema cache
        cur.execute("NOTIFY pgrst, 'reload schema';")
        print("\nNotified PostgREST schema cache reload.")

        # Inspect database catalog directly for validation
        print("\n--- Database Catalog Summary ---")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = [r[0] for r in cur.fetchall()]
        print(f"Public tables ({len(tables)}): {', '.join(tables)}")

    except Exception as e:
        print(f"ERROR executing migrations: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()
        print("\nDatabase connection closed. Migration process complete.")


if __name__ == "__main__":
    apply_migrations()
