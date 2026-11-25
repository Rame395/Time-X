import os
import sys
import uvicorn

if __name__ == "__main__":
    # Ensure current directory is on sys.path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "8035")),
        workers=int(os.environ.get("UVICORN_WORKERS", "1")),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
