# AI Billing Agent - Quick Start Guide

## Overview

This is a production-ready AI-powered billing automation system for intermodal trucking companies. It automatically tracks containers, calculates charges (per diem, demurrage, detention), and generates invoices.

## Features Implemented

✅ **McLeod LoadMaster Integration** - Automatic load synchronization every 15 minutes  
✅ **Terminal49 Container Tracking** - Real-time container milestone tracking with webhooks  
✅ **Intelligent Billing Engine** - Automatic per diem, demurrage, and detention calculation  
✅ **QuickBooks Integration** - Automated invoice generation and payment tracking  
✅ **Proactive Alerts** - Email/SMS notifications before charges start  
✅ **AI-Powered Agents** - Claude-powered natural language interface and decision-making  
✅ **Background Jobs** - Celery-based periodic tasks and async processing  
✅ **Production Ready** - Docker deployment, error handling, logging, and monitoring

## Architecture

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
│ McLeod          │◄─────►│   AI Billing     │◄─────►│ Terminal49      │
│ LoadMaster API  │       │   Agent          │       │ Container API   │
└─────────────────┘       └────────┬─────────┘       └─────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │ QuickBooks      │
                          │ Online API      │
                          └─────────────────┘
```

## Quick Start

### Option 1: Docker (Recommended)

1. **Clone and Setup**
   ```bash
   cd /Users/alex/arnata/billing-agent
   cp .env.example .env
   # Edit .env with your API credentials
   ```

2. **Start All Services**
   ```bash
   docker-compose up -d
   ```

3. **View Logs**
   ```bash
   docker-compose logs -f
   ```

4. **Access Services**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Flower (Celery): http://localhost:5555

### Option 2: Local Development

1. **Run Setup Script**
   ```bash
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```

2. **Activate Virtual Environment**
   ```bash
   source venv/bin/activate
   ```

3. **Configure Environment**
   ```bash
   # Edit .env with your credentials
   nano .env
   ```

4. **Initialize Database**
   ```bash
   python scripts/init_db.py
   ```

5. **Start Services**
   
   Terminal 1 - API Server:
   ```bash
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```
   
   Terminal 2 - Celery Worker:
   ```bash
   celery -A tasks.celery_app worker --loglevel=info
   ```
   
   Terminal 3 - Celery Beat (Scheduler):
   ```bash
   celery -A tasks.celery_app beat --loglevel=info
   ```
   
   Terminal 4 - Flower (Optional):
   ```bash
   celery -A tasks.celery_app flower --port=5555
   ```

## Configuration

### Required API Credentials

Edit `.env` and add your API credentials:

```bash
# McLeod LoadMaster
MCLEOD_API_URL=https://api.mcleodloadmaster.com
MCLEOD_API_TOKEN=your_token_here
MCLEOD_COMPANY_ID=your_company_id

# Terminal49
TERMINAL49_API_KEY=your_key_here
TERMINAL49_WEBHOOK_SECRET=your_secret_here

# QuickBooks
QUICKBOOKS_CLIENT_ID=your_client_id
QUICKBOOKS_CLIENT_SECRET=your_secret
QUICKBOOKS_REALM_ID=your_realm_id
QUICKBOOKS_ENVIRONMENT=sandbox  # or production

# Anthropic Claude
ANTHROPIC_API_KEY=your_anthropic_key

# Optional: Email/SMS
SENDGRID_API_KEY=your_sendgrid_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
```

## Core Workflows

### 1. Load Sync → Container Tracking

```
Every 15 minutes:
1. System polls McLeod API for new drayage loads
2. For each new load with container number:
   - Creates load record in database
   - Starts tracking via Terminal49 API
   - Calculates last free day
   - Sets up alert schedule
