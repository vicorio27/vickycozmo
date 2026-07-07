"""
Robot backend abstraction layer.

Allows using either the official Anki Cozmo SDK or pycozmo (direct WiFi)
through the same interface.
"""
import os

def create_backend(backend_type="anki", **kwargs):
    """Factory function to create a robot backend.
    
    Args:
        backend_type: "anki" for official SDK, "pycozmo" for direct WiFi.
        **kwargs: passed to the backend constructor.
    
    Returns:
        A RobotBackend instance.
    """
    if backend_type == "pycozmo":
        from .pycozmo_backend import PyCozmoBackend
        return PyCozmoBackend(**kwargs)
    else:
        from .anki_backend import AnkiBackend
        return AnkiBackend(**kwargs)
