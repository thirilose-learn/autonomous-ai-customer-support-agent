import os
import pytest
from app.database.schema_validator import validate_schema, EXPECTED_TABLES

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "supabase", "migrations", "20260907203000_initial_schema.sql"
)


def test_migration_file_exists_and_contains_definitions():
    """Verify that the SQL migration file exists and declares all required structures."""
    assert os.path.exists(MIGRATION_PATH), f"Migration file not found at {MIGRATION_PATH}"
    with open(MIGRATION_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify vector extension declaration
    assert "CREATE EXTENSION IF NOT EXISTS vector;" in content

    # Verify all 8 table definitions
    for table_name in EXPECTED_TABLES.keys():
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in content

    # Verify composite primary keys
    assert "PRIMARY KEY (order_id, order_item_id)" in content
    assert "PRIMARY KEY (order_id, payment_sequential)" in content

    # Verify products table has both Portuguese and English category columns
    assert "product_category_name VARCHAR(100) REFERENCES product_category_name_translation" in content
    assert "product_category_name_english VARCHAR(100)" in content

    # Verify key indexes are defined
    assert "CREATE INDEX IF NOT EXISTS idx_customers_unique_id" in content
    assert "CREATE INDEX IF NOT EXISTS idx_orders_customer_id" in content
    assert "CREATE INDEX IF NOT EXISTS idx_orders_customer_status_date" in content
    assert "CREATE INDEX IF NOT EXISTS idx_products_category_english" in content


@pytest.mark.skipif(
    not os.path.exists("backend/.env"),
    reason="backend/.env required for live Supabase schema test",
)
def test_supabase_tables_and_columns_exist():
    """Verify all 8 tables and their expected columns exist in Supabase PostgREST schema cache."""
    report = validate_schema(require_empty=False)
    if report.get("missing_tables") == list(EXPECTED_TABLES.keys()):
        pytest.skip("Database schema has not yet been applied to the remote Supabase project.")
    
    assert report["success"] is True, f"Schema validation failed: {report}"
    assert len(report["missing_tables"]) == 0, f"Missing tables: {report['missing_tables']}"
    assert len(report["column_mismatches"]) == 0, f"Column mismatches: {report['column_mismatches']}"


EXPECTED_ROW_COUNTS = {
    "product_category_name_translation": 73,
    "customers": 99441,
    "products": 32951,
    "orders": 99441,
    "order_items": 112650,
    "order_payments": 103886,
    "customer_support_intents": 26872,
    "customer_demo_accounts": 25,
}


@pytest.mark.skipif(
    not os.path.exists("backend/.env"),
    reason="backend/.env required for live Supabase schema test",
)
def test_supabase_tables_ingested_row_counts():
    """Verify all tables match expected Level 2 processed source row counts."""
    report = validate_schema(require_empty=False)
    assert report["success"] is True, f"Schema validation failed: {report}"

    for table_name, expected_count in EXPECTED_ROW_COUNTS.items():
        actual_count = report.get("table_counts", {}).get(table_name)
        assert (
            actual_count == expected_count
        ), f"Table '{table_name}' count mismatch: expected {expected_count:,}, found {actual_count:,}"

