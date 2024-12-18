import re
from langchain_core.documents import Document
# from langchain_community.vectorstores import NNITChroma, Chroma
from langchain_openai import AzureOpenAIEmbeddings

from datetime import datetime

import json
import os
from openai import AzureOpenAI
# from prompt import iamge_instruction


with open('/home/adminsiyu/code/nnit-chat-chromadb/vector_code/config.json', 'r') as f:
    config_data = json.load(f)

openai_api_key = config_data['api_key_ada3']
azure_endpoint = config_data['azure_endpoint_ada3']
openai_api_version = config_data['openai_api_version']
model_name_emdedding = config_data['model_name_emdedding_ada3']
model_name_gpt = config_data['model_name_gpt35_ada3']
model_name_gpt_4o = config_data['model_name_4o']

persist_directory = f'/home/adminsiyu/code/study-code/BD/vectorstore'
collection_name = "BD-ACE"
date = datetime.now().strftime("%Y-%m-%d")


client = AzureOpenAI(
    api_key=openai_api_key,
    base_url=f"{azure_endpoint}/openai/deployments/{model_name_gpt_4o}",
    api_version="2023-12-01-preview"
)

embeddings = AzureOpenAIEmbeddings(
    openai_api_key=openai_api_key,
    azure_endpoint=azure_endpoint,
    openai_api_version=openai_api_version,
    model=model_name_emdedding
)

db = NNITChroma(
    collection_name=collection_name,
    embedding_function=embeddings,
    persist_directory=persist_directory,
    collection_metadata={
        "date":date
    }
)

def get_image_filenames(directory):
    files = os.listdir(directory)
    image_files = [f[:-4] for f in files if f.startswith("page_") and f.endswith(".png")]
    return image_files


def extract_information_from_image(image_url):
    response = client.chat.completions.create(
        model=model_name_gpt_4o,
        messages=[
            { "role": "system", "content": "extract information from image" },
            { 
                "role": "user", 
                "content": [  
                    { 
                        "type": "text", 
                        "text": "extract information from image"
                    },
                    { 
                        "type": "image_url",
                        "image_url": {
                            "url": f"http://chatgpt.nnit.cn:8002/images/{image_url}.png",
                            "detail": "high"
                        }
                    }
                ] 
            } 
        ],
        max_tokens=3000 
    )

    return response.choices[0].message.content

def extract_markdown_h1(text):
    # 使用正则表达式查找 Markdown 一级标题
    matches = re.findall(r'^#\s*(.*)', text, re.MULTILINE)
    
    # 返回第一个标题的内容，如果没有找到则返回 "Unknown"
    return matches[0].strip() if matches else "Unknown"


def build_docs(image_url) -> dict:
    page_content = extract_information_from_image(image_url)
    source = f"系统经销商培训手册__v1.0_{image_url}"

    doc = Document(
        page_content=page_content,
        metadata={"source": source},
    )
    id = extract_markdown_h1(page_content) + f"-{image_url}"
    # print(id)
    print(f"===已完成{image_url}===")
    # print({"doc":doc, "id":id})
    return {"doc":doc, "id":id}

if __name__ == "__main__":

    # directory = '/home/adminsiyu/code/study-code/BD/images'
    directory = '/home/adminsiyu/code/study-code/BD/images/erp'
    url_list = get_image_filenames(directory)
    docs = []

    # 示例用法
    for url in url_list:
        print(f"===开始处理{url}===")
        doc = build_docs(url)
        print(doc)
        # docs.append(doc)
        db.add_documents(documents=[doc['doc']], ids=[doc['id']])
        print(f"===已添加{url}===")


    # filename = './documents.txt'
    # with open(filename, 'w') as f:
    #     for item in docs:
    #         # print(f"{item}")
    #         f.write(f"{item}\n")
    
    # db.add_documents