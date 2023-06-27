from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id
        is_active = True
    
    def get_id(self):
        return self.id

class Artist:
    def __init__(self, name, email, password, genres, description):
        self.name = name
        self.email = email
        self.password = password
        self.genres = genres
        self.description = description

    def to_dict(self):
        return {
            'name': self.name,
            'email': self.email,
            'password': self.password,
            'genres': self.genres,
            'description': self.description
        }

class Fan:
    def __init__(self, email, password):
        self.email = email
        self.password = password

    def to_dict(self):
        return {
            'email': self.email,
            'password': self.password
        }
