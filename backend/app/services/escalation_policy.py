"""
Escalation Policy & Validation Service.
Enforces deterministic validation for human support escalation:
1. Backend-authoritative contact validation (email/phone).
2. Prevents premature escalation when user merely requests a human without stating an issue.
3. Ensures escalation is justified by policy/order context and backed by verified customer contact.
"""

import re
from typing import Tuple, Optional, List, Any, Dict

# RFC-compliant email regex
EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# Standard international and national phone formats (7 to 18 digits with standard delimiters)
PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,4}[-.\s]?)?(?:\(?\d{2,5}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{3,5}\b"
)

# Generic human-request phrases with no problem description
GENERIC_HUMAN_REQUESTS = [
    "i want to speak to a human",
    "i want to speak with a human",
    "i want to talk to a human",
    "speak to a human",
    "talk to a human",
    "human please",
    "connect to human",
    "connect to a human",
    "i need a human",
    "i want a human",
    "human support",
    "human manager",
    "speak to a manager",
    "talk to a manager",
    "connect to manager",
    "i want a supervisor",
    "i need a supervisor",
    "i want to speak to a supervisor",
    "i want to speak with a supervisor",
    "i need to speak with a supervisor",
    "i need to speak with a supervisor regarding an issue",
    "i want to speak with a supervisor regarding an issue",
    "request supervisor review",
    "request a supervisor review",
    "live agent",
    "representative",
    "customer service representative",
    "human assistance",
    "connect to support",
    "talk to someone",
    "speak to someone",
]

# Regex patterns for substantive complaints or issues
SUBSTANTIVE_PROBLEM_PATTERNS = [
    r"\bdamage[sd]?\b",
    r"\bbroken\b",
    r"\bdefect(ive)?\b",
    r"\bfaulty\b",
    r"\bcracked\b",
    r"\bshattered\b",
    r"\bscratched\b",
    r"\btorn\b",
    r"\bwrong\s+(item|product|order|package|shipment|color|size)?\b",
    r"\bmissing\s+(item|product|part|package)?\b",
    r"\bnever\s+(received|arrived)\b",
    r"\bnot\s+(received|delivered|arrived)\b",
    r"\bdid\s*n['o]t\s+(receive|arrive|get)\b",
    r"\blost\s+(in\s+transit)?\b",
    r"\bstolen\b",
    r"\boverdue\b",
    r"\blate\s+(delivery)?\b",
    r"\brefund\b",
    r"\breturn\b",
    r"\breplacement\b",
    r"\bexchange\b",
    r"\bcancel(lation)?\b",
    r"\b(unauthorized|double|twice|incorrect|wrong)\s+charge\b",
    r"\bcharged\s+twice\b",
    r"\bbilling\s+(error|issue|problem)\b",
    r"\bdispute\b",
    r"\bwarranty\b",
    r"\bexception\b",
    r"\bclaim\b",
    r"\bunresolv(able|ed)\b",
]

SUBSTANTIVE_REGEX = re.compile("|".join(SUBSTANTIVE_PROBLEM_PATTERNS), re.IGNORECASE)
ORDER_ID_REGEX = re.compile(r"\b[0-9a-fA-F]{32}\b|\border\s+#?[0-9a-fA-F]+\b", re.IGNORECASE)

HUMAN_OR_SUPERVISOR_TERMS = [
    r"\b(speak|talk)\s+(with|to)\s+(a\s+)?(human|supervisor|manager|person|representative|agent|someone)\b",
    r"\b(need|want)\s+(a\s+)?(human|supervisor|manager|representative|agent)\b",
    r"\b(request|ask\s+for)\s+(supervisor|human|manager)\s+review\b",
    r"\bconnect\s+(me\s+)?to\s+(a\s+)?(human|supervisor|manager|representative|agent|someone)\b",
    r"\b(human|supervisor|manager|representative)\s+(support|review|assistance|agent)\b",
    r"\blive\s+(agent|support|representative|chat)\b",
    r"\brequest\s+supervisor\s+review\b",
]
HUMAN_OR_SUPERVISOR_REGEX = re.compile("|".join(HUMAN_OR_SUPERVISOR_TERMS), re.IGNORECASE)


def extract_contact_info(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Backend-authoritative extraction of email and phone numbers from user text or conversation.
    Returns (email, phone).
    """
    if not text:
        return None, None

    email_match = EMAIL_REGEX.search(text)
    email = email_match.group(0).strip() if email_match else None

    phone = None
    phone_matches = PHONE_REGEX.findall(text)
    for p in phone_matches:
        # Filter out standalone short numbers or year-like strings
        digits_only = re.sub(r"\D", "", p)
        if 7 <= len(digits_only) <= 15:
            phone = p.strip()
            break

    return email, phone


def validate_contact_info(contact_str: str) -> Tuple[bool, Optional[str], Optional[str], str]:
    """
    Validates customer-provided contact information.
    Must be a valid email address OR a valid phone number.
    Returns:
        (is_valid: bool, email: Optional[str], phone: Optional[str], error_message: str)
    """
    if not contact_str or not contact_str.strip():
        return (
            False,
            None,
            None,
            "Contact information is missing. A valid email address or phone number is required before a support escalation ticket can be created."
        )

    clean_str = contact_str.strip()
    email, phone = extract_contact_info(clean_str)

    if email:
        return True, email, None, ""

    if phone:
        return True, None, phone, ""

    return (
        False,
        None,
        None,
        f"The provided contact information '{clean_str}' is invalid. Please provide a valid email address (e.g. name@example.com) or phone number (e.g. +55 11 98765-4321)."
    )


def has_substantive_issue(text: str) -> bool:
    """
    Checks whether the text describes a substantive complaint, problem,
    order ID, or issue (damaged, defective, wrong product, delivery issue, refund, etc.).
    """
    if not text:
        return False
    clean = text.strip()
    if ORDER_ID_REGEX.search(clean):
        return True
    if SUBSTANTIVE_REGEX.search(clean):
        return True
    return False


def is_generic_human_request(message: str) -> bool:
    """
    Determines if a customer prompt is merely a bare request for a human/supervisor/manager
    without describing an actual problem, order number, or substantive complaint.
    """
    if not message:
        return False

    clean = re.sub(r"[^\w\s]", " ", message.strip().lower())
    clean_words = " ".join(clean.split())

    # Check for exact matches with common bare requests
    for phrase in GENERIC_HUMAN_REQUESTS:
        if clean_words == phrase or clean_words.startswith(phrase + " ") or clean_words.endswith(" " + phrase):
            if not has_substantive_issue(message):
                return True

    # Check regex patterns
    if HUMAN_OR_SUPERVISOR_REGEX.search(message):
        if not has_substantive_issue(message):
            return True

    return False


def is_order_related_issue(text: str) -> bool:
    """
    Checks if an issue description specifically relates to an order, package,
    delivery, item, or damaged shipment (which requires order identification).
    """
    if not text:
        return False
    lower = text.lower()
    return bool(
        re.search(
            r"\b(order|package|delivery|delivered|shipment|shipped|tracking|transit|carrier|damaged|broken|crushed|defective|wrong item|missing item|arrived)\b",
            lower,
        )
    )


def validate_escalation_readiness(
    reason: str,
    contact_info: str,
    order_id: Optional[str] = None,
    customer: Optional[Any] = None,
) -> Tuple[bool, Optional[str], Optional[str], str]:
    """
    Backend-authoritative evaluation of an escalation request before writing to database:
    1. Ensures the reason is substantive (not empty or just a bare human/supervisor request).
    2. Validates contact information (email or phone).
    3. Enforces that multi-order customers must have identified/confirmed their affected order for order issues.
    """
    if not reason or not reason.strip():
        return False, None, None, "Escalation failed: An explicit reason detailing the unresolved issue is required."

    if is_generic_human_request(reason):
        return (
            False,
            None,
            None,
            "Escalation not created: The customer has requested a human but has not yet described their issue. "
            "Please ask the customer what specific issue or order they need assistance with so we can investigate first."
        )

    is_valid_contact, email, phone, contact_err = validate_contact_info(contact_info)
    if not is_valid_contact:
        return False, None, None, f"Escalation not created: {contact_err}"

    # Fallback model & tool safety: enforce order ownership and multi-order identification
    clean_oid = str(order_id).strip().lower() if order_id and str(order_id).strip().lower() not in ["none", "null"] else None
    if clean_oid and customer is not None and hasattr(customer, "customer_unique_id") and customer.customer_unique_id:
        try:
            from app.services.customer_data_service import get_order_for_customer
            order_rec = get_order_for_customer(order_id=clean_oid, customer=customer)
            if not order_rec:
                return (
                    False,
                    None,
                    None,
                    f"Action Denied: Order '{clean_oid}' does not belong to the current customer ({customer.demo_customer_id})."
                )
        except Exception:
            pass
    elif not clean_oid and customer is not None and getattr(customer, "total_orders", 0) > 1 and is_order_related_issue(reason):
        return (
            False,
            None,
            None,
            "Action Denied: Multi-order customer must identify or confirm the affected order ID before escalating."
        )

    return True, email, phone, ""



# Ticket ID pattern for identifying completed escalations
TICKET_ID_REGEX = re.compile(r"\bESC-[A-F0-9]{8}\b", re.IGNORECASE)

# Regex for 32-character hexadecimal order ID (Olist standard)
HEX_ORDER_ID_REGEX = re.compile(r"\b([a-f0-9]{32})\b", re.IGNORECASE)

# Regex for named order reference like "order ABC123", "order #826b..."
ORDER_REF_REGEX = re.compile(r"\border\s+(?:#\s*)?([a-zA-Z0-9_-]{4,36})\b", re.IGNORECASE)

# Date references: ISO (YYYY-MM-DD), Month Day, or DD/MM/YYYY
DATE_REF_REGEX = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember))\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,\s*\d{4})?)\b",
    re.IGNORECASE,
)

# Common product/category indicators for disambiguation
KNOWN_PRODUCT_INDICATORS = [
    "bed bath", "bed_bath", "watches", "watch", "sports", "leisure",
    "furniture", "decor", "home construction", "construction",
    "computers", "accessories", "health", "beauty", "auto", "toys",
    "baby", "garden", "telephony", "perfumery", "electronics",
    "fashion", "appliances", "luggage", "stationery", "tools",
    "drill", "table", "chair", "bedsheet", "pillow", "headphones",
    "speaker", "phone", "bag", "shoes", "shirt", "lamp",
]


def get_last_escalation_boundary(history: List[Any]) -> int:
    """
    Finds the index of the most recent message in history that created or confirmed
    an escalation ticket (matching ESC-[A-F0-9]{8}).
    Returns the index in history, or -1 if no escalation ticket exists in history.
    Any user messages/reasons at or before this index belong to an already-completed escalation.
    """
    last_idx = -1
    for i, m in enumerate(history):
        content = str(getattr(m, "content", ""))
        if TICKET_ID_REGEX.search(content):
            last_idx = i
    return last_idx


def get_previous_order_from_history(history: List[Any]) -> Optional[str]:
    """
    Finds the most recently mentioned 32-hex order ID in active conversation history
    (strictly after any completed escalation ticket boundary).
    Returns the lowercase 32-hex order ID if found, else None.
    """
    boundary_idx = get_last_escalation_boundary(history)
    active_history = history[boundary_idx + 1:] if boundary_idx >= 0 else history
    for m in reversed(active_history):
        content = str(getattr(m, "content", ""))
        match = HEX_ORDER_ID_REGEX.search(content)
        if match:
            return match.group(1).lower()
    return None


def resolve_order_by_product_context(
    product_query: str,
    customer: Optional[Any] = None,
    customer_orders: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[bool, Optional[str], bool]:
    """
    Resolves an order ID from product description or category name for a customer.
    Returns: (is_unique, order_id, is_ambiguous)
    - is_unique: True if the product matches items in exactly 1 customer order.
    - order_id: The matching order ID if unique, else None.
    - is_ambiguous: True if the product matches items across multiple customer orders.
    """
    if not product_query or not product_query.strip():
        return False, None, False

    orders: List[Dict[str, Any]] = []
    if customer_orders is not None:
        orders = customer_orders
    elif customer is not None:
        if hasattr(customer, "orders") and customer.orders:
            orders = customer.orders
        elif hasattr(customer, "customer_unique_id"):
            try:
                from app.services.customer_data_service import get_orders_for_customer
                orders = get_orders_for_customer(customer=customer)
            except Exception:
                orders = []

    if not orders:
        return False, None, False

    query_lower = product_query.strip().lower()

    # Find matching orders
    matching_order_ids = set()
    for o in orders:
        oid = o.get("order_id")
        if not oid:
            continue
        # Check items in order
        items = o.get("items", [])
        matched = False
        for itm in items:
            cat = str(itm.get("category", "")).lower()
            if cat and (cat in query_lower or any(word in cat for word in query_lower.split() if len(word) > 3)):
                matching_order_ids.add(oid)
                matched = True
                break
        if not matched:
            # Check items_summary strings e.g. ["1x Construction Tools (R$ 150.00)"]
            for s in o.get("items_summary", []):
                s_lower = str(s).lower()
                if any(word in s_lower for word in query_lower.split() if len(word) > 3):
                    matching_order_ids.add(oid)
                    break

    if len(matching_order_ids) == 1:
        return True, list(matching_order_ids)[0], False
    elif len(matching_order_ids) > 1:
        return False, None, True
    else:
        return False, None, False


def extract_order_and_product_context(
    text: str,
    history: List[Any],
    customer: Optional[Any] = None,
    customer_orders: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Determines if an order or product has been sufficiently identified for escalation.
    Returns: (is_identified, order_id, product_info)

    CRITICAL DETERMINISTIC RULES:
    1. Single-order customer: If customer has only 1 order (total_orders <= 1), the affected
       order is unambiguous and resolves automatically to sample_order_id.
    2. Explicit order ID in current message: If the user's message contains an explicit 32-hex
       order ID, it is validated and used as the affected order (taking precedence over any
       previously discussed order).
    3. Named order reference in current message: Extracts references like 'order ABC123'.
    4. Confirmation of previously discussed order: If an order was previously established in
       history AND the user explicitly confirms it ('Yes, that order', 'the order we discussed'),
       it resolves to that order.
       CRITICAL: If an order exists in history but the user has NOT explicitly confirmed it
       concerns that order, it is NOT resolved! (Requires clarification turn).
    5. Product context in current message: If the user identifies a product or category:
       - If it uniquely belongs to exactly 1 order -> resolves to that order.
       - If it appears in multiple orders -> returns ambiguous (escalation blocked, ask order ID).
    6. Date reference in current message: Provides valid order context.
    7. Explicit 'latest order' in current message: Resolves to customer's sample/latest order.
    """
    # 1. Single-order customer: order is unambiguous
    if customer is not None and getattr(customer, "total_orders", 0) <= 1:
        sample_id = getattr(customer, "sample_order_id", None)
        return True, sample_id, None

    # 2. Explicit 32-hex order ID in CURRENT message
    hex_in_text = HEX_ORDER_ID_REGEX.search(text)
    if hex_in_text:
        new_order_id = hex_in_text.group(1).lower()
        if customer is not None and hasattr(customer, "customer_unique_id"):
            try:
                from app.services.customer_data_service import get_order_for_customer
                order_row = get_order_for_customer(order_id=new_order_id, customer=customer)
                if not order_row:
                    # Order does not belong to this customer
                    return False, None, None
            except Exception:
                pass
        return True, new_order_id, None

    # 2b. Explicit 32-hex order ID provided by the USER in an active complaint message in history
    boundary_idx = get_last_escalation_boundary(history)
    active_history = history[boundary_idx + 1:] if boundary_idx >= 0 else history
    for m in reversed(active_history):
        is_user_msg = (
            getattr(m, "type", "") == "human"
            or m.__class__.__name__ == "HumanMessage"
            or (isinstance(m, dict) and m.get("role") in ["user", "human"])
        )
        if is_user_msg:
            content = str(getattr(m, "content", "") if hasattr(m, "content") else m.get("content", ""))
            if is_order_related_issue(content):
                hex_in_user_msg = HEX_ORDER_ID_REGEX.search(content)
                if hex_in_user_msg:
                    user_oid = hex_in_user_msg.group(1).lower()
                    if customer is not None and hasattr(customer, "customer_unique_id"):
                        try:
                            from app.services.customer_data_service import get_order_for_customer
                            order_row = get_order_for_customer(order_id=user_oid, customer=customer)
                            if not order_row:
                                return False, None, None
                        except Exception:
                            pass
                    return True, user_oid, None

    # 3. Explicit named order reference in CURRENT message (e.g. "order ABC123")
    ref_match = ORDER_REF_REGEX.search(text)
    if ref_match:
        candidate = ref_match.group(1).strip()
        if candidate.lower() not in {"arrived", "details", "status", "items", "damaged", "broken", "number", "id", "we", "just", "discussed"}:
            return True, candidate, None

    # 4. Confirmation of previously discussed order from active history
    prev_order_id = get_previous_order_from_history(history)
    if prev_order_id:
        # Check if user says it's a different order without providing the ID yet
        is_different = bool(re.search(r"\b(different\s+order|another\s+order|not\s+that\s+order|no\b)", text, re.IGNORECASE))
        if not is_different:
            # Check for affirmative confirmation of the previously discussed order
            is_confirmation = bool(
                re.search(
                    r"\b(yes|yeah|yep|correct|exactly|sure|right|that\s+order|the\s+order\s+we\s+(just\s+)?discussed|the\s+one\s+we\s+(just\s+)?discussed|same\s+order|that('s|\s+is)\s+the\s+order|that('s|\s+is)\s+the\s+one)\b",
                    text,
                    re.IGNORECASE,
                )
            )
            if is_confirmation:
                return True, prev_order_id, None

    # 5. Product context in current message: check for uniqueness
    found_product = None
    lower_text = text.lower()
    for ind in KNOWN_PRODUCT_INDICATORS:
        if ind in lower_text:
            found_product = ind.title()
            break

    if found_product or any(w in lower_text for w in ["item", "product"]):
        prod_query = found_product if found_product else text
        is_unique, resolved_oid, is_ambiguous = resolve_order_by_product_context(
            product_query=prod_query,
            customer=customer,
            customer_orders=customer_orders,
        )
        if is_unique and resolved_oid:
            return True, resolved_oid, found_product
        elif is_ambiguous:
            # Ambiguous product appears across multiple orders: block escalation
            return False, None, found_product
        elif found_product:
            # If customer has multiple orders and product cannot be uniquely verified, block
            if customer is not None and getattr(customer, "total_orders", 0) > 1:
                return False, None, found_product

    # 6. Check for order date in CURRENT message
    date_match = DATE_REF_REGEX.search(text)
    if date_match:
        return True, None, f"Order Date: {date_match.group(0)}"

    # 7. Check for explicit reference to "latest order" / "most recent order" in CURRENT message
    if re.search(r"\b(latest|most\s+recent|last)\s+order\b", text, re.IGNORECASE):
        sample_id = getattr(customer, "sample_order_id", None) if customer else None
        return True, sample_id, "Latest Order"

    return False, None, None


def detect_pending_escalation_intent(
    history: List[Any],
    user_message: str,
    customer: Optional[Any] = None,
    customer_orders: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[bool, Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Detects if the conversation has reached full escalation readiness:
    1. Verified contact info (email/phone) is present.
    2. A substantive issue exists in current message or UN-TICKETED active history.
       (Messages at or before an already-created ticket ESC-XXXXXXXX are excluded).
    3. If customer has multiple orders and the issue is order-related, sufficient
       identifying order or product context must be present.
    Returns: (is_pending, email, phone, reason, order_id)
    """
    # Step A: Determine escalation boundary to avoid state contamination
    boundary_idx = get_last_escalation_boundary(history)
    active_history = history[boundary_idx + 1:] if boundary_idx >= 0 else history

    # Step B: Check for contact info in user message or full conversation history
    # (Customer contact provided earlier in the session remains valid contact on file)
    msg_email, msg_phone = extract_contact_info(user_message)
    full_history_text = " ".join([str(getattr(m, "content", "")) for m in history])
    hist_email, hist_phone = extract_contact_info(full_history_text)

    email = msg_email or hist_email
    phone = msg_phone or hist_phone

    if not email and not phone:
        return False, None, None, None, None

    # Step C: Check for substantive issue ONLY in current message or un-ticketed active history
    substantive_reason = None
    if has_substantive_issue(user_message) and not is_generic_human_request(user_message):
        substantive_reason = user_message.strip()
    else:
        # Search backward ONLY through active_history (strictly after the last ticket boundary)
        for m in reversed(active_history):
            content = str(getattr(m, "content", "")).strip()
            if has_substantive_issue(content) and not is_generic_human_request(content):
                c_email, c_phone = extract_contact_info(content)
                if c_email and len(content.strip()) == len(c_email):
                    continue
                clean_reason = content.replace("\n", " ").strip()
                if len(clean_reason) > 200:
                    clean_reason = clean_reason[:200] + "..."
                substantive_reason = clean_reason
                break

    # If no substantive reason exists in the post-ticket active window, NOT ready for escalation!
    if not substantive_reason:
        return False, email, phone, None, None

    # Step D: Check Order / Product context requirement
    # Check if the customer has multiple orders and the issue requires order identification
    is_order_identified, resolved_order_id, product_info = extract_order_and_product_context(
        text=user_message,
        history=active_history,
        customer=customer,
        customer_orders=customer_orders,
    )

    if customer is not None and getattr(customer, "total_orders", 0) > 1:
        if not is_order_identified:
            # Multi-order customer has not identified or confirmed which order is affected.
            # Do NOT escalate prematurely! Agent must clarify order context first.
            return False, email, phone, substantive_reason, None

    return True, email, phone, substantive_reason, resolved_order_id
