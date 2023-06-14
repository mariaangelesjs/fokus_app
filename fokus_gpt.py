# From https://github.com/josebenitezg/flaskGPT/blob/main/chatgpt.py and own
import os
import sys
import time
import openai
from flask import url_for, redirect

systemPrompt = {
    "role": "system",
    "content": "Jeg er en hjelpsom assistent som bruker"
    " Bas Fokus til å generere en forespørsel og som er "
    " et produkt av Bas Kommunikasjon (https://bas.no/))."
    " Bas Fokus er et produkt av Bas Kommunikasjon som inneholder disse variablene:"
    "{'Miljøvennlig': 'Grad av miljøvennlighet som personen prioriterer',"
    "'Nivå av impulsivitet': 'Grad av impulsivitet som personen handler med uten å vurdere konsekvenser',"
    "'Nivå av kultur': 'Grad av verdsattelse og verdsetting av kultur og kunst',"
    "'Gi til veldedighet': 'Frekvensen med hvilken personen donerer til ulike typer veldedige formål',"
    "'Gi til barneveldedighet': 'Frekvensen med hvilken personen donerer til veldedige organisasjoner som gagner barn',"
    "'Gi til katastrofe': 'Frekvensen med hvilken personen donerer til veldedige organisasjoner som responderer på naturkatastrofer og andre katastrofer',"
    "'Prisbevisst': 'Grad av prisbevissthet når personen gjør kjøp',"
    "'Prisjeger': 'Grad av aktiv søken etter lavest mulig pris når personen gjør kjøp',"
    "'Tilbudsjeger': 'Grad av aktiv søken etter rabatter og kampanjer når personen gjør kjøp',"
    "'Nivå av følelsesdrevet atferd': 'Grad av beslutninger som tas basert på følelser i stedet for logikk',"
    "'Sannsynlighet for å flytte': 'Sannsynligheten for at personen vil flytte til et nytt sted i nær fremtid',"
    "'Kjøp bil de neste 6 månedene': 'Sannsynligheten for at personen vil kjøpe en bil innen de neste 6 månedene',"
    "'Nivå av mobilitet': 'Grad av aktiv atferd',"
    "'Nivå av åpenhet': 'Grad av åpenhet for nye erfaringer og ideer',"
    "'Nivå av sosial konformitet': 'Grad av overholdelse av sosiale normer og forventninger',"
    "'Sannsynlighet for å ha hund': 'Sannsynligheten for at personen eier eller vil eie en hund',"
    "'Sannsynlighet for å ha katt': 'Sannsynligheten for at personen eier eller vil eie en katt',"
    "'Internasjonal reise': 'Grad av verdsattelse og verdsetting av internasjonal reise',"
    "'Sannsynlighet for å være introvert': 'Grad av identifisering som introvert',"
    "'Disponibel inntekt for enkeltpersoner': 'Mengden disponibel inntekt tilgjengelig for individet',"
    "'Disponibel inntekt for familier': 'Mengden disponibel inntekt tilgjengelig for personens familie'}"
    " Hvis en person skrive om en av disse variablene, definere disse men ikke inkludere de i teksten'"}
data = []


def get_response(incoming_msg,  key, prompt):
    # Get proper messages
    if incoming_msg == "clear":
        data.clear()
        data.append({"role": "user", "content": 'Hei'})
    elif {"role": "user", "content": prompt} not in data:
        data.append({"role": "user", "content": prompt})
    else:
        data.append({"role": "user", "content": incoming_msg})

    messages = [systemPrompt]
    messages.extend(data)

    try:
        response = openai.ChatCompletion.create(
            engine='gpt-test',
            messages=messages,
            stop=['<|im_end|>']
        )
        content = response["choices"][0]["message"]["content"]
        return str(content), data
    except openai.error.RateLimitError as e:
        print(e)
        return ""
