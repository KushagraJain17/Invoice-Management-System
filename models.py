from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Activity(db.Model):
    __tablename__ = 'activities'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(10), nullable=False)  # User who performed the action
    user_role = db.Column(db.String(20), nullable=False)  # 'seller' or 'customer'
    action_type = db.Column(db.String(50), nullable=False)  # 'product_added', 'invoice_created', etc.
    description = db.Column(db.Text, nullable=False)  # Human-readable description
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_role': self.user_role,
            'action_type': self.action_type,
            'description': self.description,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'time_ago': self.get_time_ago()
        }
    
    def get_time_ago(self):
        now = datetime.utcnow()
        diff = now - self.timestamp
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"

class Seller(db.Model):
    __tablename__ = 'sellers'
    
    s_id = db.Column(db.String(10), primary_key=True)  # S_ID
    s_name = db.Column(db.String(100), nullable=False)  # S_NAME
    s_email = db.Column(db.String(100), nullable=False, unique=True)  # S_EMAIL
    s_address = db.Column(db.Text, nullable=False)      # S_ADDRESS
    s_phone = db.Column(db.String(20), nullable=False)  # S_PHONE
    password = db.Column(db.String(255), nullable=False) # PASSWORD
    
    # Relationships
    products = db.relationship('Product', backref='seller', lazy=True, cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='seller', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)
    
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
    
    c_id = db.Column(db.String(10), primary_key=True)    # C_ID
    c_name = db.Column(db.String(100), nullable=False)  # C_NAME
    c_email = db.Column(db.String(100), nullable=False, unique=True)  # C_EMAIL
    c_phone_no = db.Column(db.String(20), nullable=False)  # C_PHONE_NO
    c_address = db.Column(db.Text, nullable=False)       # C_ADDRESS
    password = db.Column(db.String(255), nullable=True, default='')  # PASSWORD (optional for customers)
    
    # Relationships
    invoices = db.relationship('Invoice', backref='customer', lazy=True)
    
    # Properties for template compatibility
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

    def set_password(self, password):
        if password is None or password == '':
            self.password = ''
            return
        self.password = generate_password_hash(password)

    def check_password(self, password):
        if not self.password:
            return False
        return check_password_hash(self.password, password)

class Product(db.Model):
    """PRODUCT entity from ER diagram"""
    __tablename__ = 'products'
    
    p_id = db.Column(db.String(10), primary_key=True)    # P_ID
    p_name = db.Column(db.String(100), nullable=False)  # P_NAME
    p_price = db.Column(db.Numeric(10, 2), nullable=False)  # P_PRICE
    p_description = db.Column(db.Text, nullable=True)    # P_DESCRIPTION
    p_stock = db.Column(db.Integer, nullable=False, default=0)  # P_STOCK
    s_id = db.Column(db.String(10), db.ForeignKey('sellers.s_id'), nullable=False)  # S_ID (FK)
    
    # Relationships
    invoice_items = db.relationship('InvoiceItem', backref='product', lazy=True)
    
    # Properties for template compatibility
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
    status = db.Column(db.String(20), nullable=False, default='pending')  # STATUS
    tax = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # TAX
    amount = db.Column(db.Numeric(10, 2), nullable=False)  # AMOUNT
    s_id = db.Column(db.String(10), db.ForeignKey('sellers.s_id'), nullable=False)  # S_ID (FK)
    c_id = db.Column(db.String(10), db.ForeignKey('customers.c_id'), nullable=False)  # C_ID (FK)
    
    # Relationships
    invoice_items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')
    
    # Properties for template compatibility
    @property
    def id(self):
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
    
    
    def to_dict(self):
        return {
            'id': self.invoice_no,
            'date': self.invoice_datetime.strftime('%Y-%m-%d'),
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
    """INVOICE_ITEM entity from ER diagram"""
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
