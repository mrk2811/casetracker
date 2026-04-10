"""
Email parser for eTrack court notification emails.

Parses incoming court notification emails from NY eTrack system
to extract case updates, new filings, appearance changes, etc.

Supports both plain text and HTML email formats.
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ParsedEmailEvent:
    """A single event extracted from a court notification email."""
    event_type: str  # filing, appearance_scheduled, appearance_changed, decision, status_change
    index_number: Optional[str] = None
    court_type: Optional[str] = None
    county: Optional[str] = None
    case_title: Optional[str] = None  # e.g., "Smith v. Jones"
    event_date: Optional[str] = None
    event_time: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    justice: Optional[str] = None
    part: Optional[str] = None
    raw_text: Optional[str] = None


@dataclass
class ParsedEmail:
    """Result of parsing a court notification email."""
    is_court_notification: bool = False
    sender: Optional[str] = None
    subject: Optional[str] = None
    received_at: Optional[str] = None
    events: list[ParsedEmailEvent] = field(default_factory=list)
    raw_body: Optional[str] = None
    parse_errors: list[str] = field(default_factory=list)


# Patterns that identify eTrack court notification emails
COURT_NOTIFICATION_SUBJECTS = [
    r"(?i)court\s*notification",
    r"(?i)etrack\s*notification",
    r"(?i)case\s*update",
    r"(?i)new\s*filing",
    r"(?i)appearance\s*scheduled",
    r"(?i)hearing\s*notice",
    r"(?i)motion\s*filed",
    r"(?i)decision\s*issued",
    r"(?i)calendar\s*notice",
    r"(?i)court\s*date",
    r"(?i)nyscef",
    r"(?i)e-?filing",
    r"(?i)webcivil",
    r"(?i)webcrimin",
]

COURT_NOTIFICATION_SENDERS = [
    r"(?i)noreply@nycourts\.gov",
    r"(?i)etrack@nycourts\.gov",
    r"(?i)notification@courts\.state\.ny\.us",
    r"(?i)nyscef@nycourts\.gov",
    r"(?i).*@courts\.state\.ny\.us",
    r"(?i).*nycourts\.gov",
]

# Regex patterns for extracting case data from email body
INDEX_NUMBER_PATTERN = re.compile(
    r"(?:Index\s*(?:No\.?|Number|#)\s*[:.]?\s*|Case\s*#?\s*[:.]?\s*)"
    r"(\d{3,6}/\d{2,4}|\d{5,12}|[A-Z]{1,4}-\d{4}-\d{3,6})",
    re.IGNORECASE,
)

# Fallback: catch bare index-number-like patterns (e.g. 152847/2026)
# only used when the primary pattern finds nothing
BARE_INDEX_PATTERN = re.compile(
    r"\b(\d{3,6}/\d{4})\b",
)

# Fallback: catch alphanumeric case numbers like CV-2026-00891, CR-2025-12345
ALPHANUMERIC_INDEX_PATTERN = re.compile(
    r"\b([A-Z]{1,4}-\d{4}-\d{3,6})\b",
)

CASE_TITLE_PATTERN = re.compile(
    r"(?:(?:Case|Matter|Re)\s*[:.]?\s*)"
    r"([A-Z][a-zA-Z'\-]+(?:\s+(?:et\s+al\.?|Jr\.?|Sr\.?|III|II|IV))?)"
    r"\s+(?:v\.?|vs\.?)\s+"
    r"([A-Z][a-zA-Z'\-]+(?:\s+(?:et\s+al\.?|Jr\.?|Sr\.?|III|II|IV))?)",
    re.IGNORECASE,
)

COUNTY_PATTERN = re.compile(
    r"(?:County\s*[:.]?\s*)([\w\s]+?)(?:\s*(?:Court|Supreme|Civil|Criminal|\n|$))",
    re.IGNORECASE,
)

COURT_TYPE_PATTERN = re.compile(
    r"(?:Court\s*[:.]?\s*)([\w\s]+?)(?:\s*(?:County|\n|$))|"
    r"(Supreme\s*Court|Civil\s*Court|Criminal\s*Court|Housing\s*Court|"
    r"Family\s*Court|Surrogate.?s?\s*Court)",
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(
    r"(?:Date\s*[:.]?\s*|Scheduled\s+(?:for|on)\s+|on\s+)"
    r"(\d{1,2}/\d{1,2}/\d{2,4}|"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE,
)

TIME_PATTERN = re.compile(
    r"(?:Time\s*[:.]?\s*|at\s+)"
    r"(\d{1,2}:\d{2}\s*(?:AM|PM|a\.m\.|p\.m\.)?)",
    re.IGNORECASE,
)

LOCATION_PATTERN = re.compile(
    r"(?:Location|Courtroom|Room|Part)\s*[:.]?\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

JUSTICE_PATTERN = re.compile(
    r"(?:Justice|Judge|Hon\.?)\s*[:.]?\s*([A-Z][a-zA-Z'\-\s,\.]+?)(?:\n|$)",
    re.IGNORECASE,
)

# Event type detection patterns
FILING_PATTERNS = [
    re.compile(r"(?i)new\s+filing"),
    re.compile(r"(?i)document\s+filed"),
    re.compile(r"(?i)motion\s+(?:to\s+\w+\s+)?filed"),
    re.compile(r"(?i)petition\s+filed"),
    re.compile(r"(?i)complaint\s+filed"),
    re.compile(r"(?i)answer\s+filed"),
    re.compile(r"(?i)e-?filed"),
]

APPEARANCE_PATTERNS = [
    re.compile(r"(?i)(?:hearing|conference|trial|appearance)\s+scheduled"),
    re.compile(r"(?i)court\s+date\s+(?:scheduled|set)"),
    re.compile(r"(?i)calendar(?:ed)?\s+(?:for|on)"),
    re.compile(r"(?i)(?:next|upcoming)\s+(?:hearing|appearance|conference)"),
    re.compile(r"(?i)adjourned\s+to"),
]

DECISION_PATTERNS = [
    re.compile(r"(?i)decision\s+(?:issued|rendered|filed)"),
    re.compile(r"(?i)order\s+(?:signed|issued|entered)"),
    re.compile(r"(?i)judgment\s+(?:entered|issued)"),
    re.compile(r"(?i)ruling\s+(?:issued|made)"),
]

STATUS_CHANGE_PATTERNS = [
    re.compile(r"(?i)case\s+(?:disposed|closed|settled|dismissed)"),
    re.compile(r"(?i)status\s+(?:changed|updated)"),
    re.compile(r"(?i)discontinued"),
    re.compile(r"(?i)transferred"),
]


def is_court_notification(sender: str, subject: str, body: str) -> bool:
    """
    Determine if an email is a court notification.
    
    Privacy compliance: Only court notification emails should be parsed.
    All other emails are discarded without reading content.
    """
    # Check sender first (most reliable)
    for pattern in COURT_NOTIFICATION_SENDERS:
        if re.search(pattern, sender):
            return True

    # Check subject
    for pattern in COURT_NOTIFICATION_SUBJECTS:
        if re.search(pattern, subject):
            return True

    # Check body for strong court notification indicators (limited check)
    court_body_indicators = [
        r"(?i)index\s*(?:no|number|#)",
        r"(?i)supreme\s*court.*county",
        r"(?i)civil\s*court",
        r"(?i)criminal\s*court",
        r"(?i)nyscef",
        r"(?i)etrack",
        r"(?i)court\s+date",
        r"(?i)\bCase\s+[A-Z]{1,4}-\d{4}-\d{3,6}\b",
        r"(?i)(?:hearing|conference|appearance)\s+scheduled",
    ]
    body_preview = body[:500] if body else ""
    match_count = sum(1 for p in court_body_indicators if re.search(p, body_preview))
    if match_count >= 2:
        return True

    return False


def _detect_event_type(text: str) -> str:
    """Detect the type of court event from email text."""
    for pattern in FILING_PATTERNS:
        if pattern.search(text):
            return "filing"

    for pattern in APPEARANCE_PATTERNS:
        if pattern.search(text):
            return "appearance_scheduled"

    for pattern in DECISION_PATTERNS:
        if pattern.search(text):
            return "decision"

    for pattern in STATUS_CHANGE_PATTERNS:
        if pattern.search(text):
            return "status_change"

    return "update"


def _extract_text_from_html(html: str) -> str:
    """Extract clean text from HTML email body."""
    soup = BeautifulSoup(html, "lxml")
    # Remove script and style elements
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _normalize_court_type(raw: str) -> str:
    """Normalize court type string to match our schema."""
    raw_lower = raw.lower().strip()
    if "supreme" in raw_lower:
        return "supreme"
    if "criminal" in raw_lower:
        return "criminal"
    if "housing" in raw_lower or "civil" in raw_lower or "local" in raw_lower:
        return "local_civil"
    return "supreme"  # default


def _parse_date_string(date_str: str) -> Optional[str]:
    """Parse various date formats into ISO format."""
    formats = [
        "%m/%d/%Y",
        "%m/%d/%y",
        "%B %d, %Y",
        "%B %d %Y",
        "%b %d, %Y",
        "%b %d %Y",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str.strip(), fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str


def parse_email(
    sender: str,
    subject: str,
    body_text: Optional[str] = None,
    body_html: Optional[str] = None,
    received_at: Optional[str] = None,
) -> ParsedEmail:
    """
    Parse a court notification email and extract case events.
    
    Privacy note: This function should only be called after
    is_court_notification() returns True. Non-court emails
    are discarded without parsing.
    
    Args:
        sender: Email sender address
        subject: Email subject line
        body_text: Plain text body (preferred)
        body_html: HTML body (fallback)
        received_at: When the email was received (ISO format)
    
    Returns:
        ParsedEmail with extracted events and metadata
    """
    result = ParsedEmail(
        sender=sender,
        subject=subject,
        received_at=received_at or datetime.utcnow().isoformat(),
    )

    # Get the text content
    text = body_text or ""
    if not text and body_html:
        text = _extract_text_from_html(body_html)

    if not text:
        result.parse_errors.append("No email body content to parse")
        return result

    result.raw_body = text[:5000]  # Store limited raw body for audit

    # Check if this is a court notification
    if not is_court_notification(sender, subject, text):
        result.is_court_notification = False
        return result

    result.is_court_notification = True

    # Extract case information
    try:
        event = ParsedEmailEvent(
            event_type=_detect_event_type(subject + " " + text),
            raw_text=text[:2000],
        )

        # Extract index number
        idx_match = INDEX_NUMBER_PATTERN.search(text)
        if idx_match:
            event.index_number = idx_match.group(1)
        else:
            # Also check subject
            idx_match = INDEX_NUMBER_PATTERN.search(subject)
            if idx_match:
                event.index_number = idx_match.group(1)
            else:
                # Fallback: look for bare index number pattern
                bare_match = BARE_INDEX_PATTERN.search(text)
                if not bare_match:
                    bare_match = BARE_INDEX_PATTERN.search(subject)
                if bare_match:
                    event.index_number = bare_match.group(1)
                else:
                    # Fallback: look for alphanumeric case numbers (e.g. CV-2026-00891)
                    alpha_match = ALPHANUMERIC_INDEX_PATTERN.search(text)
                    if not alpha_match:
                        alpha_match = ALPHANUMERIC_INDEX_PATTERN.search(subject)
                    if alpha_match:
                        event.index_number = alpha_match.group(1)

        # Extract case title (parties)
        title_match = CASE_TITLE_PATTERN.search(text)
        if title_match:
            event.case_title = f"{title_match.group(1)} v. {title_match.group(2)}"

        # Extract county
        county_match = COUNTY_PATTERN.search(text)
        if county_match:
            event.county = county_match.group(1).strip()

        # Extract court type
        court_match = COURT_TYPE_PATTERN.search(text)
        if court_match:
            raw_court = court_match.group(1) or court_match.group(2)
            if raw_court:
                event.court_type = _normalize_court_type(raw_court)

        # Extract date
        date_match = DATE_PATTERN.search(text)
        if date_match:
            event.event_date = _parse_date_string(date_match.group(1))

        # Extract time
        time_match = TIME_PATTERN.search(text)
        if time_match:
            event.event_time = time_match.group(1).strip()

        # Extract location
        loc_match = LOCATION_PATTERN.search(text)
        if loc_match:
            event.location = loc_match.group(1).strip()

        # Extract justice
        justice_match = JUSTICE_PATTERN.search(text)
        if justice_match:
            event.justice = justice_match.group(1).strip()

        # Build description from subject + key details
        desc_parts = [subject]
        if event.case_title:
            desc_parts.append(f"Case: {event.case_title}")
        if event.event_date:
            desc_parts.append(f"Date: {event.event_date}")
        event.description = " | ".join(desc_parts)

        result.events.append(event)

    except Exception as e:
        logger.error(f"Error parsing email body: {e}")
        result.parse_errors.append(f"Parse error: {str(e)}")

    return result


def parse_multi_case_email(
    sender: str,
    subject: str,
    body_text: Optional[str] = None,
    body_html: Optional[str] = None,
    received_at: Optional[str] = None,
) -> ParsedEmail:
    """
    Parse an email that may contain updates for multiple cases.
    
    Some court notification emails (e.g., daily digests) contain
    updates for multiple cases. This parser splits them and
    creates separate events for each case.
    """
    # First try single-case parse
    result = parse_email(sender, subject, body_text, body_html, received_at)

    if not result.is_court_notification:
        return result

    text = body_text or ""
    if not text and body_html:
        text = _extract_text_from_html(body_html)

    # Look for multiple index numbers in the body
    all_indices = INDEX_NUMBER_PATTERN.findall(text)
    # Also check for alphanumeric case numbers
    alpha_indices = ALPHANUMERIC_INDEX_PATTERN.findall(text)
    # Merge unique index numbers (avoid duplicates already captured by primary pattern)
    seen = set(all_indices)
    for idx in alpha_indices:
        if idx not in seen:
            all_indices.append(idx)
            seen.add(idx)

    if len(all_indices) <= 1:
        return result  # Single case, already parsed

    # Multiple cases found - split by index number sections
    events = []
    for idx_num in all_indices:
        # Find the section around this index number
        pattern = re.compile(
            rf"(?:(?:Index\s*(?:No\.?|Number|#)|Case)\s*[:.]?\s*{re.escape(idx_num)})"
            r"([\s\S]*?)(?=(?:Index\s*(?:No\.?|Number|#)|Case)\s*[:.]?\s*[A-Z0-9]|$)",
            re.IGNORECASE,
        )
        section_match = pattern.search(text)
        section_text = section_match.group(1) if section_match else ""

        event = ParsedEmailEvent(
            event_type=_detect_event_type(section_text),
            index_number=idx_num,
            raw_text=section_text[:1000],
        )

        # Parse section-specific details
        title_match = CASE_TITLE_PATTERN.search(section_text)
        if title_match:
            event.case_title = f"{title_match.group(1)} v. {title_match.group(2)}"

        date_match = DATE_PATTERN.search(section_text)
        if date_match:
            event.event_date = _parse_date_string(date_match.group(1))

        time_match = TIME_PATTERN.search(section_text)
        if time_match:
            event.event_time = time_match.group(1).strip()

        event.description = f"{subject} | Index #{idx_num}"
        events.append(event)

    if events:
        result.events = events

    return result
