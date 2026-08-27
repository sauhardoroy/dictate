"""Launch the Dictate ASR Model Benchmark & Playground Web Application."""
import sys
import os
import argparse
import webbrowser
import uvicorn

# Configure stdout/stderr for utf-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Dictate ASR Model Benchmark & Playground")
    parser.add_argument("--host", default="127.0.0.1", help="Host IP to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port to run on (default: 8765)")
    parser.add_argument("--open-browser", action="store_true", default=False, help="Open default browser automatically")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    print("\n" + "=" * 64)
    print("  DICTATE ASR BENCHMARK & MODEL PLAYGROUND")
    print("=" * 64)
    print(f"  URL: {url}")
    print("  Features:")
    print("    - Real-Time Microphone Streaming Playground (Universal for all models)")
    print("    - Side-by-Side Benchmark Matrix (Parakeet TDT, FastConformer, Whisper, Zipformer)")
    print("    - One-Click Model Catalog & Downloader")
    print("=" * 64 + "\n")

    if args.open_browser:
        def _open():
            import time
            time.sleep(1.2)
            webbrowser.open(url)
        import threading
        threading.Thread(target=_open, daemon=True).start()

    from benchmark_web.server import app
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
