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
)
app.permanent_session_lifetime = timedelta(minutes=20)
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

        if int(session['phone']) in fokus['KR_Phone_Mobile']:
            person = fokus[fokus['KR_Phone_Mobile'] ==
                           int(session['phone'])][fokus_segments]
        else:
            person = fokus.sample(1, random_state=42)[fokus_segments]
        session['data-person'] = person.to_json()
                    
        return redirect(url_for('prompt'))
    return render_template('form.html')

# Creating person based on who the person is


@app.route('/prompt_generation', methods=['GET', 'POST'])
def prompt():
    person = pd.read_json(session['data-person'])

    # Pretty variables and description

    fokus_variables_norwegian = {'Miljøvennlig': 'Grad av miljøvennlighet som personen prioriterer',
                                 'Nivå av impulsivitet': 'Grad av impulsivitet som personen handler med uten å vurdere konsekvenser',
                                 'Nivå av kultur': 'Grad av verdsattelse og verdsetting av kultur og kunst',
                                 'Gi til veldedighet': 'Frekvensen med hvilken personen donerer til ulike typer veldedige formål',
                                 'Gi til barneveldedighet': 'Frekvensen med hvilken personen donerer til veldedige organisasjoner som gagner barn',
                                 'Gi til katastrofe': 'Frekvensen med hvilken personen donerer til veldedige organisasjoner som responderer på naturkatastrofer og andre katastrofer',
                                 'Prisbevisst': 'Grad av prisbevissthet når personen gjør kjøp',
                                 'Prisjeger': 'Grad av aktiv søken etter lavest mulig pris når personen gjør kjøp',
                                 'Tilbudsjeger': 'Grad av aktiv søken etter rabatter og kampanjer når personen gjør kjøp',
                                 'Nivå av følelsesdrevet atferd': 'Grad av beslutninger som tas basert på følelser i stedet for logikk',
                                 'Sannsynlighet for å flytte': 'Sannsynligheten for at personen vil flytte til et nytt sted i nær fremtid',
                                 'Kjøp bil de neste 6 månedene': 'Sannsynligheten for at personen vil kjøpe en bil innen de neste 6 månedene',
                                 'Nivå av mobilitet': 'Grad av aktiv atferd',
                                 'Nivå av åpenhet': 'Grad av åpenhet for nye erfaringer og ideer',
                                 'Nivå av sosial konformitet': 'Grad av overholdelse av sosiale normer og forventninger',
                                 'Sannsynlighet for å ha hund': 'Sannsynligheten for at personen eier eller vil eie en hund',
                                 'Sannsynlighet for å ha katt': 'Sannsynligheten for at personen eier eller vil eie en katt',
                                 'Internasjonal reise': 'Grad av verdsattelse og verdsetting av internasjonal reise',
                                 'Sannsynlighet for å være introvert': 'Grad av identifisering som introvert',
                                 'Disponibel inntekt for enkeltpersoner': 'Mengden disponibel inntekt tilgjengelig for individet',
                                 'Disponibel inntekt for familier': 'Mengden disponibel inntekt tilgjengelig for personens familie'}
    # Real names and pretty variable
    fokus_real_new = {'environmentFriendly': 'Miljøvennlig',
                      'levelOfImpulsivity': 'Nivå av impulsivitet',
                      'levelOfCulture': 'Nivå av kultur',
                      'giveToCharity': 'Gi til veldedighet',
                      'giveToChildrenCharity': 'Gi til barneveldedighet',
                      'giveToCatastrophe': 'Gi til katastrofe',
                      'priceConscious': 'Prisbevisst',
                      'lowPriceSeeker': 'Lavprisjeger',
                      'offerSeeker': 'Tilbudsjeger',
                      'levelOfFeelingsDriven': 'Nivå av følelsesdrevet atferd',
                      'movingProbability': 'Sannsynlighet for å flytte',
                      'buyCar6m': 'Kjøp bil de neste 6 månedene',
                      'levelOfMovility': 'Nivå av bevegelighet',
                      'levelOfOpenness': 'Nivå av åpenhet',
                      'levelOfSocialConformity': 'Nivå av sosial konformitet',
                      'dogProbability': 'Sannsynlighet for å ha hund',
                      'catProbability': 'Sannsynlighet for å ha katt',
                      'internationalTravel': 'Internasjonal reise',
                      'introvertProbability': 'Sannsynlighet for å være introvert',
                      'disposableIncomeIndividual': 'Disponibel inntekt for enkeltpersoner',
                      'disposableIncomeFamily': 'Disponibel inntekt for familier'}

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
            ' av ' +
            session['product'] +
            ' til en person med ' +
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
        with limiter.limit("20/hour"):
            if request.method == 'GET':
                session['input'] = request.args.get('msg')
            if request.method == 'POST':
                return Response(
                    ChainStreamHandler.chain(
                        session['input'], key,'chat',
                        STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
                        CONTAINERNAME), mimetype='text/event-stream')
            else:
                return Response(None, mimetype='text/event-stream')
    except:
        return ""

@app.route('/unique_email', methods=['GET', 'POST'])
def gpt_email():
    return render_template('gpt_email.html')
    
@app.route('/get_email', methods=['GET', 'POST'])
def gpt_email_response():
    try:
        with limiter.limit("20/hour"):
            if request.method =='GET':
                session['tone'] = request.args.get('msg')
                tone = session['tone']
                print(session['tone'])
                session['full_prompt'] = str(session['prompt_done']).replace(
                    ' Skriv en artikel',f' Skriv en e-post fra Bas Analyse med {tone} tone of voice').replace('en person', session['name'])
                print(session['full_prompt'])
                try:
                    session['subject'] = request.args.get('subject')
                    session['content'] = request.args.get('content')

                except:
                    pass
            if request.method=='POST':
                return  Response(
                            ChainStreamHandler.chain(
                                session['full_prompt'] , key, 'email',
                                STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
                                CONTAINERNAME), mimetype='text/html')
            else:
                return Response(None, mimetype='text/html')
    except:
            return ""


username = client.get_secret('basAnalyseMail').value
mailpass = client.get_secret('basAnalyseMailPassword').value
STORAGEACCOUNTKEY = client.get_secret('storageFokusString').value
@app.route('/end', methods=['GET', 'POST'])
def fokus_end():
    try:
        send_email(
            username, mailpass, 
            session['name'], session['email'],
              session['subject'], session['content'])
        del username, mailpass
    except:
        pass
    if request.method == 'POST':
        session['feedback'] = request.form.get('feedback_done')
        print(session['feedback'])
        old_messages = download_pickle(
                    STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
                    CONTAINERNAME, 'output/fokus-test/conversation.pickle',  'No')
        try:
            feedback_old = pd.read_parquet(get_data(
                STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
                CONTAINERNAME, 'output/fokus-test/fokusGPT_leads.parquet'))
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
                             'output/fokus-test/fokusGPT_leads.parquet',
                             STORAGEACCOUNTURL, STORAGEACCOUNTKEY)
            del old_messages
            delete_blob(
            STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
              CONTAINERNAME,'output/fokus-test/conversation.pickle')
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
                                 'output/fokus-test/fokusGPT_leads.parquet',
                                 STORAGEACCOUNTURL,STORAGEACCOUNTKEY)
                delete_blob(
            STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
              CONTAINERNAME,'output/fokus-test/conversation.pickle')
            except:
                return "Ikke mulig å laste ned feedback"
    
    return render_template('fokus_gpt_end.html')

           


if __name__ == '__main__':
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.run(debug=True)
