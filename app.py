from flask import Flask, request, redirect, render_template
import firebase_admin
from flask_login import login_user, login_required, logout_user, LoginManager, current_user
from firebase_admin import credentials, firestore
import hashlib
from google.cloud import storage
import re
from data import *
from datetime import datetime, timedelta
import datetime
from google.oauth2.service_account import Credentials
import json
import ast

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
            current_user_id = current_user.id
            fan_ref = db.collection('fans').where('email', '==', current_user_id).limit(1).get()
            current_user_following = False
            if len(fan_ref) > 0:
                fan_doc = fan_ref[0].to_dict()
                if 'following' in fan_doc:
                     if artist['email'] in fan_doc['following']:
                        current_user_following = True
            return render_template('artist.html', name=artist['name'], description=artist['description'], genres=artist['genres'], current_user=current_user.id, email=artist['email'], current_user_following = current_user_following)
    return render_template('dash.html')

def create_bucket_if_not_exists(bucket_name):
    storage_client = storage.Client()
    bucket = storage.Bucket(storage_client, bucket_name)
    if not bucket.exists():
        bucket.create(location="us")

@app.route('/upload_image', methods=['POST'])
def upload_image():
    image_file = request.files['image']
    title = request.form.get('title')
    description = request.form.get('description')
    email = request.form.get('email')
    bucket_name = "haydens-music-" + re.sub(r'[^a-z0-9-_]', '', email.lower()) + '-images'
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
    bucket_name = "haydens-music-" + re.sub(r'[^a-z0-9-_]', '', email.lower()) + '-songs'
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

@app.route('/artist/<name>/view_songs', methods=['POST'])
@login_required
def view_songs(name):
    email = request.form.get('email')
    bucket_name = "haydens-music-" + re.sub(r'[^a-z0-9-_]', '', email.lower()) + '-songs'
    create_bucket_if_not_exists(bucket_name)
    credentials = Credentials.from_service_account_file('training-project-388915-firebase-adminsdk-7tfwk-7384b5f0ef.json')
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs()
    songs = []
    for blob in blobs:
        song = {}
        song['name'] = blob.name
        song['metadata'] = blob.metadata
        song['url'] = blob.generate_signed_url(
            version='v4',
            expiration=datetime.datetime.utcnow() + timedelta(minutes=5),
            method='GET'
        )
        songs.append(song)
    return render_template('view_songs.html', name=name, songs=songs, email=email)


@app.route('/artist/<name>/view_images', methods=['POST'])
@login_required
def view_images(name):
    email = request.form.get('email')
    bucket_name = "haydens-music-" + re.sub(r'[^a-z0-9-_]', '', email.lower()) + '-images'
    create_bucket_if_not_exists(bucket_name)
    credentials = Credentials.from_service_account_file('training-project-388915-firebase-adminsdk-7tfwk-7384b5f0ef.json')
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs()
    images = []
    for blob in blobs:
        image = {}
        image['name'] = blob.name
        image['metadata'] = blob.metadata
        image['url'] = blob.generate_signed_url(
            version='v4',
            expiration=datetime.datetime.utcnow() + timedelta(minutes=5),
            method='GET'
        )
        images.append(image)
    return render_template('view_images.html', name=name, images=images)

@app.route('/post_message', methods=['POST'])
def post_message():
    message = request.form.get('message')
    email = request.form.get('email')
    current_date_time = datetime.datetime.now()
    formatted_date = current_date_time.strftime("%B %d, %Y %I:%M %p")
    query = db.collection('artists').where('email', '==', email)
    artist_docs = query.get()
    if artist_docs:
        for artist_doc in artist_docs:
            if 'messages' in artist_doc.to_dict():
                messages = artist_doc.get('messages')
            else:
                messages = []
            messages.append({
                'message': message,
                'timestamp': formatted_date
            })
            artist_doc.reference.update({'messages': messages})
    return redirect('/dash')

@app.route('/artist/<name>/view_messages', methods=['POST'])
def view_messages(name):
    email = request.form.get('email')
    query = db.collection('artists').where('email', '==', email)
    artist_docs = query.get()
    messages = []
    if artist_docs:
        for artist_doc in artist_docs:
           if 'messages' in artist_doc.to_dict():
                artist_messages = artist_doc.to_dict()['messages']
                messages.extend(artist_messages)
    return render_template('view_messages.html', messages=messages, name=name)

@app.route('/follow_artist', methods=['POST'])
def follow_artist():
    email = request.form.get('email')
    current_user_id = request.form.get('current_user')
    artist_ref = db.collection('artists').where('email', '==', email).limit(1).get()
    if len(artist_ref) > 0:
        artist_doc = artist_ref[0].reference
        artist_doc.update({
            'followers': firestore.ArrayUnion([current_user_id])
        })

    fan_ref = db.collection('fans').where('email', '==', current_user_id).limit(1).get()
    if len(fan_ref) > 0:
        fan_doc = fan_ref[0].reference
        fan_doc.update({
            'following': firestore.ArrayUnion([email])
        })
    return redirect('/dash')

@app.route('/unfollow_artist', methods=['POST'])
def unfollow_artist():
    email = request.form.get('email')
    current_user_id = request.form.get('current_user')
    artist_ref = db.collection('artists').where('email', '==', email).limit(1).get()
    if len(artist_ref) > 0:
        artist_doc = artist_ref[0].reference
        artist_doc.update({
            'followers': firestore.ArrayRemove([current_user_id])
        })

    fan_ref = db.collection('fans').where('email', '==', current_user_id).limit(1).get()
    if len(fan_ref) > 0:
        fan_doc_ref = fan_ref[0].reference
        fan_doc_ref.update({
            'following': firestore.ArrayRemove([email])
        })
    return redirect('/dash')

@app.route('/add_rating', methods=['POST'])
def add_rating():
    rating = request.form.get('rating')
    song_title = request.form.get('song_title')
    review = request.form.get('review')
    email = request.form.get('email')
    bucket_name = "haydens-music-" + re.sub(r'[^a-z0-9-_]', '', email.lower()) + '-songs'
    credentials = Credentials.from_service_account_file('training-project-388915-firebase-adminsdk-7tfwk-7384b5f0ef.json')
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs()
    for blob in blobs:
        if blob.metadata["song_title"] == song_title:
            metadata = blob.metadata or {}
            if "reviews" in metadata:
                metadata_reviews = ast.literal_eval(metadata.get("reviews"))
                metadata_reviews[current_user.id] = [rating, review]
                metadata['reviews'] = metadata_reviews
            else:
                metadata['reviews'] = {current_user.id:[rating, review]}
            summed = 0
            reviews = metadata["reviews"]
            for review in reviews:
                summed += float(reviews[review][0])
            metadata["average_rating"] = summed / len(reviews) 
            blob.metadata = metadata
            blob.patch()
    return redirect('/dash')

if __name__ == "__main__":
    app.run(port=5001, debug=True)


