"""
Escalation Policy & Validation Service.
Enforces deterministic validation for human support escalation:
1. Backend-authoritative contact validation (email/phone).
2. Prevents premature escalation when user merely requests a human without stating an issue.
3. Ensures escalation is justified by policy/order context and backed by verified customer contact.
"""

import re
from typing import Tuple, Optional, List, Any

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


def validate_escalation_readiness(
    reason: str,
    contact_info: str,
) -> Tuple[bool, Optional[str], Optional[str], str]:
    """
    Backend-authoritative evaluation of an escalation request before writing to database:
    1. Ensures the reason is substantive (not empty or just a bare human/supervisor request).
    2. Validates contact information (email or phone).
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


def extract_order_and_product_context(
    text: str,
    history: List[Any],
    customer: Optional[Any] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Determines if an order or product has been sufficiently identified for escalation.
    Returns: (is_identified, order_id, product_info)

    Rules:
    1. If customer has only 1 order (total_orders <= 1), the affected order is unambiguous.
       Resolves to customer's sample_order_id or single order.
    2. If text or active history contains an explicit 32-hex order ID, extracts it.
    3. If text or active history contains a named order reference (e.g. 'order ABC123'), extracts it.
    4. If text references 'latest order', 'recent order', 'last order', resolves to latest order.
    5. If text contains an order date, provides sufficient order context.
    6. If text contains a known product category or item name, provides product context.
    """
    # 1. Single-order customer: order is unambiguous
    if customer is not None and getattr(customer, "total_orders", 0) <= 1:
        sample_id = getattr(customer, "sample_order_id", None)
        return True, sample_id, None

    combined_text = text + " " + " ".join([str(getattr(m, "content", "")) for m in history])

    # 2. Check for explicit 32-hex order ID
    hex_match = HEX_ORDER_ID_REGEX.search(combined_text)
    if hex_match:
        return True, hex_match.group(1).lower(), None

    # 3. Check for named order reference (e.g. "order ABC123")
    ref_match = ORDER_REF_REGEX.search(combined_text)
    if ref_match:
        candidate = ref_match.group(1).strip()
        # Avoid matching generic terms like "order arrived" or "order details"
        if candidate.lower() not in {"arrived", "details", "status", "items", "damaged", "broken", "number", "id"}:
            return True, candidate, None

    # 4. Check for reference to "latest order" / "most recent order"
    if re.search(r"\b(latest|most\s+recent|last|recent)\s+order\b", combined_text, re.IGNORECASE):
        sample_id = getattr(customer, "sample_order_id", None) if customer else None
        return True, sample_id, "Latest Order"

    # 5. Check for order date
    date_match = DATE_REF_REGEX.search(combined_text)
    if date_match:
        return True, None, f"Order Date: {date_match.group(0)}"

    # 6. Check for product or category indicator
    lower_text = combined_text.lower()
    for ind in KNOWN_PRODUCT_INDICATORS:
        if ind in lower_text:
            return True, None, ind.title()

    return False, None, None


def detect_pending_escalation_intent(
    history: List[Any],
    user_message: str,
    customer: Optional[Any] = None,
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
        user_message, active_history, customer
    )

    if customer is not None and getattr(customer, "total_orders", 0) > 1:
        if not is_order_identified:
            # Multi-order customer has not identified which order or product is affected.
            # Do NOT escalate prematurely! Agent must ask for order ID / date / product first.
            return False, email, phone, substantive_reason, None

    return True, email, phone, substantive_reason, resolved_order_id
