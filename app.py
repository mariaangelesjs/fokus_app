#!/usr/bin/python

# Import packages
from flask import (Flask, request, session, render_template,
                   url_for, redirect, Response)
from datetime import timedelta
from sources.blobs import (get_data, upload_df, download_pickle, delete_blob)
from sources.emails import send_email
import logging
import pandas as pd
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
import openai
from sources.fokus_gpt import ChainStreamHandler
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import numpy as np
import random

# Get app
app = Flask(__name__)
CORS(app, supports_credentials=True)

limiter = Limiter(
    get_remote_address,
    app=app
)

# Start logger

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

limiter = Limiter(
    get_remote_address,
    app=app
)

# Suppress info from blob storage logger

blob_logger = logging.getLogger(
    'azure.core.pipeline.policies.http_logging_policy')
blob_logger.setLevel(logging.WARNING)

# Get environment variables
KVUri = f'https://bas-analyse.vault.azure.net'
credential = DefaultAzureCredential()

# Add cookie configuration
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_PERMANENT=False
)


# Assign client

global client
client = SecretClient(vault_url=KVUri, credential=credential)
STORAGEACCOUNTURL = client.get_secret('storageAccountURL').value
STORAGEACCOUNTKEY = client.get_secret('storageFokusString').value
STORAGESTRING = client.get_secret('storageAnalyseString').value
CONTAINERNAME = '***CONTAINER***'

# assign app key

uid_secret_key = client.get_secret('gptFokusFlask').value
app.secret_key = uid_secret_key

# Setting up openai client

openai.api_type = 'azure'
key = client.get_secret('fokusGPT').value
openai.api_base = client.get_secret('gptendpoint').value
openai.api_version = client.get_secret('gptversion').value

# Get input data


@app.route('/', methods=['GET', 'POST'])
def welcome():
    if request.method == 'POST':
        # getting input with name = fname in HTML form
        session['lead'] = request.form.get('lead')
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
        if session['phone'].startswith('+47'):
            session['phone'] = session['phone'].replace('+47', '')
        else:
            session['phone'] = session['phone'].replace(' ', '')

        if session['phone'] in fokus['KR_Phone_Mobile']:
            person = fokus[fokus['KR_Phone_Mobile'] ==
                           int(session['phone'])][fokus_segments]
        else:
            person = fokus.sample(1, random_state=42)[fokus_segments]
        session['data-person'] = person.to_json()
        del person

        return redirect(url_for('prompt'))
    return render_template('form.html')

# Creating person based on who the person is


