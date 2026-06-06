import os
import sys

import pytest
from fastapi.testclient import TestClient

# Make src/ importable without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import app  # noqa: E402  (import after sys.path mutation)


@pytest.fixture
def client():
    """Return a FastAPI TestClient wrapping the app."""
    return TestClient(app)
