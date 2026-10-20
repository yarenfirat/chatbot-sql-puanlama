import os 
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
load_dotenv()

my_api_key_openai = os.getenv("openai_key")

llm=ChatOpenAI(
    model_name="gpt-4o", 
    openai_api_key=my_api_key_openai,
)