# Version: v0.1.0

"""
LLM-friendly description:
- Purpose: Minimal FastAPI web app for: (1) collecting RSS crypto news, (2) running a 24h sentiment predictor,
  and (3) viewing DB contents (articles, predictions, LLM queries).
- Pages:
  - GET /             : Home with buttons + forms
  - POST /collect     : Trigger RSS collection
  - POST /predict     : Run LLM predictor on last 24h
  - GET /articles     : Partial view of recent articles
  - GET /predictions  : Partial view of latest prediction items
  - GET /llm          : Partial view of latest LLM prompts/responses
- Security: No auth for localhost demo. Add HTTP Basic if you deploy.
"""
import os
import pathlib
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.storage import ensure_tables, add_log, list_recent_articles, list_prediction_items, list_llm_queries
from app.rss_collector import collect as collect_rss
from app.predictor import run as run_predictor

APP = FastAPI(title="Crypto News Sentiment (demo)")
templates = Jinja2Templates(directory=str(pathlib.Path(__file__).parent / "templates"))

# serve /static only if the directory exists
static_dir = pathlib.Path(__file__).parent / "static"
if static_dir.exists():
    APP.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

ensure_tables()

@APP.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@APP.post("/collect")
def collect_handler():
    add_log("web", "Starting RSS collection")
    n = collect_rss()
    add_log("web", f"RSS collection finished: {n} new rows")
    return RedirectResponse("/", status_code=303)

@APP.post("/predict")
def predict_handler(system_prompt: str = Form(None), model: str = Form("google/gemini-2.5-flash")):
    add_log("web", f"Starting predictor (model={model}, prompt_length={len(system_prompt) if system_prompt else 0})")
    
    # Check if API key is available
    if not os.getenv("OPENROUTER_API_KEY"):
        add_log("web", "ERROR: OPENROUTER_API_KEY not set")
        return RedirectResponse("/?error=no_api_key", status_code=303)
    
    try:
        n = run_predictor(model=model, system_prompt=system_prompt)
        add_log("web", f"Predictor finished: saved {n} items")
        return RedirectResponse("/", status_code=303)
    except Exception as e:
        add_log("web", f"Predictor failed: {str(e)}")
        return RedirectResponse("/?error=predictor_failed", status_code=303)

@APP.get("/articles", response_class=HTMLResponse)
def articles_partial(request: Request, hours: int = 24):
    rows = list_recent_articles(hours=hours, limit=200)
    return templates.TemplateResponse("_articles.html", {"request": request, "rows": rows, "hours": hours})

@APP.get("/predictions", response_class=HTMLResponse)
def predictions_partial(request: Request, limit: int = 200):
    rows = list_prediction_items(limit=limit)
    return templates.TemplateResponse("_predictions.html", {"request": request, "rows": rows})

@APP.get("/llm", response_class=HTMLResponse)
def llm_partial(request: Request, limit: int = 50):
    rows = list_llm_queries(limit=limit)
    return templates.TemplateResponse("_llm.html", {"request": request, "rows": rows})

if __name__ == "__main__":
    import uvicorn
    print("Starting Crypto News Sentiment App...")
    print("Access the app at: http://localhost:8000")
    print("Press Ctrl+C to stop the server")
    uvicorn.run(APP, host="0.0.0.0", port=8000)
