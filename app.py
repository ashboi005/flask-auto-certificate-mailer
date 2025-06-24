from flask import Flask, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from config import configure_app, db
from models import User

app = Flask(__name__)
configure_app(app)

@app.route('/')
def hello():
    return 'Hello, World!'

@app.route('/signup', methods=['POST'])
def register():
    data = request.get_json()
    username = data['username']
    email = data['email']
    password = data['password']
    password_hash = generate_password_hash(password)
    new_user = User(username=username, email=email, password_hash=password_hash)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        return jsonify({'message': 'Login successful'}), 200
    return jsonify({'message': 'Invalid credentials'}), 401

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)