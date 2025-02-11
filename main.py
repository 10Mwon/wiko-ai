from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Union, List, Dict
import openai
from sentence_transformers import SentenceTransformer
import faiss
import json
import os
from dotenv import load_dotenv
import glob

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

json_folder = "base_data"
json_files = glob.glob(os.path.join(json_folder, "*.json"))

documents = []
for file_path in json_files:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    document = {
        "title": data.get("title", data.get("name", "Untitled")),
        "description": data.get("content", "")
    }
    documents.append(document)

document_texts = [doc["description"] for doc in documents]

model = SentenceTransformer('all-MiniLM-L6-v2')
document_embeddings = model.encode(document_texts)
if document_embeddings.ndim == 1:
    document_embeddings = document_embeddings.reshape(1, -1)
embedding_dim = document_embeddings.shape[1]
index = faiss.IndexFlatL2(embedding_dim)
index.add(document_embeddings)

def retrieve_information(query: str, top_k: int = 3):
    query_embedding = model.encode([query])
    distances, indices = index.search(query_embedding, top_k)
    retrieved = [documents[i] for i in indices[0] if i < len(documents)]
    return retrieved

def generate_response(user_query: str, retrieved_info: list):
    info_text = ""
    for i, info in enumerate(retrieved_info, 1):
        info_text += f"{i}. 제목: {info.get('title')}\n   설명: {info.get('description')}\n"
    prompt = f"""
    사용자 질문: "{user_query}"
    
    아래는 관련 정보입니다:
    {info_text}
    
    위 정보를 바탕으로 사용자에게 알기 쉽게 답변을 작성해 주세요.
    """
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "너는 지금 외국인 근로자와 대화를 하는 친절한 상담원이야."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500,
    )
    answer = response.choices[0].message.content.strip()
    return answer

def format_center_info(center: dict) -> str:
    center_name = center.get("center_name", "")
    address = center.get("address", "")
    telephone = center.get("telephone", "")
    url = center.get("url", "")
    if url:
        return f"{center_name}\n{address}\n전화번호: {telephone}\n웹사이트: {url}"
    else:
        return f"{center_name}\n{address}\n전화번호: {telephone}"

current_dir = os.path.dirname(os.path.abspath(__file__))
preset_answers_file = os.path.join(current_dir, "preset_answers", "preset_answers.json")
with open(preset_answers_file, "r", encoding="utf-8") as f:
    preset_answers = json.load(f)

app = FastAPI()

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str = None
    sub_questions: Union[List[str], List[Dict[str, str]], None] = None

@app.post("/chatbot", response_model=QueryResponse)
async def chat_endpoint(query_request: QueryRequest):
    user_question = query_request.question.strip()
    try:
        if user_question in preset_answers:
            top_value = preset_answers[user_question]
            if isinstance(top_value, dict):
                sub_qs = list(top_value.keys())
                return QueryResponse(sub_questions=sub_qs)
            else:
                return QueryResponse(answer=str(top_value))
    
        for top_key, top_value in preset_answers.items():
            if isinstance(top_value, dict):
                if user_question in top_value:
                    sub_value = top_value[user_question]
                    if isinstance(sub_value, dict):
                        return QueryResponse(sub_questions=list(sub_value.keys()))
                    elif isinstance(sub_value, list):
                        if sub_value and isinstance(sub_value[0], dict):
                            formatted_entries = [format_center_info(entry) for entry in sub_value]
                            final_answer = "\n\n".join(formatted_entries)
                        else:
                            final_answer = "\n\n".join(sub_value)
                    else:
                        final_answer = str(sub_value)
                    return QueryResponse(answer=final_answer)
                for sub_key, sub_value in top_value.items():
                    if isinstance(sub_value, dict) and user_question in sub_value:
                        value = sub_value[user_question]
                        if isinstance(value, list):
                            final_answer = "\n\n".join(value)
                        else:
                            final_answer = str(value)
                        return QueryResponse(answer=final_answer)
        
        retrieved_data = retrieve_information(user_question, top_k=3)
        answer = generate_response(user_question, retrieved_data)
        return QueryResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
