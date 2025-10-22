#!/usr/bin/env python
"""Initialize database with sample data."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import init_db, Customer
from models.database import SessionLocal


def create_sample_customer():
    """Create a sample customer."""
    db = SessionLocal()
    try:
        # Check if customer exists
        existing = db.query(Customer).filter(Customer.name == "Sample Customer").first()
        if existing:
            print("Sample customer already exists")
            return
        
        customer = Customer(
            mcleod_customer_id="SAMPLE001",
            name="Sample Customer",
            email="customer@example.com",
            phone="+1-555-0100",
            per_diem_rate=100.0,
            demurrage_rate=150.0,
            detention_rate=125.0,
            chassis_split_fee=50.0,
            pre_pull_fee=75.0,
            free_days=3,
            per_diem_free_days=3,
            demurrage_free_days=2,
            auto_invoice=True,
            send_alerts=True,
            alert_email="alerts@example.com",
            payment_terms="Net 30",
            active=True,
        )
        
        db.add(customer)
        db.commit()
        
        print(f"✅ Created sample customer: {customer.name}")
        
    except Exception as e:
        print(f"❌ Error creating sample customer: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """Initialize database."""
    print("🗄️  Initializing database...")
    
    try:
        init_db()
        print("✅ Database tables created")
        
        create_sample_customer()
        
        print("✅ Database initialization complete!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

