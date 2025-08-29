# Version: v0.1.0

"""
LLM-friendly description:
- Purpose: Read last 24h of articles and ask an LLM (via OpenRouter) for 24h coin sentiment.
- Output: Saves the raw JSON + extracted per-asset items into prediction tables.
- Env:
  - OPENROUTER_API_KEY (required to actually call the API)
  - OPENROUTER_MODEL (optional; default: google/gemini-2.5-flash)
- Security: No keys are stored in DB; only prompts/responses and token counts (if provided) are kept.
"""
import os, json, time, requests
from typing import Dict, Any, List, Tuple
from .storage import add_log, add_prediction, add_prediction_item, add_llm_query, list_recent_articles

HORIZON_MINUTES = 24 * 60

DEFAULT_SYSTEM = """You analyze recent market text and produce structured JSON.
Rules:
- Return strictly valid JSON matching the provided schema.
- horizon_minutes MUST be 1440 (24 hours).
- overall_sentiment MUST be one of: bullish, bearish, neutral, mixed.
- Only include assets in bullish/bearish if confidence is strong.
- If only one side is supported, leave the other empty.
- Focus on widely discussed topics and clearest trends.
- Prioritize assets that recur across multiple articles.
- Keep assets short (e.g., BTC, ETH, SOL) and predictions one sentence.
- No extra commentary, no markdown.
"""

SCHEMA = {
    "name": "asset_prediction_result",
    "schema": {
        "type": "object",
        "properties": {
            "horizon_minutes": {"type":"integer"},
            "overall_sentiment": {"type":"string", "enum": ["bullish", "bearish", "neutral", "mixed"]},
            "bullish": {"type":"array", "items": {"type":"object", "properties": {
                "asset": {"type":"string"},
                "prediction": {"type":"string"}
            }, "required":["asset","prediction"]}},
            "bearish": {"type":"array", "items": {"type":"object", "properties": {
                "asset": {"type":"string"},
                "prediction": {"type":"string"}
            }, "required":["asset","prediction"]}}
        },
        "required": ["horizon_minutes", "overall_sentiment"],
        "additionalProperties": False
    },
    "strict": True
}

def build_prompt(articles: List[Tuple]) -> str:
    lines = []
    for title, link, source, published_str, snippet in articles:
        # keep prompt compact
        lines.append(f"{published_str} {title} | {snippet} [{link}]")
    context = "\n- ".join(lines)
    prompt = (
        f"HORIZON_MINUTES={HORIZON_MINUTES}\n\n"
        f"DATA_TIMESPAN: News articles from the past 24 hours.\n\n"
        f"PREDICTION_HORIZON: Predict market movements for the next 24 hours (1440 minutes).\n\n"
        f"Recent market context (most recent first):\n- {context}"
        if lines else
        "No recent articles found; respond with neutral sentiment and empty lists."
    )
    return prompt

def run(model: str, system_prompt: str = None) -> int:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    model = os.getenv("OPENROUTER_MODEL", model or "google/gemini-2.5-flash")
    if not api_key:
        add_log("predictor", "OPENROUTER_API_KEY missing; cannot call LLM.")
        return 0

    # Fetch last 24h of news
    articles = list_recent_articles(hours=24, limit=300)
    if not articles:
        add_log("predictor", "No articles in last 24h; collect RSS first.")
        return 0

    prompt = build_prompt(articles)
    system = system_prompt or DEFAULT_SYSTEM

    add_log("predictor", f"Calling LLM model={model} with {len(articles)} articles (24h horizon)")

    start = time.time()
    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "https://localhost"),
                "X-Title": os.getenv("OPENROUTER_TITLE", "CryptoNewsSentimentApp"),
            },
            json={
                "model": model,
                "messages": [
                    {"role":"system","content": system},
                    {"role":"user","content": prompt}
                ],
                "response_format": {
                    "type":"json_schema",
                    "json_schema": {
                        "name": SCHEMA["name"],
                        "strict": True,
                        "schema": SCHEMA["schema"]
                    }
                },
                "max_tokens": 2000
            },
            timeout=120
        )
        res.raise_for_status()
        elapsed_ms = int((time.time() - start) * 1000)
        body = res.json()
        content = body["choices"][0]["message"]["content"]
        tokens_used = body.get("usage", {}).get("total_tokens")

        add_llm_query(model=model, prompt=prompt, response=content, tokens_used=tokens_used, duration_ms=elapsed_ms)

        try:
            data = json.loads(content)
        except Exception as e:
            add_prediction(HORIZON_MINUTES, model, json.dumps(body), content or "")
            add_log("predictor", f"Model did not return valid JSON: {e}")
            return 0

        overall = str(data.get("overall_sentiment", "unknown"))
        add_prediction(HORIZON_MINUTES, model, json.dumps(data), f"Overall sentiment: {overall}")

        saved = 0
        for stance_key in ("bullish", "bearish"):
            for item in (data.get(stance_key) or []):
                asset = str(item.get("asset","?")).strip()[:64]
                text  = str(item.get("prediction","?")).strip()
                add_prediction_item(HORIZON_MINUTES, model, asset, stance_key, text)
                saved += 1

        add_log("predictor", f"Saved {saved} prediction items in {elapsed_ms}ms")
        return saved

    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        add_log("predictor", f"LLM API call failed: {e}")
        add_llm_query(model=model, prompt=prompt, response=f"ERROR: {e}", duration_ms=elapsed_ms)
        return 0
