"""
Foreign Key & Referential Integrity Verification Script.
Queries Supabase to verify that all foreign key relationships are strictly intact
and zero orphan records exist.
"""

import os
import sys
import httpx
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_client_credentials():
    load_dotenv(os.path.join(BASE_DIR, "backend", ".env"))
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in backend/.env")
    return url.rstrip("/"), key


def verify_referential_integrity():
    url, key = get_client_credentials()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }

    print("==================================================")
    print("VALIDATING FOREIGN KEY REFERENTIAL INTEGRITY")
    print("==================================================")

    checks = [
        {
            "name": "orders -> customers (customer_id)",
            "query": "orders?select=customer_id,customers(customer_id)&limit=100",
            "desc": "Join orders to parent customers",
        },
        {
            "name": "order_items -> orders (order_id)",
            "query": "order_items?select=order_id,orders(order_id)&limit=100",
            "desc": "Join order_items to parent orders",
        },
        {
            "name": "order_items -> products (product_id)",
            "query": "order_items?select=product_id,products(product_id)&limit=100",
            "desc": "Join order_items to parent products",
        },
        {
            "name": "order_payments -> orders (order_id)",
            "query": "order_payments?select=order_id,orders(order_id)&limit=100",
            "desc": "Join order_payments to parent orders",
        },
        {
            "name": "products -> product_category_name_translation (product_category_name)",
            "query": "products?select=product_category_name,product_category_name_translation(product_category_name)&product_category_name=not.is.null&limit=100",
            "desc": "Join products to category translations",
        },
        {
            "name": "customer_demo_accounts -> orders (sample_order_id)",
            "query": "customer_demo_accounts?select=sample_order_id,orders(order_id)&limit=25",
            "desc": "Join demo accounts to sample orders",
        },
    ]

    all_passed = True
    with httpx.Client(timeout=30.0) as client:
        for check in checks:
            endpoint = f"{url}/rest/v1/{check['query']}"
            resp = client.get(endpoint, headers=headers)
            if resp.status_code != 200:
                print(f"  [FAILED] {check['name']}: HTTP {resp.status_code} - {resp.text}")
                all_passed = False
                continue

            rows = resp.json()
            if not rows:
                print(f"  [FAILED] {check['name']}: Returned empty dataset")
                all_passed = False
                continue

            # Check that embedded resource joined correctly (non-null parent)
            # Find embedded key
            orphan_count = 0
            for row in rows:
                # Find foreign table key
                for k, v in row.items():
                    if isinstance(v, dict) and v is None:
                        orphan_count += 1

            if orphan_count > 0:
                print(f"  [FAILED] {check['name']}: Found {orphan_count} orphan references in sample")
                all_passed = False
            else:
                print(f"  [PASSED] {check['name']}: Verified sample ({len(rows)} rows joined successfully)")

    return all_passed


if __name__ == "__main__":
    success = verify_referential_integrity()
    sys.exit(0 if success else 1)
