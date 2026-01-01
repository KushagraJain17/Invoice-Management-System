from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mail import Mail, Message
from datetime import datetime, date, timedelta
from config import Config
from models import db, Seller, Customer, Product, Invoice, InvoiceItem
from decimal import Decimal
import random
import os

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Initialize mail
mail = Mail(app)


def generate_next_product_id():
    """Generate next product ID using dictionary-based approach"""
    existing_ids = {pid for (pid,) in db.session.query(Product.p_id).all()}
    max_num = 0
    
    # Extract numbers from existing P### format IDs
    for pid in existing_ids:
        if pid.startswith('P') and len(pid) == 4:
            try:
                num = int(pid[1:])
                if num > max_num:
                    max_num = num
            except ValueError:
                continue
    
    # Find next available ID
    while True:
        max_num += 1
        candidate = f"P{max_num:03d}"
        if candidate not in existing_ids:
            return candidate

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session or session['user_role'] != role:
                flash('Access denied. Insufficient permissions.', 'error')
                if session.get('user_role') == 'admin':
                    return redirect(url_for('admin_dashboard'))
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def update_overdue_invoices():
    """Update invoice status to overdue if current date > due_date"""
    today = date.today()
    overdue_invoices = Invoice.query.filter(
        Invoice.status.in_(['pending', 'overdue']),
        Invoice.due_date.isnot(None),
        Invoice.due_date < today
    ).all()
    
    for invoice in overdue_invoices:
        if invoice.status != 'overdue':
            invoice.status = 'overdue'
    
    if overdue_invoices:
        db.session.commit()

