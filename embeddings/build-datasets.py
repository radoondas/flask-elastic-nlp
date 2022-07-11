import shutil
import os
import requests
import zipfile
from tqdm.auto import tqdm
import pandas as pd
import json
import argparse
import sys
from os.path import exists

from elasticsearch import Elasticsearch
from elasticsearch.helpers import parallel_bulk

UNSPLASH_FOLDER = 'unsplash/'
UNSPLASH_FILE = 'unsplash-research-dataset-lite-1.2.0.zip'
UNSPLASH_URL = 'https://unsplash.com/data/lite/1.2.0'

EMBEDDINGS_FOLDER = 'images/'
EMBEDDINGS_FILE = 'image-embeddings.json.zip'

LES_MISERABLE_FOLDER = "les-miserable/"
LES_MISERABLE_FILE = "les-miserable-embedded.json.zip"

BLOGS_FOLDER = "blogs/"
BLOGS_FILE = "blogs-with-embeddings.json.zip"

es = Elasticsearch(hosts='https://1270.0.0.1:9200')

parser = argparse.ArgumentParser()
parser.add_argument('--es_host', dest='es_host', required=False, default="https://127.0.0.1:9200",
                    help="Elasticsearch hostname. Default: https://127.0.0.1:9200")
parser.add_argument('--es_user', dest='es_user', required=False, default='elastic',
                    help="Elasticsearch username. Default: elastic")
parser.add_argument('--es_password', dest='es_password', required=False, default='changeme',
                    help="Elasticsearch password. Default: changeme")
parser.add_argument('--verify_certs', dest='verify_certs', required=False, action=argparse.BooleanOptionalAction,
                    help="Verify certificates. Default: False")
parser.add_argument('--thread_count', dest='thread_count', required=False, default=4, type=int,
                    help="Number of indexing threads. Default: 4")
parser.add_argument('--chunk_size', dest='chunk_size', required=False, default=1000, type=int,
                    help="")
parser.add_argument('--timeout', dest='timeout', required=False, default=120, type=int,
                    help="Request timeout in seconds. Default: 120")
parser.add_argument('--delete_existing', dest='delete_existing', required=False, action=argparse.BooleanOptionalAction,
                    help="Delete existing indices if they are present in the cluster. Default: True")

args = parser.parse_args()


def main():
    global args
    global es

    # Initialize the client
    # TODO: args.verify_certs does not work correctly when read from the arguments
    es = Elasticsearch(hosts=[args.es_host], basic_auth=(args.es_user, args.es_password),
                       verify_certs=args.verify_certs, request_timeout=args.timeout)

    # Import images dataset
    import_image_dataset()

    # Import les miserable dataset
    import_les_miserable_dataset()

    # Import blogs dataset
    import_blogs_dataset()


def gen_rows(df):
    for doc in df.to_dict(orient='records'):
        yield doc


def import_image_dataset():
    print('Importing image dataset')
    global es, args
    global UNSPLASH_FILE, UNSPLASH_FOLDER

    # Create a new directory because it does not exist
    if not os.path.exists(UNSPLASH_FOLDER):
        os.makedirs(UNSPLASH_FOLDER)

    with requests.get(UNSPLASH_URL, stream=True) as r:
        # check header to get content length, in bytes
        total_length = int(r.headers.get("Content-Length"))
        UNSPLASH_FILE = os.path.basename(r.url)

        # implement progress bar via tqdm
        with tqdm.wrapattr(r.raw, "read", total=total_length, desc="") as raw:
            with open(UNSPLASH_FOLDER + os.path.basename(r.url), 'wb') as output:
                print('Downloading Unsplash dataset light.')
                shutil.copyfileobj(raw, output)

    # TODO: file check exists !!!

    with zipfile.ZipFile(UNSPLASH_FOLDER + UNSPLASH_FILE, 'r') as zip_ref:
        print('Extracting file ', UNSPLASH_FOLDER + UNSPLASH_FILE, '.')
        zip_ref.extractall(UNSPLASH_FOLDER + 'data')

    with zipfile.ZipFile(EMBEDDINGS_FOLDER + EMBEDDINGS_FILE, 'r') as zip_ref:
        print('Extracting file ', EMBEDDINGS_FOLDER + EMBEDDINGS_FILE, '.')
        zip_ref.extractall(EMBEDDINGS_FOLDER)

    df_unsplash = pd.read_csv(UNSPLASH_FOLDER + 'data/' + 'photos.tsv000', sep='\t', header=0)
    df_unsplash['photo_description'].fillna('', inplace=True)
    df_unsplash['ai_description'].fillna('', inplace=True)
    df_unsplash['photographer_first_name'].fillna('', inplace=True)
    df_unsplash['photographer_last_name'].fillna('', inplace=True)
    df_unsplash['photographer_username'].fillna('', inplace=True)
    df_unsplash['exif_camera_make'].fillna('', inplace=True)
    df_unsplash['exif_camera_model'].fillna('', inplace=True)
    df_unsplash['exif_iso'].fillna(0, inplace=True)

    df_unsplash_subset = df_unsplash[
        ['photo_id', 'photo_url', 'photo_image_url', 'photo_description', 'ai_description', 'photographer_first_name',
         'photographer_last_name', 'photographer_username', 'exif_camera_make', 'exif_camera_model', 'exif_iso']]
    df_embeddings = pd.read_json(EMBEDDINGS_FOLDER + 'image-embeddings.json', lines=True)

    # https://www.geeksforgeeks.org/how-to-merge-two-csv-files-by-specific-column-using-pandas-in-python/
    df_merged = pd.merge(df_unsplash_subset, df_embeddings,
                         on='photo_id',
                         how='inner')

    # index name to index data into
    index = "image-embeddings"
    with open(EMBEDDINGS_FOLDER + "image-embeddings-mappings.json", "r") as config_file:
        config = json.loads(config_file.read())
        if args.delete_existing:
            if es.indices.exists(index=index):
                print("Deleting existing %s" % index)
                es.indices.delete(index=index, ignore=[400, 404])

        print("Creating index %s" % index)
        es.indices.create(index=index, mappings=config["mappings"], settings=config["settings"], ignore=[400, 404])

    count = 0
    for success, info in parallel_bulk(
            client=es,
            actions=gen_rows(df_merged),
            thread_count=args.thread_count,
            chunk_size=args.chunk_size,
            timeout='%ss' % args.timeout,
            index=index
    ):
        if success:
            count += 1
            if count % args.chunk_size == 0:
                print('Indexed %s documents' % str(count), flush=True)
                sys.stdout.flush()
        else:
            print('Doc failed', info)

    print('Indexed %s image embeddings documents' % str(count), flush=True)
    sys.stdout.flush()


