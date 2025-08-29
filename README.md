# Crypto News Sentiment App

A minimal FastAPI web app for collecting RSS crypto news, running sentiment predictions with LLMs, and viewing database contents.

## Features

- **RSS Collection**: Collect crypto news from RSS feeds
- **LLM Predictions**: Run sentiment analysis using various LLM models
- **Database Viewing**: View articles, predictions, and LLM queries
- **Responsive UI**: Modern web interface with loading states and scrollable content

## Quick Start

### Prerequisites
- Python 3.8+
- Required packages (see `requirements.txt`)

### Installation
```bash
pip install -r requirements.txt
```

### Running the App

**Option 1: Using the launcher script (recommended)**
```bash
python run.py
```

**Option 2: Direct from app directory**
```bash
cd app
python main.py
```

**Option 3: Using uvicorn**
```bash
uvicorn app.main:APP --host 0.0.0.0 --port 8000
```

The app will be available at: http://localhost:8000

## Usage

1. **Collect RSS**: Click "📡 Collect RSS" to gather latest crypto news
2. **Run Predictions**: Use the "🤖 Run with this prompt" button to analyze sentiment
3. **View Results**: Scroll through articles, predictions, and LLM queries in the scrollable sections

## UI Features

- **Loading States**: Buttons show "Running..." while scripts execute
- **Scrollable Content**: All data tables are contained in scrollable areas (max height: 400px)
- **Responsive Design**: Works on desktop and mobile devices

## Environment Variables

**Required:**
- `OPENROUTER_API_KEY`: Your OpenRouter API key for LLM calls (get one at [openrouter.ai](https://openrouter.ai) together with some credits)

**Optional:**
- `OPENROUTER_MODEL`: Override default model (defaults to `google/gemini-2.5-flash`)
- `APP_DB_PATH`: Custom database path (defaults to `data/app.db`)
- `OPENROUTER_REFERER`: Referer for OpenRouter API (defaults to `https://localhost`)
- `OPENROUTER_TITLE`: App title for OpenRouter API (defaults to `CryptoNewsSentimentApp`)

### Setup Environment Variables

Create a `.env` file in the project root:

```bash
# Required
OPENROUTER_API_KEY=sk-or-your-actual-key-here

# Optional overrides
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

## Database

The app uses SQLite for storage. Database files are automatically created in the `data/` directory.

## Project Structure

```
├── app/
│   ├── main.py          # FastAPI app and routes
│   ├── predictor.py     # LLM prediction logic
│   ├── rss_collector.py # RSS feed collection
│   ├── storage.py       # Database operations
│   └── templates/       # HTML templates
├── data/                # Database files (auto-created)
├── run.py               # Launcher script
└── requirements.txt     # Python dependencies
```
