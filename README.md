# FOKUS GPT

Here we created a Flask APP that runs from Azure Web Services.

## What's Bas Analytics purpose?
>
> This demo will save possible leads that Bas Kommunikasjon can use. Also, the users will be sent a personalised e-mail depending on who they are.
> **Fun takes :**
> > This also helps us learn from our leads and retrain our models.
>
## What is contained within?
>
> * Home : Users connect to this application via their windows account (Microsoft tentant or personal microsoft).the user needs to fill in a form that asks for its name, e-mail, phone, work position and industry.
> * Personalided prompt : the user can create a personalised prompt that will be used to prompt our Bas Analytics Chat GPT so that the user gets an article that sells their product of interest. The user has three options: choose how many words (300 or 500), choose which Bas Fokus variable they want to get, and which product they want to sell.
> * Bas Fokus - GPT: the user has a pre-made prompt to start chatting with ChatGPT. There is a max of 5 answers that the user can do to our personalised chat. The chat learns from previous prompts.
> * Feedback (still testing) : the user will be directed to give feedback if wanted.

### How does this run?

* Front-end is a combination of HTML and JavaScript code.
* Back-end is python-based.
* Both front-end and back-end are contained within a Flask APP and deployed through Azure Pipelines.
* After deployment, the app runs through Azure Web Apps and can be displayed/embebbed on a website.
  
## Application Structure

```
.
|──────sources/
| |────blobs.py
|──────static/
| |────css/
| |────images/
| |────styles/
|──────templates/
|──────app.py
|──────azure-pipelines.yml
|──────fokus-gpt.py
|──────requirements.txt

```

## Run Bas Fokus GPT 

### Develop

```
$ python webapp/run.py
```

In flask, Default port is `5000`

Swagger document page:  `http://127.0.0.1:5000/api`

### Run flask for production

**Run with gunicorn**
Our startup command is pre-defined in our deployment:

```
gunicorn --bind=0.0.0.0 --workers=4 --timeout 600 app:app
```

