"""
DocuMind AI — Application Entry Point
=======================================
WHY THIS FILE IS MINIMAL:
    main.py is the entry point — the file you point uvicorn at.
    It should contain as little logic as possible.

    The actual app setup lives in backend/app.py (the factory).
    This separation means:
    - Tests can import `create_app()` without starting the server
    - The entry point is trivially simple to read
    - You can swap the server (uvicorn → gunicorn) by changing just this file

RUNNING THE SERVER:
    Development (with hot-reload):
        python main.py
        -- or --
        uvicorn main:app --reload --host 0.0.0.0 --port 8000

    Production (with multiple workers):
        gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker

WHY NOT `uvicorn.run()` IN PRODUCTION?
    uvicorn.run() is single-process. Production needs multiple worker processes
    (one per CPU core) for parallelism. gunicorn manages worker processes;
    each worker runs uvicorn. This is the standard production deployment pattern.
"""

import uvicorn
from backend.app import application as app  # noqa: F401 — imported for uvicorn
from backend.config.settings import settings


if __name__ == "__main__":
    # This block only runs when you execute `python main.py` directly.
    # When uvicorn is invoked from CLI (`uvicorn main:app`), __name__ == "main"
    # and this block does NOT run — uvicorn manages the server itself.
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,     # Hot-reload only in development
        log_level="debug" if settings.debug else "info",
        # workers=1 in dev; use gunicorn for multi-worker production
    )
