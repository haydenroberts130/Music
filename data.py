from flask_login import UserMixin
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

class FireBaseTemplate():
    def __init__(self):
        self._key = 'training-project-388915-firebase-adminsdk-7tfwk-7384b5f0ef.json'
        self._credentials = Credentials.from_service_account_file(self._key)
        self._storage_client = storage.Client(credentials=self._credentials)
    
    def create_bucket_if_not_exists(self, bucket_name):
        storage_client = storage.Client()
        bucket = storage.Bucket(storage_client, bucket_name)
        if not bucket.exists():
            bucket.create(location="us")

    def get_image_bucket(self, email):
        bucket_name = "haydens-music-" + re.sub(r'[^a-z0-9-_]', '', email.lower()) + '-images'
        self.create_bucket_if_not_exists(bucket_name)
        storage_client = self._storage_client
        bucket = storage_client.bucket(bucket_name)
        return bucket
    
    def upload_image(self, image_file, title, description, bucket):
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
    
    def get_song_bucket(self, email):
        bucket_name = "haydens-music-" + re.sub(r'[^a-z0-9-_]', '', email.lower()) + '-songs'
        self.create_bucket_if_not_exists(bucket_name)
        storage_client = self._storage_client
        bucket = storage_client.bucket(bucket_name)
        return bucket
    
    def upload_song(self, song_file, song_title, album_name, song_description, bucket):
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
    
    def get_songs_from_bucket(self, bucket):
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
        return songs
    
    def get_images_from_bucket(self, bucket):
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
        return images
    
    def add_rating_to_song(rating, song_title, review, bucket):
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
    
    def get_reviews_from_song(self, bucket, song_title):
        blobs = bucket.list_blobs()
        for blob in blobs:
            if blob.metadata["song_title"] == song_title:
                metadata = blob.metadata or {}
                if "reviews" in metadata:
                    reviews = ast.literal_eval(metadata.get("reviews")).values()
                    return reviews
        return None

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
