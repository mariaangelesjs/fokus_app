# From https://github.com/josebenitezg/flaskGPT/blob/main/chatgpt.py and own
import os
import sys
import time
import openai
from flask import  url_for, redirect

data = []


def get_response(incoming_msg,  key, prompt):
    # Get proper messages
    if incoming_msg == "clear":
        data.clear()
        data.append({"role": "user", "content": 'Hei'})
    elif {"role":"user", "content": prompt} not in data:
        data.append({"role":"user", "content": prompt})
    else:
        data.append({"role": "user", "content": incoming_msg})
    
    try:
        response = openai.ChatCompletion.create(
            engine='gpt-test',
            messages=data,
            stop=['<|im_end|>']
        )
        content = response["choices"][0]["message"]["content"]
        return str(content)
    except openai.error.RateLimitError as e:
        print(e)
        return redirect(url_for('fokus_end'))
   
