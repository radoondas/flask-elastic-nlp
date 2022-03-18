from flask import Flask
from config import Config
from sentence_transformers import SentenceTransformer

app = Flask(__name__)
app.config.from_object(Config)
# Load model, run against the image and create image embedding
img_model = SentenceTransformer('clip-ViT-B-32')

from app import routes