```

### 2. Container Monitoring → Alerts

```
Every hour:
1. Check all active containers
2. Calculate days until per diem starts
3. Send alerts 24h before charges begin
4. Monitor containers already accruing charges
```

### 3. Load Delivery → Invoice Generation

```
Every 4 hours:
1. Find delivered loads
2. Calculate all charges (freight + per diem + demurrage + detention)
3. AI validates charges for accuracy
4. Generate invoice in QuickBooks
5. Send invoice to customer
6. Track payment status
```

### 4. Payment Tracking → Dispute Handling

```
Daily at 9 AM:
1. Check payment status in QuickBooks
2. Detect short payments (disputes)
3. AI drafts professional response email
4. Flag for human review if needed
```

## API Endpoints

### Loads
- `GET /api/loads` - List all loads
- `GET /api/loads/{load_id}` - Get load details

### Containers
- `GET /api/containers` - List all containers
- `GET /api/containers/{container_number}` - Get container tracking info

### Invoices
- `GET /api/invoices` - List invoices
- `GET /api/invoices/{invoice_id}` - Get invoice details
- `POST /api/invoices/{invoice_id}/send` - Send invoice to customer

### AI Agent
- `POST /api/agent/query` - Natural language queries ("What's the status of container ABC123?")
- `POST /api/agent/analyze` - Analyze container for charge risk
- `POST /api/agent/draft-dispute-response` - Generate dispute email

### Webhooks
- `POST /webhooks/terminal49` - Terminal49 container updates (auto-registered)
- `POST /webhooks/quickbooks` - QuickBooks payment notifications

## Background Tasks

Automated periodic tasks:

- **Every 15 min**: Sync new loads from McLeod
- **Every 30 min**: Update container statuses from Terminal49
- **Every hour**: Check and send alerts
- **Every 4 hours**: Process pending invoices
- **Daily at 9 AM**: Check payment status
- **Daily at 5 PM**: Generate daily report

## AI Agent Capabilities

The system includes three specialized AI agents powered by Claude:

### 1. Tracking Agent
- Analyzes container risk for potential charges
- Decides if pre-pull is cost-effective
- Monitors containers and generates alerts

### 2. Billing Agent
- Validates calculated charges for accuracy
- Analyzes billing patterns and trends
- Recommends rate optimizations
- Generates billing metrics

### 3. Dispute Agent
- Drafts professional dispute response emails
- Analyzes dispute validity
- Suggests resolutions
- Generates collections emails

## Testing

Run the test suite:

```bash
pytest tests/ -v --cov=.
```

Run specific tests:

```bash
pytest tests/test_charge_calculator.py -v
```

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Celery Monitoring (Flower)
Visit http://localhost:5555 to see:
- Active workers
- Task queue status
- Task execution history
- Task success/failure rates

### Logs
```bash
# Docker
docker-compose logs -f api
docker-compose logs -f celery_worker

# Local
tail -f logs/api.log
tail -f logs/celery.log
```

## Common Operations

### Add a New Customer
```python
from models import Customer
from models.database import SessionLocal

db = SessionLocal()
customer = Customer(
    mcleod_customer_id="CUST123",
    name="ABC Logistics",
    email="billing@abclogistics.com",
    per_diem_rate=85.0,
    demurrage_rate=125.0,
    detention_rate=100.0,
    free_days=4,
    auto_invoice=True,
    send_alerts=True,
)
db.add(customer)
db.commit()
```

### Manually Trigger Load Sync
```bash
# Using Celery
celery -A tasks.celery_app call tasks.celery_tasks.sync_mcleod_loads
```

### Check Container Status
```bash
curl http://localhost:8000/api/containers/MAEU1234567
```

### Generate Invoice for Load
```bash
curl -X POST http://localhost:8000/api/invoices/process-load/123
```

## Database Migrations

Create new migration:
```bash
alembic revision --autogenerate -m "Add new field"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback:
```bash
alembic downgrade -1
```

## Troubleshooting

### Issue: Database connection error
**Solution**: Check `DATABASE_URL` in `.env` and ensure PostgreSQL is running

### Issue: API credentials invalid
**Solution**: Verify all API keys in `.env` are correct and have proper permissions

### Issue: Celery tasks not running
**Solution**: 
1. Check Redis is running: `redis-cli ping`
2. Check Celery worker logs: `docker-compose logs celery_worker`
3. Verify `REDIS_URL` in `.env`

### Issue: No containers being tracked
**Solution**: 
1. Check McLeod API sync logs
2. Verify Terminal49 API key is valid
3. Ensure container numbers are in loads

## Production Deployment

### Security Checklist
- [ ] Change all default passwords and secrets
- [ ] Use strong `SECRET_KEY` in production
- [ ] Enable HTTPS/TLS
- [ ] Restrict CORS origins
- [ ] Set up firewall rules
- [ ] Enable database encryption
- [ ] Configure Sentry for error tracking

### Scaling
- Increase Celery workers: `--concurrency=8`
- Add more API instances behind load balancer
- Use PostgreSQL connection pooling
- Enable Redis persistence for task reliability

### Monitoring
- Set up Sentry DSN for error tracking
- Configure log aggregation (ELK, Datadog, etc.)
- Monitor API response times
- Track Celery task success rates
- Set up alerts for critical failures

## Success Metrics

Track these KPIs:

- **Container Tracking Rate**: Target 95%+ automatically tracked
- **On-Time Returns**: Target 80%+ returns before per diem
- **Invoice Automation**: Target 90%+ auto-generated without review
- **Cost Savings**: Target $50K+ annual savings per customer
- **Time Savings**: Target 5+ hours/week saved per dispatcher

## Support

For issues or questions:
1. Check logs for error details
2. Review API documentation at `/docs`
3. Check GitHub issues
4. Contact system administrator

## License

Proprietary - All rights reserved

---

**Built with**: Python 3.11, FastAPI, SQLAlchemy, Celery, LangChain, Claude AI, Docker

**Version**: 1.0.0

