import os
import sys
import time
import openai


systemPrompt = { "role": "system", "content": "You are a helpful assistant that uses Bas Fokus to generate a prompt." }
data = []

def get_response(incoming_msg,  key):
    if incoming_msg == "clear":
        data.clear()
        data.append({"role": "assistant", "content": 'Hello'})
    else:  
        data.append({"role": "assistant", "content": incoming_msg})

    messages = [ systemPrompt ]
    messages.extend(data)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
        stop=['<|im_end|>']
        )
        content = response["choices"][0]["message"]["content"]
        return content
    except openai.error.RateLimitError as e:
        print(e)
        return ""