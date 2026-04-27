from fastapi import APIRouter

from app.api.routes import auth, channels, dashboard, messages, push, push_keys, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(channels.router)
api_router.include_router(push_keys.router)
api_router.include_router(messages.router)
api_router.include_router(dashboard.router)
api_router.include_router(push.router, prefix="")
