from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
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
        "title": data["title"],
        "description": data["content"]
    }
    documents.append(document)

document_texts = [doc["description"] for doc in documents]

model = SentenceTransformer('all-MiniLM-L6-v2')
document_embeddings = model.encode(document_texts)

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


preset_answers = {
    "비자 발급 절차를 알려줘": "비자 발급 절차는 먼저 신청서를 작성하고, 필요한 서류를 제출한 후, 심사를 거쳐 발급됩니다.",
    "비자 신청서 작성 방법은?": "비자 신청서는 해당 국가의 대사관 또는 영사관 홈페이지에서 양식을 다운로드하여 작성할 수 있습니다.",
    "비자 심사 기준은 무엇인가요?": "비자 심사 기준은 신청자의 자격, 제출 서류의 완전성, 체류 목적 등에 따라 달라집니다."
}


app = FastAPI()

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str

@app.post("/chatbot", response_model=QueryResponse)
async def chat_endpoint(query_request: QueryRequest):
    user_question = query_request.question
    try:
        if user_question in preset_answers:
            answer = preset_answers[user_question]
        else:
            retrieved_data = retrieve_information(user_question, top_k=3)
            answer = generate_response(user_question, retrieved_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return QueryResponse(answer=answer)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
