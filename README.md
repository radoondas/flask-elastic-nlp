# flask-elastic-nlp

## Req
Import models: https://github.com/grabowskit/nlp-lab/blob/main/eland-import-models

## How to run app locally
This option does not require Docker, but you can run it directly from CLI (ubix based only) 

```bash
$ cd flask-elastic-nlp
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
# !!! configure file `.env` with values pointing to your Elasticsearch cluster
$ flask run
# Access URL `127.0.0.1:5000`
```
NOTE: If you see that port 5000 is not available (new McOS and airplay...), then just run flask app on different port `flask run --port=5001`

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