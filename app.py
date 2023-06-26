from flask import Flask, request, redirect, render_template
import firebase_admin
from firebase_admin import credentials, firestore
import hashlib

app = Flask(__name__)

#firestore details
cred = credentials.Certificate('training-project-388915-firebase-adminsdk-7tfwk-7384b5f0ef.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route('/')
def home():
    return render_template('home.html')

def hash_password(password):
    hash_object = hashlib.sha256(password.encode())
    hashed_password = hash_object.hexdigest()
    return hashed_password

def validate_credentials(email, password, role):
    if role == 'artist':
        users_ref = db.collection('artists')
    elif role == 'fan':
        users_ref = db.collection('fans')
    else:
        return False
    query = users_ref.where('email', '==', email).limit(1).get()
    for doc in query:
        user_data = doc.to_dict()
        stored_password = user_data.get('password')
        if stored_password == hash_password(password):
            return True
    return False


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if validate_credentials(email, password):
            return redirect('/movies')
        else:
            return render_template('login.html', error_message='Invalid email or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        hashed_password = hash_password(password)
        user_data = {
            'email': email,
            'password': hashed_password,
            'role': role
        }
        if role == 'artist':
            genres = request.form.getlist('genres[]')
            description = request.form['description']
            user_data['genres'] = genres
            user_data['description'] = description
            db.collection('artists').add(user_data)
        elif role == 'fan':
            db.collection('fans').add(user_data)
        return redirect('/login')
    return render_template('register.html')

if __name__ == "__main__":
    app.run(port=5001, debug=True)


