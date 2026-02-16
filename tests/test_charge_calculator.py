"""Tests for charge calculator."""
import pytest
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models import Customer, Load, Container
from services.charge_calculator import ChargeCalculator


@pytest.fixture
def sample_customer(db_session):
    """Create sample customer."""
    customer = Customer(
        mcleod_customer_id="TEST001",
        name="Test Customer",
        per_diem_rate=100.0,
        demurrage_rate=150.0,
        detention_rate=125.0,
        free_days=3,
    )
    db_session.add(customer)
    db_session.commit()
    return customer


@pytest.fixture
def sample_container(db_session, sample_customer):
    """Create sample container with load."""
    load = Load(
        mcleod_order_id="ORD001",
        mcleod_load_number="LOAD001",
        customer_id=sample_customer.id,
        container_number="TEST1234567",
        base_freight_rate=500.0,
    )
    db_session.add(load)
    db_session.flush()
    
    container = Container(
        container_number="TEST1234567",
        load_id=load.id,
        vessel_discharged=datetime.utcnow() - timedelta(days=5),
        picked_up=datetime.utcnow() - timedelta(days=3),
    )
    db_session.add(container)
    db_session.commit()
    return container


def test_calculate_per_diem(db_session, sample_container, sample_customer):
    """Test per diem calculation."""
    calculator = ChargeCalculator(db_session)
    
    days, amount = calculator.calculate_per_diem(
        sample_container,
        sample_customer,
        as_of_date=date.today()
    )
    
    # Should have some per diem charges
    assert days >= 0
    assert amount >= 0
    assert amount == days * sample_customer.per_diem_rate


def test_calculate_last_free_day(db_session, sample_container, sample_customer):
    """Test last free day calculation."""
    calculator = ChargeCalculator(db_session)
    
    last_free_day = calculator.calculate_last_free_day(
        sample_container,
        sample_customer
    )
    
    assert last_free_day is not None
    assert isinstance(last_free_day, date)


def test_calculate_all_charges(db_session, sample_customer):
    """Test all charges calculation."""
    load = Load(
        mcleod_order_id="ORD002",
        mcleod_load_number="LOAD002",
        customer_id=sample_customer.id,
        container_number="TEST9999999",
        base_freight_rate=750.0,
    )
    db_session.add(load)
    db_session.flush()
    
    container = Container(
        container_number="TEST9999999",
        load_id=load.id,
        vessel_discharged=datetime.utcnow() - timedelta(days=10),
        picked_up=datetime.utcnow() - timedelta(days=8),
    )
    db_session.add(container)
    db_session.commit()
    
    load.container = container
    
    calculator = ChargeCalculator(db_session)
    charges = calculator.calculate_all_charges(load)
    
    # Should have at least base freight
    assert len(charges) >= 1
    
    # Check base freight exists
    freight_charges = [c for c in charges if c.charge_type.value == "base_freight"]
    assert len(freight_charges) == 1
    assert freight_charges[0].amount == 750.0

