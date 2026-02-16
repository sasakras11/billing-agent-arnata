"""Application-wide constants.

Default billing rates (per diem, demurrage, detention, free days) are configured
in config.Settings; use get_settings().get_rate_config() or customer-specific rates.
"""

# Alert timing (in hours)
ALERT_HOURS_BEFORE_CHARGE = 24
URGENT_ALERT_HOURS = 6
CRITICAL_ALERT_HOURS = 2

# Sync intervals (in minutes)
MCLEOD_SYNC_INTERVAL = 15
TERMINAL49_SYNC_INTERVAL = 30
ALERT_CHECK_INTERVAL = 60
INVOICE_SYNC_INTERVAL = 120

# Container size constants
CONTAINER_20FT = "20"
CONTAINER_40FT = "40"
CONTAINER_40FT_HC = "40HC"
CONTAINER_45FT = "45"

CONTAINER_SIZES = [
    CONTAINER_20FT,
    CONTAINER_40FT,
    CONTAINER_40FT_HC,
    CONTAINER_45FT,
]

# Container states
CONTAINER_STATE_EMPTY = "empty"
CONTAINER_STATE_FULL = "full"
CONTAINER_STATE_DISCHARGED = "discharged"
CONTAINER_STATE_PICKED_UP = "picked_up"
CONTAINER_STATE_DELIVERED = "delivered"
CONTAINER_STATE_RETURNED = "returned"

# Invoice statuses
INVOICE_DRAFT = "draft"
INVOICE_PENDING = "pending"
INVOICE_SENT = "sent"
INVOICE_PAID = "paid"
INVOICE_OVERDUE = "overdue"
INVOICE_DISPUTED = "disputed"
INVOICE_VOIDED = "voided"

# Charge types
CHARGE_BASE_FREIGHT = "base_freight"
CHARGE_PER_DIEM = "per_diem"
CHARGE_DEMURRAGE = "demurrage"
CHARGE_DETENTION = "detention"
CHARGE_FUEL_SURCHARGE = "fuel_surcharge"
CHARGE_CHASSIS_SPLIT = "chassis_split"
CHARGE_OVERWEIGHT = "overweight"
CHARGE_PRE_PULL = "pre_pull"
CHARGE_STORAGE = "storage"
CHARGE_OTHER = "other"

# Alert types
ALERT_PER_DIEM_WARNING = "per_diem_warning"
ALERT_DEMURRAGE_WARNING = "demurrage_warning"
ALERT_DETENTION_WARNING = "detention_warning"
ALERT_INVOICE_OVERDUE = "invoice_overdue"
ALERT_PAYMENT_RECEIVED = "payment_received"
ALERT_CONTAINER_STATUS = "container_status"
ALERT_INTEGRATION_ERROR = "integration_error"

# API timeouts (in seconds)
API_TIMEOUT_DEFAULT = 30
API_TIMEOUT_LONG = 60
API_TIMEOUT_SHORT = 10

# Retry configuration
MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_FACTOR = 2
RETRY_INITIAL_DELAY = 1  # seconds

# Date formats
DATE_FORMAT_ISO = "%Y-%m-%d"
DATETIME_FORMAT_ISO = "%Y-%m-%dT%H:%M:%S"
DATE_FORMAT_DISPLAY = "%m/%d/%Y"
DATETIME_FORMAT_DISPLAY = "%m/%d/%Y %I:%M %p"

# Validation limits
MAX_CONTAINER_NUMBER_LENGTH = 11
MIN_CONTAINER_NUMBER_LENGTH = 11
MAX_LOAD_REFERENCE_LENGTH = 50
MAX_CUSTOMER_NAME_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 500

# AI confidence thresholds
AI_CONFIDENCE_HIGH = 0.9
AI_CONFIDENCE_MEDIUM = 0.7
AI_CONFIDENCE_LOW = 0.5

# Pagination defaults
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

# Email templates
EMAIL_INVOICE_SUBJECT = "Invoice #{invoice_number} - {customer_name}"
EMAIL_ALERT_SUBJECT = "Container Alert: {container_number}"
EMAIL_DISPUTE_SUBJECT = "Re: Invoice #{invoice_number} Dispute"

# Webhook event types
WEBHOOK_CONTAINER_DISCHARGED = "container.transport.vessel_discharged"
WEBHOOK_CONTAINER_AVAILABLE = "container.transport.available_for_pickup"
WEBHOOK_CONTAINER_PICKED_UP = "container.transport.picked_up_full"
WEBHOOK_CONTAINER_DELIVERED = "container.transport.delivered_full"
WEBHOOK_CONTAINER_RETURNED = "container.transport.returned_empty"
WEBHOOK_INVOICE_PAID = "invoice.paid"
WEBHOOK_PAYMENT_RECEIVED = "payment.received"

