"""
Vercel serverless entrypoint — exports FastAPI ASGI app.
"""

from app.main import app

__all__ = ["app"]