@app.route('/prompt_generation', methods=['GET', 'POST'])
def prompt():
    person = pd.read_json(session['data-person'])
    session.pop('data-person')
    # Pretty variables and description

    fokus_variables_norwegian = {'Miljøbevisste': 'De er opptatt av å redusere sitt miljøavtrykk. Økologiske eller bærekraftige produkter vil være mer attraktive for denne gruppen',
                                 'Impulsive': 'De handler ofte uten å tenke seg godt om, noe som betyr at de kan være mottakelige for tidsbegrensede tilbud eller flash-salg',
                                 'Kulturnivå': 'Grad av verdsattelse og verdsetting av kultur og kunst',
                                 'Gi til veldedighet': 'Frekvensen med hvilken personen donerer til ulike typer veldedige formål',
                                 'Gi til barneveldedighet': 'Frekvensen med hvilken personen donerer til veldedige organisasjoner som gagner barn',
                                 'Gi til katastrofe': 'Frekvensen med hvilken personen donerer til veldedige organisasjoner som responderer på naturkatastrofer og andre katastrofer',
                                 'Prisjegere': 'Grad av prisbevissthet når personen gjør kjøp',
                                 'Lavprisjegere': 'Grad av aktiv søken etter lavest mulig pris når personen gjør kjøp',
                                 'Tilbudsjeger': 'Grad av aktiv søken etter rabatter og kampanjer når personen gjør kjøp',
                                 'Følelsesdrevne': 'De handler ofte basert på følelser og impulser, noe som gjør dem mottakelige for markedsføring som appellerer til følelser, enten det er glede, nostalgi, spenning, eller noe annet',
                                 'Flyttesannsynlighet': 'Sannsynligheten for at personen vil flytte til et nytt sted i nær fremtid',
                                 'Sannsynlighet for å kjøpe ny bil': 'Sannsynligheten for at personen vil kjøpe en bil innen de neste 6 månedene',
                                 'Aktive': 'De har en aktiv livsstil og liker å være i bevegelse. De kan derfor være mer interessert i produkter og tjenester som støtter en aktiv livsstil',
                                 'Liberale': 'De verdsetter frihet og selvstendighet, så produkter og tjenester som fremmer disse verdiene kan være attraktive for dem',
                                 'Sosialt påvirkede': 'De lar andres meninger og handlinger styre deres egne. Dette betyr at omtaler, anbefalinger og sosiale bevis kan være effektive markedsføringsstrategier.',
                                 'Hundeelskere': 'Sannsynligheten for at personen eier eller vil eie en hund',
                                 'Katteelskere': 'Sannsynligheten for at personen eier eller vil eie en katt',
                                 'Utenlandsreisende': 'De liker å reise utenlands og oppleve nye kulturer. Reise-relaterte produkter og tjenester, samt kulturelt mangfold, kan appellere til dem',
                                 'Introverte': ' De foretrekker å være alene eller i små grupper fremfor store sosiale situasjoner. Produkter og tjenester som fremmer selvstendighet, personlig utvikling eller hjemmekos kan være tiltrekkende for denne gruppen',
                                 'Kjøpekraft per individ': 'Mengden disponibel inntekt tilgjengelig for individet',
                                 'Kjøpekraft per familier': 'Mengden disponibel inntekt tilgjengelig for personens familie'}
    # Real names and pretty variable
    fokus_real_new = {'environmentFriendly': 'Miljøbevisste',
                      'levelOfImpulsivity': 'Impulsive',
                      'levelOfCulture': 'Kulturnivå',
                      'giveToCharity': 'Gi til veldedighet',
                      'giveToChildrenCharity': 'Gi til barneveldedighet',
                      'giveToCatastrophe': 'Gi til katastrofe',
                      'priceConscious': 'Prisjegeret',
                      'lowPriceSeeker': 'Lavprisjegere',
                      'offerSeeker': 'Tilbudsjegere',
                      'levelOfFeelingsDriven': 'Følelsesdrevne',
                      'movingProbability': 'Flyttesannsynlighet',
                      'buyCar6m': 'Sannsynlighet for å kjøpe ny bil',
                      'levelOfMovility': 'Aktive',
                      'levelOfOpenness': 'Liberale',
                      'levelOfSocialConformity': 'Sosialt påvirkede',
                      'dogProbability': 'Hundeelskere',
                      'catProbability': 'Katteelskere',
                      'internationalTravel': 'Utenlandsreisende',
                      'introvertProbability': 'Introverte',
                      'disposableIncomeIndividual': 'Kjøpekraft per individ',
                      'disposableIncomeFamily': 'Kjøpekraft per familier'}

    # Get transpose for front-end form
    person_table = person.rename(
        columns=fokus_real_new).reset_index(drop=True).T
    person_table.rename_axis('Fokus variabel', axis='index', inplace=True)
    person_table.columns = ['Verdi']

    # Get values for prompt

    if request.method == 'POST':
        session['variable'] = request.form.get('variable')
        session['words'] = request.form.get('words')
        session['product'] = request.form.get('product')
        for key, value in fokus_real_new.items():
            if session['variable'] == value:
                fokus_real_variable = key
        value = person[fokus_real_variable].values[0]
        session['prompt_done'] = str(
            'Skriv' +
            ' en artikel med ' +
            session['words'] +
            ' som sier hvordan kan man øke salg av ' +
            session['product'] +
            ' til personer med ' +
            str(value) + ' i ' +
            session['variable'] + ' som er ' +
            session['work-position'] + ' i ' +
            session['industry']).replace('_', ' ')
        return redirect(url_for('choose_gpt'))
    return render_template(
        'select_columns.html',
        columns=fokus_variables_norwegian,
        tables=person_table.reset_index().to_dict(orient='records'))


@app.route('/choose_service')
def choose_gpt():
    # run the bot
    return render_template('choose_gpt.html')


@app.route('/unique_ad', methods=['GET', 'POST'])
def fokus_gpt():
    # run the bot
    return render_template('gpt_test.html', prompt=session['prompt_done'])


@app.route('/get', methods=['GET', 'POST'])
def gpt_chat_response():
    try:
        # End bot with this message after 10 messages (before cut)
        with limiter.limit("20/day"):
            if request.method == 'GET':
                session['input'] = request.args.get('msg')
            if request.method == 'POST':
                return Response(
                    ChainStreamHandler.chain(
                        session['input'], key, 'chat',
                        STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
                        CONTAINERNAME, random_conversation), mimetype='text/event-stream')
            else:
                return Response(None, mimetype='text/event-stream')
    except:
        if session['lead'] == 'Nei':
                    session.clear()
        return "rate limit is 10 requests per day. You have requested too much"


