"""
General-purpose helper utilities for CaseAI Copilot.
"""
from datetime import date, datetime
from typing import Optional, Any
import re


def days_since(date_str: str) -> Optional[int]:
    """
    Returns the number of days elapsed since the given date string.

    Args:
        date_str: A date string in YYYY-MM-DD format (or similar parseable format).

    Returns:
        Integer number of days, or None if the date string is invalid or empty.
    """
    if not date_str or not str(date_str).strip():
        return None

    # Normalize: strip whitespace and handle NaN-like strings
    cleaned = str(date_str).strip()
    if cleaned.lower() in ("", "nan", "none", "null", "nat"):
        return None

    # Try common date formats
    formats = ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt).date()
            return (date.today() - parsed).days
        except ValueError:
            continue

    return None


def is_date_within_days(date_str: str, days: int) -> bool:
    """
    Returns True if the given date is within the specified number of days from today.

    Args:
        date_str: Date string in a parseable format.
        days:     Number of days window.

    Returns:
        True if date is within range, False otherwise.
    """
    elapsed = days_since(date_str)
    if elapsed is None:
        return False
    return elapsed <= days


def safe_get(d: Any, *keys: str, default=None) -> Any:
    """
    Safely navigate a nested dictionary using a chain of keys.

    Args:
        d:       The root dictionary (or object).
        *keys:   Sequence of keys to traverse.
        default: Value to return if any key is missing.

    Returns:
        The value at the end of the key chain, or default.

    Example:
        safe_get(data, "patient", "address", "city", default="Unknown")
    """
    current = d
    for key in keys:
        if current is None:
            return default
        if isinstance(current, dict):
            current = current.get(key)
        else:
            current = getattr(current, key, None)
    return current if current is not None else default


def truncate_text(text: str, max_len: int = 2000) -> str:
    """
    Truncates text to a maximum length, appending an ellipsis if truncated.

    Args:
        text:    Input text string.
        max_len: Maximum allowed length (default 2000 characters).

    Returns:
        Truncated string with ellipsis, or original string if within limit.
    """
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3].rstrip() + "..."


def combine_text_safely(*texts: str, separator: str = "\n\n", max_total: int = 12000) -> str:
    """
    Combines multiple text chunks with a separator, up to a maximum total length.
    Useful for building AI prompt context without exceeding token limits.

    Args:
        *texts:     Variable number of text strings to combine.
        separator:  Separator between chunks (default double newline).
        max_total:  Maximum total character length (default 12000).

    Returns:
        Combined string, truncated if necessary.
    """
    valid_texts = [t for t in texts if t and t.strip()]
    combined = separator.join(valid_texts)
    if len(combined) > max_total:
        combined = combined[:max_total - 3].rstrip() + "..."
    return combined


def format_date_display(date_str: str) -> str:
    """
    Formats a date string for display in the UI.
    Returns a human-readable format or "Not recorded" if the date is missing/invalid.

    Args:
        date_str: A date string in YYYY-MM-DD or similar format.

    Returns:
        Formatted date string like "March 8, 2024" or "Not recorded".
    """
    if not date_str or not str(date_str).strip():
        return "Not recorded"

    cleaned = str(date_str).strip()
    if cleaned.lower() in ("nan", "none", "null", "nat", ""):
        return "Not recorded"

    formats = ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.strftime("%B %-d, %Y") if hasattr(parsed, "strftime") else cleaned
        except ValueError:
            continue
        except Exception:
            # %-d (day without zero-padding) may not work on Windows
            try:
                parsed = datetime.strptime(cleaned, fmt)
                return parsed.strftime("%B %d, %Y").replace(" 0", " ")
            except Exception:
                continue

    return cleaned  # Return as-is if no format matched
