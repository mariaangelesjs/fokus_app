#!/usr/bin/python

# Import packages
from urllib.request import urlopen
from flask import Flask, request, session, render_template, url_for, redirect
import uuid
import datetime
from datetime import timedelta
from sources.blobs import get_data
from flask_login import LoginManager
import logging
from azure.storage.blob import BlobServiceClient
import os
import pandas as pd
from sources.blobs import get_data
import gc
from io import BytesIO
from azure.storage.blob import BlobServiceClient
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
import openai
import streamlit as st
from streamlit_chat import message
from fokus_gpt import get_response
app = Flask(__name__)

uid_secret_key = str(uuid.uuid4())

app.secret_key = uid_secret_key

# Start logger

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


# Suppress info from blob storage logger

blob_logger = logging.getLogger(
    'azure.core.pipeline.policies.http_logging_policy')
blob_logger.setLevel(logging.WARNING)

# Get environment variables
KVUri = f'https://bas-analyse.vault.azure.net'
credential = DefaultAzureCredential()
client = SecretClient(vault_url=KVUri, credential=credential)
STORAGEACCOUNTURL = client.get_secret('storageAccountURL').value
STORAGEACCOUNTKEY = client.get_secret('storageFokusString').value
STORAGESTRING = client.get_secret('storageAnalyseString').value
CONTAINERNAME = '***CONTAINER***'

openai.api_type = 'azure'
openai.api_key = client.get_secret('fokusGPT').value
openai.api_base = client.get_secret('gptendpoint').value
openai.api_version = client.get_secret('gptversion').value

# Get input data


@app.route('/', methods=['GET', 'POST'])
def welcome():
    if request.method == 'POST':
        # getting input with name = fname in HTML form
        session['name'] = request.form.get('name')
        session['email'] = request.form.get('e-post')
        # getting input with name = lname in HTML form
        session['phone'] = request.form.get('phone')
        session['industry'] = request.form.get('industry')
        session['work-position'] = request.form.get('work-position')
        fokus = pd.read_parquet(get_data(
            STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
            CONTAINERNAME, 'output/fokus-snapshot/FokusKategorierMemento.parquet'))
        fokus_segments = ['environmentFriendly', 'levelOfImpulsivity',
                          'levelOfCulture', 'giveToCharity',
                          'giveToChildrenCharity', 'giveToCatastrophe',
                          'priceConscious', 'lowPriceSeeker',
                          'offerSeeker', 'levelOfFeelingsDriven',
                          'movingProbability', 'buyCar6m',
                          'levelOfMovility', 'levelOfOpenness',
                          'levelOfSocialConformity', 'dogProbability',
                          'catProbability', 'internationalTravel',
                          'introvertProbability',
                          'disposableIncomeIndividual', 'disposableIncomeFamily']
        global person
        try:
            person = fokus[fokus['KR_Phone_Mobile'] ==
                           int(session['phone'])][fokus_segments]
        except:
            person = fokus.sample(1, random_state=42)[fokus_segments]
        return redirect(url_for('prompt'))
    return render_template('form.html')


@app.route('/prompt_generation', methods=['GET', 'POST'])
def prompt():
    if request.method == 'POST':
        session['variable'] = request.form.get('variable')
        session['words'] = request.form.get('words')
        session['product'] = request.form.get('product')
        global prompt_done
        value = person[session['variable']].replace(
            {'Lav': 'Low', 'Middels': 'Mild', 'Høy': 'High'}).values[0]
        prompt_done = str(
            'Write a ' +
            session['words'] +
            ' article selling ' +
            session['product'] +
            ' for a person with ' +
            str(value) + ' in ' +
            session['variable'] + ' that works as ' +
            session['work-position'] + ' in ' +
            session['industry']).replace('_', ' ')
        return redirect(url_for('fokus_gpt'))
    return render_template('select_columns.html', columns=person.columns.values, person=person)


@app.route('/unique_ad', methods=['GET', 'POST'])
def fokus_gpt():
    # Return answer as JSON
    return render_template('gpt_test.html', prompt=prompt_done)

@app.route('/get', methods=['GET', 'POST'])
def gpt_response():
    userText = request.args.get('msg')
    return str(get_response(userText, openai.api_key))


    # if request.method == 'POST':
if __name__ == '__main__':
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.run(debug=True)
