from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, translate, wordbook, tts, dictionary, lexical, settings, languages


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the singleton CacheService and inject it into the provider registry."""
    from app.database import AsyncSessionLocal
    from app.services.cache_postgres import PostgresCacheService
    from app.providers.registry import init_registry

    cache_service = PostgresCacheService(AsyncSessionLocal)
    init_registry(cache_service)
    yield


app = FastAPI(
    title="MyDic API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(translate.router)
app.include_router(wordbook.router)
app.include_router(tts.router)
app.include_router(dictionary.router)
app.include_router(lexical.router)
app.include_router(settings.router)
app.include_router(languages.router)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}
