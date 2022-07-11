from app import app, img_model, es
from flask import render_template, redirect, url_for, request
from app.searchForm import SearchForm
from app.searchBlogsForm import SearchBlogsForm
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
INFER_MODEL_TEXT_EMBEDDINGS = 'sentence-transformers__msmarco-minilm-l-12-v3'
INFER_MODEL_Q_AND_A = 'deepset__tinyroberta-squad2'

INDEX_IM_EMBED = 'image-embeddings'
INDEX_LES_MIS = 'les-miserable-embedded'
INDEX_BLOG_SEARCH = 'blogs'

HOST = app.config['ELASTICSEARCH_HOST']
AUTH = (app.config['ELASTICSEARCH_USER'], app.config['ELASTICSEARCH_PASSWORD'])
HEADERS = {'Content-Type': 'application/json'}

TLS_VERIFY = app.config['VERIFY_TLS']

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
    if not es.indices.exists(index=index_name):
        return render_template('search.html', title='Image search', model_up=False,
                               index_name=index_name, missing_index=True)

    if app_models.get(INFER_MODEL_IM_SEARCH) == 'started':
        form = SearchForm()
        # Check for  method
        if request.method == 'POST':
            if form.validate_on_submit():
                embeddings = sentence_embedding(form.searchbox.data)
                search_response = knn_search_images(embeddings['predicted_value'])

                return render_template('search.html', title='Image search', form=form,
                                       search_results=search_response['hits']['hits'],
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
                search_response = infer_trained_model(form.searchbox.data, INFER_MODEL_TEXT_CLASS)

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
                search_response = infer_trained_model(form.searchbox.data, INFER_MODEL_NER)

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
                search_response = infer_trained_model(form.searchbox.data, INFER_MODEL_FILL_MASK)

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
    is_model_up_and_running(INFER_MODEL_TEXT_EMBEDDINGS)

    index_name = INDEX_LES_MIS
    if not es.indices.exists(index=index_name):
        return render_template('embeddings.html', title='Embeddings', model_up=False,
                               index_name=index_name, missing_index=True)

    if app_models.get(INFER_MODEL_TEXT_EMBEDDINGS) == 'started':
        form = SearchForm()
        # Check for  method
        if request.method == 'POST':
            if form.validate_on_submit():
                embeddings_response = infer_trained_model(form.searchbox.data, INFER_MODEL_TEXT_EMBEDDINGS)
                search_response = knn_les_miserable_embeddings(embeddings_response['predicted_value'])

                return render_template('embeddings.html', title='Embeddings', form=form,
                                       search_results=search_response['hits']['hits'],
                                       query=form.searchbox.data, model_up=True, missing_index=False)

            else:
                return redirect(url_for('embeddings'))
        else:  # GET
            return render_template('embeddings.html', title='Embeddings', form=form, model_up=True, missing_index=False)
    else:
        return render_template('embeddings.html', title='Embeddings', model_up=False,
                               model_name=INFER_MODEL_TEXT_EMBEDDINGS, missing_index=False)


@app.route('/similar_image', methods=['GET', 'POST'])
def similar_image():
    index_name = INDEX_IM_EMBED
    if not es.indices.exists(index=index_name):
        return render_template('similar_image.html', title='Similar image', index_name=index_name, missing_index=True)

    is_model_up_and_running(INFER_MODEL_IM_SEARCH)

    if app_models.get(INFER_MODEL_IM_SEARCH) == 'started':
        form = InputFileForm()
        if request.method == 'POST':
            if form.validate_on_submit():
                if request.files['file'].filename == '':
                    return render_template('similar_image.html', title='Similar image', form=form,
                                           err='No file selected', model_up=True)

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

                return render_template('similar_image.html', title='Similar image', form=form,
                                       search_results=search_response['hits']['hits'],
                                       original_file=url_path_file, model_up=True)
            else:
                return redirect(url_for('similar_image'))
        else:
            return render_template('similar_image.html', title='Similar image', form=form, model_up=True)
    else:
        return render_template('similar_image.html', title='Similar image', model_up=False,
                               model_name=INFER_MODEL_IM_SEARCH)


@app.route('/blog_search', methods=['GET', 'POST'])
def blog_search():
    global app_models
    is_model_up_and_running(INFER_MODEL_TEXT_EMBEDDINGS)
    is_model_up_and_running(INFER_MODEL_Q_AND_A)

    qa_model = True if app_models.get(INFER_MODEL_Q_AND_A) == 'started' else False
    index_name = INDEX_BLOG_SEARCH

    if not es.indices.exists(index=index_name):
        return render_template('blog_search.html', title='Blog search', te_model_up=False,
                               index_name=index_name, missing_index=True, qa_model_up=qa_model)

    if app_models.get(INFER_MODEL_TEXT_EMBEDDINGS) == 'started':
        form = SearchBlogsForm()
        # Check for method
        if request.method == 'POST':
            if form.validate_on_submit():
                if form.searchboxBlogWindow.data is None or len(form.searchboxBlogWindow.data) == 0:
                    embeddings_response = infer_trained_model(form.searchbox.data, INFER_MODEL_TEXT_EMBEDDINGS)
                    search_response = knn_blogs_embeddings(embeddings_response['predicted_value'],
                                                           form.searchboxAuthor.data)

                    return render_template('blog_search.html', title='Blog search', form=form,
                                           search_results=search_response['hits']['hits'],
                                           query=form.searchbox.data, te_model_up=True, qa_model_up=qa_model,
                                           missing_index=False)
                else:
                    search_response = q_and_a(question=form.searchbox.data, full_text=form.searchboxBlogWindow.data)
                    return render_template('blog_search.html', title='Blog search', form=form,
                                           qa_results=search_response.body,
                                           query=form.searchbox.data, te_model_up=True, qa_model_up=qa_model,
                                           missing_index=False)
            else:
                return redirect(url_for('blog_search'))
        else:  # GET
            return render_template('blog_search.html', title='Blog Search', form=form, te_model_up=True,
                                   qa_model_up=qa_model, missing_index=False)
    else:
        return render_template('blog_search.html', title='Blog search', te_model_up=False, qa_model_up=qa_model,
                               model_name=INFER_MODEL_TEXT_EMBEDDINGS, missing_index=False)


@app.errorhandler(413)
@app.errorhandler(RequestEntityTooLarge)
def app_handle_413(e):
    return render_template('error.413.html', title=e.name, e_name=e.name, e_desc=e.description,
                           max_bytes=app.config["MAX_CONTENT_LENGTH"])


def sentence_embedding(query: str):
    response = es.ml.infer_trained_model(model_id=INFER_MODEL_IM_SEARCH, docs=[{"text_field": query}])
    return response['inference_results'][0]


def knn_search_images(dense_vector: list):
    source_fields = ["photo_description", "ai_description", "photo_url", "photo_image_url", "photographer_first_name",
                     "photographer_username", "photographer_last_name"]
    query = {
        "field": "image_embedding",
        "query_vector": dense_vector,
        "k": 5,
        "num_candidates": 100
    }

    response = es.knn_search(
        index=INDEX_IM_EMBED,
        fields=source_fields,
        knn=query, source=False)

    return response


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


def infer_trained_model(query: str, model: str):
    response = es.ml.infer_trained_model(model_id=model, docs=[{"text_field": query}])
    return response['inference_results'][0]


def knn_les_miserable_embeddings(dense_vector: list):
    source_fields = ["paragraph", "line"]
    query = {
        "field": "ml.inference.predicted_value",
        "query_vector": dense_vector,
        "k": 5,
        "num_candidates": 10
    }

    response = es.knn_search(
        index=INDEX_LES_MIS,
        fields=source_fields,
        knn=query,
        source=False)

    return response


def image_embedding(image, model):
    return model.encode(image)


def is_model_up_and_running(model: str):
    global app_models

    # TODO: change to ES client library
    # res = es.ml.get_trained_models_stats(model_id=model)

    endpoint = "/_ml/trained_models/{}/_stats".format(model)
    r = requests.get(HOST + endpoint, auth=AUTH, headers=HEADERS, verify=TLS_VERIFY)
    json_response = r.json()

    if r.status_code == 200:
        if "deployment_stats" in json_response['trained_model_stats'][0]:
            app_models[model] = json_response['trained_model_stats'][0]['deployment_stats']['state']
        else:
            app_models[model] = 'down'
    elif r.status_code == 404:
        app_models[model] = 'na'


def knn_blogs_embeddings(dense_vector: list, filter: str):
    source_fields = ["body_content_window", "id", "title", "byline", "url"]
    query = {
        "field": "text_embedding.predicted_value",
        "query_vector": dense_vector,
        "k": 10,
        "num_candidates": 30
    }

    if len(filter) > 0:
        print('ss')
        fltr = {
            "term": {
              "byline.keyword": filter
            }
        }
        response = es.knn_search(
            index=INDEX_BLOG_SEARCH,
            fields=source_fields,
            knn=query,
            filter=fltr,
            source=False)
    else:
        response = es.knn_search(
            index=INDEX_BLOG_SEARCH,
            fields=source_fields,
            knn=query,
            source=False)

    return response


def q_and_a(question: str, full_text: str):
    cfg = {
        "question_answering": {
            "question": question,
            "max_answer_length": 30
        }
    }
    response = es.ml.infer_trained_model(model_id=INFER_MODEL_Q_AND_A, docs=[{"text_field": full_text}],
                                         inference_config=cfg)
    return response['inference_results'][0]
