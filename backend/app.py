from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core.runtime import AGCNVoiceRuntime


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_FILE = PROJECT_ROOT / "test_web" / "index.html"

app = FastAPI(
    title="AGCN Live Voice",
    version="0.5.1-product-details",
)

runtime = AGCNVoiceRuntime()


class LiveStartRequest(BaseModel):
    username: str


class ProductRequest(BaseModel):
    name: str
    description: str = ""
    description_points: list[str] = Field(default_factory=list)
    regular_price: str | float | None = None
    current_price: str | float | None = None
    discount: str | float | None = None
    additional_info: str = ""
    category: str = ""
    image_url: str = ""


@app.get("/")
def root():
    return FileResponse(WEB_FILE)


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "AGCN Live Voice",
        "version": "0.5.1-product-details",
    }


@app.get("/api/status")
def status():
    return runtime.snapshot()


@app.post("/api/live/start")
def start_live(req: LiveStartRequest):
    try:
        result = runtime.start(req.username)
        if not result.get("ok"):
            raise HTTPException(
                status_code=400,
                detail=result.get("message"),
            )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/live/stop")
def stop_live():
    return runtime.stop()


@app.get("/api/products")
def products():
    return {
        "ok": True,
        "products": runtime.store.list(),
        "active_product": runtime.store.active(),
    }


@app.post("/api/products")
def add_product(req: ProductRequest):
    try:
        return runtime.add_product(req.model_dump())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/products/{product_id}")
def update_product(product_id: str, req: ProductRequest):
    try:
        return runtime.update_product(
            product_id,
            req.model_dump(),
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/products/{product_id}/activate")
def activate_product(product_id: str):
    try:
        return runtime.activate_product(product_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/api/products/{product_id}")
def delete_product(product_id: str):
    result = runtime.delete_product(product_id)
    if not result.get("ok"):
        raise HTTPException(
            status_code=404,
            detail=result.get("message"),
        )
    return result


@app.websocket("/ws")
async def websocket_status(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(runtime.snapshot())
            await asyncio.sleep(0.7)
    except WebSocketDisconnect:
        pass
