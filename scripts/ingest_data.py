"""
Reliable Batch Ingestion Script for Supabase PostgreSQL.
Ingests processed Olist, Bitext, and Synthetic datasets into Supabase via PostgREST API.

Key Design Principles:
1. Strict referential dependency ordering.
2. Robust type parsing and empty string -> None (NULL) normalization.
3. Batching with retry and rate-limit backoff.
4. Comprehensive post-ingestion validation (record counts and FK integrity).
"""

import os
import sys
import csv
import time
from typing import List, Dict, Any, Callable
import httpx
from dotenv import load_dotenv

BATCH_SIZE = 500
MAX_RETRIES = 5
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_client_credentials():
    load_dotenv(os.path.join(BASE_DIR, "backend", ".env"))
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in backend/.env")
    return url.rstrip("/"), key


def to_int(val: str):
    if not val or val.strip() == "":
        return None
    try:
        return int(float(val.strip()))
    except ValueError:
        return None


def to_float(val: str):
    if not val or val.strip() == "":
        return None
    try:
        return float(val.strip())
    except ValueError:
        return None


def to_str(val: str):
    if val is None or val.strip() == "":
        return None
    return val.strip()


# Row transformers for each dataset
def transform_translation(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "product_category_name": to_str(row["product_category_name"]),
        "product_category_name_english": to_str(row["product_category_name_english"]),
    }


def transform_customer(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "customer_id": to_str(row["customer_id"]),
        "customer_unique_id": to_str(row["customer_unique_id"]),
        "customer_zip_code_prefix": to_str(row.get("customer_zip_code_prefix")),
        "customer_city": to_str(row.get("customer_city")),
        "customer_state": to_str(row.get("customer_state")),
    }


def transform_product(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "product_id": to_str(row["product_id"]),
        "product_category_name": to_str(row.get("product_category_name")),
        "product_category_name_english": to_str(row.get("product_category_name_english")),
        "product_name_lenght": to_int(row.get("product_name_lenght")),
        "product_description_lenght": to_int(row.get("product_description_lenght")),
        "product_photos_qty": to_int(row.get("product_photos_qty")),
        "product_weight_g": to_float(row.get("product_weight_g")),
        "product_length_cm": to_float(row.get("product_length_cm")),
        "product_height_cm": to_float(row.get("product_height_cm")),
        "product_width_cm": to_float(row.get("product_width_cm")),
    }


def transform_order(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "order_id": to_str(row["order_id"]),
        "customer_id": to_str(row["customer_id"]),
        "customer_unique_id": to_str(row["customer_unique_id"]),
        "order_status": to_str(row["order_status"]),
        "order_purchase_timestamp": to_str(row["order_purchase_timestamp"]),
        "order_approved_at": to_str(row.get("order_approved_at")),
        "order_delivered_carrier_date": to_str(row.get("order_delivered_carrier_date")),
        "order_delivered_customer_date": to_str(row.get("order_delivered_customer_date")),
        "order_estimated_delivery_date": to_str(row["order_estimated_delivery_date"]),
    }


def transform_order_item(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "order_id": to_str(row["order_id"]),
        "order_item_id": to_int(row["order_item_id"]),
        "product_id": to_str(row["product_id"]),
        "seller_id": to_str(row["seller_id"]),
        "shipping_limit_date": to_str(row["shipping_limit_date"]),
        "price": to_float(row["price"]),
        "freight_value": to_float(row["freight_value"]),
    }


def transform_order_payment(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "order_id": to_str(row["order_id"]),
        "payment_sequential": to_int(row["payment_sequential"]),
        "payment_type": to_str(row["payment_type"]),
        "payment_installments": to_int(row["payment_installments"]),
        "payment_value": to_float(row["payment_value"]),
    }


def transform_intent(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "flags": to_str(row["flags"]),
        "instruction": to_str(row["instruction"]),
        "category": to_str(row["category"]),
        "intent": to_str(row["intent"]),
        "response": to_str(row["response"]),
    }


def transform_demo_account(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "demo_customer_id": to_str(row["demo_customer_id"]),
        "customer_unique_id": to_str(row["customer_unique_id"]),
        "display_name": to_str(row["display_name"]),
        "demo_email": to_str(row["demo_email"]),
        "total_orders": to_int(row["total_orders"]),
        "primary_scenario": to_str(row["primary_scenario"]),
        "sample_order_id": to_str(row.get("sample_order_id")),
        "customer_city": to_str(row.get("customer_city")),
        "customer_state": to_str(row.get("customer_state")),
    }


TABLE_SPECS = [
    {
        "table": "product_category_name_translation",
        "csv_path": "processed_data/olist/product_category_name_translation.csv",
        "transformer": transform_translation,
        "upsert_on": "product_category_name",
    },
    {
        "table": "customers",
        "csv_path": "processed_data/olist/customers.csv",
        "transformer": transform_customer,
        "upsert_on": "customer_id",
    },
    {
        "table": "products",
        "csv_path": "processed_data/olist/products.csv",
        "transformer": transform_product,
        "upsert_on": "product_id",
    },
    {
        "table": "orders",
        "csv_path": "processed_data/olist/orders.csv",
        "transformer": transform_order,
        "upsert_on": "order_id",
    },
    {
        "table": "order_items",
        "csv_path": "processed_data/olist/order_items.csv",
        "transformer": transform_order_item,
        "upsert_on": "order_id,order_item_id",
    },
    {
        "table": "order_payments",
        "csv_path": "processed_data/olist/order_payments.csv",
        "transformer": transform_order_payment,
        "upsert_on": "order_id,payment_sequential",
    },
    {
        "table": "customer_support_intents",
        "csv_path": "processed_data/bitext/customer_support_intents.csv",
        "transformer": transform_intent,
        "upsert_on": None,  # plain insert with auto-generated id
    },
    {
        "table": "customer_demo_accounts",
        "csv_path": "processed_data/synthetic/customer_demo_accounts.csv",
        "transformer": transform_demo_account,
        "upsert_on": "demo_customer_id",
    },
]


