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
    get_all_payments_for_customer,
)


def _format_status(status_str: Optional[str]) -> str:
    s = (status_str or "").strip().lower()
    mapping = {
        "delivered": "Delivered",
        "entregue": "Delivered",
        "shipped": "Shipped",
        "enviado": "Shipped",
        "canceled": "Canceled",
        "cancelado": "Canceled",
        "processing": "Processing",
        "processando": "Processing",
        "invoiced": "Invoiced",
        "faturado": "Invoiced",
        "unavailable": "Unavailable",
        "indisponivel": "Unavailable",
        "approved": "Approved",
        "aprovado": "Approved",
        "created": "Created",
        "criado": "Created",
    }
    return mapping.get(s, s.capitalize() if s else "Unknown")


def build_customer_tools(customer: CustomerContext) -> List[BaseTool]:
    """
    Constructs tools pre-bound to the authenticated CustomerContext.
    All database operations execute strictly within the customer's isolated scope.
    """

    @tool
    def get_my_orders() -> str:
        """
        Retrieve past and active orders for the currently authenticated customer.
        Returns order ID, status, purchase date, delivery date, item count, and product category summary for up to 10 recent orders.
        Takes no arguments.
        """
        orders = get_orders_for_customer(customer=customer, limit=10)
        if not orders:
            return f"No orders found for customer {customer.display_name}."

        formatted_orders = []
        for o in orders:
            status_text = _format_status(o.get('order_status'))
            items_summary = o.get("items_summary", [])
            items_desc = ", ".join(items_summary) if items_summary else "Items details not available"
            total_items = o.get("total_items", len(items_summary))
            formatted_orders.append(
                f"- Order ID: {o['order_id']}\n"
                f"  Status: {status_text}\n"
                f"  Purchased: {o.get('order_purchase_timestamp', 'N/A')}\n"
                f"  Delivered: {o.get('order_delivered_customer_date') or 'Pending Delivery'}\n"
                f"  Estimated Delivery: {o.get('order_estimated_delivery_date') or 'N/A'}\n"
                f"  Total Items: {total_items}\n"
                f"  Products: {items_desc}\n"
                f"  Order Total: R$ {o.get('total_order_amount', 0.0):.2f}"
            )
        return f"Found {len(orders)} order(s) for {customer.display_name}:\n\n" + "\n\n".join(formatted_orders)

    @tool
    def get_my_order_details(order_id: Optional[str] = None) -> str:
        """
        Retrieve items, products, categories, pricing, freight, dimensions, and weights for an order owned by the customer.
        If order_id is provided, returns details for that specific order.
        If order_id is omitted, empty, or 'latest', automatically returns items and details for the customer's most recent order.
        Args:
            order_id: Optional 32-character hexadecimal order identifier.
        """
        clean_id = (order_id or "").strip()
        details = get_order_details_for_customer(order_id=clean_id, customer=customer)
        if not details:
            if clean_id and clean_id.lower() not in ["latest", "recent", "none"]:
                return f"Order '{clean_id}' was not found under your account. Please check the order ID."
            return f"No orders found under the account for {customer.display_name}."

        actual_order_id = details.get("order_id", clean_id)
        is_latest_note = " (Most Recent Order)" if (not clean_id or clean_id.lower() in ["latest", "recent", "none"]) else ""

        items_str = []
        for itm in details.get("items", []):
            specs = []
            if itm.get("weight_g"):
                specs.append(f"Weight: {itm['weight_g']:.0f}g")
            if itm.get("dimensions"):
                specs.append(f"Dimensions: {itm['dimensions']}")
            spec_text = f" ({', '.join(specs)})" if specs else ""

            items_str.append(
                f"  * Item #{itm['item_number']}: {itm['category']} - R$ {itm['price']:.2f} (Freight: R$ {itm['freight']:.2f}){spec_text}"
            )

        status_text = _format_status(details.get('status'))
        return (
            f"Order Details for {actual_order_id}{is_latest_note}:\n"
            f"- Status: {status_text}\n"
            f"- Purchased: {details.get('purchase_date')}\n"
            f"- Delivered: {details.get('delivered_date') or 'In transit / Pending'}\n"
            f"- Estimated Delivery: {details.get('estimated_delivery_date') or 'N/A'}\n"
            f"- Total Items: {details.get('items_count')}\n"
            f"- Items Breakdown:\n" + ("\n".join(items_str) if items_str else "  * No individual items recorded") + "\n"
            f"- Product Subtotal: R$ {details.get('total_products_amount'):.2f}\n"
            f"- Freight Subtotal: R$ {details.get('total_freight_amount'):.2f}\n"
            f"- Total Order Amount: R$ {details.get('total_order_amount'):.2f}"
        )

    @tool
    def get_my_payment_details(order_id: Optional[str] = None) -> str:
        """
        Retrieve payment method, installments, and payment value for the customer's orders.
        If order_id is provided, returns payment details for that specific order.
        If order_id is omitted or empty, returns payment summaries for all recent orders owned by this customer.
        Args:
            order_id: Optional 32-character hexadecimal order identifier.
        """
        clean_id = (order_id or "").strip()
        if clean_id:
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
        else:
            all_pmts = get_all_payments_for_customer(customer=customer, limit=5)
            if not all_pmts:
                return f"No orders or payment records found for customer {customer.display_name}."

            sections = []
            for entry in all_pmts:
                pmt_lines = []
                for p in entry.get("payments", []):
                    pmt_lines.append(
                        f"  * Payment #{p.get('payment_sequential')}: {p.get('payment_type')} "
                        f"({p.get('payment_installments')} installment(s)) - R$ {float(p.get('payment_value', 0.0)):.2f}"
                    )
                status_text = _format_status(entry.get('order_status'))
                sections.append(
                    f"- Order ID: {entry['order_id']} (Status: {status_text}, "
                    f"Purchased: {entry.get('purchase_date', 'N/A')})\n"
                    + ("\n".join(pmt_lines) if pmt_lines else "  * No payment record on file")
                    + f"\n  Total Paid: R$ {entry.get('total_paid', 0.0):.2f}"
                )
            return (
                f"Payment Records for Recent Orders of {customer.display_name}:\n\n"
                + "\n\n".join(sections)
            )

    return [get_my_orders, get_my_order_details, get_my_payment_details]
