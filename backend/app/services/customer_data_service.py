"""
Customer Data Service.
Executes customer-scoped queries against Supabase PostgreSQL.
Enforces strict cross-customer isolation by binding all queries to CustomerContext.customer_unique_id.
"""

import re
from typing import List, Dict, Any, Optional
from app.database.supabase_client import get_supabase_client
from app.schemas.session import CustomerContext


def format_category_name(raw_name: Optional[str]) -> str:
    """
    Formats raw Portuguese/database category keys into customer-friendly English titles.
    E.g. 'bed_bath_table' -> 'Bed Bath & Table', 'sports_leisure' -> 'Sports & Leisure'.
    """
    if not raw_name or not raw_name.strip():
        return "General Merchandise"

    clean = raw_name.strip().replace("_", " ")
    # Clean common conjunctions
    clean = re.sub(r"\b&\b", "&", clean)
    clean = clean.replace(" and ", " & ")
    words = [w.capitalize() for w in clean.split()]
    formatted = " ".join(words)
    # Common English category aesthetic enhancements
    formatted = formatted.replace("Bed Bath Table", "Bed Bath & Table")
    formatted = formatted.replace("Sports Leisure", "Sports & Leisure")
    formatted = formatted.replace("Furniture Decor", "Furniture & Decor")
    formatted = formatted.replace("Home Construction", "Home Construction")
    formatted = formatted.replace("Health Beauty", "Health & Beauty")
    return formatted