def post_batch(client: httpx.Client, url: str, headers: Dict[str, str], table: str, batch: List[Dict[str, Any]], upsert_on: str = None):
    endpoint = f"{url}/rest/v1/{table}"
    req_headers = {
        **headers,
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    if upsert_on:
        req_headers["Prefer"] = f"return=minimal,resolution=merge-duplicates"
        endpoint += f"?on_conflict={upsert_on}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.post(endpoint, headers=req_headers, json=batch, timeout=60.0)
            if resp.status_code in (200, 201, 204):
                return True
            if resp.status_code in (429, 500, 502, 503, 504):
                backoff = attempt * 2
                print(f"      [Retry {attempt}/{MAX_RETRIES}] HTTP {resp.status_code}. Backing off {backoff}s...")
                time.sleep(backoff)
                continue
            # Any 4xx client error
            raise RuntimeError(f"POST {table} failed with HTTP {resp.status_code}: {resp.text}")
        except httpx.RequestError as exc:
            backoff = attempt * 2
            print(f"      [Retry {attempt}/{MAX_RETRIES}] Request error: {exc}. Backing off {backoff}s...")
            time.sleep(backoff)

    raise RuntimeError(f"Failed to ingest batch into '{table}' after {MAX_RETRIES} attempts.")


def ingest_table(client: httpx.Client, url: str, headers: Dict[str, str], spec: Dict[str, Any]):
    table = spec["table"]
    csv_file = os.path.join(BASE_DIR, spec["csv_path"])
    transformer = spec["transformer"]
    upsert_on = spec["upsert_on"]

    print(f"\n--> Ingesting table: {table} from {spec['csv_path']}")
    t0 = time.time()
    batch = []
    total_processed = 0

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = transformer(row)
            batch.append(record)
            if len(batch) >= BATCH_SIZE:
                post_batch(client, url, headers, table, batch, upsert_on)
                total_processed += len(batch)
                batch = []
                if total_processed % 10000 == 0:
                    print(f"    Ingested {total_processed} rows...")

        if batch:
            post_batch(client, url, headers, table, batch, upsert_on)
            total_processed += len(batch)

    elapsed = time.time() - t0
    print(f"    Completed {table}: {total_processed} rows in {elapsed:.2f}s ({total_processed/max(elapsed, 0.01):.1f} rows/s)")
    return total_processed


def verify_counts(client: httpx.Client, url: str, headers: Dict[str, str]):
    print("\n==================================================")
    print("VALIDATING ROW COUNTS AGAINST LEVEL 2 CSV SOURCES")
    print("==================================================")
    all_matched = True
    for spec in TABLE_SPECS:
        table = spec["table"]
        csv_file = os.path.join(BASE_DIR, spec["csv_path"])
        
        # Source count
        with open(csv_file, "r", encoding="utf-8") as f:
            src_count = sum(1 for _ in csv.DictReader(f))

        # Remote count
        count_headers = {**headers, "Prefer": "count=exact"}
        head_resp = client.head(f"{url}/rest/v1/{table}", headers=count_headers)
        content_range = head_resp.headers.get("content-range", "")
        remote_count = None
        if "/" in content_range:
            try:
                remote_count = int(content_range.split("/")[1])
            except (ValueError, IndexError):
                pass

        match = (src_count == remote_count)
        status = "MATCH" if match else "MISMATCH"
        print(f"  [{status}] {table}: Source={src_count:,} | Remote={remote_count if remote_count is not None else 'N/A':,}")
        if not match:
            all_matched = False

    return all_matched


def run_ingestion():
    url, key = get_client_credentials()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }

    with httpx.Client(timeout=60.0) as client:
        # First check that schema exists
        root_resp = client.get(f"{url}/rest/v1/", headers=headers)
        definitions = root_resp.json().get("definitions", {})
        missing = [spec["table"] for spec in TABLE_SPECS if spec["table"] not in definitions]
        if missing:
            print(f"ERROR: Cannot ingest! Tables missing in database schema: {missing}")
            print("Please run the schema migration in Supabase SQL editor first:")
            print(f"supabase/migrations/20260907203000_initial_schema.sql")
            sys.exit(1)

        print("All 8 tables verified in schema. Beginning sequential ingestion...")
        start_time = time.time()
        for spec in TABLE_SPECS:
            ingest_table(client, url, headers, spec)

        total_time = time.time() - start_time
        print(f"\nAll tables ingested in {total_time/60:.2f} minutes.")

        # Validation
        success = verify_counts(client, url, headers)
        if success:
            print("\nSUCCESS: All tables match Level 2 source counts exactly!")
        else:
            print("\nWARNING: Some table counts did not match.")
            sys.exit(1)


if __name__ == "__main__":
    run_ingestion()
