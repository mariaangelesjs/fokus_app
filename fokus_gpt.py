# From and own custom
# https://gist.github.com/python273/563177b3ad5b9f74c0f8f3299ec13850
from langchain.prompts import (
    MessagesPlaceholder, 
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chains import ConversationChain
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.manager import CallbackManager
import threading 
import queue
    
class ThreadedGenerator:
    def __init__(self):
        self.queue = queue.Queue()

    def __iter__(self):
        return self

    def __next__(self):
        item = self.queue.get()
        if item is StopIteration: raise item
        return item

    def send(self, data):
        self.queue.put(data)

    def close(self):
        self.queue.put(StopIteration)

class ChainStreamHandler(StreamingStdOutCallbackHandler):
    def __init__(self, gen):
        super().__init__()
        self.gen = gen

    def on_llm_new_token(self, token: str, **kwargs):
        self.gen.send(token)

    def llm_thread(incoming_msg, key, g):
        try:
            systemPrompt = SystemMessagePromptTemplate.from_template(
            '''
            Jeg er en hjelpsom assistent som bruker"
            Bas Fokus til å generere en forespørsel og som er 
            et produkt av Bas Kommunikasjon.
            Du kan få informasjon om [Bas Kommunikasjon] fra https://bas.no/.
            [Bas Fokus] er et produkt av [Bas Kommunikasjon] som inneholder disse variablene:
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
            'Disponibel inntekt for familier': 'Mengden disponibel inntekt tilgjengelig for personens familie'}}
            Hvis en person skrive om en av disse variablene, definere disse men ikke inkludere de i artikelen'
            Ikke gi lov til diskriminering.

        '''
        )
            humanPrompt = HumanMessagePromptTemplate.from_template("{input}")
            history = MessagesPlaceholder(variable_name="history")
            prompt = ChatPromptTemplate.from_messages([systemPrompt, history, humanPrompt])
            llm = ChatOpenAI(temperature=0, engine="gpt-test", openai_api_key=key, streaming=True, callback_manager=CallbackManager([ChainStreamHandler(g)]))
            memory = ConversationBufferMemory(return_messages=True)
            conversation = ConversationChain(memory=memory, prompt=prompt, llm=llm)
            conversation(incoming_msg)
        finally:
            g.close()


    def chain(incoming_msg, key):
            g = ThreadedGenerator()
            threading.Thread(target=ChainStreamHandler.llm_thread, args=(incoming_msg, key, g)).start()
            return g