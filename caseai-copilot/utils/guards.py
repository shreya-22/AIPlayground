"""
Security guards for CaseAI Copilot.
Includes SQL injection prevention and input validation utilities.
"""
import re
from typing import Tuple


class SQLGuard:
    """
    Validates SQL queries to prevent injection attacks and destructive operations.
    Only SELECT queries are permitted through the application interface.
    """

    DANGEROUS_KEYWORDS = [
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "TRUNCATE",
        "EXEC",
        "EXECUTE",
        "MERGE",
        "CREATE",
        "GRANT",
        "REVOKE",
        "BACKUP",
        "RESTORE",
        "BULK",
        "OPENROWSET",
        "OPENQUERY",
        "XP_",
        "SP_",
    ]

    @staticmethod
    def validate_query(query: str) -> Tuple[bool, str]:
        """
        Validates a SQL query string for safety.

        Returns:
            (True, "valid") if the query passes all checks.
            (False, reason) if the query is rejected.
        """
        if not query or not query.strip():
            return False, "Query is empty."

        # Normalize for keyword checking
        normalized = query.strip().upper()

        # Must start with SELECT
        if not normalized.startswith("SELECT"):
            return False, (
                "Only SELECT queries are permitted. "
                "The query must begin with the SELECT keyword."
            )

        # Check for dangerous keywords
        for keyword in SQLGuard.DANGEROUS_KEYWORDS:
            # Use word boundary matching to avoid false positives on substrings
            # e.g. "EXECUTE" should not match "EXECUTED" — but we also check XP_ / SP_
            if keyword.endswith("_"):
                # Prefix check (e.g. XP_, SP_)
                if keyword in normalized:
                    return False, (
                        f"Query contains a disallowed keyword or prefix: '{keyword}'. "
                        "This type of SQL statement is not permitted."
                    )
            else:
                pattern = r"\b" + re.escape(keyword) + r"\b"
                if re.search(pattern, normalized):
                    return False, (
                        f"Query contains a disallowed keyword: '{keyword}'. "
                        "Only read-only SELECT queries are permitted."
                    )

        # Check for semicolons that might chain statements
        if ";" in query:
            return False, (
                "Query contains a semicolon (;). Statement chaining is not permitted. "
                "Please submit a single SELECT query without semicolons."
            )

        # Check for inline comment patterns
        if "--" in query:
            return False, (
                "Query contains an inline comment pattern '--'. "
                "Comments are not permitted in queries."
            )

        if "/*" in query or "*/" in query:
            return False, (
                "Query contains a block comment pattern '/* */'. "
                "Comments are not permitted in queries."
            )

        return True, "valid"

    @staticmethod
    def sanitize_identifier(identifier: str) -> str:
        """
        Sanitizes a SQL identifier (table name, column name, etc.) to prevent injection.
        Only alphanumeric characters and underscores are allowed.

        Raises:
            ValueError: If the identifier contains disallowed characters.
        """
        if not identifier:
            raise ValueError("Identifier cannot be empty.")

        if not re.match(r"^[A-Za-z0-9_]+$", identifier):
            raise ValueError(
                f"Invalid identifier '{identifier}'. "
                "Identifiers may only contain letters, numbers, and underscores."
            )

        return identifier


def validate_user_question(question: str) -> Tuple[bool, str]:
    """
    Validates a user-supplied question for the AI Q&A feature.

    Returns:
        (True, "") if the question is valid.
        (False, error_message) if the question fails validation.
    """
    if not question or not question.strip():
        return False, "Question cannot be empty. Please enter a question."

    stripped = question.strip()

    min_length = 5
    max_length = 500

    if len(stripped) < min_length:
        return False, (
            f"Question is too short (minimum {min_length} characters). "
            "Please provide a more specific question."
        )

    if len(stripped) > max_length:
        return False, (
            f"Question is too long (maximum {max_length} characters). "
            f"Please shorten your question. Current length: {len(stripped)} characters."
        )

    return True, ""
