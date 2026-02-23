# python3 playground.py

from anthropic import Anthropic
from dotenv import load_dotenv
import sys

sys.path.insert(0, "/Users/hariom/rolplay-ai/agente_rolplay/src")
from agente_rolplay.tools import clasificador_saludo_inicial, anthropic_completion
from agente_rolplay.system_prompt import prompt_saludo, texto_agrocker, context

import os

load_dotenv()
anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = os.getenv("ANTHROPIC_MODEL_NAME")
supabase_api_key = os.getenv("SUPABASE_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")

client = Anthropic(api_key=anthropic_api_key)

if __name__ == "__main__":
    # query = "Hola quiero una muestra"
    query = "su producto elimina la macrofamina ? "
    messages = [{"role": "user", "content": query}]

    ans = clasificador_saludo_inicial(messages=messages)
    print(ans)

    system_prompt = prompt_saludo
    system_prompt += f"ES LA UNICA INFORMACIÓN QUE PUEDES PROPORCIONAR DEL PRODUCTO 'AGROCKER' : {texto_agrocker}"
    # system_prompt += context

    messages = [{"role": "user", "content": query}]

    anthropic_completion(system_prompt=system_prompt, messages=messages)

    # system_prompt = prompt_saludo
    # system_prompt += f"ES LA UNICA INFORMACIÓN QUE PUEDES PROPORCIONAR DEL PRODUCTO 'AGROCKER' : {texto_agrocker}"
    # queries = [
    #     'Hola quiero una muestra',
    #     'Hola quiero mas informacion de los productos y saber si distribuyen en Guadalajara y Michoacan',
    #     'buenos dias , tiene producto para curar abejas ? de la varroa ? ',
    # ]
    # answers = []

    # for query in queries:
    #     messages = [{"role": "user", "content": query}]

    #     answer = anthropic_completion(
    #         system_prompt=system_prompt,
    #         messages=messages
    #     )
    #     answers.append((query, answer['answer']))

    # for q,a in answers:
    #     print('===================')
    #     print('Q:', q)
    #     print('A:', a)
    #     print('===================')
