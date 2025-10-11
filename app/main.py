from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.ws import router as ws_router

app = FastAPI(title="Whisper Realtime WS API", version="0.1.0")

# CORS: adjust allowed origins for RN + web as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten on prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


# WebSocket router
app.include_router(ws_router)
