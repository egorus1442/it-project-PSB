import json
import uuid
from pydantic import BaseModel


class RagRequest(BaseModel):
    id: str
    thread_id: uuid.UUID
    question: str


class RagResponse(BaseModel):
    id: str
    answer: str


def stub_rag(request_data: RagRequest) -> RagResponse:
    """
    Функция-заглушка для RAG-системы.
    
    Принимает запрос в формате:
    {
        "id": "пример id",
        "question": "Любой вопрос",
        "thread_id": "пример thread_id"
    }
    
    Возвращает ответ в формате:
    {
        "id": "пример id",
        "answer": "Ответ"
    }
    """
    response = RagResponse(
        id = request_data.id,
        answer="Тестовый ответ."
    )
    return response