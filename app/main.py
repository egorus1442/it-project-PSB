from fastapi import FastAPI
from app.api.endpoints import router as endpoints_router


app = FastAPI(title="RAG API", version="0.0.1")

app.include_router(endpoints_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
