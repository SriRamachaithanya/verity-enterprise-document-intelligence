import httpx
import ollama
import pytest


def _is_ollama_running() -> bool:
    try:
        res = httpx.get("http://127.0.0.1:11434/api/tags", timeout=1.0)
        return res.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException, OSError):
        return False


@pytest.mark.skipif(not _is_ollama_running(), reason="Ollama daemon is offline")
def test_ollama_local_api_responsive():
    res = httpx.get("http://127.0.0.1:11434/api/tags", timeout=5.0)
    assert res.status_code == 200
    data = res.json()
    model_names = [m["name"] for m in data.get("models", [])]
    assert any("qwen2.5:1.5b" in name for name in model_names)


@pytest.mark.skipif(not _is_ollama_running(), reason="Ollama daemon is offline")
@pytest.mark.asyncio
async def test_ollama_generate():
    client = ollama.AsyncClient(host="http://127.0.0.1:11434")
    response = await client.generate(
        model="qwen2.5:1.5b",
        prompt="Reply with the exact word 'READY' and nothing else.",
        options={"temperature": 0.0},
    )
    assert "READY" in response["response"].strip()

