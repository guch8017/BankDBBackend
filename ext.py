from flask_sqlalchemy import SQLAlchemy

database = SQLAlchemy(session_options={'autocommit': True})