from flask import Flask
from ext import database
from api.customer import cs_bp
from api.account import ac_bp
from api.manage import mg_bp
from flask_migrate import Migrate
import config

app = Flask(__name__)
app.config.from_object(config)
database.init_app(app)
migrate = Migrate(app=app, db=database)
app.register_blueprint(cs_bp)
app.register_blueprint(ac_bp)
app.register_blueprint(mg_bp)

@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    app.run(host='0.0.0.0')
