#!/usr/bin/env python3

import os
import sys
from datetime import datetime
from decimal import Decimal
import uuid

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Seller, Customer, Product, Invoice, InvoiceItem
from werkzeug.security import generate_password_hash

def create_tables():
    print("Creating database tables...")
    with app.app_context():
        db.create_all()
        print("Tables created successfully!")

def insert_sample_data():
    print("Inserting sample data...")
    
    with app.app_context():
        if Seller.query.first():
            print("Sample data already exists. Skipping...")
            return

        seller1 = Seller(
            s_id='S001',
            s_name='John Seller',
            s_email='john.seller@example.com',
            s_address='123 Business Street, City, State 12345',
            s_phone='123-456-7890'
        )
        seller1.set_password('password')
        
        seller2 = Seller(
            s_id='S002',
            s_name='Jane Business Owner',
            s_email='jane.business@example.com',
            s_address='456 Commerce Ave, City, State 12345',
            s_phone='098-765-4321'
        )
        seller2.set_password('password')
        
        db.session.add(seller1)
        db.session.add(seller2)
        
        customer1 = Customer(
            c_id='C001',
            c_name='Jane Customer',
            c_email='customer@example.com',
            c_phone_no='555-123-4567',
            c_address='789 Customer Lane, City, State 12345'
        )
        customer1.set_password('password')
        
        customer2 = Customer(
            c_id='C002',
            c_name='John Doe',
            c_email='john@example.com',
            c_phone_no='555-987-6543',
            c_address='321 Client Street, City, State 12345'
        )
        customer2.set_password('password')
        
        customer3 = Customer(
            c_id='C003',
            c_name='Bob Johnson',
            c_email='bob@example.com',
            c_phone_no='555-456-7890',
            c_address='654 Buyer Blvd, City, State 12345'
        )
        customer3.set_password('password')
        
        db.session.add(customer1)
        db.session.add(customer2)
        db.session.add(customer3)
        
        product1_id = uuid.uuid4().hex
        product2_id = uuid.uuid4().hex
        product3_id = uuid.uuid4().hex
        product4_id = uuid.uuid4().hex
        product5_id = uuid.uuid4().hex

        products = [
            Product(
                p_id=product1_id,
                p_name='Wireless Headphones',
                p_price=Decimal('99.99'),
                p_description='High-quality wireless headphones with noise cancellation',
                p_stock=25,
                s_id='S001'
            ),
            Product(
                p_id=product2_id,
                p_name='Smart Watch',
                p_price=Decimal('199.99'),
                p_description='Fitness tracking smart watch with heart rate monitor',
                p_stock=15,
                s_id='S001'
            ),
            Product(
                p_id=product3_id,
                p_name='Bluetooth Speaker',
                p_price=Decimal('79.99'),
                p_description='Portable Bluetooth speaker with 360-degree sound',
                p_stock=30,
                s_id='S001'
            ),
            Product(
                p_id=product4_id,
                p_name='Laptop Stand',
                p_price=Decimal('49.99'),
                p_description='Adjustable aluminum laptop stand for ergonomic work',
                p_stock=20,
                s_id='S001'
            ),
            Product(
                p_id=product5_id,
                p_name='Wireless Mouse',
                p_price=Decimal('29.99'),
                p_description='Ergonomic wireless mouse with precision tracking',
                p_stock=50,
                s_id='S001'
            )
        ]
        
        for product in products:
            db.session.add(product)
        
        invoice1 = Invoice(
            invoice_no='INV-001',
            invoice_datetime=datetime(2024, 1, 15),
            status='paid',
            tax=Decimal('24.00'),
            amount=Decimal('299.97'),
            s_id='S001',
            c_id='C001'
        )
        db.session.add(invoice1)
        
        invoice2 = Invoice(
            invoice_no='INV-002',
            invoice_datetime=datetime(2024, 1, 14),
            status='pending',
            tax=Decimal('14.40'),
            amount=Decimal('179.98'),
            s_id='S001',
            c_id='C001'
        )
        db.session.add(invoice2)
        
        invoice3 = Invoice(
            invoice_no='INV-003',
            invoice_datetime=datetime(2024, 1, 13),
            status='overdue',
            tax=Decimal('12.80'),
            amount=Decimal('159.98'),
            s_id='S001',
            c_id='C002'
        )
        db.session.add(invoice3)
        
        invoice_items = [
            # Invoice 1 items
            InvoiceItem(
                invoice_no='INV-001',
                p_id='P001',
                item_quantity=1,
                discount=Decimal('0.00')
            ),
            InvoiceItem(
                invoice_no='INV-001',
                p_id='P002',
                item_quantity=1,
                discount=Decimal('0.00')
            ),
            # Invoice 2 items
            InvoiceItem(
                invoice_no='INV-002',
                p_id='P003',
                item_quantity=2,
                discount=Decimal('0.00')
            ),
            # Invoice 3 items
            InvoiceItem(
                invoice_no='INV-003',
                p_id='P001',
                item_quantity=1,
                discount=Decimal('0.00')
            ),
            InvoiceItem(
                invoice_no='INV-003',
                p_id='P003',
                item_quantity=1,
                discount=Decimal('0.00')
            )
        ]
        
        for item in invoice_items:
            db.session.add(item)
        
        # Commit all changes
        db.session.commit()
        print("Sample data inserted successfully!")

def main():
    """Main function to initialize database"""
    print("Initializing Invoice Management System Database...")
    print("=" * 50)
    
    try:
        # Create tables
        create_tables()
        
        # Insert sample data
        insert_sample_data()
        
        print("=" * 50)
        print("Database initialization completed successfully!")
        print("\nSample Data Created:")
        print("   - 2 Sellers (S001, S002)")
        print("   - 3 Customers (C001, C002, C003)")
        print("   - 5 Products (P001-P005)")
        print("   - 3 Invoices (INV-001 to INV-003)")
        print("   - 5 Invoice Items")
        print("\nDemo Credentials:")
        print("   Seller 1: john.seller@example.com / password")
        print("   Seller 2: jane.business@example.com / password")
        print("   Customer: customer@example.com / password")
        
    except Exception as e:
        print(f"Error during initialization: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
