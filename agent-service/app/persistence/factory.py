from __future__ import annotations

from ..config import Settings
from .base import NullStateStore, StateStore


def build_state_store(settings: Settings) -> StateStore:
    backend = settings.persistence_backend.lower().strip()
    if backend in {"", "memory", "none"}:
        return NullStateStore()
    if backend == "firestore":
        from .firestore import FirestoreStateStore

        return FirestoreStateStore(
            project_id=settings.google_cloud_project,
            database=settings.firestore_database,
            organization_id=settings.organization_id,
        )
    raise ValueError(f"Unsupported persistence backend: {settings.persistence_backend}")
