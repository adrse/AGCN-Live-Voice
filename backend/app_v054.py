from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core.product_research_v054 import ProductResearchEngineV054
from core.runtime import AGCNVoiceRuntime


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_FILE = PROJECT_ROOT / "test_web" / "index_v054.html"

app = FastAPI(
    title="AGCN Live Voice",
    version="0.5.6-reliable-identity",
)

runtime = AGCNVoiceRuntime()

# O site atual é apenas um protótipo temporário de validação. Ativamos o
# Lens também nele para conseguir testar a lógica antes do executável Windows.
os.environ["AGCN_LENS_ENABLED"] = "1"

research_engine = ProductResearchEngineV054()
research_engine.enrichment.lens.headless = True


class LiveStartRequest(BaseModel):
    username: str


class ProductRequest(BaseModel):
    product_url: str = ""
    name: str
    brand: str = ""
    model: str = ""
    category: str = ""
    description: str = ""
    key_benefits: str = ""
    problems_solved: str = ""
    differentials: str = ""
    included_items: str = ""
    compatibility: str = ""
    size_info: str = ""
    battery_info: str = ""
    usage_info: str = ""
    warranty: str = ""
    limitations: str = ""
    additional_info: str = ""
    image_url: str = ""

    regular_price: str | float | None = None
    current_price: str | float | None = None
    discount: str | float | None = None
    stock: str | float | None = None
    shipping_info: str = ""
    coupon: str = ""
    live_offer: bool = False
    live_offer_text: str = ""
    promotion_note: str = ""

    manual_fields: list[str] = Field(default_factory=list)
    research_meta: dict[str, dict[str, Any]] = Field(default_factory=dict)
    research_summary: dict[str, Any] = Field(default_factory=dict)


class UnlockFieldRequest(BaseModel):
    field: str


class ProductResearchRequest(BaseModel):
    url: str
    hint: str = ""


@app.get("/")
def root():
    return FileResponse(WEB_FILE)


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "AGCN Live Voice",
        "version": "0.5.6-reliable-identity",
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


@app.post("/api/product-research/analyze")
def analyze_product(req: ProductResearchRequest):
    try:
        return research_engine.analyze(
            req.url,
            hint=req.hint,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "A pesquisa não conseguiu concluir esta tentativa: "
                + str(exc)[:180]
            ),
        ) from exc


@app.get("/api/products")
def products():
    return {
        "ok": True,
        "products": runtime.store.list(),
        "active_product": runtime.store.active(),
    }


@app.get("/api/products/{product_id}")
def product(product_id: str):
    item = runtime.store.get(product_id)
    if not item:
        raise HTTPException(
            status_code=404,
            detail="Produto não encontrado.",
        )
    return {"ok": True, "product": item}


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


@app.post("/api/products/{product_id}/unlock-field")
def unlock_product_field(
    product_id: str,
    req: UnlockFieldRequest,
):
    try:
        item = runtime.store.unlock_field(
            product_id,
            req.field,
        )
        return {
            "ok": True,
            "message": "Campo liberado para pesquisa futura.",
            "product": item,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
