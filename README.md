# AI Billing Agent for Intermodal Trucking

A production-ready AI-powered billing automation system for drayage and intermodal trucking companies. Automatically tracks containers, calculates charges (per diem, demurrage, detention), and generates invoices.

## Features

- 🚛 **McLeod LoadMaster Integration** - Automatic load data synchronization
- 📦 **Terminal49 Container Tracking** - Real-time container milestone tracking
- 💰 **Intelligent Billing Engine** - Automatic calculation of per diem, demurrage, and detention
- 📊 **QuickBooks Integration** - Automated invoice generation and payment tracking
- 🔔 **Proactive Alerts** - Prevent charges before they start
- 🤖 **AI-Powered Agent** - Natural language interface and autonomous decision-making

## Architecture

```
McLeod LoadMaster API ←→ AI Agent ←→ Terminal49 API
                           ↓
                      QuickBooks API
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose (optional)




### Docker Deployment

```bash
docker-compose up -d
```

## Project Structure

```
billing-agent/
├── agents/
│   ├── tracking_agent.py      # Container tracking automation
│   ├── billing_agent.py        # Charge calculation & invoicing
│   └── dispute_agent.py        # Payment dispute resolution
├── integrations/
│   ├── mcleod_client.py        # McLeod API client
│   ├── terminal49_client.py    # Terminal49 API client
│   └── quickbooks_client.py    # QuickBooks API client
├── services/
│   ├── charge_calculator.py    # Billing calculation logic
│   ├── invoice_generator.py    # Invoice creation
│   └── alert_service.py        # Notification system
├── models/
│   ├── database.py             # SQLAlchemy setup
│   ├── load.py                 # Load model
│   ├── container.py            # Container model
│   ├── charge.py               # Charge model
│   ├── invoice.py              # Invoice model
│   ├── customer.py             # Customer model
│   └── alert.py                # Alert model
├── api/
│   ├── main.py                 # FastAPI application
│   ├── routes/                 # API endpoints
│   └── webhooks/               # Webhook handlers
├── tasks/
│   └── celery_tasks.py         # Background jobs
├── config.py                   # Configuration
├── requirements.txt
└── docker-compose.yml
```

## API Endpoints

### Core Endpoints
- `GET /api/loads` - List all loads
- `GET /api/loads/{load_id}` - Get load details
- `GET /api/containers/{container_number}` - Get container tracking info
- `GET /api/invoices` - List invoices
- `POST /api/invoices/{invoice_id}/send` - Send invoice to customer

### Webhook Endpoints
- `POST /webhooks/terminal49` - Terminal49 container updates
- `POST /webhooks/quickbooks` - QuickBooks payment notifications

### AI Agent Endpoints
- `POST /api/agent/query` - Natural language queries
- `POST /api/agent/analyze` - Analyze container for potential charges
- `POST /api/agent/draft-dispute-response` - Generate dispute email

## Key Workflows

### 1. New Load Processing
1. System polls McLeod API every 15 minutes
2. Detects new drayage loads with container numbers
3. Automatically starts tracking via Terminal49
4. Calculates last free day and creates alerts

### 2. Per Diem Alert
1. Terminal49 sends webhook when container discharged
2. Agent calculates last free day based on free time
3. Alert sent 24h before deadline
4. If not returned on time, charges calculated automatically

### 3. Invoice Generation
1. Load delivered, all charges calculated
2. AI agent creates invoice in QuickBooks
3. Attaches proof documents (BOL, gate tickets)
4. Tracks payment status
5. Handles disputes automatically

## Configuration

### Customer Rate Contracts

Configure customer-specific rates in the database:

```python
customer = Customer(
    name="ABC Logistics",
    per_diem_rate=85.00,
    demurrage_rate=125.00,
    detention_rate=100.00,
    free_days=4
)
```

### Alert Thresholds

Customize alert timing in `config.py`:

```python
alert_hours_before_charge = 24  # Alert 24h before per diem starts
urgent_alert_hours = 6           # Urgent alert if 6h remaining
```

## Monitoring

- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics`
- **Flower UI**: http://localhost:5555 (Celery monitoring)
- **Sentry**: Error tracking (configure SENTRY_DSN)

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_billing_agent.py
```

## Success Metrics

- ✅ 95%+ containers tracked automatically
- ✅ 80%+ on-time returns (avoiding per diem)
- ✅ $50K+ annual savings per customer
- ✅ 90%+ invoices generated without human intervention
- ✅ 5+ hours/week saved per dispatcher

## API Documentation

Once running, access interactive API docs at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Support

For issues and questions, please contact your system administrator.

## License

Proprietary - All rights reserved

