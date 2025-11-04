"""Validation utilities for data integrity."""
import re
from typing import Optional

from exceptions import ValidationError
from constants import MAX_CONTAINER_NUMBER_LENGTH, MIN_CONTAINER_NUMBER_LENGTH


def validate_container_number(container_number: str) -> str:
    """
    Validate ISO 6346 container number format.
    
    Format: 4 letters (owner code) + 6 digits (serial number) + 1 check digit
    Example: TCLU1234567
    
    Args:
        container_number: Container number to validate
        
    Returns:
        Validated and normalized container number (uppercase, no spaces)
        
    Raises:
        ValidationError: If container number is invalid
    """
    if not container_number:
        raise ValidationError("Container number cannot be empty")
    
    # Normalize: uppercase and remove spaces
    normalized = container_number.upper().replace(" ", "").replace("-", "")
    
    # Check length
    if len(normalized) != MIN_CONTAINER_NUMBER_LENGTH:
        raise ValidationError(
            f"Container number must be {MIN_CONTAINER_NUMBER_LENGTH} characters, "
            f"got {len(normalized)}: {container_number}"
        )
    
    # Check format: 4 letters + 7 digits
    pattern = r'^[A-Z]{4}\d{7}$'
    if not re.match(pattern, normalized):
        raise ValidationError(
            f"Container number must match format AAAA1234567: {container_number}"
        )
    
    # Validate check digit (ISO 6346 algorithm)
    owner_code = normalized[:4]
    serial = normalized[4:10]
    check_digit = int(normalized[10])
    
    # Calculate expected check digit
    calculated = _calculate_container_check_digit(owner_code + serial)
    
    if calculated != check_digit:
        raise ValidationError(
            f"Invalid check digit for {container_number}. "
            f"Expected {calculated}, got {check_digit}"
        )
    
    return normalized


def _calculate_container_check_digit(container_base: str) -> int:
    """
    Calculate ISO 6346 check digit for container number.
    
    Args:
        container_base: First 10 characters (4 letters + 6 digits)
        
    Returns:
        Check digit (0-9)
    """
    # Letter to number mapping (A=10, B=12, C=13, etc.)
    letter_values = {
        'A': 10, 'B': 12, 'C': 13, 'D': 14, 'E': 15, 'F': 16, 'G': 17,
        'H': 18, 'I': 19, 'J': 20, 'K': 21, 'L': 23, 'M': 24, 'N': 25,
        'O': 26, 'P': 27, 'Q': 28, 'R': 29, 'S': 30, 'T': 31, 'U': 32,
        'V': 34, 'W': 35, 'X': 36, 'Y': 37, 'Z': 38
    }
    
    total = 0
    for i, char in enumerate(container_base):
        if char.isalpha():
            value = letter_values[char]
        else:
            value = int(char)
        
        # Multiply by position weight (2^i)
        total += value * (2 ** i)
    
    # Check digit is remainder mod 11, mod 10
    check_digit = (total % 11) % 10
    
    return check_digit


def validate_email(email: str) -> str:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Validated email (lowercase, trimmed)
        
    Raises:
        ValidationError: If email is invalid
    """
    if not email:
        raise ValidationError("Email cannot be empty")
    
    # Normalize
    normalized = email.lower().strip()
    
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, normalized):
        raise ValidationError(f"Invalid email format: {email}")
    
    return normalized


def validate_phone_number(phone: str) -> str:
    """
    Validate and normalize US phone number.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        Normalized phone number (digits only, 10 digits)
        
    Raises:
        ValidationError: If phone number is invalid
    """
    if not phone:
        raise ValidationError("Phone number cannot be empty")
    
    # Extract digits only
    digits = re.sub(r'\D', '', phone)
    
    # Check length (10 digits for US)
    if len(digits) == 11 and digits[0] == '1':
        # Strip leading 1
        digits = digits[1:]
    
    if len(digits) != 10:
        raise ValidationError(
            f"Phone number must be 10 digits, got {len(digits)}: {phone}"
        )
    
    return digits


def validate_positive_amount(
    amount: float,
    field_name: str = "Amount",
    allow_zero: bool = False
) -> float:
    """
    Validate that amount is positive (and optionally non-zero).
    
    Args:
        amount: Amount to validate
        field_name: Name of field for error message
        allow_zero: Whether to allow zero values
        
    Returns:
        Validated amount
        
    Raises:
        ValidationError: If amount is invalid
    """
    if amount is None:
        raise ValidationError(f"{field_name} cannot be None")
    
    if not isinstance(amount, (int, float)):
        raise ValidationError(f"{field_name} must be a number, got {type(amount)}")
    
    if allow_zero:
        if amount < 0:
            raise ValidationError(f"{field_name} must be non-negative, got {amount}")
    else:
        if amount <= 0:
            raise ValidationError(f"{field_name} must be positive, got {amount}")
    
    return float(amount)


def validate_rate(rate: float, rate_type: str = "Rate") -> float:
    """
    Validate billing rate.
    
    Args:
        rate: Rate to validate (should be positive)
        rate_type: Type of rate for error message
        
    Returns:
        Validated rate
        
    Raises:
        ValidationError: If rate is invalid
    """
    return validate_positive_amount(rate, rate_type, allow_zero=False)


def validate_days(days: int, field_name: str = "Days") -> int:
    """
    Validate number of days.
    
    Args:
        days: Number of days to validate
        field_name: Name of field for error message
        
    Returns:
        Validated days
        
    Raises:
        ValidationError: If days is invalid
    """
    if not isinstance(days, int):
        raise ValidationError(f"{field_name} must be an integer, got {type(days)}")
    
    if days < 0:
        raise ValidationError(f"{field_name} must be non-negative, got {days}")
    
    return days


def validate_required_string(
    value: Optional[str],
    field_name: str,
    max_length: Optional[int] = None
) -> str:
    """
    Validate required string field.
    
    Args:
        value: String value to validate
        field_name: Name of field for error message
        max_length: Maximum allowed length
        
    Returns:
        Validated string (stripped)
        
    Raises:
        ValidationError: If string is invalid
    """
    if not value:
        raise ValidationError(f"{field_name} is required")
    
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string, got {type(value)}")
    
    stripped = value.strip()
    
    if not stripped:
        raise ValidationError(f"{field_name} cannot be empty or whitespace")
    
    if max_length and len(stripped) > max_length:
        raise ValidationError(
            f"{field_name} must be at most {max_length} characters, "
            f"got {len(stripped)}"
        )
    
    return stripped

