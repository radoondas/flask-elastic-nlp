from app import app
from flask import render_template, redirect, url_for, request
from app.searchForm import SearchForm
from app.inputFileForm import InputFileForm
from werkzeug.utils import secure_filename
import requests
import os
from sentence_transformers import SentenceTransformer
from PIL import Image


INFER_ENDPOINT = '/_ml/trained_models/sentence-transformers__clip-vit-b-32-multilingual-v1/deployment/_infer'
INFER_ENDPOINT_TEXT_CLASS = "/_ml/trained_models/distilbert-base-uncased-finetuned-sst-2-english/deployment/_infer"
INFER_ENDPOINT_NER = "/_ml/trained_models/dslim__bert-base-ner/deployment/_infer"
INFER_ENDPOINT_FILL_MASK = "/_ml/trained_models/bert-base-uncased/deployment/_infer"
INFER_ENDPOINT_LES_MISERABLE = "/_ml/trained_models/sentence-transformers__msmarco-minilm-l-12-v3/deployment/_infer"
KNN_SEARCH_IMAGES = '/image-embeddings/_knn_search'
KNN_SEARCH_LES_MISERABLE = '/les-miserable-embedded/_knn_search'


HOST = app.config['ELASTICSEARCH_HOST']
AUTH = (app.config['ELASTICSEARCH_USER'], app.config['ELASTICSEARCH_PASSWORD'])
HEADERS = {'Content-Type': 'application/json'}


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Home')


@app.route('/search', methods=['GET', 'POST'])
def search():
    form = SearchForm()
    # Check for  method
    if request.method == 'POST':
        if form.validate_on_submit():
            # print("Other: " + str(form.validate_on_submit()))
            # print("Query: " + request.args.get('query'))
            # print("Method: " + request.method)
            # print("Searchbox data:" + form.searchbox.data)

            embeddings = sentence_embedding(form.searchbox.data)
            search_response = knn_search_images(embeddings)

            return render_template('search.html', title='Image search', form=form, search_results=search_response.json()['hits']['hits'], query=form.searchbox.data)

        else:
            return redirect(url_for('search'))
    else:  # GET
        return render_template('search.html', title='Image search', form=form)


@app.route('/classification', methods=['GET', 'POST'])
def classification():
    form = SearchForm()
    # Check for  method
    if request.method == 'POST':
        if form.validate_on_submit():
            search_response = text_classification(form.searchbox.data)

            return render_template('classification.html', title='Classification', form=form,
                                   search_results=search_response, query=form.searchbox.data)

        else:
            return redirect(url_for('classification'))
    else:  # GET
        return render_template('classification.html', title='Classification', form=form)


@app.route('/ner', methods=['GET', 'POST'])
def ner():
    form = SearchForm()
    # Check for  method
    if request.method == 'POST':
        if form.validate_on_submit():
            search_response = ner_nlp_query(form.searchbox.data)

            return render_template('ner.html', title='NER', form=form,
                                   search_results=search_response, query=form.searchbox.data)

        else:
            return redirect(url_for('ner'))
    else:  # GET
        return render_template('ner.html', title='NER', form=form)


@app.route('/fill_mask', methods=['GET', 'POST'])
def fill_mask():
    form = SearchForm()
    # Check for  method
    if request.method == 'POST':
        if form.validate_on_submit():
            search_response = fill_mask_query(form.searchbox.data)

            return render_template('fill_mask.html', title='Fill Mask', form=form,
                                   search_results=search_response, query=form.searchbox.data)
        else:
            return redirect(url_for('fill_mask'))
    else:  # GET
        return render_template('fill_mask.html', title='Fill Mask', form=form)


@app.route('/embeddings', methods=['GET', 'POST'])
def embeddings():
    form = SearchForm()
    # Check for  method
    if request.method == 'POST':
        if form.validate_on_submit():
            embeddings_response = sentence_embedding_les_miserable(form.searchbox.data)
            search_response = knn_search_embeddings(embeddings_response)

            return render_template('embeddings.html', title='Embeddings', form=form, search_results=search_response.json()['hits']['hits'], query=form.searchbox.data)

        else:
            return redirect(url_for('embeddings'))
    else:  # GET
        return render_template('embeddings.html', title='Embeddings', form=form)


