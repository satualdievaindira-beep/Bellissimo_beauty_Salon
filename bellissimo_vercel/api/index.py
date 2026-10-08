"""Vercel entrypoint for Bellissimo Beauty Salon.
The Flask application remains in the project root so local and Vercel behavior match.
"""
from app import app

__all__ = ["app"]
