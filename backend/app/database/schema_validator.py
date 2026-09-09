"""
Schema Validator for Supabase PostgreSQL Database.
Validates the presence of required tables, columns, and data counts via Supabase PostgREST API.

Note on Validation Scope (in strict accordance with project guidelines):
- Table accessibility, column names, and zero-row states are actively verified via PostgREST API.
- PostgreSQL-level physical indexes, foreign key enforcement internals, and pgvector extension
  are defined in the DDL migration (supabase/migrations/20260907203000_initial_schema.sql)
  and are NOT claimed as verified via PostgREST since PostgREST OpenAPI does not expose pg_catalog.
"""

import os
from typing import Dict, List, Any
import httpx
from dotenv import load_dotenv

# Expected schema specifications
EXPECTED_TABLES = {
    "product_category_name_translation": [
        "product_category_name",
        "product_category_name_english",
    ],
    "customers": [
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
    ],
    "products": [
        "product_id",
        "product_category_name",
        "product_category_name_english",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ],
    "orders": [
        "order_id",
        "customer_id",
        "customer_unique_id",
        "order_status",
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": [
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value",
    ],
    "order_payments": [
        "order_id",
        "payment_sequential",
        "payment_type",
        "payment_installments",
        "payment_value",
    ],
    "customer_support_intents": [
        "id",
        "flags",
        "instruction",
        "category",
        "intent",
        "response",
    ],
    "customer_demo_accounts": [
        "demo_customer_id",
        "customer_unique_id",
        "display_name",
        "demo_email",
        "total_orders",
        "primary_scenario",
        "sample_order_id",
        "customer_city",
        "customer_state",
    ],
}


def get_client_credentials():
    load_dotenv("backend/.env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in backend/.env")
    return url.rstrip("/"), key


def validate_schema(require_empty: bool = True) -> Dict[str, Any]:
    """
    Validates table existence, column presence, and row counts.
    If require_empty is True (Level 3C), asserts row count == 0.
    """
    url, key = get_client_credentials()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }

    # 1. Fetch OpenAPI specification from PostgREST root
    with httpx.Client(timeout=15.0) as client:
        root_resp = client.get(f"{url}/rest/v1/", headers=headers)
        if root_resp.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to fetch OpenAPI root: HTTP {root_resp.status_code}",
                "details": root_resp.text,
            }

        openapi_doc = root_resp.json()
        definitions = openapi_doc.get("definitions", {})

        results = {
            "success": True,
            "validation_mode": "PostgREST OpenAPI & REST Head Counts",
            "verified_tables": {},
            "missing_tables": [],
            "column_mismatches": {},
            "table_counts": {},
            "violations": [],
        }

        for table_name, expected_cols in EXPECTED_TABLES.items():
            if table_name not in definitions:
                results["missing_tables"].append(table_name)
                results["success"] = False
                continue

            # Check columns
            table_def = definitions[table_name]
            actual_cols = list(table_def.get("properties", {}).keys())
            missing_cols = [c for c in expected_cols if c not in actual_cols]
            if missing_cols:
                results["column_mismatches"][table_name] = missing_cols
                results["success"] = False

            results["verified_tables"][table_name] = {
                "columns_found": len(actual_cols),
                "expected_columns_verified": len(expected_cols),
            }

            # 2. Check row counts via HEAD request with Prefer: count=exact
            count_headers = {**headers, "Prefer": "count=exact"}
            head_resp = client.head(f"{url}/rest/v1/{table_name}", headers=count_headers)
            
            content_range = head_resp.headers.get("content-range", "")
            # content-range format: "0-0/0" or "*/0" or "0-9/10"
            count = None
            if "/" in content_range:
                try:
                    count = int(content_range.split("/")[1])
                except (ValueError, IndexError):
                    count = None

            results["table_counts"][table_name] = count

            if require_empty and count is not None and count > 0:
                results["violations"].append(
                    f"Table '{table_name}' contains {count} rows; expected 0 in Level 3C schema-only mode."
                )
                results["success"] = False

        return results


if __name__ == "__main__":
    import sys
    print("Running Supabase Schema Validator...")
    report = validate_schema(require_empty=True)
    print(f"Validation Result: {'SUCCESS' if report['success'] else 'FAILED'}")
    print(f"Missing Tables: {report.get('missing_tables', [])}")
    print(f"Column Mismatches: {report.get('column_mismatches', {})}")
    print(f"Table Counts: {report.get('table_counts', {})}")
    if report.get("violations"):
        print(f"Violations: {report['violations']}")
    sys.exit(0 if report["success"] else 1)
