
from fastapi import APIRouter

from neuralshelf.features.admin.router import router as admin_router
from neuralshelf.features.auth.router import router as auth_router
from neuralshelf.features.chat.router import router as chat_router
from neuralshelf.features.documents.router import router as documents_router
from neuralshelf.features.health.router import router as health_router
from neuralshelf.features.retrieval.router import router as retrieval_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(documents_router)
api_router.include_router(retrieval_router)
api_router.include_router(chat_router)
api_router.include_router(admin_router)
