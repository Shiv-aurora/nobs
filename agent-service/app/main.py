from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .auth import SignatureVerifier, SignedServiceMiddleware
from .service import Services


def create_app(services: Services | None = None) -> FastAPI:
    app = FastAPI(
        title="NoPing Agent Service",
        version="0.1.0",
        description="Permission-aware organizational routing, attention gating, decisions, and memory.",
    )
    service_bundle = services or Services()
    app.state.services = service_bundle
    app.add_middleware(
        SignedServiceMiddleware,
        verifier=SignatureVerifier(
            secret=service_bundle.settings.service_signing_secret,
            demo_mode=service_bundle.settings.demo_mode,
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8065", "http://localhost:4173", "http://localhost:8080"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-NoPing-Timestamp", "X-NoPing-Signature-Version", "X-NoPing-Signature"],
    )
    app.include_router(router)
    return app


app = create_app()
