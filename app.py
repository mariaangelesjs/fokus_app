#!/usr/bin/python

# Import packages
from flask import Flask, request, session, render_template, url_for, redirect
import uuid
from datetime import timedelta
from sources.blobs import get_data
import logging
import pandas as pd
from sources.blobs import get_data
from azure.storage.blob import BlobServiceClient
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
import openai
from fokus_gpt import get_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

# Get app
app = Flask(__name__)
CORS(app, supports_credentials=True)

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
openai.api_key = client.get_secret('fokusGPT').value
openai.api_base = client.get_secret('gptendpoint').value
openai.api_version = client.get_secret('gptversion').value

# Get input data


@app.route('/', methods=['GET', 'POST'])
def welcome():
    global person
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
    print(person)
    fokus_variables_norwegian = {'miljøvennlig': 'Grad av miljøvennlighet som personen prioriterer',
                                 'nivå av impulsivitet': 'Grad av impulsivitet som personen handler med uten å vurdere konsekvenser',
                                 'nivå av kultur': 'Grad av verdsattelse og verdsetting av kultur og kunst',
                                 'gi til veldedighet': 'Frekvensen med hvilken personen donerer til ulike typer veldedige formål',
                                 'gi til barneveldedighet': 'Frekvensen med hvilken personen donerer til veldedige organisasjoner som gagner barn',
                                 'gi til katastrofe': 'Frekvensen med hvilken personen donerer til veldedige organisasjoner som responderer på naturkatastrofer og andre katastrofer',
                                 'prisbevisst': 'Grad av prisbevissthet når personen gjør kjøp',
                                 'søker lav pris': 'Grad av aktiv søken etter lavest mulig pris når personen gjør kjøp',
                                 'søker tilbud': 'Grad av aktiv søken etter rabatter og kampanjer når personen gjør kjøp',
                                 'nivå av følelsesstyring': 'Grad av beslutninger som tas basert på følelser i stedet for logikk',
                                 'sannsynlighet for flytting': 'Sannsynligheten for at personen vil flytte til et nytt sted i nær fremtid',
                                 'kjøp bil 6 mnd': 'Sannsynligheten for at personen vil kjøpe en bil innen de neste 6 månedene',
                                 'nivå av mobilitet': 'Grad av verdsattelse og verdsetting av mobilitet og bevegelsesfrihet',
                                 'nivå av åpenhet': 'Grad av åpenhet for nye erfaringer og ideer',
                                 'nivå av sosial konformitet': 'Grad av overholdelse av sosiale normer og forventninger',
                                 'sannsynlighet for hund': 'Sannsynligheten for at personen eier eller vil eie en hund',
                                 'sannsynlighet for katt': 'Sannsynligheten for at personen eier eller vil eie en katt',
                                 'internasjonal reise': 'Grad av verdsattelse og verdsetting av internasjonal reise',
                                 'sannsynlighet for introvert': 'Grad av identifisering som introvert',
                                 'disponibel inntekt individ': 'Mengden disponibel inntekt tilgjengelig for individet',
                                 'disponibel inntekt familie': 'Mengden disponibel inntekt tilgjengelig for personens familie'}
    fokus_real_new = {'environmentFriendly': 'miljøvennlig',
                      'levelOfImpulsivity': 'nivå av impulsivitet',
                      'levelOfCulture': 'nivå av kultur',
                      'giveToCharity': 'gi til veldedighet',
                      'giveToChildrenCharity': 'gi til barneveldedighet',
                      'giveToCatastrophe': 'gi til katastrofe',
                      'priceConscious': 'prisbevisst',
                      'lowPriceSeeker': 'lavpris-søker',
                      'offerSeeker': 'tilbudssøker',
                      'levelOfFeelingsDriven': 'nivå av følelsesdrevet atferd',
                      'movingProbability': 'sannsynlighet for å flytte',
                      'buyCar6m': 'kjøp bil de neste 6 månedene',
                      'levelOfMovility': 'nivå av bevegelighet',
                      'levelOfOpenness': 'nivå av åpenhet',
                      'levelOfSocialConformity': 'nivå av sosial konformitet',
                      'dogProbability': 'sannsynlighet for å ha hund',
                      'catProbability': 'sannsynlighet for å ha katt',
                      'internationalTravel': 'internasjonal reise',
                      'introvertProbability': 'sannsynlighet for å være introvert',
                      'disposableIncomeIndividual': 'disponibel inntekt for enkeltpersoner',
                      'disposableIncomeFamily': 'disponibel inntekt for familier'}
    if request.method == 'POST':
        session['variable'] = request.form.get('variable')
        session['words'] = request.form.get('words')
        session['product'] = request.form.get('product')
        for key, value in fokus_real_new.items():
            if session['variable'] == value:
                fokus_real_variable = key
        value = person[fokus_real_variable].values[0]
        session['prompt_done'] = str(
            'Skriv ' +
            session['words'] +
            ' en artikel ' +
            session['product'] +
            ' til en person med ' +
            str(value) + ' in ' +
            session['variable'] + ' som er ' +
            session['work-position'] + ' i ' +
            session['industry']).replace('_', ' ')

        # redirect to GPT fokus
        return redirect(url_for('fokus_gpt'))
    return render_template('select_columns.html', columns=fokus_variables_norwegian)


@app.route('/unique_ad', methods=['GET', 'POST'])
def fokus_gpt():
    # run the bot
    return render_template('gpt_test.html', prompt=session['prompt_done'])


@app.route('/get', methods=['GET', 'POST'])
@limiter.limit("10/hour")
def gpt_response():
    messages = []
    # get the response
    userText = request.args.get('msg')
    messages.append(userText)
    content, data = get_response(userText, openai.api_key,
                                 session['prompt_done'])
    if len(data) > 9:
        return redirect(url_for('fokus_end'))
    else:
        return content

# End bot with this message after 9 messages (before cut)


@app.route('/end', methods=['GET', 'POST'])
def fokus_end():
    del openai
    del client
    return render_template('fokus_gpt_end.html')


    # if request.method == 'POST':
if __name__ == '__main__':
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.run(debug=True)
