"""Custom exceptions for the billing agent system."""


class BillingAgentException(Exception):
    pass


class IntegrationError(BillingAgentException):
    pass


class McLeodAPIError(IntegrationError):
    pass


class Terminal49APIError(IntegrationError):
    pass


class QuickBooksAPIError(IntegrationError):
    pass


class ChargeCalculationError(BillingAgentException):
    pass


class InvoiceGenerationError(BillingAgentException):
    pass


class ValidationError(BillingAgentException):
    pass


class ContainerNotFoundError(BillingAgentException):
    pass


class LoadNotFoundError(BillingAgentException):
    pass


class CustomerNotFoundError(BillingAgentException):
    pass


class InvoiceNotFoundError(BillingAgentException):
    pass


class ConfigurationError(BillingAgentException):
    pass


class DatabaseError(BillingAgentException):
    pass
