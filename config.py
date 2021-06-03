"""
BACKEND CONFIG FILE

Configure parameters here
"""

DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "DB_PASSWORD"
DB_NAME = 'Bank'

SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8"

SEC_VALID_TIME = 3600
