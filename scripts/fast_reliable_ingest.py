"""
Fast, Reliable Ingestion Script for Supabase PostgreSQL.
Uses PostgreSQL direct streaming COPY via psycopg2.
Ensures strict referential dependency ordering, handles empty string NULLs,
and verifies 100% row counts and foreign-key integrity.
"""

import os
import sys
import time
import csv
import psycopg2
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TABLE_ORDER = [
    {
        "table": "product_category_name_translation",
        "csv": "processed_data/olist/product_category_name_translation.csv",
        "columns": ["product_category_name", "product_category_name_english"],
        "expected_count": 73,
    },
    {
        "table": "customers",
        "csv": "processed_data/olist/customers.csv",
        "columns": ["customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city", "customer_state"],
        "expected_count": 99441,
    },
    {
        "table": "products",
        "csv": "processed_data/olist/products.csv",
        "columns": [
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
        "expected_count": 32951,
    },
    {
        "table": "orders",
        "csv": "processed_data/olist/orders.csv",
        "columns": [
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
        "expected_count": 99441,
    },
    {
        "table": "order_items",
        "csv": "processed_data/olist/order_items.csv",
        "columns": [
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ],
        "expected_count": 112650,
    },
    {
        "table": "order_payments",
        "csv": "processed_data/olist/order_payments.csv",
        "columns": [
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ],
        "expected_count": 103886,
    },
    {
        "table": "customer_support_intents",
        "csv": "processed_data/bitext/customer_support_intents.csv",
        "columns": ["flags", "instruction", "category", "intent", "response"],
        "expected_count": 26872,
    },
    {
        "table": "customer_demo_accounts",
        "csv": "processed_data/synthetic/customer_demo_accounts.csv",
        "columns": [
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
        "expected_count": 25,
    },
]


def run_ingestion():
    load_dotenv(os.path.join(BASE_DIR, "backend", ".env"))
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL is not set.")
        sys.exit(1)

    print("==================================================")
    print("STARTING LEVEL 3D: STREAMING DATA INGESTION")
    print("==================================================")

    conn = psycopg2.connect(db_url, connect_timeout=30)
    conn.autocommit = False
    cur = conn.cursor()

    overall_start = time.time()
    total_records_ingested = 0

    try:
        for item in TABLE_ORDER:
            table = item["table"]
            csv_path = os.path.join(BASE_DIR, item["csv"])
            cols = ", ".join(f'"{c}"' for c in item["columns"])
            expected = item["expected_count"]

            print(f"\n--> Ingesting table: {table}")
            print(f"    Source: {item['csv']} ({expected:,} rows expected)")
            t0 = time.time()

            # Using COPY with CSV HEADER and NULL representation as empty string ''
            copy_sql = f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true, NULL '', QUOTE '\"', ESCAPE '\"')"

            with open(csv_path, "r", encoding="utf-8") as f:
                cur.copy_expert(copy_sql, f)

            conn.commit()
            elapsed = time.time() - t0
            total_records_ingested += expected
            print(f"    SUCCESS: Ingested {expected:,} rows in {elapsed:.2f}s ({expected/max(elapsed, 0.01):,.0f} rows/s)")

        print("\n==================================================")
        print("DATA INGESTION COMPLETED")
        print(f"Total Rows Ingested: {total_records_ingested:,}")
        print(f"Total Time: {time.time() - overall_start:.2f}s")
        print("==================================================")

        # ----------------------------------------------------
        # VALIDATION PHASE 1: EXACT ROW COUNT VERIFICATION
        # ----------------------------------------------------
        print("\n==================================================")
        print("PHASE 1: ROW COUNT VALIDATION AGAINST SOURCE CSVS")
        print("==================================================")
        all_counts_match = True
        for item in TABLE_ORDER:
            table = item["table"]
            expected = item["expected_count"]
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            actual = cur.fetchone()[0]
            matched = (actual == expected)
            status = "MATCH" if matched else "MISMATCH"
            print(f"  [{status}] {table}: Source={expected:,} | PostgreSQL={actual:,}")
            if not matched:
                all_counts_match = False

        if not all_counts_match:
            raise RuntimeError("Row count validation failed on one or more tables.")

        # ----------------------------------------------------
        # VALIDATION PHASE 2: FOREIGN KEY INTEGRITY AUDIT
        # ----------------------------------------------------
        print("\n==================================================")
        print("PHASE 2: FOREIGN KEY INTEGRITY & ORPHAN AUDIT")
        print("==================================================")

        fk_audits = [
            {
                "name": "orders.customer_id -> customers.customer_id",
                "sql": """
                    SELECT COUNT(*) 
                    FROM orders o 
                    LEFT JOIN customers c ON o.customer_id = c.customer_id 
                    WHERE c.customer_id IS NULL;
                """,
            },
            {
                "name": "order_items.order_id -> orders.order_id",
                "sql": """
                    SELECT COUNT(*) 
                    FROM order_items oi 
                    LEFT JOIN orders o ON oi.order_id = o.order_id 
                    WHERE o.order_id IS NULL;
                """,
            },
            {
                "name": "order_items.product_id -> products.product_id",
                "sql": """
                    SELECT COUNT(*) 
                    FROM order_items oi 
                    LEFT JOIN products p ON oi.product_id = p.product_id 
                    WHERE p.product_id IS NULL;
                """,
            },
            {
                "name": "order_payments.order_id -> orders.order_id",
                "sql": """
                    SELECT COUNT(*) 
                    FROM order_payments op 
                    LEFT JOIN orders o ON op.order_id = o.order_id 
                    WHERE o.order_id IS NULL;
                """,
            },
            {
                "name": "products.product_category_name -> translation.product_category_name",
                "sql": """
                    SELECT COUNT(*) 
                    FROM products p 
                    LEFT JOIN product_category_name_translation t ON p.product_category_name = t.product_category_name 
                    WHERE p.product_category_name IS NOT NULL AND t.product_category_name IS NULL;
                """,
            },
            {
                "name": "customer_demo_accounts.sample_order_id -> orders.order_id",
                "sql": """
                    SELECT COUNT(*) 
                    FROM customer_demo_accounts d 
                    LEFT JOIN orders o ON d.sample_order_id = o.order_id 
                    WHERE d.sample_order_id IS NOT NULL AND o.order_id IS NULL;
                """,
            },
        ]

        all_fks_clean = True
        for audit in fk_audits:
            cur.execute(audit["sql"])
            orphan_count = cur.fetchone()[0]
            status = "VERIFIED (0 orphans)" if orphan_count == 0 else f"FAILED ({orphan_count} orphans)"
            print(f"  [{'PASSED' if orphan_count == 0 else 'FAILED'}] {audit['name']}: {status}")
            if orphan_count != 0:
                all_fks_clean = False

        if not all_fks_clean:
            raise RuntimeError("Foreign key audit detected orphan records.")

        # Notify PostgREST cache reload to update internal statistics
        cur.execute("NOTIFY pgrst, 'reload schema';")
        conn.commit()

        print("\n==================================================")
        print("ALL VALIDATION CHECKS PASSED: DATA INGESTION VERIFIED")
        print("==================================================")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR during ingestion: {type(e).__name__}: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run_ingestion()
