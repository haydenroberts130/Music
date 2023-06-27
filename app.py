from flask import Flask, request, redirect, render_template
import firebase_admin
from flask_login import login_user, login_required, logout_user, LoginManager, current_user
from firebase_admin import credentials, firestore
import hashlib
from google.cloud import storage
import re
from data import *

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id
        is_active = True
    
    def get_id(self):
        return self.id

config = {}
config["SECRET_KEY"] = "123"

app = Flask(__name__)
app.config.from_mapping(config)
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    user = User(user_id)
    return user

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
        role = request.form['role']
        if validate_credentials(email, password, role):
            user = User(email)
            login_user(user)
            return redirect('/dash')
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
        if role == 'artist':
            genres = request.form.getlist('genres[]')
            description = request.form['description']
            name = request.form['name']
            artist = Artist(name, email, hashed_password, genres, description)
            db.collection('artists').add(artist.to_dict())
        elif role == 'fan':
            fan = Fan(email, hashed_password)
            db.collection('fans').add(fan.to_dict())
        return redirect('/login')
    return render_template('register.html')

@app.route('/dash')
@login_required
def dashboard():
    artists = []
    artist_collection = db.collection('artists').get()
    for artist in artist_collection:
        artists.append(artist.to_dict())
    return render_template('dash.html', artists=artists)

@app.route('/artist/<name>', methods=['GET', 'POST'])
@login_required
def artist(name):
    if request.method == 'POST':
        artist_ref = db.collection('artists').where('name', '==', name).limit(1)
        artist_docs = artist_ref.stream()
        for doc in artist_docs:
            artist = doc.to_dict()
            return render_template('artist.html', name=artist['name'], description=artist['description'], genres=artist['genres'], current_user=current_user.id, email=artist['email'])
    return render_template('dash.html')

def create_bucket_if_not_exists(bucket_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    if not bucket.exists():
        storage_client.create_bucket(bucket, location="us")

@app.route('/upload_image', methods=['POST'])
def upload_image():
    image_file = request.files['image']
    title = request.form.get('title')
    description = request.form.get('description')
    email = request.form.get('email')
    bucket_name = re.sub(r'[^a-z0-9-_]', '', email.lower()) + '-images'
    create_bucket_if_not_exists(bucket_name)
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob_name = image_file.filename
    blob = bucket.blob(blob_name)
    blob.upload_from_file(image_file)
    if title or description:
        metadata = {}
        if title:
            metadata['title'] = title
        if description:
            metadata['description'] = description
        blob.metadata = metadata
        blob.patch()
    return redirect('/dash')

@app.route('/upload_song', methods=['POST'])
def upload_song():
    song_file = request.files['song']
    song_title = request.form.get('song_title')
    album_name = request.form.get('album_name')
    song_description = request.form.get('song_description')
    email = request.form.get('email')
    bucket_name = re.sub(r'[^a-z0-9-_]', '', email.lower()) + '-songs'
    create_bucket_if_not_exists(bucket_name)
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob_name = song_file.filename
    blob = bucket.blob(blob_name)
    blob.upload_from_file(song_file)
    if song_title or album_name or song_description:
        metadata = {}
        if song_title:
            metadata['song_title'] = song_title
        if album_name:
            metadata['album_name'] = album_name
        if song_description:
            metadata['song_description'] = song_description
        blob.metadata = metadata
        blob.patch()
    return redirect('/dash')

if __name__ == "__main__":
    app.run(port=5001, debug=True)


