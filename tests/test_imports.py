def test_backend_dependencies_importable():
    import coverage
    import docx
    import dotenv
    import faiss
    import fastapi
    import fastmcp
    import httpx
    import mcp
    import numpy
    import ollama
    import pydantic
    import pymupdf
    import pytest
    import ruff
    import sentence_transformers
    import uvicorn

    assert fastapi.__version__ is not None
    assert uvicorn.__version__ is not None
    assert pydantic.__version__ is not None
    assert dotenv.__file__ is not None
    assert mcp.__file__ is not None
    assert fastmcp.__file__ is not None
    assert pymupdf.__version__ is not None
    assert docx.__version__ is not None
    assert sentence_transformers.__version__ is not None
    assert hasattr(faiss, "IndexFlatL2")
    assert numpy.__version__ is not None
    assert ollama.__name__ == "ollama"
    assert httpx.__version__ is not None
    assert pytest.__version__ is not None
    assert ruff.__file__ is not None
    assert coverage.__version__ is not None