@app.route('/similar_image', methods=['GET', 'POST'])
def similar_image():
    form = InputFileForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            if request.files['file'].filename == '':
                return render_template('similar_image.html', title='Vision', form=form, err='No selected file')

            filename = secure_filename(form.file.data.filename)

            url_dir = 'static/tmp-uploads/'
            upload_dir = 'app/' + url_dir
            upload_exists = os.path.exists(upload_dir)
            if not upload_exists:
                # Create a new directory because it does not exist
                os.makedirs(upload_dir)
                print("The new directory is created!")

            file_path = upload_dir + filename
            url_path_file = url_dir + filename
            form.file.data.save(upload_dir + filename)

            # TODO: add delete image

            img_model = SentenceTransformer('clip-ViT-B-32')
            embedding = image_embedding(file_path, img_model)
            # Execute KN search over the image dataset
            search_response = knn_search_images(embedding.tolist())

            return render_template('similar_image.html', title='Vision', form=form, search_results=search_response.json()['hits']['hits'], original_file=url_path_file)
        else:
            return redirect(url_for('cloud_vision'))
    else:
        return render_template('similar_image.html', title='Vision', form=form)


def sentence_embedding(query: str):
    inf = '{ "docs" : [ {"text_field": "' + query + '"} ] }'

    response = requests.post(HOST + INFER_ENDPOINT, auth=AUTH, headers=HEADERS, data=inf)

    return response.json()['predicted_value']


def knn_search_images(dense_vector: list):
    query = ('{ "knn" : '
             '{"field": "image_embedding",'
             '"k": 5,'
             '"num_candidates": 100,'
             '"query_vector" : ' + str(dense_vector) + '},'
             '"fields": ["photo_description", "ai_description", "photo_url", "photo_image_url"],'
             '"_source": false'
             '}'
             )

    return requests.get(HOST + KNN_SEARCH_IMAGES, auth=AUTH, headers=HEADERS, data=query)


def print_hits(search_response):
    hits = search_response.json()['hits']['hits']
    for hit in hits:
        fields = hit['fields']
        print("photo_description: " + fields['photo_description'][0])
        print("ai_description: " + fields['ai_description'][0])
        print("photo_url: " + fields['photo_url'][0])
        print("score: " + str(hit['_score']))
        print("photo_image_url: " + fields['photo_image_url'][0])
        print()


def text_classification(query: str):
    inf = '{ "docs": { "text_field": "' + query + '"} }'
    response = requests.post(HOST + INFER_ENDPOINT_TEXT_CLASS, auth=AUTH, headers=HEADERS, data=inf)

    return response.json()


def ner_nlp_query(query: str):
    inf = '{ "docs": { "text_field": "' + query + '"} }'
    response = requests.post(HOST + INFER_ENDPOINT_NER, auth=AUTH, headers=HEADERS, data=inf)

    return response.json()


def fill_mask_query(query: str):
    inf = '{ "docs": { "text_field": "' + query + '"} }'
    response = requests.post(HOST + INFER_ENDPOINT_FILL_MASK, auth=AUTH, headers=HEADERS, data=inf)

    return response.json()


def sentence_embedding_les_miserable(query: str):
    inf = '{ "docs" : [ {"text_field": "' + query + '"} ] }'

    response = requests.post(HOST + INFER_ENDPOINT_LES_MISERABLE, auth=AUTH, headers=HEADERS, data=inf)

    return response.json()['predicted_value']


def knn_search_embeddings(dense_vector: list):
    query = ('{  "_source": ["paragraph", "line"], '
             '"knn" : {'
             '"field": "ml.inference.predicted_value",'
             '"k": 5,'
             '"num_candidates": 10,'
             '"query_vector" : ' + str(dense_vector) + '}'
             '}'
             )

    return requests.get(HOST + KNN_SEARCH_LES_MISERABLE, auth=AUTH, headers=HEADERS, data=query)


def image_embedding(image, model):
    return model.encode(image)


def load_image(url_or_path) -> Image:
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        return Image.open(requests.get(url_or_path, stream=True).raw)
    else:
        return Image.open(url_or_path)
