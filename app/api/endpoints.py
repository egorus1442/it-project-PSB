import uuid
from fastapi import APIRouter, Cookie, HTTPException, Query, Response, status, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
import jwt

from sqlalchemy.orm import sessionmaker, Session

from passlib.context import CryptContext

from app.services.db import SessionLocal, User
from app.services.logging_rag_service import rag_send_message
from app.services.auth import create_access_token
from app.core.config import settings
from app.services.rag_service import RagRequest

router = APIRouter()

# Зависимость для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

#регистрация
class UserRegister(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully."}


# Аутентификация и получение токена
class TokenLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"

@router.post("/token", response_model=TokenResponse)
def get_token(login_data: TokenLoginRequest, db: Session = Depends(get_db)):
    
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    token = create_access_token(user_identifier=login_data.email)
    return {"access_token": token, "token_type": "Bearer"}

#для Rag
class ChatRequest(BaseModel):
    id: str
    question: str
    thread_id: uuid.UUID

class ChatResponse(BaseModel):
    id: str
    answer: str

oauth2_scheme = HTTPBearer()

def verify_token(authorization: dict = Depends(oauth2_scheme)):
    """
    Функция для проверки валидности JWT.
    
    Извлекает payload из токена или выбрасывает исключение, если токен недействительный.
    """
    token: str = authorization.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return payload


@router.post("/public/chat", response_model=ChatResponse)
def public_send_message(
    request: ChatRequest,
    token_payload: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user_email = token_payload.get("user_identifier")
    if not user_email:
        raise HTTPException(status_code=400, detail="Invalid token payload")
    
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    rag_request = RagRequest(
        id = request.id,
        thread_id = request.thread_id,
        question=request.question
    )
    rag_response = rag_send_message(rag_request, db, user_id=user.id)
    
    return ChatResponse(
        id=rag_response.id,
        answer=rag_response.answer
    )


@router.post("/web/session")
def web_post_session(response: Response, phone_number: str = Query()):
    # TODO: Generate session
    response.set_cookie('session_id', str(uuid.uuid4()))


@router.delete("/web/session")
def web_delete_session(response: Response):
    response.delete_cookie("session_id")


@router.post("/web/chat", response_model=ChatResponse)
def web_send_message(
    request: ChatRequest,
    session_id: str = Cookie(),
    db: Session = Depends(get_db)
):
    rag_request = RagRequest(
        id = request.id,
        thread_id = request.thread_id,
        question=request.question
    )
    rag_response = rag_send_message(rag_request, db, session_id=session_id)
    
    return ChatResponse(
        id=rag_response.id,
        answer=rag_response.answer
    )


@router.post("/bot/chat", response_model=ChatResponse)
def bot_send_message(
    request: ChatRequest,
    chat_id: str = Query(),
    db: Session = Depends(get_db)
):
    rag_request = RagRequest(
        id = request.id,
        thread_id = request.thread_id,
        question=request.question
    )
    rag_response = rag_send_message(rag_request, db, chat_id=chat_id)
    
    return ChatResponse(
        id=rag_response.id,
        answer=rag_response.answer
    )