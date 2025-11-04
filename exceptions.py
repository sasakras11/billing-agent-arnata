"""Custom exceptions for the billing agent system."""


class BillingAgentException(Exception):
    """Base exception for billing agent errors."""
    pass


class IntegrationError(BillingAgentException):
    """Raised when external API integration fails."""
    pass


class McLeodAPIError(IntegrationError):
    """Raised when McLeod API calls fail."""
    pass


class Terminal49APIError(IntegrationError):
    """Raised when Terminal49 API calls fail."""
    pass


class QuickBooksAPIError(IntegrationError):
    """Raised when QuickBooks API calls fail."""
    pass


class ChargeCalculationError(BillingAgentException):
    """Raised when charge calculation fails."""
    pass


class InvoiceGenerationError(BillingAgentException):
    """Raised when invoice generation fails."""
    pass


class ValidationError(BillingAgentException):
    """Raised when data validation fails."""
    pass


class ContainerNotFoundError(BillingAgentException):
    """Raised when container is not found."""
    pass


class LoadNotFoundError(BillingAgentException):
    """Raised when load is not found."""
    pass


class CustomerNotFoundError(BillingAgentException):
    """Raised when customer is not found."""
    pass


class InvoiceNotFoundError(BillingAgentException):
    """Raised when invoice is not found."""
    pass


class ConfigurationError(BillingAgentException):
    """Raised when configuration is invalid or missing."""
    pass


class DatabaseError(BillingAgentException):
    """Raised when database operations fail."""
    pass

