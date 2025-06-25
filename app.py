from flask import Flask
from config import configure_app, db
from blueprints.auth.routes import auth_bp
from blueprints.main.routes import main_bp
from blueprints.hackathon.routes import hackathon_bp

app = Flask(__name__)
configure_app(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(main_bp)
app.register_blueprint(hackathon_bp)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)