@app.route('/unique_email', methods=['GET', 'POST'])
def gpt_email():
    return render_template('gpt_email.html')


random_conversation = random.randint(-10000000000000, 10000000000000)


@app.route('/get_email', methods=['GET', 'POST'])
def gpt_email_response():
    try:
        with limiter.limit("10/day"):
            if request.method == 'GET':
                session['tone'] = request.args.get('msg')
                tone_replace = str(
                    'Skriv en e-post fra Bas Analyse med en ' + session['tone'] + ' tone of voice')
                print(tone_replace)
                session['full_prompt'] = str(session['prompt_done']).replace(
                    'Skriv en artikel', tone_replace).replace('personer', session['name']) 
                print(session['full_prompt'])
            if request.method == 'POST':
                return Response(
                    ChainStreamHandler.chain(
                        session['full_prompt'], key, 'email',
                        STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
                        CONTAINERNAME, random_conversation), mimetype='text/event-stream')
            else:
                # This is for saving feedback
                return Response(None, mimetype='text/event-stream')
    except:
        if session['lead'] == 'Nei':
                    session.clear()
        session['subject'] = request.args.get('subject')
        print(session['subject'])
        session['content'] = request.args.get('content')
        print(session['content'])
        return "rate limit is 5 requests per day. You have requested too much"


username = client.get_secret('basAnalyseMail').value
mailpass = client.get_secret('basAnalyseMailPassword').value
STORAGEACCOUNTKEY = client.get_secret('storageFokusString').value


@app.route('/end', methods=['GET', 'POST'])
def fokus_end():
    # This is for saving feedback
    if session['lead'] == 'Nei':
        session.clear()
        delete_blob(
                STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
                CONTAINERNAME, f'output/fokus-test/FokusGPT/conversation_{random_conversation}.pickle')
        return redirect(url_for('welcome'))
    else:
        if request.method == 'POST':
            session['feedback'] = request.form.get('feedback_done')
            print(session['feedback'])
            old_messages = download_pickle(
                STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
                CONTAINERNAME, f'output/fokus-test/FokusGPT/conversation_{random_conversation}.pickle',  'No')
            try:
                feedback_old = pd.read_parquet(get_data(
                    STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
                    CONTAINERNAME, 'output/fokus-test/FokusGPT/FokusGPT_leads.parquet'))
                feedback_new = pd.DataFrame(
                    index=[0], data={
                        'Navn': str(session['name']),
                        'Phone': str(session['phone']),
                        'E-post': str(session['email']),
                        'Stilling': str(session['work-position']),
                        'Industri': str(session['industry']),
                        'Tilbakemelding': str(session['feedback'])})
                feedback_new['Samtale'] = str(old_messages)
                feedback = pd.concat([feedback_old, feedback_new],
                                    axis=0).reset_index(drop=True)
                upload_df(feedback, CONTAINERNAME,
                        'output/fokus-test/FokusGPT/FokusGPT_leads.parquet',
                        STORAGEACCOUNTURL, STORAGEACCOUNTKEY)
                del old_messages
                delete_blob(
                    STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
                    CONTAINERNAME, f'output/fokus-test/FokusGPT/conversation_{random_conversation}.pickle')
                logging.info('Deleted blob')
                session.clear()
                return redirect(url_for('welcome'))
            except:
                try:
                    feedback = pd.DataFrame(index=[0], data={
                        'Navn': str(session['name']),
                        'Phone': str(session['phone']),
                        'E-post': str(session['email']),
                        'Stilling': str(session['work-position']),
                        'Industri': str(session['industry']),
                        'Tilbakemelding': str(session['feedback'])})
                    feedback['Samtale'] = str(old_messages)
                    upload_df(feedback, CONTAINERNAME,
                            'output/fokus-test/FokusGPT/FokusGPT_leads.parquet',
                            STORAGEACCOUNTURL, STORAGEACCOUNTKEY)
                    delete_blob(
                        STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
                        CONTAINERNAME, f'output/fokus-test/FokusGPT/conversation_{random_conversation}.pickle')
                    logging.info('Deleted blob')
                    session.clear()
                    return redirect(url_for('welcome'))
                except:
                    session.clear()
                    return "Ikke mulig å laste ned tilbakemelding"

    return render_template('fokus_gpt_end.html')


if __name__ == '__main__':
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.run()
