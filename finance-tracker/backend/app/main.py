"""Точка сборки приложения.

create_app принимает репозиторий: в продакшене — SqlRepository,
в интеграционных тестах — InMemoryRepository.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import accounts, operations, reports
from app.api.errors import register_error_handlers
from app.config import Settings
from app.db.session import create_engine_for, create_session_factory, init_schema
from app.repositories.base import Repository
from app.repositories.sql import SqlRepository


def create_app(repository: Repository | None = None) -> FastAPI:
    app = FastAPI(
        title="Finance Tracker API",
        version="1.0.0",
        description="Учёт личных финансов: счета, операции, месячные отчёты.",
    )

    if repository is None:
        settings = Settings.from_env()
        engine = create_engine_for(settings.database_url)
        init_schema(engine)
        repository = SqlRepository(create_session_factory(engine))

    app.state.repository = repository

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    app.include_router(accounts.router)
    app.include_router(operations.router)
    app.include_router(reports.router)

    @app.get("/health", tags=["service"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