def import_les_miserable_dataset():
    print('Importing Mes miserable dataset')
    global es, args
    global LES_MISERABLE_FOLDER, LES_MISERABLE_FILE

    file_exists = exists(LES_MISERABLE_FOLDER + LES_MISERABLE_FILE)
    if not file_exists:
        print("Missing file " + LES_MISERABLE_FILE + ". Skipping. Needs fix.")
    else:
        # Unzip and upload book paragraph embeddings
        with zipfile.ZipFile(LES_MISERABLE_FOLDER + LES_MISERABLE_FILE, 'r') as zip_ref:
            print('Extracting file ', LES_MISERABLE_FOLDER + LES_MISERABLE_FILE, '.')
            zip_ref.extractall(LES_MISERABLE_FOLDER)

        df_les_miserable_embeddings = pd.read_json(LES_MISERABLE_FOLDER + 'les-miserable-embedded.json', lines=True)

        INDEX_LES_MIS = 'les-miserable-embedded'
        index_lm = INDEX_LES_MIS
        with open(LES_MISERABLE_FOLDER + "les-miserable-embedded-mappings.json", "r") as config_file_lm:
            config_lm = json.loads(config_file_lm.read())
            if args.delete_existing:
                if es.indices.exists(index=index_lm):
                    print("Deleting existing %s" % index_lm)
                    es.indices.delete(index=index_lm, ignore=[400, 404])

            print("Creating index %s" % index_lm)
            es.indices.create(index=index_lm, mappings=config_lm["mappings"], settings=config_lm["settings"],
                              ignore=[400, 404])

        count = 0
        for success, info in parallel_bulk(
                client=es,
                actions=gen_rows(df_les_miserable_embeddings),
                thread_count=args.thread_count,
                chunk_size=args.chunk_size,
                timeout='%ss' % args.timeout,
                index=index_lm
        ):
            if success:
                count += 1
                if count % args.chunk_size == 0:
                    print('Indexed %s documents' % str(count), flush=True)
                    sys.stdout.flush()
            else:
                print('Doc failed', info)

        print('Indexed %s les-miserable embeddings documents' % str(count), flush=True)
        sys.stdout.flush()


def import_blogs_dataset():
    print('Importing blogs dataset')
    global es, args
    global BLOGS_FOLDER, BLOGS_FILE

    file_exists = exists(BLOGS_FOLDER + BLOGS_FILE)
    if not file_exists:
        print("Missing file " + BLOGS_FILE + ". Skipping. Needs fix.")
    else:
        # Unzip index file
        with zipfile.ZipFile(BLOGS_FOLDER + BLOGS_FILE, 'r') as zip_ref:
            print('Extracting file ', BLOGS_FOLDER + BLOGS_FILE, '.')
            zip_ref.extractall(BLOGS_FOLDER)

        df_blogs_embeddings = pd.read_json(BLOGS_FOLDER + 'blogs-with-embeddings.json', lines=True)

        INDEX_BLOG = 'blogs'
        # index_lm = INDEX_BLOG
        with open(BLOGS_FOLDER + "blogs-with-embeddings-mappings.json", "r") as config_file_blg:
            config_blg = json.loads(config_file_blg.read())
            if args.delete_existing:
                if es.indices.exists(index=INDEX_BLOG):
                    print("Deleting existing %s" % INDEX_BLOG)
                    es.indices.delete(index=INDEX_BLOG, ignore=[400, 404])

            print("Creating index %s" % INDEX_BLOG)
            es.indices.create(index=INDEX_BLOG, mappings=config_blg["mappings"], settings=config_blg["settings"],
                              ignore=[400, 404])

        count = 0
        for success, info in parallel_bulk(
                client=es,
                actions=gen_rows(df_blogs_embeddings),
                thread_count=args.thread_count,
                chunk_size=args.chunk_size,
                timeout='%ss' % args.timeout,
                index=INDEX_BLOG
        ):
            if success:
                count += 1
                if count % args.chunk_size == 0:
                    print('Indexed %s documents' % str(count), flush=True)
                    sys.stdout.flush()
            else:
                print('Doc failed', info)

        print('Indexed %s blogs embeddings documents' % str(count), flush=True)
        sys.stdout.flush()

    print("Done!\n")
    sys.stdout.flush()


if __name__ == '__main__':
    main()
