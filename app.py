from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from datetime import datetime
from config import Config
from models import db, Seller, Customer, Product, Invoice, InvoiceItem, Activity
from decimal import Decimal
import io

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database0
db.init_app(app)

# Ensure tables exist when the app starts
with app.app_context():
    db.create_all()

# Helper utilities
import re

def generate_next_product_id():
    existing_ids = [pid for (pid,) in db.session.query(Product.p_id).all()]
    max_num = 0
    for pid in existing_ids:
        m = re.match(r'^P(\d+)$', pid)
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num
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
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_activity(action_type, description):
    """Log an activity for the current user"""
    if 'user_id' in session and 'user_role' in session:
        activity = Activity(
            user_id=session['user_id'],
            user_role=session['user_role'],
            action_type=action_type,
            description=description
        )
        db.session.add(activity)
        db.session.commit()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('seller_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Check if user is a seller
        seller = Seller.query.filter_by(s_email=email).first()
        if seller and seller.check_password(password):
            session.permanent = False
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
                
                # Generate unique seller ID
                seller_count = Seller.query.count()
                seller_id = f"S{seller_count + 1:03d}"
                
                # Create new seller
                seller = Seller(
                    s_id=seller_id,
                    s_name=name,
                    s_email=email,
                    s_address=address,
                    s_phone=phone
                )
                seller.set_password(password)
                db.session.add(seller)
                db.session.commit()
                
                # Auto-login
                session['user_id'] = seller.s_id
                session['user_name'] = seller.s_name
                session['user_email'] = seller.s_email
                session['user_role'] = 'seller'
                
            
            flash('Registration successful!', 'success')
            return redirect(url_for('seller_dashboard'))
                
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/seller')
@login_required
@role_required('seller')
def seller_dashboard():
    total_products = Product.query.filter_by(s_id=session['user_id']).count()
    total_customers = Customer.query.count()
    total_invoices = Invoice.query.filter_by(s_id=session['user_id']).count()
    paid_invoices_qs = Invoice.query.filter_by(s_id=session['user_id'], status='paid')
    pending_invoices_qs = Invoice.query.filter_by(s_id=session['user_id'], status='pending')
    overdue_invoices_qs = Invoice.query.filter_by(s_id=session['user_id'], status='overdue')
    paid_invoices_count = paid_invoices_qs.count()
    unpaid_invoices_count = pending_invoices_qs.count() + overdue_invoices_qs.count()
    revenue_collected = sum(float(inv.amount) for inv in paid_invoices_qs.all())
    revenue_due = sum(float(inv.amount) for inv in pending_invoices_qs.all()) + \
                   sum(float(inv.amount) for inv in overdue_invoices_qs.all())
    
    # Get recent activities for this seller
    recent_activities = Activity.query.filter_by(user_id=session['user_id']).order_by(Activity.timestamp.desc()).limit(5).all()
    
    stats = {
        'total_products': total_products,
        'total_customers': total_customers,
        'total_invoices': total_invoices,
        'paid_invoices': paid_invoices_count,
        'unpaid_invoices': unpaid_invoices_count,
        'revenue_collected': revenue_collected,
        'revenue_due': revenue_due
    }
    
    return render_template('seller/dashboard.html', stats=stats, activities=recent_activities)

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
            
            # Log activity
            log_activity('product_added', f'Added new product "{name}"')
            
            flash('Product added successfully!', 'success')
            return redirect(url_for('seller_products'))
            
        except Exception as e:
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
            
        except Exception as e:
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
            flash(f'Cannot delete product "{product.name}" because it is referenced in {len(invoice_items)} invoice(s). Please delete the invoices first.', 'error')
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
        
        # Log activity
        log_activity('product_added', f'Added new product "{name}" from invoice creation')
        
        return jsonify({
            'success': True,
            'product': new_product.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/seller/customers')
@login_required
@role_required('seller')
def seller_customers():
    # Show all customers with optional search by name
    q = request.args.get('q', '').strip()
    base = Customer.query
    if q:
        base = base.filter(Customer.c_name.ilike(f"%{q}%"))
    customers = base.order_by(Customer.c_name.asc()).all()
    return render_template('seller/customers.html', customers=customers, q=q)

@app.route('/seller/customers/<customer_id>/invoices')
@login_required
@role_required('seller')
def view_customer_invoices(customer_id):
    customer = Customer.query.get(customer_id)
    if not customer:
        flash('Customer not found', 'error')
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
            password=''  # Avoid DB default issues
        )
        db.session.add(customer)
        db.session.commit()
        
        # Log activity
        log_activity('customer_created', f'Created new customer "{name}"')
        
        flash('Customer added successfully!', 'success')
        return redirect(url_for('seller_customers'))

    except Exception as e:
        db.session.rollback()
        flash('Failed to add customer', 'error')
        return redirect(url_for('seller_customers'))

@app.route('/seller/customers/edit/<customer_id>', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def edit_customer(customer_id):
    customer = Customer.query.get(customer_id)
    if not customer:
        flash('Customer not found', 'error')
        return redirect(url_for('seller_customers'))

    if request.method == 'POST':
        try:
            customer.c_name = request.form.get('name', customer.c_name)
            customer.c_email = request.form.get('email', customer.c_email)
            customer.c_phone_no = request.form.get('phone', customer.c_phone_no)
            customer.c_address = request.form.get('address', customer.c_address)
            db.session.commit()
            log_activity('customer_updated', f'Updated customer "{customer.c_name}"')
            flash('Customer updated successfully!', 'success')
            return redirect(url_for('seller_customers'))
        except Exception:
            db.session.rollback()
            flash('Failed to update customer', 'error')
    return render_template('seller/edit_customer.html', customer=customer)

@app.route('/seller/invoices')
@login_required
@role_required('seller')
def seller_invoices():
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
            customer_id = request.form['customer_id']
            tax = Decimal(request.form.get('tax', 0))
            
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
                    password=''  # Avoid DB default issues
                )
                db.session.add(customer)
                db.session.flush()  # Get the customer ID
                
                # Log activity
                log_activity('customer_created', f'Created new customer "{customer_name}" during invoice creation')
            else:
                # Get existing customer info
                customer = Customer.query.get(customer_id)
                if not customer:
                    flash('Customer not found', 'error')
                    return redirect(url_for('create_invoice'))
            
            # Process items
            items = []
            subtotal = Decimal('0')
            
            item_indices = sorted(list(set([key.split('_')[1] for key in request.form if key.startswith('product_') and key.endswith('_id')]))) # noqa: E501

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
                    # Log activity for product creation
                    log_activity('product_added', f'Added new product "{temp_name}" during invoice creation')
                else:
                    product = Product.query.get(product_id)

                if product:
                    item_total = (product.p_price * quantity) - discount
                    subtotal += item_total
                    items.append({
                        'product': product,
                        'quantity': quantity,
                        'discount': discount,
                        'total': item_total
                    })
            
            if not items:
                flash('Please add at least one item', 'error')
                return redirect(url_for('create_invoice'))
            
            total = subtotal + tax
            
            # Create invoice
            invoice_count = Invoice.query.count()
            invoice_id = f"INV-{invoice_count + 1:03d}"
            
            new_invoice = Invoice(
                invoice_no=invoice_id,
                invoice_datetime=datetime.utcnow(),
                status='pending',
                tax=tax,
                amount=total,
                s_id=session['user_id'],
                c_id=customer_id
            )
            
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
            
            db.session.commit()
            
            # Log activity
            log_activity('invoice_created', f'Created invoice {invoice_id} for {customer.c_name}')
            
            flash(f'Invoice {invoice_id} created successfully!', 'success')
            return redirect(url_for('seller_invoices'))
            
        except Exception as e:
            db.session.rollback()
            flash('Failed to create invoice', 'error')
    
    products = Product.query.filter_by(s_id=session['user_id']).all()
    customers = Customer.query.all()
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
    
    if request.method == 'POST':
        try:
            # Update invoice status
            new_status = request.form.get('status', invoice.status)
            old_status = invoice.status
            invoice.status = new_status
            
            # Update tax
            invoice.tax = Decimal(request.form.get('tax', invoice.tax))
            
            # Update discounts for each item
            subtotal = Decimal('0')
            for item in invoice.invoice_items:
                discount_key = f'discount_{item.item_id}'
                if discount_key in request.form:
                    item.discount = Decimal(request.form[discount_key])
                subtotal += (item.product.p_price * item.item_quantity) - item.discount
            
            # Recalculate total
            invoice.amount = subtotal + invoice.tax
            
            # If status changed to 'paid', update product stock
            if old_status != 'paid' and new_status == 'paid':
                for item in invoice.invoice_items:
                    product = item.product
                    product.p_stock = max(0, product.p_stock - item.item_quantity)
            
            # If status changed from 'paid' to something else, restore product stock
            if old_status == 'paid' and new_status != 'paid':
                for item in invoice.invoice_items:
                    product = item.product
                    product.p_stock = product.p_stock + item.item_quantity
            
            db.session.commit()
            
            # Log activity
            log_activity('invoice_updated', f'Updated invoice {invoice_id} - Status: {new_status}')
            
            flash('Invoice updated successfully!', 'success')
            return redirect(url_for('seller_invoices'))
            
        except Exception as e:
            db.session.rollback()
            flash('Failed to update invoice', 'error')
    
    products = Product.query.filter_by(s_id=session['user_id']).all()
    customers = Customer.query.all()
    products_data = [product.to_dict() for product in products]
    
    return render_template('seller/edit_invoice.html', invoice=invoice, products=products_data, customers=customers)


@app.route('/invoice/<invoice_id>')
@login_required
@role_required('seller')
def view_invoice(invoice_id):
    invoice = Invoice.query.get(invoice_id)
    
    if not invoice:
        flash('Invoice not found', 'error')
        return redirect(url_for('seller_dashboard'))
    
    # Check if seller has access to this invoice
    if invoice.s_id != session['user_id']:
        flash('Access denied', 'error')
        return redirect(url_for('seller_dashboard'))
    
    return render_template('invoice/view.html', invoice=invoice)


@app.route('/invoice/<invoice_id>/download')
@login_required
@role_required('seller')
def download_invoice(invoice_id):
    """Generate a simple PDF of the invoice and prompt download."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm
        from reportlab.lib import colors
    except Exception:
        flash('PDF generation dependency missing. Please install reportlab.', 'error')
        return redirect(url_for('view_invoice', invoice_id=invoice_id))

    invoice = Invoice.query.get(invoice_id)
    if not invoice or invoice.s_id != session.get('user_id'):
        flash('Invoice not found or access denied', 'error')
        return redirect(url_for('seller_invoices'))

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 30 * mm
    pdf.setFont('Helvetica-Bold', 16)
    pdf.drawString(20 * mm, y, f'Invoice #{invoice.invoice_no}')
    y -= 10 * mm

    pdf.setFont('Helvetica', 11)
    pdf.drawString(20 * mm, y, f'Date: {invoice.invoice_datetime.strftime("%Y-%m-%d %H:%M")}')
    y -= 6 * mm
    customer = Customer.query.get(invoice.c_id)
    if customer:
        pdf.drawString(20 * mm, y, f'Bill To: {customer.c_name}  <{customer.c_email}>')
        y -= 10 * mm

    # Table headers
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(20 * mm, y, 'Product')
    pdf.drawString(100 * mm, y, 'Qty')
    pdf.drawString(120 * mm, y, 'Price (₹)')
    pdf.drawString(155 * mm, y, 'Total (₹)')
    y -= 5 * mm
    pdf.setStrokeColor(colors.black)
    pdf.line(20 * mm, y, 190 * mm, y)
    y -= 6 * mm

    pdf.setFont('Helvetica', 11)
    subtotal = Decimal('0')
    for item in invoice.invoice_items:
        product = item.product
        price = product.p_price
        line_total = (price * item.item_quantity) - item.discount
        subtotal += line_total
        pdf.drawString(20 * mm, y, f'{product.p_name}')
        pdf.drawRightString(115 * mm, y, str(item.item_quantity))
        pdf.drawRightString(145 * mm, y, f'{price:.2f}')
        pdf.drawRightString(190 * mm, y, f'{line_total:.2f}')
        y -= 6 * mm
        if y < 40 * mm:
            pdf.showPage()
            y = height - 20 * mm

    # Summary
    y -= 4 * mm
    pdf.line(120 * mm, y, 190 * mm, y)
    y -= 8 * mm
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawRightString(170 * mm, y, 'Subtotal:')
    pdf.setFont('Helvetica', 12)
    pdf.drawRightString(190 * mm, y, f'{subtotal:.2f}')
    y -= 6 * mm
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawRightString(170 * mm, y, 'Tax:')
    pdf.setFont('Helvetica', 12)
    pdf.drawRightString(190 * mm, y, f'{invoice.tax:.2f}')
    y -= 8 * mm
    pdf.setFont('Helvetica-Bold', 13)
    pdf.drawRightString(170 * mm, y, 'Total:')
    pdf.setFont('Helvetica-Bold', 13)
    pdf.drawRightString(190 * mm, y, f'{invoice.amount:.2f}')

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    filename = f"{invoice.invoice_no}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

@app.errorhandler(500)
def handle_internal_error(error):
    flash('An unexpected error occurred. Please try again later.', 'error')
    return redirect(url_for('seller_dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False, host='0.0.0.0', port=5000)