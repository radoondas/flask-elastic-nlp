from app import app
from flask import render_template, redirect, url_for, request
from app.searchForm import SearchForm
import requests


INFER_ENDPOINT = '/_ml/trained_models/sentence-transformers__clip-vit-b-32-multilingual-v1/deployment/_infer'
INFER_ENDPOINT_TEXT_CLASS = "/_ml/trained_models/distilbert-base-uncased-finetuned-sst-2-english/deployment/_infer"
INFER_ENDPOINT_NER = "/_ml/trained_models/dslim__bert-base-ner/deployment/_infer"
KNN_SEARCH = '/image-embeddings/_knn_search'

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

            em = sentence_embedding(form.searchbox.data)
            search_response = knn_search(em)
            print_hits(search_response)

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
            search_response = ner_nlp(form.searchbox.data)

            return render_template('ner.html', title='NER', form=form,
                                   search_results=search_response, query=form.searchbox.data)

        else:
            return redirect(url_for('ner'))
    else:  # GET
        return render_template('ner.html', title='NER', form=form)


def sentence_embedding(query: str):
    inf = '{ "docs" : [ {"text_field": "' + query + '"} ] }'

    response = requests.post(HOST + INFER_ENDPOINT, auth=AUTH, headers=HEADERS, data=inf)

    return response.json()['predicted_value']


def knn_search(dense_vector: list):
    query = ('{ "knn" : '
             '{"field": "image_embedding",'
             '"k": 5,'
             '"num_candidates": 100,'
             '"query_vector" : ' + str(dense_vector) + '},'
                                                       '"fields": ["photo_description", "ai_description", "photo_url", "photo_image_url"],'
                                                       '"_source": false'
                                                       '}'
             )

    return requests.get(HOST + KNN_SEARCH, auth=AUTH, headers=HEADERS, data=query)


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


def ner_nlp(query: str):
    inf = '{ "docs": { "text_field": "' + query + '"} }'
    response = requests.post(HOST + INFER_ENDPOINT_NER, auth=AUTH, headers=HEADERS, data=inf)

    return response.json()
