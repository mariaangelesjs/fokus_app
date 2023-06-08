# From https://github.com/josebenitezg/flaskGPT/blob/main/chatgpt.py and own
import os
import sys
import time
import openai


systemPrompt = {
    "role": "system",
    "content": "Du er en hjelpsom assistent som bruker"
      " Bas Fokus til å generere en forespørsel og som er "
      " et produkt av Bas Kommunikasjon (https://bas.no/)) ."}
data = []


def get_response(incoming_msg,  key, prompt):
    if incoming_msg == "clear":
        data.clear()
        data.append({"role": "user", "content": 'Hei'})
        data.append({"role":"user", "content": prompt})
    elif {"role":"user", "content": prompt} not in data:
        data.append({"role":"user", "content": prompt})
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
        return str(content)
    except openai.error.RateLimitError as e:
        print(e)
        return ""
   
