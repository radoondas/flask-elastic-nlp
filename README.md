# flask-elastic-nlp
![](docs/img/similar_image.gif)

## Important initial thoughts
This code is just a proof-of-concept to showcase the simplicity of NLP implementation into Elastic stack. 
The code as-is is not meant to be deployed in the production environment.

## Requirements
### Elasticsearch version
v8.3.0+

### Required models
In order to sucesfuly execute all the examples you need to import 5 NLP models.
- [dslim/bert-base-ner](https://huggingface.co/dslim/bert-base-NER)
- [sentence-transformers/clip-ViT-B-32-multilingual-v1](https://huggingface.co/sentence-transformers/clip-ViT-B-32-multilingual-v1)
- [distilbert-base-uncased-finetuned-sst-2-english](https://huggingface.co/distilbert-base-uncased-finetuned-sst-2-english)
- [bert-base-uncased](https://huggingface.co/bert-base-uncased)
- [sentence-transformers/msmarco-MiniLM-L-12-v3](https://huggingface.co/sentence-transformers/msmarco-MiniLM-L-12-v3)
- [deepset/tinyroberta-squad2](https://huggingface.co/deepset/tinyroberta-squad2)

### Elasticsearch resources
To run all models in parallel, you will need ~21GB of memory because models are loaded into memory. 

If your computer does not have enough memory, then you can configure less memory and always run only 1 or 2 models 
at the same time, depending on how much memory you have available.
To change the value of your docker-compose, go to `es-docker/.env` file and change `MEM_LIMIT`.

### Python environment
**Python v3.9+**

## How to
Before starting the Flask application, you have to set up an Elasticsearch cluster with data (indices) and NLP models.

### 0. Setup Python env
We need to setup Python env to use scripts.
```bash
$ cd flask-elastic-nlp
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
```

### 1. Elasticsearch cluster
You can use the docker-compose bundled in the repository or use your cluster or the ESS cloud.

```bash
$ cd es-docker
$ docker-compose up -d
```
Wait and check if the cluster is up and running using Kibana or `curl`.

Once the cluster is up and running, let's get the CA certificate out from the Elasticsearch cluster, so we can use it in the rest of the setup.
```bash
$ docker cp elastic-nlp-85-es01-1://usr/share/elasticsearch/config/certs/ca/ca.crt ../app/conf/ca.crt
$ cp ../app/conf/ca.crt ../embeddings/ca.crt
```

### 2. Load NLP models 
Let's load the models into the application. We use the `eland` python client to load the models. For more details, follow the [documentation](https://www.elastic.co/guide/en/elasticsearch/client/eland/current/index.html).

In the main directory
```bash
# wait until each model is loaded and started. If you do not have enough memory, you will see errors sometimes confusing
$ eland_import_hub_model --url https://elastic:changeme@localhost:9200 --hub-model-id dslim/bert-base-NER --task-type ner --start --ca-certs app/conf/ca.crt
$ eland_import_hub_model --url https://elastic:changeme@127.0.0.1:9200 --hub-model-id sentence-transformers/clip-ViT-B-32-multilingual-v1 --task-type text_embedding --start --ca-certs app/conf/ca.crt
$ eland_import_hub_model --url https://elastic:changeme@127.0.0.1:9200 --hub-model-id distilbert-base-uncased-finetuned-sst-2-english --task-type text_classification --start --ca-certs app/conf/ca.crt
$ eland_import_hub_model --url https://elastic:changeme@127.0.0.1:9200 --hub-model-id bert-base-uncased --task-type fill_mask --start --ca-certs app/conf/ca.crt
$ eland_import_hub_model --url https://elastic:changeme@127.0.0.1:9200 --hub-model-id sentence-transformers/msmarco-MiniLM-L-12-v3 --task-type text_embedding --start --ca-certs app/conf/ca.crt
$ eland_import_hub_model --url https://elastic:changeme@127.0.0.1:9200 --hub-model-id deepset/tinyroberta-squad2 --task-type question_answering --start --ca-certs app/conf/ca.crt
```
You can verify that all models are up and running in Kibana: `Machine Learning -> Trained models`

![](docs/img/models.png)

If you see in the screen that some models are missing and you see a message. `ML job and trained model synchronization required`, go ahead and click the link to synchronize models.

![](docs/img/model-sync.png)


### 3. Import data indices
We also need the data indices which we use in our flask app. In the process, the script will also download the dataset from Unsplash.

Make sure that Python environment is set.
```bash
$ cd embeddings
$ python3 build-datasets.py --es_host "https://127.0.0.1:9200" --es_user "elastic" --es_password "changeme" \                                                                                                                                                             2 ↵
  --verify_certs --delete_existing
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
To run the application in a Docker container, we need to build it and then run the image with the Flask application.
```bash
$ cd flask-elastic-nlp
````

### Build the image
In order to be able to run the application in the Docker environment, we need to build the image locally. Because this 
is a Python application with dependencies, the build of the image might take longer. All the requirements are installed.   
```bash
$ docker build . --tag elastic-nlp/flask-nlp:0.0.1
```
Once, the build is complete, we can verify if the image is available.
```bash
$ docker images | grep flask-nlp
```

### Run the image
To run the application, we need to run the Docker image. 

#### Using local (Docker) Elastic stack
From the CLI we need to run the image using the `docker run` command.
```bash
$ docker run --network elastic-nlp_default -p 5001:5001  \
  -e ES_HOST='https://es01:9200' -e ES_USER='elastic' \
  -e ES_PWD='changeme' elastic-nlp/flask-nlp:0.0.1
```
Notes:
- Option `--network elastic-nlp_default` is important for the application to connect to the Elastic cluster in your 
  Docker environment
- Variable `ES_HOST='https://es01:9200'` is using Docker alias in the network. If you used the Docker compose file as is, 
  you do not need to change the url for Elasticsearh

#### Using external (e.g. ESS) Elastic stack
From the CLI we need to run the image using the `docker run` command. By external Elastic stack we mean non-dockerized, 
or self-managed, or ESS cloud deployment.
```bash
$ docker run -p 5001:5001  \
  -e ES_HOST='https://URL:PORT' -e ES_USER='elastic' \
  -e ES_PWD='changeme' elastic-nlp/flask-nlp:0.0.1
```
Notes: 
- Change `ES_HOST='https://URL:PORT'` to your ELasticsearch URL+PORT

### Access the application
The application is now up and running and is accessible on `http://127.0.0.1:5001` 

#### Important note
When the application is starting up, it needs to download a model from the Internet, and it will take some time, 
depending on your network connection, to start up. You might see in the terminal similar output.
```bash
$ docker run --network elastic-nlp_default -p 5001:5001  \
  -e ES_HOST='https://es01:9200' -e ES_USER='elastic' \
  -e ES_PWD='changeme' elastic-nlp/flask-nlp:0.0.1
 * Serving Flask app 'flask-elastic-nlp.py' (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
Downloading: 100%|██████████| 690/690 [00:00<00:00, 464kB/s]
Downloading: 100%|██████████| 4.03k/4.03k [00:00<00:00, 3.21MB/s]
Downloading: 100%|██████████| 525k/525k [00:00<00:00, 740kB/s]  
Downloading: 100%|██████████| 316/316 [00:00<00:00, 367kB/s]
Downloading: 100%|██████████| 605M/605M [03:10<00:00, 3.18MB/s] 
Downloading: 100%|██████████| 389/389 [00:00<00:00, 264kB/s]
Downloading: 100%|██████████| 604/604 [00:00<00:00, 528kB/s]
Downloading: 100%|██████████| 961k/961k [00:00<00:00, 1.07MB/s]
Downloading: 100%|██████████| 1.88k/1.88k [00:00<00:00, 1.61MB/s]
Downloading: 100%|██████████| 116/116 [00:00<00:00, 74.1kB/s]
Downloading: 100%|██████████| 122/122 [00:00<00:00, 85.5kB/s]
/usr/local/lib/python3.9/site-packages/elasticsearch/_sync/client/__init__.py:395: SecurityWarning: Connecting to 'https://es01:9200' using TLS with verify_certs=False is insecure
  _transport = transport_class(
 * Running on all addresses.
   WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://192.168.48.2:5001/ (Press CTRL+C to quit)
```

![](docs/img/app.png)