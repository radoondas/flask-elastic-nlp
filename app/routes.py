from app import app, img_model
from flask import render_template, redirect, url_for, request
from app.searchForm import SearchForm
from app.inputFileForm import InputFileForm
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import requests
import os
from PIL import Image

INFER_ENDPOINT = "/_ml/trained_models/{model}/deployment/_infer"

INFER_MODEL_IM_SEARCH = 'sentence-transformers__clip-vit-b-32-multilingual-v1'
INFER_MODEL_TEXT_CLASS = 'distilbert-base-uncased-finetuned-sst-2-english'
INFER_MODEL_NER = 'dslim__bert-base-ner'
INFER_MODEL_FILL_MASK = 'bert-base-uncased'
INFER_MODEL_LES_MISERABLE = 'sentence-transformers__msmarco-minilm-l-12-v3'

INDEX_IM_EMBED = 'image-embeddings'
KNN_SEARCH_IMAGES = "/{}/_knn_search".format(INDEX_IM_EMBED)
INDEX_LES_MIS = 'les-miserable-embedded'
KNN_SEARCH_LES_MISERABLE = "/{}/_knn_search".format(INDEX_LES_MIS)

HOST = app.config['ELASTICSEARCH_HOST']
AUTH = (app.config['ELASTICSEARCH_USER'], app.config['ELASTICSEARCH_PASSWORD'])
HEADERS = {'Content-Type': 'application/json'}

app_models = {}


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Home')


@app.route('/search', methods=['GET', 'POST'])
def search():
    global app_models
    is_model_up_and_running(INFER_MODEL_IM_SEARCH)

    index_name = INDEX_IM_EMBED
    if not is_index_present(index_name):
        return render_template('search.html', title='Image search', model_up=False,
                               index_name=index_name, missing_index=True)

    if app_models.get(INFER_MODEL_IM_SEARCH) == 'started':
        form = SearchForm()
        # Check for  method
        if request.method == 'POST':
            if form.validate_on_submit():
                embeddings = sentence_embedding(form.searchbox.data)
                search_response = knn_search_images(embeddings)

                return render_template('search.html', title='Image search', form=form,
                                       search_results=search_response.json()['hits']['hits'],
                                       query=form.searchbox.data,  model_up=True)

            else:
                return redirect(url_for('search'))
        else:  # GET
            return render_template('search.html', title='Image search', form=form, model_up=True)
    else:
        return render_template('search.html', title='Image search', model_up=False, model_name=INFER_MODEL_IM_SEARCH)


@app.route('/classification', methods=['GET', 'POST'])
def classification():
    global app_models
    is_model_up_and_running(INFER_MODEL_TEXT_CLASS)

    if app_models.get(INFER_MODEL_TEXT_CLASS) == 'started':
        form = SearchForm()
        # Check for  method
        if request.method == 'POST':
            if form.validate_on_submit():
                search_response = text_classification(form.searchbox.data)

                return render_template('classification.html', title='Classification', form=form,
                                       search_results=search_response, query=form.searchbox.data, model_up=True)

            else:
                return redirect(url_for('classification'))
        else:  # GET
            return render_template('classification.html', title='Classification', form=form,  model_up=True)
    else:
        return render_template('classification.html', title='Classification', model_up=False,
                               model_name=INFER_MODEL_TEXT_CLASS)


@app.route('/ner', methods=['GET', 'POST'])
def ner():
    global app_models
    is_model_up_and_running(INFER_MODEL_NER)

    if app_models.get(INFER_MODEL_NER) == 'started':
        form = SearchForm()
        # Check for  method
        if request.method == 'POST':
            if form.validate_on_submit():
                search_response = ner_nlp_query(form.searchbox.data)

                return render_template('ner.html', title='NER', form=form, search_results=search_response,
                                       query=form.searchbox.data, model_up=True)

            else:
                return redirect(url_for('ner'))
        else:  # GET
            return render_template('ner.html', title='NER', form=form, model_up=True)
    else:
        return render_template('ner.html', title='NER', model_up=False, model_name=INFER_MODEL_NER)


@app.route('/fill_mask', methods=['GET', 'POST'])
def fill_mask():
    global app_models
    is_model_up_and_running(INFER_MODEL_FILL_MASK)

    if app_models.get(INFER_MODEL_FILL_MASK) == 'started':
        form = SearchForm()
        # Check for  method
        if request.method == 'POST':
            if form.validate_on_submit():
                search_response = fill_mask_query(form.searchbox.data)

                return render_template('fill_mask.html', title='Fill Mask', form=form,
                                       search_results=search_response, query=form.searchbox.data, model_up=True)
            else:
                return redirect(url_for('fill_mask'))
        else:  # GET
            return render_template('fill_mask.html', title='Fill Mask', form=form, model_up=True)
    else:
        return render_template('fill_mask.html', title='Fill Mask', model_up=False, model_name=INFER_MODEL_FILL_MASK)


