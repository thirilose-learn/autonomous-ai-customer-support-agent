"""
Deterministic demo customer selection module.
Selects 25 curated demo customer personas covering real-world support scenarios:
- VIP repeat buyers (17, 9, and 7 orders)
- In-transit / shipped orders (carrier tracking)
- Canceled orders (refund / cancellation policy inquiries)
- Unavailable orders (stock / fulfillment issues)
- Multi-item orders (order breakdown)
- Split payment orders (vouchers + credit card)
- Single-order delivered customers from diverse geographic states
"""

import os
import csv
from collections import defaultdict


def select_demo_personas(dataset_dir: str):
    cust_path = os.path.join(dataset_dir, "customers_dataset.csv")
    orders_path = os.path.join(dataset_dir, "orders_dataset.csv")
    items_path = os.path.join(dataset_dir, "order_items_dataset.csv")
    payments_path = os.path.join(dataset_dir, "order_payments_dataset.csv")

    # 1. Map customer_id -> (customer_unique_id, city, state)
    cust_id_to_meta = {}
    unique_to_loc = {}
    with open(cust_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cid = row["customer_id"].strip()
            uid = row["customer_unique_id"].strip()
            city = row["customer_city"].strip()
            state = row["customer_state"].strip()
            cust_id_to_meta[cid] = (uid, city, state)
            if uid not in unique_to_loc:
                unique_to_loc[uid] = (city, state)

    # 2. Gather orders per unique customer
    user_orders = defaultdict(list)
    order_to_status = {}
    order_to_uid = {}
    with open(orders_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            oid = row["order_id"].strip()
            cid = row["customer_id"].strip()
            status = row["order_status"].strip()
            uid, _, _ = cust_id_to_meta[cid]
            user_orders[uid].append((oid, status))
            order_to_status[oid] = status
            order_to_uid[oid] = uid

    # 3. Gather order item counts
    order_item_counts = defaultdict(int)
    with open(items_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            order_item_counts[row["order_id"].strip()] += 1

    # 4. Gather payment types and counts
    order_payment_types = defaultdict(set)
    with open(payments_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            oid = row["order_id"].strip()
            ptype = row["payment_type"].strip()
            order_payment_types[oid].add(ptype)

    selected = []
    seen_uids = set()

    def add_persona(uid, scenario, sample_order):
        if uid in seen_uids:
            return
        seen_uids.add(uid)
        city, state = unique_to_loc[uid]
        total_orders = len(user_orders[uid])
        idx = len(selected) + 1
        demo_id = f"DEMO_{idx:05d}"
        disp_name = f"Customer {idx:05d}"
        email = f"customer_{idx:05d}@demo.internal"
        selected.append({
            "demo_customer_id": demo_id,
            "customer_unique_id": uid,
            "display_name": disp_name,
            "demo_email": email,
            "total_orders": total_orders,
            "primary_scenario": scenario,
            "sample_order_id": sample_order,
            "customer_city": city,
            "customer_state": state,
        })

    # Scenario 1: Top VIP customer (17 orders)
    add_persona("8d50f5eadf50201ccdcedfb9e2ac8455", "VIP_REPEAT_BUYER_17_ORDERS", user_orders["8d50f5eadf50201ccdcedfb9e2ac8455"][0][0])

    # Scenario 2: Repeat buyer with 9 orders
    add_persona("3e43e6105506432c953e165fb2acf44c", "HIGH_VOLUME_REPEAT_BUYER_9_ORDERS", user_orders["3e43e6105506432c953e165fb2acf44c"][0][0])

    # Scenario 3, 4, 5: Repeat buyers with 7 orders
    top_7 = ["1b6c7548a2a1f9037c1fd3ddfed95f33", "6469f99c1f9dfae7733b25662e7f1782", "ca77025e7201e3b30c44b472ff346268"]
    for uid in top_7:
        add_persona(uid, "REPEAT_BUYER_7_ORDERS", user_orders[uid][0][0])

    # Scenario 6, 7: In-transit / Shipped orders
    for uid, olist in user_orders.items():
        if len(selected) >= 7:
            break
        for oid, status in olist:
            if status == "shipped":
                add_persona(uid, "IN_TRANSIT_SHIPPED_ORDER", oid)
                break

    # Scenario 8, 9: Canceled orders
    for uid, olist in user_orders.items():
        if len(selected) >= 9:
            break
        for oid, status in olist:
            if status == "canceled":
                add_persona(uid, "CANCELED_ORDER_REFUND_INQUIRY", oid)
                break

    # Scenario 10: Unavailable order
    for uid, olist in user_orders.items():
        if len(selected) >= 10:
            break
        for oid, status in olist:
            if status == "unavailable":
                add_persona(uid, "UNAVAILABLE_ORDER_ESCALATION", oid)
                break

    # Scenario 11: Multi-item single order (>= 5 items)
    for oid, cnt in order_item_counts.items():
        if cnt >= 5:
            uid = order_to_uid.get(oid)
            if uid and uid not in seen_uids and order_to_status.get(oid) == "delivered":
                add_persona(uid, f"DELIVERED_MULTI_ITEM_ORDER_{cnt}_ITEMS", oid)
                break

    # Scenario 12: Split payment (vouchers + credit card)
    for oid, ptypes in order_payment_types.items():
        if "voucher" in ptypes and "credit_card" in ptypes:
            uid = order_to_uid.get(oid)
            if uid and uid not in seen_uids:
                add_persona(uid, "SPLIT_PAYMENT_VOUCHER_AND_CREDIT", oid)
                break

    # Scenario 13 - 25: Diverse single-order delivered customers across different Brazilian states
    target_states = ["SP", "RJ", "MG", "RS", "PR", "BA", "SC", "DF", "GO", "PE", "CE", "ES", "MT"]
    for state in target_states:
        if len(selected) >= 25:
            break
        for uid, olist in user_orders.items():
            if uid not in seen_uids and len(olist) == 1:
                oid, status = olist[0]
                city, ustate = unique_to_loc[uid]
                if status == "delivered" and ustate == state:
                    add_persona(uid, f"DELIVERED_STANDARD_{state}", oid)
                    break

    # If still under 25, pad with delivered customers
    for uid, olist in user_orders.items():
        if len(selected) >= 25:
            break
        if uid not in seen_uids and len(olist) == 1 and olist[0][1] == "delivered":
            add_persona(uid, f"DELIVERED_STANDARD_{unique_to_loc[uid][1]}", olist[0][0])

    return selected
