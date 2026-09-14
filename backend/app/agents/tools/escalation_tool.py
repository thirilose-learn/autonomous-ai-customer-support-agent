"""
Human Agent Escalation Tool.
Allows the AI agent to escalate complex disputes, supervisor requests, or policy exceptions to a human support agent.
Persists the real ticket record in Supabase table support_escalations with customer contact info.
Enforces:
1. Customer identity is derived strictly from CustomerContext.
2. Escalation requires an underlying investigated reason (not bare 'human please').
3. Valid contact info (email or phone) is mandatory before persistence.
"""

from typing import Optional, List
from langchain_core.tools import tool, BaseTool
from app.schemas.session import CustomerContext
from app.services.escalation_service import create_escalation_ticket
from app.services.escalation_policy import validate_escalation_readiness


def build_escalation_tools(customer: CustomerContext) -> List[BaseTool]:
    """
    Constructs the escalation tool bound strictly to authenticated customer identity.
    """

    @tool
    def request_human_escalation(
        reason: str,
        contact_info: str = "",
        urgency: str = "normal",
        order_id: Optional[str] = None,
        product_name: Optional[str] = None,
    ) -> str:
        """
        Escalate an investigated, unresolvable customer issue to a human support specialist or supervisor.
        Requirements:
        1. You must have investigated the customer's specific issue using available tools/policies first.
        2. Escalation is only justified if the issue cannot be resolved autonomously based on policy or data.
        3. You MUST have collected a valid contact method (email address or phone number) from the customer.
        4. For order issues, provide the affected order_id or product_name when available.

        Args:
            reason: Specific, substantive description of the investigated problem requiring human intervention.
            contact_info: The customer's email address (e.g., customer@example.com) OR phone number (e.g., +55 11 98765-4321).
            urgency: Priority level ('normal', 'high', 'critical').
            order_id: The specific order ID (e.g., 32-hex ID or reference) affected by this issue.
            product_name: The specific product name or category affected by this issue.
        """
        # Backend-authoritative validation of reason and contact information
        is_ready, email, phone, validation_err = validate_escalation_readiness(
            reason=reason,
            contact_info=contact_info,
        )

        if not is_ready:
            return (
                f"Action Denied: {validation_err}\n"
                f"Guidance: Do NOT claim that a ticket was created. Communicate the requirement to the customer politely."
            )

        # Attach order_id to reason and conversation summary for human support context
        formatted_reason = reason.strip()
        if order_id and order_id not in formatted_reason:
            formatted_reason = f"[Order: {order_id}] {formatted_reason}"

        summary_parts = []
        if order_id:
            summary_parts.append(f"Affected Order: {order_id}")
        if product_name:
            summary_parts.append(f"Product: {product_name}")
        conversation_summary = " | ".join(summary_parts) if summary_parts else None

        try:
            persisted = create_escalation_ticket(
                customer=customer,
                reason=formatted_reason,
                priority=urgency,
                conversation_summary=conversation_summary,
                contact_email=email,
                contact_phone=phone,
            )

            ticket_id = persisted["ticket_id"]
            priority_display = persisted.get("priority", "normal").upper()
            status_display = persisted.get("status", "open").upper()
            created_at_display = persisted.get("created_at", "")
            contact_used = email or phone or "Verified on file"
            order_display = f"- Affected Order: {order_id}\n" if order_id else ""
            product_display = f"- Affected Product: {product_name}\n" if product_name else ""

            return (
                f"Escalation Request Created Successfully and Saved in Database.\n"
                f"- Ticket ID: {ticket_id}\n"
                f"- Customer: {customer.display_name} ({customer.demo_customer_id})\n"
                f"- Contact: {contact_used}\n"
                f"{order_display}"
                f"{product_display}"
                f"- Urgency: {priority_display}\n"
                f"- Status: {status_display} (Assigned to Support Queue)\n"
                f"- Reason: {persisted['reason']}\n"
                f"- Logged At: {created_at_display}\n\n"
                f"DIRECTIVE FOR FINAL RESPONSE: You MUST clearly state the exact Ticket ID ({ticket_id}) "
                f"to the customer so they can track their case, and confirm that their contact information ({contact_used}) has been attached to the ticket for human follow-up. Do NOT state or imply that an email, SMS, or message has already been sent."
            )
        except Exception as exc:
            return (
                f"Escalation Failed: Could not record the escalation ticket in the database ({str(exc)}). "
                f"The ticket was NOT created. Inform the customer that we could not register the escalation ticket right now "
                f"and advise them to try again."
            )

    return [request_human_escalation]
