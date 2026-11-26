"""Shared Ollama client used by ObsAgent's multi-agent workflow."""

from .ollama import chat, normalizar_argumentos

__all__ = ["chat", "normalizar_argumentos"]
