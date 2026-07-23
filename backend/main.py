from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import ALLOWED_ORIGINS
from routes.items import router as items_router
from routes.save import router as save_router
from routes.search import router as search_router

app = FastAPI(title="Fetch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(save_router)
app.include_router(items_router)
app.include_router(search_router)


@app.get("/health")
def health():
    return {"status": "ok"}
