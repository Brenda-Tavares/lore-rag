import re

class SecurityRedactor:
    """
    Utility to sanitize sensitive data before vectorization.
    Follows OWASP guidelines for Sensitive Information Disclosure.
    """

    # Regex patterns for common secrets
    PATTERNS = {
        "aws_access_key": r"AKIA[0-9A-Z]{16}",
        "aws_secret_key": r"(?i)aws(.{0,20})?['\"][0-9a-zA-Z\/+]{40}['\"]",
        "bearer_token": r"Bearer\s+[a-zA-Z0-9\-._~+/]+",
        "ipv4_address": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
        "email_address": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "password_assignment": r"(?i)(password|passwd|pwd|secret)\s*[:=]\s*['\"]?[^\s'\"]+['\"]?",
        "private_key": r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----[\s\S]*?-----END (RSA|EC|OPENSSH) PRIVATE KEY-----",
    }

    @classmethod
    def redact_text(cls, text: str) -> str:
        """
        Replaces sensitive patterns with safe placeholders.
        """
        sanitized_text = text
        for key, pattern in cls.PATTERNS.items():
            sanitized_text = re.sub(pattern, f"[REDACTED_{key.upper()}]", sanitized_text)
        return sanitized_text

    @classmethod
    def validate_file_type(cls, mime_type: str) -> bool:
        """
        Whitelist allowed MIME types to prevent malicious uploads.
        """
        ALLOWED_TYPES = ["text/plain", "text/markdown", "application/pdf"]
        return mime_type in ALLOWED_TYPES