def restore_stock_on_cancellation(invoice):
    """Restore product stock when invoice is cancelled"""
    for item in invoice.invoice_items:
        product = item.product
        if product:
            product.p_stock = product.p_stock + item.item_quantity

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('seller_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Check if user is admin - credentials from environment variables
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@admin.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')
        
        if email == admin_email and password == admin_password:
            session['user_id'] = 'ADMIN'
            session['user_name'] = 'Admin'
            session['user_email'] = admin_email
            session['user_role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        
        # Check if user is a seller
        seller = Seller.query.filter_by(s_email=email).first()
        if seller and seller.check_password(password):
            session['user_id'] = seller.s_id
            session['user_name'] = seller.s_name
            session['user_email'] = seller.s_email
            session['user_role'] = 'seller'
            return redirect(url_for('seller_dashboard'))
        
        flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        password = request.form['password']
        role = request.form['role']
        
        try:
            if role == 'seller':
                # Check if seller email already exists
                existing_seller = Seller.query.filter_by(s_email=email).first()
                if existing_seller:
                    flash('Seller email already exists', 'error')
                    return render_template('auth/register.html')
                
                # Check if email is configured
                if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
                    flash('Email service not configured. Please contact administrator.', 'error')
                    return render_template('auth/register.html')
                
                # Generate 4-digit OTP
                otp = str(random.randint(1000, 9999))
                
                # Store registration data and OTP in session
                session['registration_data'] = {
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'address': address,
                    'password': password,
                    'role': role,
                    'otp': otp,
                    'otp_expiry': (datetime.now() + timedelta(minutes=10)).isoformat()
                }
                
                # Send OTP email
                try:
                    msg = Message(
                        subject='OTP for Seller Registration - Invoice Management System',
                        recipients=[email],
                        sender=app.config.get('MAIL_DEFAULT_SENDER') or app.config.get('MAIL_USERNAME')
                    )
                    otp_html = render_template('email/otp_email.html', otp=otp, name=name)
                    msg.html = otp_html
                    mail.send(msg)
                    
                    flash('OTP has been sent to your email. Please check your inbox.', 'success')
                    return redirect(url_for('verify_otp'))
                except Exception as e:
                    import traceback
                    print(f"Error sending OTP email: {str(e)}")
                    print(traceback.format_exc())
                    flash('Failed to send OTP email. Please try again.', 'error')
                    session.pop('registration_data', None)
                    return render_template('auth/register.html')
                
        except Exception as e:
            import traceback
            print(f"Registration error: {str(e)}")
            print(traceback.format_exc())
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('auth/register.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    # Check if registration data exists in session
    if 'registration_data' not in session:
        flash('Please complete registration first.', 'error')
        return redirect(url_for('register'))
    
    registration_data = session['registration_data']
    
    # Check if OTP has expired
    try:
        otp_expiry = datetime.fromisoformat(registration_data['otp_expiry'])
        if datetime.now() > otp_expiry:
            session.pop('registration_data', None)
            flash('OTP has expired. Please register again.', 'error')
            return redirect(url_for('register'))
    except (ValueError, KeyError):
        session.pop('registration_data', None)
        flash('Invalid session. Please register again.', 'error')
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        stored_otp = registration_data.get('otp', '')
        
        if entered_otp == stored_otp:
            # OTP verified, complete registration
            try:
                if registration_data['role'] == 'seller':
                    # Check if seller email still doesn't exist (double check)
                    existing_seller = Seller.query.filter_by(s_email=registration_data['email']).first()
                    if existing_seller:
                        session.pop('registration_data', None)
                        flash('Seller email already exists', 'error')
                        return redirect(url_for('register'))
                    
                    # Generate unique seller ID
                    seller_count = Seller.query.count()
                    seller_id = f"S{seller_count + 1:03d}"
                    
                    # Create new seller
                    seller = Seller(
                        s_id=seller_id,
                        s_name=registration_data['name'],
                        s_email=registration_data['email'],
                        s_address=registration_data['address'],
                        s_phone=registration_data['phone']
                    )
                    seller.set_password(registration_data['password'])
                    db.session.add(seller)
                    db.session.commit()
                    
                    # Clear registration data from session
                    session.pop('registration_data', None)
                    
                    # Auto-login
                    session['user_id'] = seller.s_id
                    session['user_name'] = seller.s_name
                    session['user_email'] = seller.s_email
                    session['user_role'] = 'seller'
                    
                    flash('Registration successful!', 'success')
                    return redirect(url_for('seller_dashboard'))
            except Exception as e:
                db.session.rollback()
                import traceback
                print(f"Error completing registration: {str(e)}")
                print(traceback.format_exc())
                flash('Registration failed. Please try again.', 'error')
                session.pop('registration_data', None)
                return redirect(url_for('register'))
        else:
            flash('Invalid OTP. Please try again.', 'error')
    
    # Show email in template for user reference
    email = registration_data.get('email', '')
    return render_template('auth/verify_otp.html', email=email)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/seller')
@login_required
@role_required('seller')
def seller_dashboard():
    # Calculate stats from database
    total_products = Product.query.filter_by(s_id=session['user_id']).count()
    # Count customers created by this seller
    total_customers = Customer.query.filter_by(s_id=session['user_id']).count()
    total_invoices = Invoice.query.filter_by(s_id=session['user_id']).count()
    paid_invoices_qs = Invoice.query.filter_by(s_id=session['user_id'], status='paid')
    pending_invoices_qs = Invoice.query.filter_by(s_id=session['user_id'], status='pending')
    overdue_invoices_qs = Invoice.query.filter_by(s_id=session['user_id'], status='overdue')
    paid_invoices_count = paid_invoices_qs.count()
    unpaid_invoices_count = pending_invoices_qs.count()
    overdue_invoices_count = overdue_invoices_qs.count()
    revenue_collected = sum(float(inv.amount) for inv in paid_invoices_qs.all())
    revenue_due = sum(float(inv.amount) for inv in pending_invoices_qs.all()) + sum(float(inv.amount) for inv in overdue_invoices_qs.all())
    
    stats = {
        'total_products': total_products,
        'total_customers': total_customers,
        'total_invoices': total_invoices,
        'paid_invoices': paid_invoices_count,
        'unpaid_invoices': unpaid_invoices_count,
        'overdue_invoices': overdue_invoices_count,
        'revenue_collected': revenue_collected,
        'revenue_due': revenue_due
    }
    
    return render_template('seller/dashboard.html', stats=stats)

@app.route('/seller/products')
@login_required
@role_required('seller')
def seller_products():
    q = request.args.get('q', '').strip()
    base_query = Product.query.filter_by(s_id=session['user_id'])
    if q:
        products = base_query.filter(Product.p_name.ilike(f"%{q}%")).all()
    else:
        products = base_query.all()
    return render_template('seller/products.html', products=products, q=q)

@app.route('/seller/products/add', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def add_product():
    if request.method == 'POST':
        try:
            name = request.form['name']
            price = Decimal(request.form['price'])
            description = request.form['description']
            stock = int(request.form['stock'])
            
            # Generate product ID safely (avoid duplicates)
            product_id = generate_next_product_id()
            
            new_product = Product(
                p_id=product_id,
                p_name=name,
                p_price=price,
                p_description=description,
                p_stock=stock,
                s_id=session['user_id']
            )
            
            db.session.add(new_product)
            db.session.commit()
            
            flash('Product added successfully!', 'success')
            return redirect(url_for('seller_products'))
            
        except Exception:
            db.session.rollback()
            flash('Failed to add product', 'error')
    
    return render_template('seller/add_product.html')

@app.route('/seller/products/edit/<product_id>', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def edit_product(product_id):
    product = Product.query.filter_by(p_id=product_id, s_id=session['user_id']).first()
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('seller_products'))
    
    if request.method == 'POST':
        try:
            product.p_name = request.form['name']
            product.p_price = Decimal(request.form['price'])
            product.p_description = request.form['description']
            product.p_stock = int(request.form['stock'])
            
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('seller_products'))
            
        except Exception:
            db.session.rollback()
            flash('Failed to update product', 'error')
    
    return render_template('seller/edit_product.html', product=product)

@app.route('/seller/products/delete/<product_id>')
@login_required
@role_required('seller')
def delete_product(product_id):
    try:
        product = Product.query.filter_by(p_id=product_id, s_id=session['user_id']).first()
        if not product:
            flash('Product not found', 'error')
            return redirect(url_for('seller_products'))
        
        # Check if product is referenced in any invoice items
        invoice_items = InvoiceItem.query.filter_by(p_id=product_id).all()
        if invoice_items:
            flash(f'Cannot delete product "{product.p_name}" because it is referenced in {len(invoice_items)} invoice(s). Please delete the invoices first.', 'error')
            return redirect(url_for('seller_products'))
        
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete product: {str(e)}', 'error')
    
    return redirect(url_for('seller_products'))

@app.route('/api/products/add', methods=['POST'])
@login_required
@role_required('seller')
def api_add_product():
    """API endpoint to add a product from invoice creation page"""
    try:
        data = request.json
        name = data.get('name')
        price = Decimal(data.get('price', 0))
        description = data.get('description', '')
        stock = int(data.get('stock', 0))
        
        if not name or price <= 0:
            return jsonify({'success': False, 'error': 'Invalid product data'}), 400
        
        # Generate product ID safely
        product_id = generate_next_product_id()
        
        new_product = Product(
            p_id=product_id,
            p_name=name,
            p_price=price,
            p_description=description,
            p_stock=stock,
            s_id=session['user_id']
        )
        
        db.session.add(new_product)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'product': new_product.to_dict()
        })
        
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/seller/customers')
@login_required
@role_required('seller')
def seller_customers():
    # Show only customers created by this seller
    q = request.args.get('q', '').strip()
    
    # Get customers created by this seller
    base = Customer.query.filter_by(s_id=session['user_id'])
    
    if q:
        base = base.filter(Customer.c_name.ilike(f"%{q}%"))
    
    customers = base.order_by(Customer.c_name.asc()).all()
    return render_template('seller/customers.html', customers=customers, q=q)

@app.route('/seller/customers/<customer_id>/invoices')
@login_required
@role_required('seller')
def view_customer_invoices(customer_id):
    # Verify customer belongs to this seller
    customer = Customer.query.filter_by(c_id=customer_id, s_id=session['user_id']).first()
    
    if not customer:
        flash('Customer not found or access denied', 'error')
        return redirect(url_for('seller_customers'))
    
    invoices = Invoice.query.filter_by(c_id=customer_id, s_id=session['user_id']).all()
    return render_template('seller/customer_invoices.html', customer=customer, invoices=invoices)

@app.route('/seller/customers/add', methods=['POST'])
@login_required
@role_required('seller')
def add_customer():
    try:
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        
        # Check if customer email already exists
        existing_customer = Customer.query.filter_by(c_email=email).first()
        if existing_customer:
            flash('Customer with this email already exists', 'error')
            return redirect(url_for('seller_customers'))
        
        # Generate customer ID
        customer_count = Customer.query.count()
        customer_id = f"C{customer_count + 1:03d}"
        
        # Create new customer
        customer = Customer(
            c_id=customer_id,
            c_name=name,
            c_email=email,
            c_phone_no=phone,
            c_address=address,
            s_id=session['user_id']  # Track which seller created this customer
        )
        db.session.add(customer)
        db.session.commit()
        
        flash('Customer added successfully!', 'success')
        return redirect(url_for('seller_customers'))

    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"Error adding customer: {str(e)}")
        print(traceback.format_exc())
        flash(f'Failed to add customer: {str(e)}', 'error')
        return redirect(url_for('seller_customers'))

