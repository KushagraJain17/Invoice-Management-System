# Invoice Management System

A modern invoice management system built with Python Flask that allows sellers to manage products and invoices. Features SQLite database by default for easy deployment and local development.

## Live Demo
**🚀 [View Live Demo](https://invoice-management-system-5u38.onrender.com)**

**Note:** The app is hosted on Render's free tier, so the first request may take 50-60 seconds to load as the service spins up from sleep mode. Subsequent requests will be faster.

*Note: This is a demo environment. Any data you create may be reset periodically.*

---


## Features

### Seller Dashboard

- **Product Management**: Full CRUD operations for products
  - Add new products with name, price, description, and stock
  - Edit existing products
  - Delete products (with validation to prevent deletion of products in invoices)
  - View product inventory
- **Invoice Management**: Comprehensive invoice handling
  - View all invoices with advanced filtering (date range, amount range, status, customer)
  - Create invoices with multiple products, discounts, and tax
  - Edit invoice status and details
  - Track invoice status (paid, pending, overdue)
  - Download invoices as PDF
  - Dashboard automatically includes overdue invoices in unpaid count and amount due
- **Customer Management**: Manage customer database
  - Add, edit, and view customers
  - View invoices per customer
- **Activity Tracking**: Recent activity feed showing system actions

### Customer Dashboard

- **Invoice Viewing**: View all invoices sent to the customer
- **Invoice Details**: Detailed view of individual invoices with itemized breakdown
- **Download Invoices**: Download invoices as PDF files

### Security Features

- **Password Hashing**: All passwords are securely hashed using Werkzeug
- **Session Management**: Non-persistent sessions that expire when browser is closed
- **Role-based Access**: Separate authentication and access control for sellers and customers
- **Secure Cookies**: HTTP-only, secure, SameSite cookie settings

## Technology Stack

- **Backend**: Python Flask web framework
- **Database**: SQLite (default) with optional DATABASE_URL support for PostgreSQL/MySQL
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla JS)
- **Templates**: Jinja2 templating engine
- **PDF Generation**: ReportLab for invoice PDFs
- **Authentication**: Flask sessions with Werkzeug password hashing

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)
- (Optional) Virtual environment (recommended)

### Installation

1. **Clone the repository:**

```bash
git clone <repository-url>
cd invoice-management-system
```

2. **Create a virtual environment (recommended):**

```bash
# On Windows (PowerShell):
python -m venv venv
venv\Scripts\activate

# On macOS/Linux:
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**

Copy the example environment file:

```bash
# Windows (PowerShell):
copy env_example.txt .env

# macOS/Linux:
cp env_example.txt .env
```

Edit `.env` file with your settings:

```env
SECRET_KEY=replace-with-a-long-random-string
FLASK_DEBUG=False
PREFERRED_URL_SCHEME=https
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_SAMESITE=Lax
```

**Note**: The app uses SQLite by default (creates `invoice.db` in the project directory). No database server setup required!

5. **Initialize the database (optional - creates sample data):**

```bash
python init_db.py
```

6. **Run the application:**

```bash
python app.py
```

7. **Open browser:** [http://localhost:5000](http://localhost:5000)

## Environment Configuration

The application uses environment variables for configuration. Create a `.env` file based on `env_example.txt`.

### Required Environment Variables

- `SECRET_KEY`: A secure random string for Flask session encryption (required for production)

### Optional Environment Variables

- `FLASK_DEBUG`: Set to `True` for development, `False` for production (default: `False`)
- `DATABASE_URL`: Optional - only if you want to use PostgreSQL or MySQL instead of SQLite
  - PostgreSQL: `postgresql+psycopg2://user:password@host:5432/dbname`
  - MySQL: `mysql+pymysql://user:password@host:3306/dbname`
- `SESSION_COOKIE_SECURE`: Set to `True` in production with HTTPS (default: `True`)
- `SESSION_COOKIE_SAMESITE`: Cookie SameSite policy (default: `Lax`)

### Database

By default, the app uses SQLite and creates an `invoice.db` file in the project directory. This makes it easy to:

- Run locally without installing a database server
- Deploy to platforms like Render without additional database services
- Backup by simply copying the `.db` file

If you want to use a managed database (PostgreSQL/MySQL) for production, set the `DATABASE_URL` environment variable.

## Database Schema

The application creates the following tables:

- **`sellers`**: S_ID (PK), S_NAME, S_EMAIL, S_ADDRESS, S_PHONE, PASSWORD
- **`customers`**: C_ID (PK), C_NAME, C_EMAIL, C_PHONE_NO, C_ADDRESS, PASSWORD
- **`products`**: P_ID (PK), P_NAME, P_PRICE, P_DESCRIPTION, P_STOCK, S_ID (FK)
- **`invoices`**: INVOICE_NO (PK), INVOICE_DATETIME, STATUS, TAX, AMOUNT, S_ID (FK), C_ID (FK)
- **`invoice_items`**: ITEM_ID (PK), INVOICE_NO (FK), P_ID (FK), ITEM_QUANTITY, DISCOUNT
- **`activities`**: Activity log for tracking user actions

## API Endpoints

- `GET /` - Redirects to login or appropriate dashboard
- `GET/POST /login` - User login
- `GET/POST /register` - User registration (seller only)
- `GET /logout` - User logout
- `GET /seller` - Seller dashboard
- `GET /seller/products` - Product management page
- `GET/POST /seller/products/add` - Add new product
- `GET/POST /seller/products/edit/<id>` - Edit product
- `GET /seller/products/delete/<id>` - Delete product
- `POST /api/products/add` - API endpoint to add product from invoice page
- `GET /seller/customers` - Customer management page
- `GET/POST /seller/customers/add` - Add new customer
- `GET/POST /seller/customers/edit/<id>` - Edit customer
- `GET /seller/customers/<id>/invoices` - View customer's invoices
- `GET /seller/invoices` - Invoice management page
- `GET/POST /seller/invoices/create` - Create new invoice
- `GET/POST /seller/invoices/edit/<id>` - Edit invoice
- `GET /invoice/<id>` - View invoice details
- `GET /invoice/<id>/download` - Download invoice as PDF

## Usage Guide For Sellers:

1. **Register/Login** with seller credentials
2. **Manage Products**: Add, edit, or delete products from the Products tab
3. **Manage Customers**: Add and edit customer information
4. **Create Invoices**: Use the Create Invoice tab to generate new invoices
   - Select existing customer or create new one on the fly
   - Add multiple products with quantities and discounts
   - Real-time total calculation
5. **View Invoices**: Check all invoices with advanced filtering options
6. **Dashboard**: Monitor key metrics including overdue invoices and revenue

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
