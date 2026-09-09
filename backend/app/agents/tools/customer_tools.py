"""
Customer-Scoped Agent Tools.
Enforces session-bound customer identity: CustomerContext is baked into the tool closures.
The LLM is NEVER allowed to supply, invent, or tamper with customer_unique_id.
"""

from typing import List, Optional
import json
from langchain_core.tools import tool, BaseTool
from app.schemas.session import CustomerContext
from app.services.customer_data_service import (
    get_orders_for_customer,
    get_order_details_for_customer,
    get_order_payments_for_customer,
)


def build_customer_tools(customer: CustomerContext) -> List[BaseTool]:
    """
    Constructs tools pre-bound to the authenticated CustomerContext.
    All database operations execute strictly within the customer's isolated scope.
    """

    @tool
    def get_my_orders() -> str:
        """
        Retrieve past and active orders for the currently authenticated customer.
        Returns order ID, status, purchase date, and delivery date for up to 10 recent orders.
        Takes no arguments.
        """
        orders = get_orders_for_customer(customer=customer, limit=10)
        if not orders:
            return f"No orders found for customer {customer.display_name}."

        formatted_orders = []
        for o in orders:
            formatted_orders.append(
                f"- Order ID: {o['order_id']}\n"
                f"  Status: {o.get('order_status', 'unknown')}\n"
                f"  Purchased: {o.get('order_purchase_timestamp', 'N/A')}\n"
                f"  Delivered: {o.get('order_delivered_customer_date') or 'Pending Delivery'}\n"
                f"  Estimated Delivery: {o.get('order_estimated_delivery_date') or 'N/A'}"
            )
        return f"Found {len(orders)} order(s) for {customer.display_name}:\n\n" + "\n\n".join(formatted_orders)

    @tool
    def get_my_order_details(order_id: str) -> str:
        """
        Retrieve items, products, categories, pricing, and shipping information for a specific order owned by the customer.
        Args:
            order_id: The 32-character hexadecimal order identifier.
        """
        clean_id = (order_id or "").strip()
        details = get_order_details_for_customer(order_id=clean_id, customer=customer)
        if not details:
            return f"Order '{clean_id}' was not found under your account. Please check the order ID."

        items_str = []
        for itm in details.get("items", []):
            items_str.append(
                f"  * Item #{itm['item_number']}: {itm['category']} - R$ {itm['price']:.2f} (Shipping: R$ {itm['freight']:.2f})"
            )

        return (
            f"Order Details for {clean_id}:\n"
            f"- Status: {details.get('status')}\n"
            f"- Purchased: {details.get('purchase_date')}\n"
            f"- Delivered: {details.get('delivered_date') or 'In transit / Pending'}\n"
            f"- Estimated Delivery: {details.get('estimated_delivery_date') or 'N/A'}\n"
            f"- Total Items: {details.get('items_count')}\n"
            f"- Items Breakdown:\n" + "\n".join(items_str) + "\n"
            f"- Product Subtotal: R$ {details.get('total_products_amount'):.2f}\n"
            f"- Freight Subtotal: R$ {details.get('total_freight_amount'):.2f}\n"
            f"- Total Order Amount: R$ {details.get('total_order_amount'):.2f}"
        )

    @tool
    def get_my_payment_details(order_id: str) -> str:
        """
        Retrieve payment method, installments, and payment value for a specific order owned by the customer.
        Args:
            order_id: The 32-character hexadecimal order identifier.
        """
        clean_id = (order_id or "").strip()
        payments = get_order_payments_for_customer(order_id=clean_id, customer=customer)
        if payments is None:
            return f"Order '{clean_id}' was not found under your account."
        if not payments:
            return f"No payment records found for order '{clean_id}'."

        lines = []
        for p in payments:
            lines.append(
                f"  * Payment #{p.get('payment_sequential')}: {p.get('payment_type')} "
                f"({p.get('payment_installments')} installment(s)) - R$ {float(p.get('payment_value', 0.0)):.2f}"
            )

        total_paid = sum(float(p.get("payment_value", 0.0)) for p in payments)
        return (
            f"Payment Summary for Order {clean_id}:\n"
            + "\n".join(lines)
            + f"\nTotal Amount Paid: R$ {total_paid:.2f}"
        )

    return [get_my_orders, get_my_order_details, get_my_payment_details]
