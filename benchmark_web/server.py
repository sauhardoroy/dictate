"""FastAPI Backend Server for the Model Benchmark & Playground Suite."""
import os
import io
import json
import time
import asyncio
from typing import List, Optional
import numpy as np
import soundfile as sf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from log import get_logger

from benchmark_web.models_registry import AVAILABLE_MODELS, get_all_models_status
from benchmark_web.engine_pool import global_engine_pool

log = get_logger(__name__)

app = FastAPI(title="Dictate ASR Benchmark & Playground")

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


@app.get("/api/models")
def get_models():
    """List all supported models with download status and specs."""
    return get_all_models_status()


@app.post("/api/models/download")
async def download_model(model_id: str = Form(...)):
    """Trigger download for a model."""
    if model_id not in AVAILABLE_MODELS:
        raise HTTPException(status_code=404, detail="Model not found")

    loop = asyncio.get_event_loop()
    try:
        success = await loop.run_in_executor(None, global_engine_pool.download_model, model_id)
        return {"status": "success" if success else "failed", "model_id": model_id}
    except Exception as e:
        log.exception("Model download failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/benchmark/file")
async def benchmark_audio_file(
    file: UploadFile = File(...),
    models: str = Form("parakeet-tdt-0.6b-v3,zipformer-70M,whisper-small.en")
):
    """Run benchmark for an uploaded audio file across multiple models."""
    model_ids = [m.strip() for m in models.split(",") if m.strip()]
    if not model_ids:
        raise HTTPException(status_code=400, detail="No models specified")

    contents = await file.read()
    try:
        audio_data, sample_rate = sf.read(io.BytesIO(contents))
    except Exception as e:
        log.warning("soundfile read failed, trying basic PCM decode: %s", e)
        raise HTTPException(status_code=400, detail=f"Invalid audio format: {e}")

    # Resample to 16kHz mono float32 if needed
    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1)
    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)

    if sample_rate != 16000:
        # Resample with scipy if available or linear interpolation
        try:
            import scipy.signal
            num_samples = int(len(audio_data) * 16000 / sample_rate)
            audio_data = scipy.signal.resample(audio_data, num_samples).astype(np.float32)
        except Exception:
            indices = np.linspace(0, len(audio_data) - 1, int(len(audio_data) * 16000 / sample_rate))
            audio_data = np.interp(indices, np.arange(len(audio_data)), audio_data).astype(np.float32)

    loop = asyncio.get_event_loop()
    results = []

    for m_id in model_ids:
        try:
            res = await loop.run_in_executor(None, global_engine_pool.benchmark_audio, m_id, audio_data, 16000)
            meta = AVAILABLE_MODELS.get(m_id, {})
            res["model_name"] = meta.get("name", m_id)
            res["parameters"] = meta.get("parameters", "N/A")
            res["type"] = meta.get("type", "ASR")
            results.append(res)
        except Exception as e:
            log.exception("Benchmark error for %s: %s", m_id, e)
            results.append({
                "model_id": m_id,
                "model_name": AVAILABLE_MODELS.get(m_id, {}).get("name", m_id),
                "error": str(e)
            })

    return {
        "filename": file.filename,
        "audio_duration_sec": round(len(audio_data) / 16000.0, 2),
        "results": results
    }


@app.websocket("/ws/stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    """Real-time streaming ASR endpoint over WebSocket."""
    await websocket.accept()
    session = None
    model_id = "zipformer-70M"

    try:
        # Initial handshake message specifies model_id
        init_data = await websocket.receive_text()
        init_msg = json.loads(init_data)
        if "model_id" in init_msg:
            model_id = init_msg["model_id"]

        meta = AVAILABLE_MODELS.get(model_id, {})
        session = global_engine_pool.create_streaming_session(model_id)
        await websocket.send_json({
            "type": "ready",
            "model_id": model_id,
            "model_name": meta.get("name", model_id)
        })

        while True:
            msg = await websocket.receive()
            if "bytes" in msg and msg["bytes"]:
                raw_bytes = msg["bytes"]
                # Decode 16kHz 16-bit PCM to float32
                pcm16 = np.frombuffer(raw_bytes, dtype=np.int16)
                pcm_float = pcm16.astype(np.float32) / 32768.0

                text, chunk_latency_ms = session.process_chunk(pcm_float)
                await websocket.send_json({
                    "type": "update",
                    "text": text,
                    "chunk_latency_ms": round(chunk_latency_ms, 2)
                })

            elif "text" in msg and msg["text"]:
                cmd = json.loads(msg["text"])
                if cmd.get("type") == "finish":
                    final_text = session.finish()
                    await websocket.send_json({
                        "type": "final",
                        "text": final_text
                    })
                    break

    except WebSocketDisconnect:
        log.debug("WebSocket client disconnected")
    except Exception as e:
        log.exception("WebSocket stream error: %s", e)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


# Mount static assets
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def get_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Benchmark UI loading...</h1>")
