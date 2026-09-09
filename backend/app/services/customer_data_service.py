"""
Customer Data Service.
Executes customer-scoped queries against Supabase PostgreSQL.
Enforces strict cross-customer isolation by binding all queries to CustomerContext.customer_unique_id.
"""

from typing import List, Dict, Any, Optional
from app.database.supabase_client import get_supabase_client
from app.schemas.session import CustomerContext


def get_orders_for_customer(customer: CustomerContext, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves orders strictly belonging to the authenticated customer.
    The customer_unique_id is extracted exclusively from the validated CustomerContext.
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
    return resp.data or []


def get_order_for_customer(order_id: str, customer: CustomerContext) -> Optional[Dict[str, Any]]:
    """
    Retrieves a specific order ONLY if it belongs to the authenticated customer.
    If the order exists in the database but belongs to another customer,
    the query returns None, preventing cross-tenant information leakage.
    """
    client = get_supabase_client()
    resp = (
        client.table("orders")
        .select("order_id, customer_id, customer_unique_id, order_status, order_purchase_timestamp, order_delivered_customer_date")
        .eq("order_id", order_id)
        .eq("customer_unique_id", customer.customer_unique_id)
        .execute()
    )
    if resp.data:
        return resp.data[0]
    return None


def get_order_details_for_customer(order_id: str, customer: CustomerContext) -> Optional[Dict[str, Any]]:
    """
    Retrieves full details of an order (status, items, categories, pricing)
    ONLY if it belongs to the authenticated customer.
    Returns None if order does not exist or belongs to another customer.
    """
    order = get_order_for_customer(order_id=order_id, customer=customer)
    if not order:
        return None

    client = get_supabase_client()
    items_resp = (
        client.table("order_items")
        .select("order_item_id, product_id, price, freight_value")
        .eq("order_id", order_id)
        .order("order_item_id")
        .execute()
    )
    items = items_resp.data or []

    # Enrich product names
    enriched_items = []
    for itm in items:
        prod_resp = (
            client.table("products")
            .select("product_category_name_english")
            .eq("product_id", itm["product_id"])
            .limit(1)
            .execute()
        )
        cat_name = "general_item"
        if prod_resp.data and prod_resp.data[0].get("product_category_name_english"):
            cat_name = prod_resp.data[0]["product_category_name_english"]

        enriched_items.append({
            "item_number": itm.get("order_item_id"),
            "category": cat_name,
            "price": float(itm.get("price", 0.0)),
            "freight": float(itm.get("freight_value", 0.0)),
            "total_item_cost": round(float(itm.get("price", 0.0)) + float(itm.get("freight_value", 0.0)), 2),
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