def get_orders_for_customer(customer: CustomerContext, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves orders strictly belonging to the authenticated customer.
    Enriches each order with batch-fetched order items and product categories
    in 3 efficient PostgREST calls (orders -> order_items -> products).
    """
    client = get_supabase_client()
    resp = (
        client.table("orders")
        .select("order_id, order_status, order_purchase_timestamp, order_delivered_customer_date, order_estimated_delivery_date")
        .eq("customer_unique_id", customer.customer_unique_id)
        .order("order_purchase_timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    orders = resp.data or []
    if not orders:
        return []

    order_ids = [o["order_id"] for o in orders]

    # Batch fetch order items for all recent orders
    items_resp = (
        client.table("order_items")
        .select("order_id, order_item_id, product_id, price, freight_value")
        .in_("order_id", order_ids)
        .order("order_item_id")
        .execute()
    )
    all_items = items_resp.data or []

    # Batch fetch products for all unique product_ids
    product_ids = list({itm["product_id"] for itm in all_items if itm.get("product_id")})
    prods_map: Dict[str, Dict[str, Any]] = {}
    if product_ids:
        prods_resp = (
            client.table("products")
            .select("product_id, product_category_name_english, product_weight_g")
            .in_("product_id", product_ids)
            .execute()
        )
        prods_map = {p["product_id"]: p for p in (prods_resp.data or [])}

    # Group items by order_id
    items_by_order: Dict[str, List[Dict[str, Any]]] = {oid: [] for oid in order_ids}
    for itm in all_items:
        oid = itm["order_id"]
        if oid in items_by_order:
            prod = prods_map.get(itm.get("product_id"), {})
            cat_name = format_category_name(prod.get("product_category_name_english"))
            items_by_order[oid].append({
                "item_number": itm.get("order_item_id"),
                "category": cat_name,
                "price": float(itm.get("price", 0.0)),
                "freight": float(itm.get("freight_value", 0.0)),
            })

    # Attach item summaries to each order
    for o in orders:
        oid = o["order_id"]
        order_itms = items_by_order.get(oid, [])
        o["items"] = order_itms
        o["total_items"] = len(order_itms)

        # Build concise product summary strings (e.g. "1x Sports & Leisure (R$ 26.99)")
        summary_lines = []
        for itm in order_itms:
            summary_lines.append(f"{itm['category']} (R$ {itm['price']:.2f})")
        o["items_summary"] = summary_lines

        total_price = round(sum(i["price"] for i in order_itms), 2)
        total_freight = round(sum(i["freight"] for i in order_itms), 2)
        o["total_products_amount"] = total_price
        o["total_freight_amount"] = total_freight
        o["total_order_amount"] = round(total_price + total_freight, 2)

    return orders


def get_order_for_customer(order_id: str, customer: CustomerContext) -> Optional[Dict[str, Any]]:
    """
    Retrieves a specific order ONLY if it belongs to the authenticated customer.
    If the order exists in the database but belongs to another customer,
    the query returns None, preventing cross-tenant information leakage.
    """
    if not order_id or not order_id.strip():
        return None

    client = get_supabase_client()
    resp = (
        client.table("orders")
        .select("order_id, customer_id, customer_unique_id, order_status, order_purchase_timestamp, order_delivered_customer_date, order_estimated_delivery_date")
        .eq("order_id", order_id.strip())
        .eq("customer_unique_id", customer.customer_unique_id)
        .execute()
    )
    if resp.data:
        return resp.data[0]
    return None


def get_order_details_for_customer(order_id: Optional[str], customer: CustomerContext) -> Optional[Dict[str, Any]]:
    """
    Retrieves full details of an order (status, items, categories, pricing, specs)
    ONLY if it belongs to the authenticated customer.
    If order_id is omitted, empty, or 'latest', automatically resolves the customer's most recent order.
    Returns None if no order exists or belongs to another customer.
    """
    client = get_supabase_client()
    clean_id = (order_id or "").strip()

    # If order_id is not specified or asks for latest/recent, find customer's latest order
    if not clean_id or clean_id.lower() in ["latest", "recent", "last", "none"]:
        recent_resp = (
            client.table("orders")
            .select("order_id, customer_id, customer_unique_id, order_status, order_purchase_timestamp, order_delivered_customer_date, order_estimated_delivery_date")
            .eq("customer_unique_id", customer.customer_unique_id)
            .order("order_purchase_timestamp", desc=True)
            .limit(1)
            .execute()
        )
        if not recent_resp.data:
            return None
        order = recent_resp.data[0]
        actual_order_id = order["order_id"]
    else:
        order = get_order_for_customer(order_id=clean_id, customer=customer)
        if not order:
            return None
        actual_order_id = order["order_id"]

    # Batch query order items
    items_resp = (
        client.table("order_items")
        .select("order_item_id, product_id, price, freight_value")
        .eq("order_id", actual_order_id)
        .order("order_item_id")
        .execute()
    )
    items = items_resp.data or []

    # Batch query products
    pids = list({itm["product_id"] for itm in items if itm.get("product_id")})
    prods_map: Dict[str, Dict[str, Any]] = {}
    if pids:
        prods_resp = (
            client.table("products")
            .select("product_id, product_category_name_english, product_weight_g, product_length_cm, product_height_cm, product_width_cm")
            .in_("product_id", pids)
            .execute()
        )
        prods_map = {p["product_id"]: p for p in (prods_resp.data or [])}

    # Enrich product details
    enriched_items = []
    for itm in items:
        prod = prods_map.get(itm.get("product_id"), {})
        cat_name = format_category_name(prod.get("product_category_name_english"))

        dim_parts = []
        l = prod.get("product_length_cm")
        w = prod.get("product_width_cm")
        h = prod.get("product_height_cm")
        if l and w and h:
            dim_parts.append(f"{l:.0f}x{w:.0f}x{h:.0f} cm")

        enriched_items.append({
            "item_number": itm.get("order_item_id"),
            "category": cat_name,
            "price": float(itm.get("price", 0.0)),
            "freight": float(itm.get("freight_value", 0.0)),
            "total_item_cost": round(float(itm.get("price", 0.0)) + float(itm.get("freight_value", 0.0)), 2),
            "weight_g": float(prod.get("product_weight_g")) if prod.get("product_weight_g") else None,
            "dimensions": dim_parts[0] if dim_parts else None,
        })

    total_order_price = round(sum(i["price"] for i in enriched_items), 2)
    total_freight = round(sum(i["freight"] for i in enriched_items), 2)

    return {
        "order_id": order.get("order_id"),
        "status": order.get("order_status"),
        "purchase_date": order.get("order_purchase_timestamp"),
        "delivered_date": order.get("order_delivered_customer_date"),
        "estimated_delivery_date": order.get("order_estimated_delivery_date"),
        "items_count": len(enriched_items),
        "items": enriched_items,
        "total_products_amount": total_order_price,
        "total_freight_amount": total_freight,
        "total_order_amount": round(total_order_price + total_freight, 2),
    }


def get_order_payments_for_customer(order_id: str, customer: CustomerContext) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieves payment details for an order ONLY if it belongs to the authenticated customer.
    Returns None if the order belongs to another customer.
    """
    order = get_order_for_customer(order_id=order_id, customer=customer)
    if not order:
        return None

    client = get_supabase_client()
    resp = (
        client.table("order_payments")
        .select("payment_sequential, payment_type, payment_installments, payment_value")
        .eq("order_id", order_id)
        .order("payment_sequential")
        .execute()
    )
    return resp.data or []


def get_all_payments_for_customer(customer: CustomerContext, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieves payment details across recent orders owned strictly by the authenticated customer.
    Enforces cross-customer isolation by deriving order IDs solely from customer_unique_id.
    """
    orders = get_orders_for_customer(customer=customer, limit=limit)
    if not orders:
        return []

    client = get_supabase_client()
    results = []
    for o in orders:
        oid = o.get("order_id")
        pmts_resp = (
            client.table("order_payments")
            .select("payment_sequential, payment_type, payment_installments, payment_value")
            .eq("order_id", oid)
            .order("payment_sequential")
            .execute()
        )
        pmts = pmts_resp.data or []
        total_paid = round(sum(float(p.get("payment_value", 0.0)) for p in pmts), 2)
        results.append({
            "order_id": oid,
            "order_status": o.get("order_status"),
            "purchase_date": o.get("order_purchase_timestamp"),
            "payments": pmts,
            "total_paid": total_paid,
        })
    return results

