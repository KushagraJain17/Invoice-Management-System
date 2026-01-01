from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Seller(db.Model):
    __tablename__ = 'sellers'
    
    s_id = db.Column(db.String(10), primary_key=True)  
    s_name = db.Column(db.String(100), nullable=False)  
    s_email = db.Column(db.String(100), nullable=False, unique=True)  
    s_address = db.Column(db.Text, nullable=False)      
    s_phone = db.Column(db.String(10), nullable=False)  
    password = db.Column(db.String(255), nullable=False) 
    
    # Relationships
    products = db.relationship('Product', backref='seller', lazy=True, cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='seller', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password = password
    
    def check_password(self, password):
        return self.password == password
    
    def to_dict(self):
        return {
            'id': self.s_id,
            'name': self.s_name,
            'email': self.s_email,
            'phone': self.s_phone,
            'address': self.s_address,
            'role': 'seller'
        }

class Customer(db.Model):
    __tablename__ = 'customers'
    
    c_id = db.Column(db.String(10), primary_key=True)    
    c_name = db.Column(db.String(100), nullable=False)  
    c_email = db.Column(db.String(100), nullable=False, unique=True)  
    c_phone_no = db.Column(db.String(10), nullable=False)  
    c_address = db.Column(db.Text, nullable=False)       
    s_id = db.Column(db.String(10), db.ForeignKey('sellers.s_id'), nullable=True)  
    
    # Relationships
    invoices = db.relationship('Invoice', backref='customer', lazy=True)
    seller = db.relationship('Seller', backref='customers', lazy=True)
    
    @property
    def id(self):
        return self.c_id
    
    @property
    def name(self):
        return self.c_name
    
    @property
    def email(self):
        return self.c_email
    
    @property
    def phone(self):
        return self.c_phone_no
    
    @property
    def address(self):
        return self.c_address
    
    def to_dict(self):
        return {
            'id': self.c_id,
            'name': self.c_name,
            'email': self.c_email,
            'phone': self.c_phone_no,
            'address': self.c_address,
            'role': 'customer'
        }

class Product(db.Model):
    __tablename__ = 'products'
    
    p_id = db.Column(db.String(10), primary_key=True)    
    p_name = db.Column(db.String(100), nullable=False)  
    p_price = db.Column(db.Numeric(10, 2), nullable=False)  
    p_description = db.Column(db.Text, nullable=True)    
    p_stock = db.Column(db.Integer, nullable=False, default=0)  
    s_id = db.Column(db.String(10), db.ForeignKey('sellers.s_id'), nullable=False)  
    
    # Relationships
    invoice_items = db.relationship('InvoiceItem', backref='product', lazy=True)
    
    @property
    def id(self):
        return self.p_id
    
    @property
    def name(self):
        return self.p_name
    
    @property
    def price(self):
        return self.p_price
    
    @property
    def description(self):
        return self.p_description
    
    @property
    def stock(self):
        return self.p_stock
    
    def to_dict(self):
        return {
            'id': self.p_id,
            'name': self.p_name,
            'price': float(self.p_price),
            'description': self.p_description,
            'stock': self.p_stock,
            'seller_id': self.s_id
        }

class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    invoice_no = db.Column(db.String(20), primary_key=True)  # INVOICE_NO
    invoice_datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # INVOICE_DATETIME
    due_date = db.Column(db.Date, nullable=False)  # DUE_DATE
    status = db.Column(db.String(20), nullable=False, default='pending')  # STATUS
    tax = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # TAX
    amount = db.Column(db.Numeric(10, 2), nullable=False)  # AMOUNT
    s_id = db.Column(db.String(10), db.ForeignKey('sellers.s_id'), nullable=False)  # S_ID (FK)
    c_id = db.Column(db.String(10), db.ForeignKey('customers.c_id'), nullable=False)  # C_ID (FK)
    
    # Relationships
    invoice_items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')
    
    @property
    def id(self):
        return self.invoice_no
    
    @property
    def display_id(self):
        """Display invoice number as simple number (1, 2, 3...)"""
        try:
            # If it's already a number, return as is
            return str(int(self.invoice_no))
        except ValueError:
            # If it's in INV-001 format, extract the number
            if self.invoice_no.startswith('INV-'):
                try:
                    return str(int(self.invoice_no.replace('INV-', '').lstrip('0') or '0'))
                except:
                    return self.invoice_no
            return self.invoice_no
    
    @property
    def date(self):
        return self.invoice_datetime.strftime('%Y-%m-%d')
    
    @property
    def items(self):
        """Alias for invoice_items for template compatibility"""
        return self.invoice_items
    
    @property
    def customer_name(self):
        return self.customer.c_name
    
    @property
    def customer_email(self):
        return self.customer.c_email
    
    
    @property
    def due_date_str(self):
        """Return due date as string"""
        if self.due_date:
            return self.due_date.strftime('%Y-%m-%d')
        return datetime.today().strftime('%Y-%m-%d')
    
    def to_dict(self):
        return {
            'id': self.invoice_no,
            'date': self.invoice_datetime.strftime('%Y-%m-%d'),
            'due_date': self.due_date_str,
            'status': self.status,
            'tax': float(self.tax),
            'amount': float(self.amount),
            'seller_id': self.s_id,
            'customer_id': self.c_id,
            'customer_name': self.customer.c_name,
            'customer_email': self.customer.c_email,
            'items': [item.to_dict() for item in self.invoice_items]
        }

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    
    item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # ITEM_ID
    invoice_no = db.Column(db.String(20), db.ForeignKey('invoices.invoice_no'), nullable=False)  # INVOICE_NO (FK)
    p_id = db.Column(db.String(10), db.ForeignKey('products.p_id'), nullable=False)  # P_ID (FK)
    item_quantity = db.Column(db.Integer, nullable=False)  # ITEM_QUANTITY
    discount = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # DISCOUNT
    
    # Properties for template compatibility
    @property
    def quantity(self):
        return self.item_quantity
    
    @property
    def product_name(self):
        return self.product.p_name
    
    @property
    def price(self):
        return self.product.p_price
    
    @property
    def total(self):
        return (self.product.p_price * self.item_quantity) - self.discount
    
    def to_dict(self):
        return {
            'product_name': self.product.p_name,
            'quantity': self.item_quantity,
            'price': float(self.product.p_price),
            'discount': float(self.discount),
            'total': float((self.product.p_price * self.item_quantity) - self.discount)
        }