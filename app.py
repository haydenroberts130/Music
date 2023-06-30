from data import *

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

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        manager = UserManager()
        if manager.validate_credentials(email, password, role):
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
        manager = UserManager()
        hashed_password = manager.hash_password(password)
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

@app.route('/upload_image', methods=['POST'])
def upload_image():
    image_file = request.files['image']
    title = request.form.get('title')
    description = request.form.get('description')
    manager = BucketManager()
    bucket = manager.get_image_bucket(request.form.get('email'))
    manager.upload_image(image_file, title, description, bucket)
    return redirect('/dash')

@app.route('/upload_song', methods=['POST'])
def upload_song():
    song_file = request.files['song']
    song_title = request.form.get('song_title')
    album_name = request.form.get('album_name')
    song_description = request.form.get('song_description')
    manager = BucketManager()
    bucket = manager.get_song_bucket(request.form.get('email'))
    manager.upload_song(song_file, song_title, album_name, song_description, bucket)
    return redirect('/dash')

@app.route('/artist/<name>/view_songs', methods=['POST'])
@login_required
def view_songs(name):
    manager = BucketManager()
    email = request.form.get('email')
    bucket = manager.get_song_bucket(email)
    songs = manager.get_songs_from_bucket(bucket)
    return render_template('view_songs.html', name=name, songs=songs, email=email)

@app.route('/artist/<name>/view_images', methods=['POST'])
@login_required
def view_images(name):
    manager = BucketManager()
    bucket = manager.get_image_bucket(request.form.get('email'))
    images = manager.get_images_from_bucket(bucket)
    return render_template('view_images.html', name=name, images=images)

@app.route('/post_message', methods=['POST'])
def post_message():
    manager = MessageManager(request.form.get('email'))
    manager.post_message(request.form.get('message'))
    return redirect('/dash')

@app.route('/artist/<name>/view_messages', methods=['POST'])
def view_messages(name):
    manager = MessageManager(request.form.get('email'))
    messages = manager.get_messages()
    return render_template('view_messages.html', messages=messages, name=name)

@app.route('/follow_artist', methods=['POST'])
def follow_artist():
    email = request.form.get('email')
    manager = UserManager()
    manager.follow_artist(email)
    return redirect('/dash')

@app.route('/unfollow_artist', methods=['POST'])
def unfollow_artist():
    email = request.form.get('email')
    manager = UserManager()
    manager.unfollow_artist(email)
    return redirect('/dash')

@app.route('/add_rating', methods=['POST'])
def add_rating():
    rating = request.form.get('rating')
    song_title = request.form.get('song_title')
    review = request.form.get('review')
    manager = BucketManager()
    bucket = manager.get_song_bucket(request.form.get('email'))
    manager.add_rating_to_song(rating, song_title, review, bucket)
    return redirect('/dash')

@app.route('/reviews/<song_id>', methods=['POST'])
def view_reviews(song_id):
    email = request.form.get('email')
    song_title = request.form.get('song_title')
    manager = BucketManager()
    bucket = manager.get_song_bucket(email)
    reviews = manager.get_reviews_from_song(bucket, song_title)
    return render_template('reviews.html', email=email, song_title=song_title, reviews=reviews)

if __name__ == "__main__":
    app.run(port=5001, debug=True)