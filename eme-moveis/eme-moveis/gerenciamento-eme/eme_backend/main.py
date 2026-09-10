from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from config import settings
from endpoints.rate_limiter import limiter
from repo.connection import get_pool, close_pool

from controller.auth_router import router as auth_router
from controller.client_router import router as client_router
from controller.project_router import router as project_router
from controller.financial_router import router as financial_router
from controller.stock_router import router as stock_router
from controller.report_router import router as report_router
from controller.calendar_router import router as calendar_router
from controller.recurring_router import router as recurring_router
from controller.funnel_router import router as funnel_router

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Inicializa o pool de conexões ao subir e fecha ao desligar."""
    await get_pool()
    yield
    await close_pool()


app = FastAPI(
    title="EME Backend",
    description="API do sistema de gestão EME Móveis",
    version="1.0.0",
    lifespan=lifespan,
)

# Registrar o limiter no app
app.state.limiter = limiter


# Handler customizado para rate limit excedido
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Muitas tentativas de login. Aguarde 1 minuto e tente novamente."},
    )


# CORS — Lê origens permitidas do .env (NUNCA deixar localhost fixo em produção!)
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar todos os roteadores
app.include_router(auth_router)
app.include_router(client_router)
app.include_router(project_router)
app.include_router(financial_router)
app.include_router(stock_router)
app.include_router(report_router)
app.include_router(calendar_router)
app.include_router(recurring_router)
app.include_router(funnel_router)


@app.get("/")
async def root() -> dict:
    return {"message": "EME Backend está rodando"}
