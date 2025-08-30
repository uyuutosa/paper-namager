from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DATA_DIR = Path("data")
SETTINGS_PATH = DATA_DIR / "settings.json"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_settings(data: dict) -> None:
    ensure_data_dir()
    SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class ApiKeyPayload(BaseModel):
    provider: str = Field("openai", description="openai | azure")
    api_key: str
    model: Optional[str] = None
    endpoint: Optional[str] = None  # for azure


app = FastAPI(title="Paper Notes API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/settings")
def get_settings() -> dict:
    s = load_settings()
    # Never return secret
    return {
        "provider": s.get("provider") or "openai",
        "model": s.get("model") or "gpt-4o-mini",
        "endpoint": s.get("endpoint") or "",
        "has_key": bool(s.get("api_key")),
    }


@app.post("/api/settings/api-key")
def set_api_key(payload: ApiKeyPayload) -> dict:
    data = load_settings()
    data.update({
        "provider": payload.provider,
        "api_key": payload.api_key,
        "model": payload.model or data.get("model") or "gpt-4o-mini",
        "endpoint": payload.endpoint or data.get("endpoint") or "",
    })
    save_settings(data)
    return {"ok": True}


@app.get("/api/settings/test")
def test_api() -> dict:
    s = load_settings()
    provider = s.get("provider") or "openai"
    api_key = s.get("api_key")
    model = s.get("model") or "gpt-4o-mini"
    if not api_key:
        raise HTTPException(status_code=400, detail="API key not set")
    if provider != "openai":
        # For now, only OpenAI quick test supported
        return {"ok": True, "provider": provider, "note": "Non-OpenAI test not implemented yet"}
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI client unavailable: {e}")
    try:
        client = OpenAI(api_key=api_key)
        _ = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say OK."},
            ],
            max_tokens=3,
        )
        return {"ok": True, "provider": provider, "model": model}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"API call failed: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

