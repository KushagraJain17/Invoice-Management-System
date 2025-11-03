import os
from dotenv import load_dotenv

# Load .env from project root if present
load_dotenv()


basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configuration using environment variables.

    Notes:
    - No secrets should be committed to the repo.
    - Default storage is SQLite file in project directory. To override, set DATABASE_URL.
    """

    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me')
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_PERMANENT = False

    # Database: prefer DATABASE_URL if set; otherwise use local SQLite file
    sqlite_path = os.path.join(basedir, 'invoice.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{sqlite_path}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Other configurations
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    PREFERRED_URL_SCHEME = os.environ.get('PREFERRED_URL_SCHEME', 'https')