@app.route('/embeddings', methods=['GET', 'POST'])
def embeddings():
    global app_models
    is_model_up_and_running(INFER_MODEL_LES_MISERABLE)

    index_name = INDEX_LES_MIS
    if not is_index_present(index_name):
        return render_template('embeddings.html', title='Embeddings', model_up=False,
                               index_name=index_name, missing_index=True)

    if app_models.get(INFER_MODEL_LES_MISERABLE) == 'started':
        form = SearchForm()
        # Check for  method
        if request.method == 'POST':
            if form.validate_on_submit():
                embeddings_response = sentence_embedding_les_miserable(form.searchbox.data)
                search_response = knn_search_embeddings(embeddings_response)

                return render_template('embeddings.html', title='Embeddings', form=form,
                                       search_results=search_response.json()['hits']['hits'],
                                       query=form.searchbox.data, model_up=True, missing_index=False)

            else:
                return redirect(url_for('embeddings'))
        else:  # GET
            return render_template('embeddings.html', title='Embeddings', form=form, model_up=True, missing_index=False)
    else:
        return render_template('embeddings.html', title='Embeddings', model_up=False,
                               model_name=INFER_MODEL_LES_MISERABLE, missing_index=False)


@app.route('/similar_image', methods=['GET', 'POST'])
def similar_image():
    index_name = INDEX_IM_EMBED
    if not is_index_present(index_name):
        return render_template('similar_image.html', title='Similar image', index_name=index_name, missing_index=True)

    form = InputFileForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            if request.files['file'].filename == '':
                return render_template('similar_image.html', title='Similar image', form=form, err='No file selected')

            filename = secure_filename(form.file.data.filename)

            url_dir = 'static/tmp-uploads/'
            upload_dir = 'app/' + url_dir
            upload_dir_exists = os.path.exists(upload_dir)
            if not upload_dir_exists:
                # Create a new directory because it does not exist
                os.makedirs(upload_dir)

            # physical file-dir path
            file_path = upload_dir + filename
            # relative file path for URL
            url_path_file = url_dir + filename
            # Save the image
            form.file.data.save(upload_dir + filename)

            image = Image.open(file_path)
            embedding = image_embedding(image, img_model)

            # Execute KN search over the image dataset
            search_response = knn_search_images(embedding.tolist())

            # Cleanup uploaded file after not needed
            # if os.path.exists(file_path):
            #     os.remove(file_path)

            return render_template('similar_image.html', title='Similar image', form=form, search_results=search_response.json()['hits']['hits'], original_file=url_path_file)
        else:
            return redirect(url_for('similar_image'))
    else:
        return render_template('similar_image.html', title='Similar image', form=form)


@app.errorhandler(413)
@app.errorhandler(RequestEntityTooLarge)
def app_handle_413(e):
    return render_template('error.413.html', title=e.name, e_name=e.name, e_desc=e.description,
                           max_bytes=app.config["MAX_CONTENT_LENGTH"])


def sentence_embedding(query: str):
    query = '{ "docs" : [ {"text_field": "' + query + '"} ] }'
    response = requests.post(HOST + INFER_ENDPOINT.format(model=INFER_MODEL_IM_SEARCH), auth=AUTH,
                             headers=HEADERS, data=query)
    return response.json()['predicted_value']


def knn_search_images(dense_vector: list):
    query = ('{ "knn" : '
             '{"field": "image_embedding",'
             '"k": 5,'
             '"num_candidates": 100,'
             '"query_vector" : ' + str(dense_vector) + '},'
             '"fields": ["photo_description", "ai_description", "photo_url", "photo_image_url", '
                                                       '"photographer_first_name", "photographer_username", '
                                                       '"photographer_last_name"], '
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
    query = '{ "docs": { "text_field": "' + query + '"} }'
    response = requests.post(HOST + INFER_ENDPOINT.format(model=INFER_MODEL_TEXT_CLASS), auth=AUTH,
                             headers=HEADERS, data=query)
    return response.json()


def ner_nlp_query(query: str):
    query = '{ "docs": { "text_field": "' + query + '"} }'
    response = requests.post(HOST + INFER_ENDPOINT.format(model=INFER_MODEL_NER), auth=AUTH, headers=HEADERS, data=query)
    return response.json()


def fill_mask_query(query: str):
    query = '{ "docs": { "text_field": "' + query + '"} }'
    response = requests.post(HOST + INFER_ENDPOINT.format(model=INFER_MODEL_FILL_MASK), auth=AUTH,
                             headers=HEADERS, data=query)
    return response.json()


def sentence_embedding_les_miserable(query: str):
    query = '{ "docs" : [ {"text_field": "' + query + '"} ] }'
    response = requests.post(HOST + INFER_ENDPOINT.format(model=INFER_MODEL_LES_MISERABLE), auth=AUTH,
                             headers=HEADERS, data=query)
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


def is_model_up_and_running(model: str):
    global app_models

    endpoint = "/_ml/trained_models/{}/_stats".format(model)
    r = requests.get(HOST + endpoint, auth=AUTH, headers=HEADERS)
    json_response = r.json()

    if r.status_code == 200:
        if "deployment_stats" in json_response['trained_model_stats'][0]:
            app_models[model] = json_response['trained_model_stats'][0]['deployment_stats']['state']
        else:
            app_models[model] = 'down'
    elif r.status_code == 404:
        app_models[model] = 'na'


def is_index_present(index_name: str):
    r = requests.head(HOST + '/' + index_name, auth=AUTH)
    if r.status_code == 200:
        return True
    else:
        return False
