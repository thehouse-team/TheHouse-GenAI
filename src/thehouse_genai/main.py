"""Uvicorn entrypoint."""

from thehouse_genai.api.app import create_app

app = create_app()
