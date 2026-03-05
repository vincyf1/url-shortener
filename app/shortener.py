"""Short code generation for URL shortener.

Uses secrets.choice() for cryptographically secure random codes.
Includes URL validation utilities.
"""

import re
import secrets
import string
from urllib.parse import urlparse
from typing import Optional

from .database import Database


# Base62 alphabet: digits + lowercase + uppercase
ALPHABET = string.ascii_letters + string.digits  # a-zA-Z0-9
DEFAULT_CODE_LENGTH = 6
MAX_RETRIES = 10
CUSTOM_CODE_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,20}$")

# Allowed URL schemes
ALLOWED_SCHEMES = {"http", "https"}

# Dangerous URL patterns to reject
DANGEROUS_PATTERNS = {"javascript:", "data:", "vbscript:", "file:"}


class InvalidURLError(Exception):
    """Raised when a URL fails validation."""
    pass


class CodeGenerationError(Exception):
    """Raised when a unique short code cannot be generated."""
    pass


class CodeExistsError(Exception):
    """Raised when a custom short code already exists."""
    pass


def validate_url(url: str) -> str:
    """Validate and normalise a URL.

    Args:
        url: The URL to validate.

    Returns:
        The cleaned URL string.

    Raises:
        InvalidURLError: If the URL is invalid.
    """
    if not url or not url.strip():
        raise InvalidURLError("URL cannot be empty.")

    url = url.strip()

    # Check for dangerous schemes
    url_lower = url.lower()
    for pattern in DANGEROUS_PATTERNS:
        if url_lower.startswith(pattern):
            raise InvalidURLError(f"URLs with '{pattern}' scheme are not allowed.")

    # Parse the URL
    parsed = urlparse(url)

    # Check scheme
    if not parsed.scheme:
        raise InvalidURLError(
            "URL must include a scheme (http:// or https://)."
        )
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise InvalidURLError(
            f"Only http:// and https:// URLs are allowed (got '{parsed.scheme}://')."
        )

    # Check for a hostname
    if not parsed.netloc:
        raise InvalidURLError("URL must include a valid hostname.")

    # Reasonable length limit
    if len(url) > 2048:
        raise InvalidURLError("URL is too long (max 2048 characters).")

    return url


def validate_base_url(base_url: str) -> str:
    """Validate and normalise base URL used for generated short links.

    Accepts only absolute http/https URLs.
    """
    if not base_url or not base_url.strip():
        raise InvalidURLError("Base URL cannot be empty.")

    cleaned = base_url.strip().rstrip("/")
    parsed = urlparse(cleaned)

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise InvalidURLError("Base URL must start with http:// or https://.")

    if not parsed.netloc:
        raise InvalidURLError("Base URL must include a hostname.")

    if parsed.query or parsed.fragment:
        raise InvalidURLError("Base URL cannot include query parameters or fragments.")

    if len(cleaned) > 2048:
        raise InvalidURLError("Base URL is too long (max 2048 characters).")

    return cleaned


def validate_custom_code(code: str) -> str:
    """Validate a custom short code.

    Args:
        code: The custom short code to validate.

    Returns:
        The cleaned code.

    Raises:
        ValueError: If the code is invalid.
    """
    code = code.strip()
    if not code:
        raise ValueError("Custom code cannot be empty.")
    if not CUSTOM_CODE_PATTERN.match(code):
        raise ValueError(
            "Custom code must be 1-20 characters: letters, digits, hyphens, underscores."
        )
    return code


def generate_short_code(db: Database, length: int = DEFAULT_CODE_LENGTH) -> str:
    """Generate a unique random short code.

    Uses secrets.choice() for cryptographic randomness.

    Args:
        db: Database instance to check for uniqueness.
        length: Length of the code to generate.

    Returns:
        A unique short code string.

    Raises:
        CodeGenerationError: If unable to generate a unique code after MAX_RETRIES.
    """
    for attempt in range(MAX_RETRIES):
        code = "".join(secrets.choice(ALPHABET) for _ in range(length))
        if not db.code_exists(code):
            return code
    raise CodeGenerationError(
        f"Failed to generate a unique code after {MAX_RETRIES} attempts. "
        "This is extremely unlikely — your database may be very full."
    )


def create_short_url(
    db: Database,
    original_url: str,
    custom_code: Optional[str] = None,
    title: Optional[str] = None,
) -> dict:
    """Create a new shortened URL.

    Args:
        db: Database instance.
        original_url: The URL to shorten.
        custom_code: Optional custom short code.
        title: Optional title/label.

    Returns:
        The created URL record as a dict.

    Raises:
        InvalidURLError: If URL validation fails.
        CodeExistsError: If custom code already exists.
        CodeGenerationError: If random code generation fails.
    """
    # Validate the URL
    original_url = validate_url(original_url)

    # Determine the short code
    if custom_code:
        code = validate_custom_code(custom_code)
        if db.code_exists(code):
            raise CodeExistsError(f"Short code '{code}' is already in use.")
    else:
        code = generate_short_code(db)

    # Create the entry
    return db.add_url(short_code=code, original_url=original_url, title=title)
