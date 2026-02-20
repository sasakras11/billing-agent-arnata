"""Validation utilities for data integrity."""
import re
from datetime import date
from typing import Optional

from exceptions import ValidationError
from constants import MAX_CONTAINER_NUMBER_LENGTH, MIN_CONTAINER_NUMBER_LENGTH


def validate_container_number(container_number: str) -> str:
    """Validate ISO 6346 container number format (AAAA1234567)."""
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
    """Calculate ISO 6346 check digit for container number (first 10 chars)."""
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
    check_digit = (total % 11) % 10
    
    return check_digit


def validate_email(email: str) -> str:
    """Validate email address format."""
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
    """Validate and normalize US phone number (10 digits)."""
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


def validate_positive_amount(amount: float, field_name: str = "Amount", allow_zero: bool = False) -> float:
    """Validate that amount is positive (and optionally non-zero)."""
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
    """Validate billing rate."""
    return validate_positive_amount(rate, rate_type, allow_zero=False)


def validate_days(days: int, field_name: str = "Days") -> int:
    """Validate number of days."""
    if not isinstance(days, int):
        raise ValidationError(f"{field_name} must be an integer, got {type(days)}")
    
    if days < 0:
        raise ValidationError(f"{field_name} must be non-negative, got {days}")
    
    return days


def validate_required_string(value: Optional[str], field_name: str, max_length: Optional[int] = None, min_length: Optional[int] = None) -> str:
    """Validate required string field."""
    if not value:
        raise ValidationError(f"{field_name} is required")
    
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string, got {type(value)}")
    
    stripped = value.strip()
    
    if not stripped:
        raise ValidationError(f"{field_name} cannot be empty or whitespace")
    
    if min_length and len(stripped) < min_length:
        raise ValidationError(
            f"{field_name} must be at least {min_length} characters, "
            f"got {len(stripped)}"
        )
    
    if max_length and len(stripped) > max_length:
        raise ValidationError(
            f"{field_name} must be at most {max_length} characters, "
            f"got {len(stripped)}"
        )
    
    return stripped


def validate_date_range(start_date: Optional[date], end_date: Optional[date], field_prefix: str = "Date") -> tuple[date, date]:
    """Validate that start date is before or equal to end date."""
    if start_date is None:
        raise ValidationError(f"{field_prefix} start date is required")

    if end_date is None:
        raise ValidationError(f"{field_prefix} end date is required")

    if not isinstance(start_date, date):
        raise ValidationError(f"{field_prefix} start must be a date")

    if not isinstance(end_date, date):
        raise ValidationError(f"{field_prefix} end must be a date")
    
    if start_date > end_date:
        raise ValidationError(
            f"{field_prefix} start ({start_date}) must be before or equal to "
            f"end ({end_date})"
        )
    
    return (start_date, end_date)


def validate_percentage(value: float, field_name: str = "Percentage", allow_over_100: bool = False) -> float:
    """Validate percentage value."""
    if value is None:
        raise ValidationError(f"{field_name} cannot be None")
    
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{field_name} must be a number, got {type(value)}")
    
    if value < 0:
        raise ValidationError(f"{field_name} must be non-negative, got {value}")
    
    if not allow_over_100 and value > 100:
        raise ValidationError(f"{field_name} must be at most 100%, got {value}")
    
    return float(value)

