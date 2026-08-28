# NVIDIA GPU / CUDA Validation Guide for Dictate

This guide provides step-by-step instructions, automated verification commands, and interactive test prompts to validate GPU/CUDA hardware acceleration in Dictate when deployed on a laptop or workstation with an NVIDIA discrete GPU.

---

## 1. Prerequisites on the NVIDIA GPU System

### Drivers & Hardware
- **NVIDIA GPU**: RTX 20/30/40/50 series or GTX 16-series (Compute Capability $\ge 7.0$).
- **NVIDIA Display Driver**: Version 525+ (Windows/Linux).
- **CUDA Toolkit / Runtime**: CUDA 11.8 or CUDA 12.x installed.
- **cuDNN**: cuDNN v8.9.x or v9.x DLLs/so files on system PATH (or bundled with ONNX Runtime GPU).

### Python Dependencies
Ensure `sherpa-onnx` and `onnxruntime-gpu` are installed in the virtual environment:
```powershell
# In Dictate venv:
pip install onnxruntime-gpu
```

---

## 2. Configuration for CUDA Execution

In `settings.json` (or via Dictate Settings UI -> Advanced Tab -> Hardware Acceleration):
```json
{
  "engine": "parakeet",
  "model": "parakeet-tdt-0.6b-v3",
  "device": "cuda"
}
```

---

## 3. Automated Verification Script

Run the following test script on your NVIDIA machine to verify GPU execution:

```powershell
& ".\.venv\Scripts\python.exe" -c "
import time, soundfile as sf, numpy as np
from asr.parakeet_engine import ParakeetTDTEngine

print('=== 1. Initializing Parakeet TDT on CUDA ===')
engine = ParakeetTDTEngine(device='cuda')
t0 = time.perf_counter()
engine.load()
t_load = time.perf_counter() - t0

print(f'Model loaded in {t_load:.2f}s')
print(f'Active Provider: {engine.active_provider}')
assert engine.active_provider == 'cuda', f'Expected cuda provider, got {engine.active_provider}'

print('\n=== 2. Running Inference Benchmark ===')
audio, sr = sf.read('models/sherpa-onnx-streaming-zipformer-en-2023-06-26/test_wavs/0.wav')
audio = audio.astype(np.float32)

# Warmup run
engine.transcribe(audio)

# Timed runs
latencies = []
for _ in range(5):
    t_start = time.perf_counter()
    res = engine.transcribe(audio)
    latencies.append((time.perf_counter() - t_start) * 1000)

avg_lat = np.mean(latencies)
print(f'Transcribed: {res[\"text\"]}')
print(f'Average GPU Latency (6.6s audio): {avg_lat:.1f}ms (RTF: {avg_lat / 6600:.4f})')
print('=== CUDA VALIDATION PASSED ===')
"
```

---

## 4. Validating VRAM & GPU Utilization (nvidia-smi)

In a separate terminal, monitor GPU utilization and memory allocation while dictating:
```powershell
nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total --format=csv -l 1
```

**Expected Metrics on CUDA:**
- **VRAM Allocation**: ~450 MB – 800 MB (Parakeet TDT INT8 model).
- **Inference Latency**: 40 ms – 90 ms for 5s of speech (vs 300–600ms on CPU).
- **Log Verification in `dictate.log`**:
  ```text
  [INFO] Initialized Parakeet TDT recognizer with provider=cuda
  [INFO] Parakeet TDT engine ready (provider=cuda, hotwords=True)
  ```

---

## 5. Verification Checklist

| Test Item | Expected Result | Pass/Fail |
|---|---|---|
| `device: "cuda"` startup | Log confirms `provider=cuda` | [ ] |
| Missing CUDA DLLs fallback | Falls back cleanly to `provider=cpu` with clear warning | [ ] |
| `device: "auto"` | Defaults to `cpu` | [ ] |
| Real-time dictation latency | Transcription completes within $<100$ms of speech finish | [ ] |
| High-load 30s recording | VRAM stays $<1.2$GB; acoustic stitching executes smoothly | [ ] |
