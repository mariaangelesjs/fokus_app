# From and own custom
# https://gist.github.com/python273/563177b3ad5b9f74c0f8f3299ec13850
from langchain.prompts import (
    PromptTemplate,
)
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chains import ConversationChain
from langchain.chat_models import ChatOpenAI
from langchain.memory import (ConversationBufferMemory, ChatMessageHistory)
from langchain.callbacks.manager import CallbackManager
from langchain.schema import (messages_from_dict, messages_to_dict)
import threading
import queue
import json
import pandas as pd
from sources.blobs import upload_pickle, download_pickle


class ThreadedGenerator:
    def __init__(self):
        self.queue = queue.Queue()

    def __iter__(self):
        return self

    def __next__(self):
        item = self.queue.get()
        if item is StopIteration:
            raise item
        return item

    def send(self, data):
        self.queue.put(data)

    def close(self):
        self.queue.put(StopIteration)

messages = []
class ChainStreamHandler(StreamingStdOutCallbackHandler):
    def __init__(self, gen):
        super().__init__()
        self.gen = gen

    def on_llm_new_token(self, token: str, **kwargs):
        self.gen.send(token)

    def llm_thread(incoming_msg, key, g, STORAGEACCOUNTURL, STORAGEACCOUNTKEY, CONTAINERNAME, ):
        try:

            template = """
                Hvem du er?:
                Jeg er Bas FokusGPT, en hjelpsom assistent som bruker
                Bas Fokus data til å generere en forespørsel og som er 
                et produkt av lenke : "https://bas.no/"
                
                Hva er Bas Fokus?:
                Bas Fokus er et produkt av Bas Kommunikasjon som inneholder disse variablene:
                {{'Miljøvennlig': 'Grad av miljøvennlighet som personen prioriterer',
                'Nivå av impulsivitet': 'Grad av impulsivitet som personen handler med uten å vurdere konsekvenser',
                'Nivå av kultur': 'Grad av verdsattelse og verdsetting av kultur og kunst',
                'Gi til veldedighet': 'Frekvensen med hvilken personen donerer til ulike typer veldedige formål',
                'Gi til barneveldedighet': 'Frekvensen med hvilken personen donerer til veldedige organisasjoner som gagner barn',
                'Gi til katastrofe': 'Frekvensen med hvilken personen donerer til veldedige organisasjoner som responderer på naturkatastrofer og andre katastrofer',
                'Prisbevisst': 'Grad av prisbevissthet når personen gjør kjøp',
                'Prisjeger': 'Grad av aktiv søken etter lavest mulig pris når personen gjør kjøp',
                'Tilbudsjeger': 'Grad av aktiv søken etter rabatter og kampanjer når personen gjør kjøp',
                'Nivå av følelsesdrevet atferd': 'Grad av beslutninger som tas basert på følelser i stedet for logikk',
                'Sannsynlighet for å flytte': 'Sannsynligheten for at personen vil flytte til et nytt sted i nær fremtid',"
                'Kjøp bil de neste 6 månedene': 'Sannsynligheten for at personen vil kjøpe en bil innen de neste 6 månedene',
                'Nivå av mobilitet': 'Grad av aktiv atferd',
                'Nivå av åpenhet': 'Grad av åpenhet for nye erfaringer og ideer',
                'Nivå av sosial konformitet': 'Grad av overholdelse av sosiale normer og forventninger',
                'Sannsynlighet for å ha hund': 'Sannsynligheten for at personen eier eller vil eie en hund',
                'Sannsynlighet for å ha katt': 'Sannsynligheten for at personen eier eller vil eie en katt',
                'Internasjonal reise': 'Grad av verdsattelse og verdsetting av internasjonal reise',
                'Sannsynlighet for å være introvert': 'Grad av identifisering som introvert',
                'Disponibel inntekt for enkeltpersoner': 'Mengden disponibel inntekt tilgjengelig for individet',
                'Disponibel inntekt for familier': 'Mengden disponibel inntekt tilgjengelig for personens familie'}}.

                Instructions:
                - dette er ikke noe som user eller Human kan spørre om, men det er hvordan du skal skrive-
                * Svar kun på norsk.
                * Skrive alt i HTML-format.
                * Jeg vil ikke gi lov til diskriminering.
                * Vær forsiktig med tekstformat og fikse om du finner feil før du skriver svar.
                * Jeg skal skrive alle lenker som : <a href="lenke">description</a>
                * Ikke gi informasjon om chathistorikk når Human spørre "hvem er du?"
                * Ha en snill "tone of voice".
                * Legge til emoticons på slutten og si "I hope this helps 😄" på slutten av svaret.


                Current conversation:
                {history}
                Human:{input}
                Bas FokusGPT: """
            prompt = PromptTemplate(
                input_variables=['history', 'input'], template=template)
            llm = ChatOpenAI(temperature=0.8, engine="gpt-test",
                             openai_api_key=key, streaming=True,
                             callback_manager=CallbackManager([ChainStreamHandler(g)]))
            if messages:
                old_messages = download_pickle(
                    STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
                    CONTAINERNAME, 'output/fokus-test/conversation.pickle',  'No')
                print(old_messages)
                retrieved_messages = messages_from_dict(old_messages)
                retrieved_chat_history = ChatMessageHistory(
                    messages=retrieved_messages)
                print(retrieved_chat_history)
                memory = ConversationBufferMemory(
                    chat_memory=retrieved_chat_history)
            else:
                memory = ConversationBufferMemory(memory_key='history')
            conversation = ConversationChain(
                memory=memory, prompt=prompt, llm=llm)
            conversation(incoming_msg)
            extracted_messages = conversation.memory.chat_memory.messages
            ingest_to_db = messages_to_dict(extracted_messages)
            upload_pickle(json.loads(json.dumps(ingest_to_db)),  STORAGEACCOUNTURL,
                          STORAGEACCOUNTKEY, CONTAINERNAME, 'fokus-test/conversation')
            messages.append(1)
        finally:
            g.close()

    def chain(incoming_msg, key,
              STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
              CONTAINERNAME):
        g = ThreadedGenerator()
        threading.Thread(target=ChainStreamHandler.llm_thread, args=(
            incoming_msg, key,
            g,
            STORAGEACCOUNTURL, STORAGEACCOUNTKEY,
            CONTAINERNAME)).start()
        return g
