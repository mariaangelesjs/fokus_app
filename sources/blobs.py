#!/usr/bin/python

# Import packages
from io import BytesIO
import pickle
from azure.storage.blob import BlobServiceClient
import logging
import datetime
import pickle


logger = logging.getLogger(__name__)
############
# Functions#
############

# To download blob from Bas Analyse


def get_data(STORAGEACCOUNTURL, STORAGEACCOUNTKEY, CONTAINERNAME, BLOBNAME):
    blob_service_client_instance = BlobServiceClient(
        account_url=STORAGEACCOUNTURL, credential=STORAGEACCOUNTKEY)
    blob_client_instance = blob_service_client_instance.get_blob_client(
        CONTAINERNAME, BLOBNAME, snapshot=None)
    blob_data = blob_client_instance.download_blob()
    filebuffer = BytesIO()
    blob_data.download_to_stream(filebuffer, max_concurrency=10)
    filebuffer.seek(0)
    return filebuffer

# To upload blob into Bas Analyse


def upload_df(data, container, blobpathfilename, STORAGEACCOUNTURL, STORAGEACCOUNTKEY,dictionary):
    blob_service_client_instance = BlobServiceClient(
        account_url=STORAGEACCOUNTURL, credential=STORAGEACCOUNTKEY)
    logger.info('Uploading data')
    blob_client = blob_service_client_instance.get_blob_client(
        container=container, blob="{}.parquet".format(blobpathfilename))
    parquet_file = BytesIO()
    data.to_parquet(parquet_file, engine='pyarrow', use_dictionary=dictionary)
    # change the stream position back to the beginning after writing
    parquet_file.seek(0)
    return blob_client.upload_blob(
        data=parquet_file, overwrite=True
    )

# To upload pickle


def upload_pickle(data, STORAGEACCOUNTURL, STORAGEACCOUNTKEY, CONTAINERNAME, BLOBNAME):
    blob_service_client_instance = BlobServiceClient(
        account_url=STORAGEACCOUNTURL, credential=STORAGEACCOUNTKEY)
    logger.info('Uploading pickle')
    blob_client = blob_service_client_instance.get_blob_client(
        container=CONTAINERNAME, blob="/output/{}.pickle".format(BLOBNAME))
    pickle_file = BytesIO()
    pickle.dump(data, pickle_file)
    # change the stream position back to the beginning after writing
    pickle_file.seek(0)
    return blob_client.upload_blob(
        data=pickle_file, overwrite=True
    )

def download_pickle(STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
                    CONTAINERNAME, BLOBNAME, large_dataset):
    logger.info(f'Downloading pickle')
    blob_service_client_instance = BlobServiceClient(
        account_url=STORAGEACCOUNTURL, credential=STORAGEACCOUNTKEY)
    blob_client_instance = blob_service_client_instance.get_blob_client(
        CONTAINERNAME, BLOBNAME, snapshot=None)
    blob_data = blob_client_instance.download_blob()
    filebuffer = BytesIO()
    blob_data.download_to_stream(filebuffer, max_concurrency=10)
    filebuffer.seek(0)
    ob = pickle.load(filebuffer)
    return ob


def upload_from_filebuffer(STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
                           container, blob_path, filebuffer):
    blob_service_client_instance = BlobServiceClient(
        account_url=STORAGEACCOUNTURL, credential=STORAGEACCOUNTKEY)
    blob_client = blob_service_client_instance.get_blob_client(
        container=container, blob=blob_path)
    filebuffer.seek(0)
    blob_client.upload_blob(filebuffer, max_concurrency=10,
                            overwrite=True)

def get_client(
        container, filename,
        STORAGEACCOUNTURL, STORAGEACCOUNTKEY):
    logger.info(f'Connect to blob client')
    blob_service_client_instance = BlobServiceClient(
        account_url=STORAGEACCOUNTURL,
        credential=STORAGEACCOUNTKEY)
    logger.info(f'Create blob instance to open blob filename')
    container_client = blob_service_client_instance.get_blob_client(
        container, blob="{}".format(
            filename), snapshot=None)
    return container_client