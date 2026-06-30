from langchain.chat_models import init_chat_model

from app.conf.app_config import app_config

llm = init_chat_model(model=app_config.llm.model_name,
                      model_provider="openai",
                      base_url=app_config.llm.base_url,
                      api_key=app_config.llm.api_key,
                      temperature=0)

keyword_llm = init_chat_model(model=app_config.keyword_llm.model_name,
                      model_provider="openai",
                      base_url=app_config.keyword_llm.base_url,
                      api_key=app_config.keyword_llm.api_key)

if __name__ == '__main__':
    print(llm.invoke("你好").content)
