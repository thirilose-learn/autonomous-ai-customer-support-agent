import os
import csv
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATASET_DIR = os.path.join(ROOT_DIR, "Dataset")
PROCESSED_DIR = os.path.join(ROOT_DIR, "processed_data")


def test_processed_files_exist():
    """Verify all expected processed files exist and are non-empty."""
    expected_files = [
        os.path.join(PROCESSED_DIR, "olist", "customers.csv"),
        os.path.join(PROCESSED_DIR, "olist", "orders.csv"),
        os.path.join(PROCESSED_DIR, "olist", "order_items.csv"),
        os.path.join(PROCESSED_DIR, "olist", "order_payments.csv"),
        os.path.join(PROCESSED_DIR, "olist", "products.csv"),
        os.path.join(PROCESSED_DIR, "olist", "product_category_name_translation.csv"),
        os.path.join(PROCESSED_DIR, "bitext", "customer_support_intents.csv"),
        os.path.join(PROCESSED_DIR, "synthetic", "customer_demo_accounts.csv"),
        os.path.join(PROCESSED_DIR, "reports", "data_validation_report.json"),
        os.path.join(PROCESSED_DIR, "reports", "data_validation_report.md"),
        os.path.join(PROCESSED_DIR, "reports", "relationship_integrity_report.md"),
    ]
    for path in expected_files:
        assert os.path.exists(path), f"File missing: {path}"
        assert os.path.getsize(path) > 0, f"File is empty: {path}"


def test_processed_row_counts():
    """Verify row counts of all processed tables match raw data."""
    def count_records(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            return sum(1 for _ in reader)

    assert count_records(os.path.join(PROCESSED_DIR, "olist", "customers.csv")) == 99441
    assert count_records(os.path.join(PROCESSED_DIR, "olist", "orders.csv")) == 99441
    assert count_records(os.path.join(PROCESSED_DIR, "olist", "order_items.csv")) == 112650
    assert count_records(os.path.join(PROCESSED_DIR, "olist", "order_payments.csv")) == 103886
    assert count_records(os.path.join(PROCESSED_DIR, "olist", "products.csv")) == 32951
    assert count_records(os.path.join(PROCESSED_DIR, "bitext", "customer_support_intents.csv")) == 26872
    assert count_records(os.path.join(PROCESSED_DIR, "synthetic", "customer_demo_accounts.csv")) == 25


def test_relational_integrity_foreign_keys():
    """Verify 100% referential integrity across all Olist foreign keys."""
    # 1. Customer IDs
    customer_ids = set()
    customer_unique_ids = set()
    with open(os.path.join(PROCESSED_DIR, "olist", "customers.csv"), "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            customer_ids.add(row["customer_id"])
            customer_unique_ids.add(row["customer_unique_id"])

    # 2. Orders -> Customers
    order_ids = set()
    with open(os.path.join(PROCESSED_DIR, "olist", "orders.csv"), "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            oid = row["order_id"]
            cid = row["customer_id"]
            uid = row["customer_unique_id"]
            order_ids.add(oid)
            assert cid in customer_ids, f"Order {oid} has unmatched customer_id {cid}"
            assert uid in customer_unique_ids, f"Order {oid} has unmatched customer_unique_id {uid}"

    # 3. Products
    product_ids = set()
    with open(os.path.join(PROCESSED_DIR, "olist", "products.csv"), "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            product_ids.add(row["product_id"])

    # 4. Order Items -> Orders & Products
    with open(os.path.join(PROCESSED_DIR, "olist", "order_items.csv"), "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            oid = row["order_id"]
            pid = row["product_id"]
            assert oid in order_ids, f"Item has unmatched order_id {oid}"
            assert pid in product_ids, f"Item has unmatched product_id {pid}"

    # 5. Order Payments -> Orders
    with open(os.path.join(PROCESSED_DIR, "olist", "order_payments.csv"), "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            oid = row["order_id"]
            assert oid in order_ids, f"Payment has unmatched order_id {oid}"


def test_demo_customer_accounts_schema_and_mapping():
    """Verify demo customer personas map to valid Olist customers without sensitive credentials."""
    customer_unique_ids = set()
    with open(os.path.join(PROCESSED_DIR, "olist", "customers.csv"), "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            customer_unique_ids.add(row["customer_unique_id"])

    with open(os.path.join(PROCESSED_DIR, "synthetic", "customer_demo_accounts.csv"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames)
        assert "password" not in fieldnames
        assert "secret" not in fieldnames
        assert "auth_token" not in fieldnames

        personas = list(reader)
        assert len(personas) == 25

        for p in personas:
            assert p["customer_unique_id"] in customer_unique_ids
            assert p["display_name"].startswith("Customer ")
            assert "@demo.internal" in p["demo_email"]
            assert int(p["total_orders"]) >= 1


def test_source_dataset_immutability():
    """Verify original source files in Dataset/ have not been altered."""
    expected_sizes = {
        "Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv": 19202474,
        "customers_dataset.csv": 9033957,
        "order_items_dataset.csv": 15438671,
        "order_payments_dataset.csv": 5777138,
        "orders_dataset.csv": 17654914,
        "products_dataset.csv": 2379446,
    }
    for filename, expected_size in expected_sizes.items():
        path = os.path.join(DATASET_DIR, filename)
        assert os.path.exists(path), f"Original dataset file deleted: {filename}"
        assert os.path.getsize(path) == expected_size, f"Original dataset file modified: {filename}"
