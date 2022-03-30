# flask-elastic-nlp

## Requirements
### Required models
In order to sucesfuly execute all the examples you need to import 5 NLP models.
- [dslim/bert-base-ner](https://huggingface.co/dslim/bert-base-NER)
- [sentence-transformers/clip-ViT-B-32-multilingual-v1](https://huggingface.co/sentence-transformers/clip-ViT-B-32-multilingual-v1)
- [distilbert-base-uncased-finetuned-sst-2-english](https://huggingface.co/distilbert-base-uncased-finetuned-sst-2-english)
- [bert-base-uncased](https://huggingface.co/bert-base-uncased)
- [sentence-transformers/msmarco-MiniLM-L-12-v3](https://huggingface.co/sentence-transformers/msmarco-MiniLM-L-12-v3)

### Elasticsearch resources
To run all models in parallel, you will need ~21GB of memory, because models are loaded in to memory. 

If your computer does not have enough memory, then you can configure less memory, and always run only 1 or 2 models 
in the same time depending on how much memory you have available.
To change the value of your docker-compose, go to `es-docker/.env` file and change `MEM_LIMIT`.

## How to
Before you start the Flask application, you have to setup Elasticsearch cluster with data (indices) and NLP models.

### 0. Setup Python env
We need to setup Python env to use scripts.
```bash
$ cd flask-elastic-nlp
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
```

### 1. Elasticsearch cluster
You can use the docker-compose bundled in the repository or use your own cluster or in the ESS cloud.

```bash
$ cd es-docker
$ docker-compose up -d
```
Wait and check if the cluster is up and running using Kibana or `curl`.

### 2. Load NLP models 
Let's load the models in to the application. we use `eland` python client to load the models. For more details, follow the [documentation](https://www.elastic.co/guide/en/elasticsearch/client/eland/current/index.html).

In the main directory
```bash
# wait until each model is loaded and started. If you do not have enough memory, you will see errors sometimes confusing
$ eland_import_hub_model --url http://elastic:changeme@localhost:9200 --hub-model-id dslim/bert-base-NER --task-type ner --start
$ eland_import_hub_model --url http://elastic:changeme@127.0.0.1:9200 --hub-model-id sentence-transformers/clip-ViT-B-32-multilingual-v1 --task-type text_embedding --start
$ eland_import_hub_model --url http://elastic:changeme@127.0.0.1:9200 --hub-model-id distilbert-base-uncased-finetuned-sst-2-english --task-type text_classification --start
$ eland_import_hub_model --url http://elastic:changeme@127.0.0.1:9200 --hub-model-id bert-base-uncased --task-type fill_mask --start
$ eland_import_hub_model --url http://elastic:changeme@127.0.0.1:9200 --hub-model-id sentence-transformers/msmarco-MiniLM-L-12-v3 --task-type text_embedding --start
```
You can verify that all models are up nd running in Kibana: `Machine Learning -> Trained models`
![](models.png)

### 3. Import data indices
We need also the data indices which we use in our flask app. In the process the script will download also the dataset from Unsplash.

Make sure that Python environment is set.
```bash
$ cd embeddings
$ python3 build-datasets.py --es_host "http://127.0.0.1:9200" --es_user "elastic" --es_password "changeme" \                                                                                                                                                             2 ↵
  --verify_certs False --delete_existing
```

### 4. Run flask app
Make sure that Python environment is set.
```bash
# In the main directory 
# !!! configure file `.env` with values pointing to your Elasticsearch cluster
$ flask run --port=5001
# Access URL `127.0.0.1:5001`
```

## How to run app in Docker 
To run the application in a Docker container you have 2 options.
`cd flask-elastic-nlp`

### Option 1: Configure .env file
1. Configure correct values in `.env` file with access to Elasticsearch cluster
   ```
   ES_HOST='http://localhost:9200'
   ES_USER='elastic'
   ES_PWD='changeit'
    ```
2. Build the image: `docker build . --tag elastic-nlp/flask-nlp:0.0.1`
3. Run: `docker run -p 5000:5001 --rm  elastic-nlp/flask-nlp:0.0.1`
4. Access URL `127.0.0.1:5001`

### Option 2: Use environment variables
1. Build the image: `docker build . --tag elastic-nlp/flask-nlp:0.0.1`
2. Run: `docker run -p 5000:5001 --rm -e ES_HOST='http://localhost:9200' -e ES_USER='elastic' -e ES_PWD='password' elastic-nlp/flask-nlp:0.0.1`
3. Access URL `127.0.0.1:5001`

![](app.png)