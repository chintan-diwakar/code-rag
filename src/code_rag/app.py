"""FastAPI app for the code-rag demo.

Routes:
- GET  /          : HTMX-driven search UI
- POST /search    : returns an HTML fragment of the top-k results
- GET  /healthz   : pipeline-warm check (used by deploy probes)

The pipeline is built once during the lifespan event. First boot pays the
chunk + embed cost (~50s); subsequent boots load the disk cache and are
near-instant.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from code_rag.pipeline import VALID_MODES, Pipeline, get_pipeline, set_pipeline

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    pipeline = Pipeline.build()
    set_pipeline(pipeline)
    app.state.pipeline = pipeline
    yield
    set_pipeline(None)


def create_app() -> FastAPI:
    app = FastAPI(title="code-rag", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        pipeline = _pipeline(request)
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "modes": VALID_MODES,
                "default_mode": "hybrid",
                "n_chunks": len(pipeline.chunks),
                "model": pipeline.embedder.model_name,
            },
        )

    @app.post("/search", response_class=HTMLResponse)
    async def search(
        request: Request,
        q: str = Form(...),
        mode: str = Form("hybrid"),
        k: int = Form(5),
    ) -> HTMLResponse:
        pipeline = _pipeline(request)
        # Clamp inputs.
        if mode not in VALID_MODES:
            mode = "hybrid"
        k = max(1, min(k, 20))
        response = pipeline.search(query=q, mode=mode, k=k)
        return templates.TemplateResponse(
            request,
            "_results.html",
            {"response": response},
        )

    @app.get("/healthz")
    async def healthz(request: Request) -> dict:
        pipeline = _pipeline(request)
        return {
            "status": "ok",
            "n_chunks": len(pipeline.chunks),
            "model": pipeline.embedder.model_name,
            "modes": list(VALID_MODES),
        }

    return app


def _pipeline(request: Request) -> Pipeline:
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        # Test path: lifespan didn't run; fall back to module-level singleton.
        pipeline = get_pipeline()
    return pipeline


app = create_app()
