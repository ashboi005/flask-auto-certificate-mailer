from flask import Flask
from config import configure_app, db
from blueprints.auth.routes import auth_bp
from blueprints.main.routes import main_bp
from blueprints.hackathon.routes import hackathon_bp
from blueprints.certificates.routes import certificates_bp
from blueprints.csv.routes import csv_bp
from blueprints.bulk_email.routes import bulk_email_bp

app = Flask(__name__)
configure_app(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(main_bp)
app.register_blueprint(hackathon_bp)
app.register_blueprint(certificates_bp)
app.register_blueprint(csv_bp)
app.register_blueprint(bulk_email_bp)

if __name__ == '__main__':
    app.run(debug=True)