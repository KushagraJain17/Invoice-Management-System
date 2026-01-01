# Invoice Management System

A modern, minimalist invoice management system built with Python Flask that allows sellers to manage products and invoices, and customers to view their invoices.

## Features

### Authentication

- **Login/Registration**: Separate login and registration pages for sellers and customers
- **Role-based Access**: Different dashboards based on user role (seller/customer)
- **Session Management**: Secure session management with Flask sessions

### Seller Dashboard

- **Product Management**: Full CRUD operations for products
  - Add new products with name, price, description, and stock
  - Edit existing products
  - Delete products
  - View product inventory with low stock warnings
- **Invoice Management**: View and manage all invoices
  - View invoice details with customer information
  - Download invoices as PDF
  - Track invoice status (paid, pending, overdue)
- **Create Invoices**: Comprehensive invoice creation
  - Select customers from dropdown
  - Add multiple products with quantities and discounts
  - Real-time total calculation including tax
  - Professional invoice formatting

### Admin Dashboard

- **Seller Management**: Manage all sellers in the system
  - View all registered sellers
  - Edit seller information
  - Monitor seller activity and status
  - Approve or manage seller registrations
- **System Overview**: Administrative access to system-wide information

### Customer Dashboard

- **Invoice Viewing**: View all invoices sent to the customer
- **Invoice Details**: Detailed view of individual invoices with itemized breakdown
- **Download Invoices**: Download invoices as PDF files
- **Activity Tracking**: Recent activity feed showing payment status

### UI/UX Features

- **Minimalist Design**: Clean, modern interface with subtle shadows and rounded corners
- **Responsive Layout**: Works seamlessly on desktop, tablet, and mobile devices
- **Status Indicators**: Color-coded badges for invoice status and stock levels
- **Alert System**: Success and error notifications for user actions
- **Dynamic Forms**: Interactive invoice creation with real-time calculations

## Technology Stack

- **Backend**: Python Flask web framework
- **Database**: MySQL with SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla JS)
- **Templates**: Jinja2 templating engine
- **Icons**: Font Awesome for consistent iconography
- **Styling**: Custom CSS with utility classes and responsive design
- **Authentication**: Flask sessions with password hashing

## Project Structure

```
invoicemanagement/
├── app.py                 # Main Flask application
├── config.py              # Configuration management
├── models.py              # SQLAlchemy database models
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── templates/             # HTML templates
│   ├── base.html
│   ├── auth/
│   │   ├── login.html
│   │   ├── register.html
│   │   └── verify_otp.html
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── sellers.html
│   │   └── edit_seller.html
│   ├── seller/
│   │   ├── dashboard.html
│   │   ├── products.html
│   │   ├── add_product.html
│   │   ├── edit_product.html
│   │   ├── invoices.html
│   │   ├── create_invoice.html
│   │   ├── edit_invoice.html
│   │   ├── customers.html
│   │   ├── edit_customer.html
│   │   └── customer_analytics.html
│   ├── customer/
│   │   └── dashboard.html
│   ├── invoice/
│   │   └── view.html
│   └── email/
│       ├── invoice_email.html
│       └── otp_email.html
├── static/                # Static files
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)
- MySQL Server 5.7 or higher

### Installation

1. **Clone the repository:**

```bash
git clone https://github.com/KushagraJain17/Invoice-Management-System.git
cd Invoice-Management-System
```

2. **Install MySQL Server:**

   - **Windows**: Download from [MySQL Official Website](https://dev.mysql.com/downloads/mysql/)
   - **macOS**: `brew install mysql` or download from MySQL website
   - **Linux**: `sudo apt-get install mysql-server` (Ubuntu/Debian)

3. **Start MySQL Service:**

   - **Windows**: Start MySQL service from Services or MySQL Workbench
   - **macOS/Linux**: `sudo systemctl start mysql` or `brew services start mysql`

4. **Create a virtual environment (recommended):**

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

5. **Configure database settings:**

Create a `.env` file in the project root by copying the example file:

```bash
# Copy the example environment file
cp .env.example .env
```

Edit the `.env` file with your actual configuration:

```env
# MySQL Database Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USERNAME=root
MYSQL_PASSWORD=your_mysql_password_here
MYSQL_DATABASE=inventory_db

# Flask Configuration
SECRET_KEY=your-secret-key-change-this-in-production
FLASK_DEBUG=True

# Admin Credentials (change these in production!)
ADMIN_EMAIL=admin@admin.com
ADMIN_PASSWORD=admin

# Email Configuration (for OTP verification)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_gmail_app_password_here
MAIL_DEFAULT_SENDER=your_email@gmail.com
```

> [!WARNING]
> **Security Note**: 
> - Never commit your `.env` file to version control
> - Change the default admin credentials in production
> - Use a strong, unique SECRET_KEY (you can generate one with `python -c "import secrets; print(secrets.token_hex(16))"`)
> - For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password

6. **Install dependencies:**

```bash
pip install -r requirements.txt
```

7. **Create MySQL database:**

Log into MySQL and create the database:

```sql
CREATE DATABASE inventory_db;
```

8. **Start the application:**

The database tables will be created automatically on first run:

```bash
python app.py
```

9. **Open browser:** [http://localhost:8000](http://localhost:8000)

> [!NOTE]
> The application will automatically create all necessary database tables on first run using SQLAlchemy.

## Running the Application

```bash
python app.py
```

## Database Configuration

### Environment Variables

All application configuration is managed through environment variables in the `.env` file. See the `.env.example` file for a complete list of required variables and their descriptions.

**Important Variables:**
- **Database**: MySQL connection settings
- **Security**: Flask SECRET_KEY for session management
- **Admin**: Admin account credentials for administrative access
- **Email**: SMTP settings for OTP verification during seller registration

## Key Features Implementation

### CRUD Operations

- **Products**: Create, Read, Update, Delete with validation
- **Invoices**: Create with dynamic item addition, Read with detailed views
- **User Profiles**: Registration and profile management

### Responsive Design

- Flexible grid layouts that adapt to screen size
- Touch-friendly button sizes and spacing
- Optimized table layouts for mobile viewing

## Usage Guide

### For Admins:

1. **Login** with admin credentials (see `.env` file)
2. **Manage Sellers**: View and edit all registered sellers
3. **Monitor System**: Access system-wide information and statistics

### For Sellers:

1. **Login** with seller credentials
2. **Manage Products**: Add, edit, or delete products from the Products tab
3. **Create Invoices**: Use the Create Invoice tab to generate new invoices
4. **View Invoices**: Check all invoices and their status in the Invoices tab

### For Customers:

1. **Login** with customer credentials
2. **View Invoices**: See all invoices sent to you
3. **Invoice Details**: Click on any invoice to see detailed breakdown

## Future Enhancements

- **File Upload**: Allow product image uploads
- **Payment Processing**: Integrate with payment gateways (Stripe, PayPal)
- **Multi-tenancy**: Support multiple sellers/organizations
- **REST API**: Create API endpoints for mobile apps
- **Advanced Analytics**: Sales trends, revenue forecasting, customer insights
- **Export Options**: Export invoices to Excel/CSV
- **Notifications**: Push notifications for invoice updates
- **Multi-language Support**: Internationalization (i18n)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
