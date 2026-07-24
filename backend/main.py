import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import ALLOWED_ORIGINS
from routes.items import router as items_router
from routes.save import router as save_router
from routes.search import router as search_router
from services import reprocess

app = FastAPI(title="Fetch API")


@app.on_event("startup")
def drain_reprocess_queue_on_boot() -> None:
    """Give the queue a nudge whenever the service boots.

    Railway restarts the container on every deploy and after idling, so boot is
    a reliable-enough recurring moment to attempt a sweep. On a separate thread
    because startup must not block: the container has to accept traffic
    immediately, and the sweep can take tens of seconds.
    """
    threading.Thread(target=reprocess.sweep, daemon=True).start()

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
