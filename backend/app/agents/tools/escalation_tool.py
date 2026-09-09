"""
Human Agent Escalation Tool.
Allows the AI agent to escalate complex disputes, supervisor requests, or policy exceptions to a human support agent.
"""

from typing import Optional, List
import uuid
from datetime import datetime, timezone
from langchain_core.tools import tool, BaseTool
from app.schemas.session import CustomerContext


def build_escalation_tools(customer: CustomerContext) -> List[BaseTool]:
    """
    Constructs the escalation tool bound to customer identity.
    """

    @tool
    def request_human_escalation(reason: str, urgency: str = "normal") -> str:
        """
        Escalate the customer conversation to a human support specialist or supervisor.
        Call this tool when:
        1. The customer explicitly requests to speak with a person, manager, or supervisor.
        2. The issue involves a complex dispute, damaged goods claim, or policy exception.
        3. The automated tools cannot fulfill the customer's request.

        Args:
            reason: Detailed summary of why human escalation is required.
            urgency: Priority level ('normal', 'high', 'critical').
        """
        ticket_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        return (
            f"Escalation Request Created Successfully.\n"
            f"- Ticket ID: {ticket_id}\n"
            f"- Customer: {customer.display_name} ({customer.demo_customer_id})\n"
            f"- Urgency: {urgency.upper()}\n"
            f"- Reason: {reason}\n"
            f"- Logged At: {timestamp}\n"
            f"- Status: Assigned to Tier-2 Support Queue. A representative will review this case shortly."
        )

    return [request_human_escalation]