@app.route('/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    """Admin dashboard to manage all sellers"""
    sellers = Seller.query.order_by(Seller.s_name.asc()).all()
    
    # Get statistics
    total_sellers = Seller.query.count()
    total_customers = Customer.query.count()
    total_products = Product.query.count()
    total_invoices = Invoice.query.count()
    
    stats = {
        'total_sellers': total_sellers,
        'total_customers': total_customers,
        'total_products': total_products,
        'total_invoices': total_invoices
    }
    
    return render_template('admin/dashboard.html', sellers=sellers, stats=stats)

@app.route('/admin/sellers')
@login_required
@role_required('admin')
def admin_sellers():
    sellers = Seller.query.order_by(Seller.s_name.asc()).all()
    return render_template('admin/sellers.html', sellers=sellers)

@app.route('/admin/sellers/<seller_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_seller(seller_id):
    seller = db.session.get(Seller, seller_id)
    if not seller:
        flash('Seller not found', 'error')
        return redirect(url_for('admin_sellers'))
    
    if request.method == 'POST':
        try:
            seller.s_name = request.form.get('name', seller.s_name)
            seller.s_email = request.form.get('email', seller.s_email)
            seller.s_phone = request.form.get('phone', seller.s_phone)
            seller.s_address = request.form.get('address', seller.s_address)
            
            # Update password if provided
            new_password = request.form.get('password', '').strip()
            if new_password:
                seller.set_password(new_password)
            
            db.session.commit()
            flash('Seller updated successfully', 'success')
            return redirect(url_for('admin_sellers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update seller: {str(e)}', 'error')
    
    return render_template('admin/edit_seller.html', seller=seller)

@app.route('/admin/sellers/<seller_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_seller(seller_id):
    """Delete a seller"""
    try:
        seller = db.session.get(Seller, seller_id)
        if not seller:
            flash('Seller not found', 'error')
            return redirect(url_for('admin_sellers'))
        
        db.session.delete(seller)
        db.session.commit()
        flash('Seller deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete seller: {str(e)}', 'error')
    
    return redirect(url_for('admin_sellers'))

@app.route('/seller/customer-analytics')
@login_required
@role_required('seller')
def customer_analytics():
    """Customer analytics: most/least invoices and purchases between dates"""
    from sqlalchemy import func, desc, asc, case, and_, or_
    
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()
    
    # Build base filters
    paid_filters = [
        Invoice.s_id == session['user_id'],
        Invoice.status == 'paid'
    ]
    invoice_filters = [
        Invoice.s_id == session['user_id']
    ]
    
    if start_date_str:
        try:
            start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
            paid_filters.append(Invoice.invoice_datetime >= start_dt)
            invoice_filters.append(Invoice.invoice_datetime >= start_dt)
        except ValueError:
            pass
    
    if end_date_str:
        try:
            end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_dt_inclusive = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            paid_filters.append(Invoice.invoice_datetime <= end_dt_inclusive)
            invoice_filters.append(Invoice.invoice_datetime <= end_dt_inclusive)
        except ValueError:
            pass
    
    # Query for customers with any invoices (status-agnostic) for invoice counts
    all_invoices_query = db.session.query(
        Customer.c_id,
        Customer.c_name,
        Customer.c_email,
        func.count(Invoice.invoice_no).label('invoice_count')
    ).join(
        Invoice, Customer.c_id == Invoice.c_id
    ).filter(
        and_(*invoice_filters)
    ).group_by(
        Customer.c_id, Customer.c_name, Customer.c_email
    )
    
    # Most invoices (any status)
    most_invoices = all_invoices_query.order_by(desc('invoice_count')).first()
    
    # Least invoices (include zero by left joining)
    least_invoices_query = db.session.query(
        Customer.c_id,
        Customer.c_name,
        Customer.c_email,
        func.count(Invoice.invoice_no).label('invoice_count')
    ).outerjoin(
        Invoice, 
        and_(
            Customer.c_id == Invoice.c_id,
            and_(*invoice_filters)
        )
    ).filter(
        Customer.s_id == session['user_id']
    )
    
    least_invoices_query = least_invoices_query.group_by(
        Customer.c_id, Customer.c_name, Customer.c_email
    )
    
    least_invoices = least_invoices_query.order_by(asc('invoice_count')).first()
    
    # Query for customers with paid invoices (for purchase totals)
    paid_invoices_query = db.session.query(
        Customer.c_id,
        Customer.c_name,
        Customer.c_email,
        func.count(Invoice.invoice_no).label('invoice_count'),
        func.sum(Invoice.amount).label('total_purchased')
    ).join(
        Invoice, Customer.c_id == Invoice.c_id
    ).filter(
        and_(*paid_filters)
    ).group_by(
        Customer.c_id, Customer.c_name, Customer.c_email
    )
    
    paid_sample = paid_invoices_query.first()
    if paid_sample is None:
        most_purchased = None
        least_purchased = None
    else:
        # Get customer who purchased most (from paid invoices)
        most_purchased = paid_invoices_query.order_by(desc('total_purchased')).first()
        # Get customer who purchased least (from paid invoices)
        least_purchased = paid_invoices_query.order_by(asc('total_purchased')).first()
    
    return render_template(
        'seller/customer_analytics.html',
        most_invoices=most_invoices,
        least_invoices=least_invoices,
        most_purchased=most_purchased,
        least_purchased=least_purchased,
        no_paid_invoices=(paid_sample is None),
        start_date=start_date_str,
        end_date=end_date_str
    )

@app.route('/seller/customers/edit/<customer_id>', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def edit_customer(customer_id):
    # Verify customer belongs to this seller
    customer = Customer.query.filter_by(c_id=customer_id, s_id=session['user_id']).first()
    
    if not customer:
        flash('Customer not found or access denied', 'error')
        return redirect(url_for('seller_customers'))

    if request.method == 'POST':
        try:
            customer.c_name = request.form.get('name', customer.c_name)
            customer.c_email = request.form.get('email', customer.c_email)
            customer.c_phone_no = request.form.get('phone', customer.c_phone_no)
            customer.c_address = request.form.get('address', customer.c_address)
            db.session.commit()
            flash('Customer updated successfully!', 'success')
            return redirect(url_for('seller_customers'))
        except Exception:
            db.session.rollback()
            flash('Failed to update customer', 'error')
    return render_template('seller/edit_customer.html', customer=customer)

@app.route('/seller/customers/delete/<customer_id>')
@login_required
@role_required('seller')
def delete_customer(customer_id):
    try:
        # Verify customer belongs to this seller
        customer = Customer.query.filter_by(c_id=customer_id, s_id=session['user_id']).first()
        if not customer:
            flash('Customer not found or access denied', 'error')
            return redirect(url_for('seller_customers'))
        
        # Check if customer has any invoices
        invoices = Invoice.query.filter_by(c_id=customer_id, s_id=session['user_id']).all()
        if invoices:
            flash(f'Cannot delete customer "{customer.c_name}" because they have {len(invoices)} invoice(s). Please delete the invoices first.', 'error')
            return redirect(url_for('seller_customers'))
        
        db.session.delete(customer)
        db.session.commit()
        flash('Customer deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete customer: {str(e)}', 'error')
    
    return redirect(url_for('seller_customers'))

@app.route('/seller/invoices')
@login_required
@role_required('seller')
def seller_invoices():
    # Update overdue invoices before displaying
    update_overdue_invoices()
    
    q = request.args.get('q', '').strip()
    customer_q = request.args.get('customer', '').strip()
    status = request.args.get('status', '').strip()
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()
    min_amount_str = request.args.get('min_amount', '').strip()
    max_amount_str = request.args.get('max_amount', '').strip()

    query = Invoice.query.filter_by(s_id=session['user_id'])

    if q:
        query = query.filter(Invoice.invoice_no.ilike(f"%{q}%"))

    if customer_q:
        query = query.join(Customer).filter(
            (Customer.c_name.ilike(f"%{customer_q}%")) | (Customer.c_email.ilike(f"%{customer_q}%"))
        )

    if status:
        query = query.filter(Invoice.status == status)

    # Date range filter (expects YYYY-MM-DD)
    try:
        if start_date_str:
            start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
            query = query.filter(Invoice.invoice_datetime >= start_dt)
    except ValueError:
        pass

    try:
        if end_date_str:
            # include entire end day by adding one day and using < next day
            end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_dt_inclusive = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(Invoice.invoice_datetime <= end_dt_inclusive)
    except ValueError:
        pass

    # Amount range filter
    try:
        if min_amount_str:
            query = query.filter(Invoice.amount >= Decimal(min_amount_str))
    except Exception:
        pass
    try:
        if max_amount_str:
            query = query.filter(Invoice.amount <= Decimal(max_amount_str))
    except Exception:
        pass

    invoices = query.order_by(Invoice.invoice_datetime.desc()).all()
    return render_template(
        'seller/invoices.html',
        invoices=invoices,
        q=q,
        customer_q=customer_q,
        status=status,
        start_date=start_date_str,
        end_date=end_date_str,
        min_amount=min_amount_str,
        max_amount=max_amount_str,
    )

@app.route('/seller/invoices/create', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def create_invoice():
    if request.method == 'POST':
        try:
            customer_id = request.form.get('customer_id', '').strip()
            if not customer_id:
                flash('Please select a customer', 'error')
                return redirect(url_for('create_invoice'))
            
            # Tax will be calculated as 10% of subtotal later
            due_date_str = request.form.get('due_date', '').strip()
            
            # Parse due date
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # Check if this is a new customer being created
            if customer_id.startswith('temp_'):
                # Create new customer
                customer_name = request.form['temp_customer_name']
                customer_email = request.form['temp_customer_email']
                customer_phone = request.form['temp_customer_phone']
                customer_address = request.form['temp_customer_address']
                
                # Check if customer email already exists
                existing_customer = Customer.query.filter_by(c_email=customer_email).first()
                if existing_customer:
                    flash('Customer with this email already exists', 'error')
                    return redirect(url_for('create_invoice'))
                
                # Generate customer ID
                customer_count = Customer.query.count()
                customer_id = f"C{customer_count + 1:03d}"
                
                # Create new customer
                customer = Customer(
                    c_id=customer_id,
                    c_name=customer_name,
                    c_email=customer_email,
                    c_phone_no=customer_phone,
                    c_address=customer_address,
                    s_id=session['user_id']  # Track which seller created this customer
                )
                db.session.add(customer)
                db.session.flush()  # Get the customer ID
            else:
                # Get existing customer info and verify it belongs to this seller
                customer = db.session.get(Customer, customer_id)
                if not customer:
                    flash('Customer not found', 'error')
                    return redirect(url_for('create_invoice'))
                if customer.s_id != session['user_id']:
                    flash('Access denied: This customer does not belong to you', 'error')
                    return redirect(url_for('create_invoice'))
            
            # Process items
            items = []
            subtotal = Decimal('0')
            
            item_indices = sorted(list(set([
                key.split('_')[1] for key in request.form 
                if key.startswith('product_') and key.endswith('_id')
            ])))

            for item_index in item_indices:
                product_id = request.form.get(f'product_{item_index}_id')
                quantity = int(request.form.get(f'quantity_{item_index}', 1))
                discount = Decimal(request.form.get(f'discount_{item_index}', 0))

                # If a temp product was added inline, create it now
                if product_id and product_id.startswith('temp_'):
                    temp_name = request.form.get(f'temp_product_name_{item_index}')
                    temp_price = Decimal(request.form.get(f'temp_product_price_{item_index}', 0))
                    temp_stock = int(request.form.get(f'temp_product_stock_{item_index}', 0))
                    temp_desc = request.form.get(f'temp_product_desc_{item_index}', '')

                    new_product_id = generate_next_product_id()
                    product = Product(
                        p_id=new_product_id,
                        p_name=temp_name,
                        p_price=temp_price,
                        p_description=temp_desc,
                        p_stock=temp_stock,
                        s_id=session['user_id']
                    )
                    db.session.add(product)
                    db.session.flush()
                else:
                    product = db.session.get(Product, product_id)

                if product:
                    # Ensure sufficient stock is available
                    if product.p_stock < quantity:
                        db.session.rollback()
                        flash(f'Insufficient stock for product \"{product.p_name}\". Available: {product.p_stock}', 'error')
                        return redirect(url_for('create_invoice'))
                    item_total = (product.p_price * quantity) - discount
                    subtotal += item_total
                    items.append({
                        'product': product,
                        'quantity': quantity,
                        'discount': discount,
                        'total': item_total
                    })
                else:
                    db.session.rollback()
                    flash('Selected product not found.', 'error')
                    return redirect(url_for('create_invoice'))
            
            if not items:
                flash('Please add at least one item', 'error')
                return redirect(url_for('create_invoice'))
            
            # Calculate tax as 10% of subtotal
            tax = subtotal * Decimal('0.10')
            total = subtotal + tax
            
            # Create invoice with unique ID
            # Generate unique invoice ID as simple number
            existing_invoice_nos = [inv.invoice_no for inv in Invoice.query.all()]
            invoice_num = 1
            while True:
                invoice_id = str(invoice_num)
                if invoice_id not in existing_invoice_nos:
                    break
                invoice_num += 1
            
            new_invoice = Invoice(
                invoice_no=invoice_id,
                invoice_datetime=datetime.utcnow(),
                due_date=due_date,
                status='pending',
                tax=tax,
                amount=total,
                s_id=session['user_id'],
                c_id=customer_id
            )
            
            # Check if invoice is already overdue
            if due_date and due_date < date.today():
                new_invoice.status = 'overdue'
            
            db.session.add(new_invoice)
            db.session.flush()  # Get the invoice ID
            
            # Create invoice items
            for item in items:
                invoice_item = InvoiceItem(
                    invoice_no=new_invoice.invoice_no,
                    p_id=item['product'].p_id,
                    item_quantity=item['quantity'],
                    discount=item['discount']
                )
                db.session.add(invoice_item)
            
            # Adjust product stock levels immediately
            for item in items:
                product = item['product']
                if product:
                    product.p_stock = product.p_stock - item['quantity']
            
            db.session.commit()
            
            flash(f'Invoice {invoice_id} created successfully!', 'success')
            return redirect(url_for('seller_invoices'))
            
        except Exception as e:
            db.session.rollback()
            import traceback
            print(f"Error creating invoice: {str(e)}")
            print(traceback.format_exc())
            flash(f'Failed to create invoice: {str(e)}', 'error')
    
    products = Product.query.filter_by(s_id=session['user_id']).all()
    # Show only customers created by this seller
    customers = Customer.query.filter_by(s_id=session['user_id']).order_by(Customer.c_name.asc()).all()
    # Convert products to dictionaries for JSON serialization
    products_data = [product.to_dict() for product in products]
    return render_template('seller/create_invoice.html', products=products_data, customers=customers)

@app.route('/seller/invoices/edit/<invoice_id>', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def edit_invoice(invoice_id):
    invoice = Invoice.query.filter_by(invoice_no=invoice_id, s_id=session['user_id']).first()
    
    if not invoice:
        flash('Invoice not found', 'error')
        return redirect(url_for('seller_invoices'))
    
    # Check if invoice is cancelled - make it uneditable
    if invoice.status == 'cancelled':
        flash('Cannot edit a cancelled invoice', 'error')
        return redirect(url_for('seller_invoices'))
    
    if request.method == 'POST':
        try:
            # Update invoice status
            new_status = request.form.get('status', invoice.status)
            old_status = invoice.status
            
            # Handle cancellation - restore stock
            if new_status == 'cancelled' and old_status != 'cancelled':
                restore_stock_on_cancellation(invoice)
            
            invoice.status = new_status
            
            # Update due date
            due_date_str = request.form.get('due_date', '').strip()
            if due_date_str:
                try:
                    invoice.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # Check if invoice should be overdue
            if invoice.due_date and invoice.due_date < date.today() and new_status in ['pending', 'overdue']:
                invoice.status = 'overdue'
                new_status = 'overdue'
            
            # Handle item updates, additions, and deletions
            existing_item_ids = set()
            subtotal = Decimal('0')
            
            # Process existing items
            for item in invoice.invoice_items:
                item_id = item.item_id
                existing_item_ids.add(item_id)
                
                # Check if item should be deleted
                delete_key = f'delete_{item_id}'
                if delete_key in request.form:
                    product = item.product
                    if product:
                        product.p_stock = product.p_stock + item.item_quantity
                    db.session.delete(item)
                    continue
                
                # Update quantity
                quantity_key = f'quantity_{item_id}'
                if quantity_key in request.form:
                    new_quantity = int(request.form[quantity_key])
                    product = item.product
                    if product:
                        stock_diff = item.item_quantity - new_quantity
                        if stock_diff < 0 and product.p_stock < abs(stock_diff):
                            db.session.rollback()
                            flash(f'Insufficient stock for product \"{product.p_name}\" while updating invoice.', 'error')
                            return redirect(url_for('edit_invoice', invoice_id=invoice_id))
                        product.p_stock = product.p_stock + stock_diff
                    item.item_quantity = new_quantity
                
                # Update discount
                discount_key = f'discount_{item_id}'
                if discount_key in request.form:
                    item.discount = Decimal(request.form[discount_key])
                
                # Update price (if product changed)
                product_key = f'product_{item_id}'
                if product_key in request.form:
                    new_product_id = request.form[product_key]
                    if new_product_id and new_product_id != item.p_id:
                        old_product = item.product
                        if old_product:
                            old_product.p_stock = old_product.p_stock + item.item_quantity
                        new_product = db.session.get(Product, new_product_id)
                        if not new_product:
                            db.session.rollback()
                            flash('Selected product not found.', 'error')
                            return redirect(url_for('edit_invoice', invoice_id=invoice_id))
                        if new_product.p_stock < item.item_quantity:
                            db.session.rollback()
                            flash(f'Insufficient stock for product \"{new_product.p_name}\".', 'error')
                            return redirect(url_for('edit_invoice', invoice_id=invoice_id))
                        new_product.p_stock = new_product.p_stock - item.item_quantity
                        item.p_id = new_product_id
                        item.product = new_product
                
                subtotal += (item.product.p_price * item.item_quantity) - item.discount
            
            # Add new items
            # Extract indices from form keys like 'new_product_1_id', 'new_product_2_id', etc.
            new_item_indices = []
            for key in request.form:
                if key.startswith('new_product_') and key.endswith('_id'):
                    # Extract the number between 'new_product_' and '_id'
                    # e.g., 'new_product_1_id' -> '1'
                    parts = key.split('_')
                    if len(parts) >= 3:
                        try:
                            index = int(parts[2])  # parts[2] is the index number
                            new_item_indices.append(index)
                        except (ValueError, IndexError):
                            continue
            new_item_indices = sorted(list(set(new_item_indices)))
            
            for item_index in new_item_indices:
                product_id = request.form.get(f'new_product_{item_index}_id', '').strip()
                if product_id:
                    quantity = int(request.form.get(f'new_quantity_{item_index}', 1))
                    discount = Decimal(request.form.get(f'new_discount_{item_index}', 0))
                    
                    product = db.session.get(Product, product_id)
                    if product:
                        if product.p_stock < quantity:
                            db.session.rollback()
                            flash(f'Insufficient stock for product \"{product.p_name}\".', 'error')
                            return redirect(url_for('edit_invoice', invoice_id=invoice_id))
                        new_item = InvoiceItem(
                            invoice_no=invoice.invoice_no,
                            p_id=product_id,
                            item_quantity=quantity,
                            discount=discount
                        )
                        db.session.add(new_item)
                        product.p_stock = product.p_stock - quantity
                        subtotal += (product.p_price * quantity) - discount
                    else:
                        db.session.rollback()
                        flash('Selected product not found.', 'error')
                        return redirect(url_for('edit_invoice', invoice_id=invoice_id))
            
            # Calculate tax as 10% of subtotal
            invoice.tax = subtotal * Decimal('0.10')
            # Recalculate total
            invoice.amount = subtotal + invoice.tax
            
            db.session.commit()
            
            flash('Invoice updated successfully!', 'success')
            return redirect(url_for('seller_invoices'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update invoice: {str(e)}', 'error')
    
    products = Product.query.filter_by(s_id=session['user_id']).all()
    products_data = [product.to_dict() for product in products]
    
    return render_template('seller/edit_invoice.html', invoice=invoice, products=products_data)


@app.route('/invoice/<invoice_id>')
@login_required
@role_required('seller')
def view_invoice(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    
    if not invoice:
        flash('Invoice not found', 'error')
        return redirect(url_for('seller_dashboard'))
    
    # Check if seller has access to this invoice
    if invoice.s_id != session['user_id']:
        flash('Access denied', 'error')
        return redirect(url_for('seller_dashboard'))
    
    return render_template('invoice/view.html', invoice=invoice)

@app.route('/seller/invoices/delete/<invoice_id>')
@login_required
@role_required('seller')
def delete_invoice(invoice_id):
    try:
        # Verify invoice belongs to this seller
        invoice = Invoice.query.filter_by(invoice_no=invoice_id, s_id=session['user_id']).first()
        if not invoice:
            flash('Invoice not found or access denied', 'error')
            return redirect(url_for('seller_invoices'))
        
        # Only allow deletion of cancelled invoices
        if invoice.status != 'cancelled':
            flash('Only cancelled invoices can be deleted', 'error')
            return redirect(url_for('seller_invoices'))
        
        # Delete invoice (invoice_items will be cascade deleted due to relationship)
        db.session.delete(invoice)
        db.session.commit()
        flash('Invoice deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete invoice: {str(e)}', 'error')
    
    return redirect(url_for('seller_invoices'))

@app.route('/seller/invoices/send-email/<invoice_id>')
@login_required
@role_required('seller')
def send_invoice_email(invoice_id):
    try:
        # Verify invoice belongs to this seller
        invoice = Invoice.query.filter_by(invoice_no=invoice_id, s_id=session['user_id']).first()
        if not invoice:
            flash('Invoice not found or access denied', 'error')
            return redirect(url_for('seller_invoices'))
        
        # Get customer email
        customer_email = invoice.customer.c_email
        if not customer_email:
            flash('Customer email not found', 'error')
            return redirect(url_for('seller_invoices'))
        
        # Check if email is configured
        if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
            flash('Email not configured. Please configure email settings first.', 'error')
            return redirect(url_for('seller_invoices'))
        
        # Get seller information for sender name
        seller = invoice.seller
        
        # Create email message
        msg = Message(
            subject=f'Invoice {invoice.invoice_no} - Invoice Management System',
            recipients=[customer_email],
            sender=app.config.get('MAIL_DEFAULT_SENDER') or app.config.get('MAIL_USERNAME')
        )
        # Create email body with invoice details
        invoice_html = render_template('email/invoice_email.html', invoice=invoice, seller=seller)
        msg.html = invoice_html
        
        # Send email
        mail.send(msg)
        flash(f'Invoice sent successfully to {customer_email}!', 'success')
        
    except Exception as e:
        import traceback
        print(f"Error sending email: {str(e)}")
        print(traceback.format_exc())
        flash(f'Failed to send email: {str(e)}', 'error')
    
    return redirect(url_for('seller_invoices'))


@app.errorhandler(500)
def handle_internal_error(error):
    flash('An unexpected error occurred. Please try again later.', 'error')
    return redirect(url_for('seller_dashboard'))

if __name__ == '__main__':
    with app.app_context():
        # create any missing tables
        db.create_all()
    app.run(debug=True, host='127.0.0.1', port=8000)