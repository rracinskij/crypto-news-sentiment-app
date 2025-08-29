# Version: v0.1.0

"""
LLM-friendly description:
- Purpose: Fetches recent crypto news from a fixed set of RSS feeds.
- Strategy: For each feed, read the latest stored publish time. If none, use (now - 24h).
  Fetch only entries newer than the threshold and store them in the DB.
- Note: Adapted from a richer example (handles timeouts, bozo flag, content fields).
"""
import time, datetime, logging, concurrent.futures
import feedparser
from typing import List, Dict
from .storage import add_log, save_articles, get_latest_article_time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

FEEDS: List[str] = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss",
    "https://www.newsbtc.com/feed/",
    "https://99bitcoins.com/feed/",
    "https://bitcoinethereumnews.com/feed/",
    "https://bitcoinmagazine.com/feed",
    "https://news.bitcoin.com/feed/",
    "https://bitcoinik.com/feed/",
    "https://www.bitrates.com/feed/rss",
    "https://coin24h.com/feed/",
    "https://coincentral.com/news/feed/",
    "https://coincheckup.com/blog/feed/",
    "https://coindoo.com/feed/",
    "https://coinjournal.net/feed/",
    "https://www.cryptobreaking.com/feed/",
    "https://cryptobriefing.com/feed/",
    "https://crypto-economy.com/feed/",
    "https://www.crypto-news-flash.com/feed/",
    "https://www.cryptonewsz.com/feed/",
    "https://www.cryptoninjas.net/feed/",
    "https://cryptopotato.com/feed/",
    "https://cryptoticker.io/en/feed/",
    "https://currencycrypt.net/feed/",
    "https://www.financemagnates.com/cryptocurrency/feed/",
    "https://fullycrypto.com/feed",
    "https://thenewscrypto.com/feed/",
    "https://u.today/rss",
    "https://zycrypto.com/feed/"
]

def _parse_feed(url: str):
    def parse():
        return feedparser.parse(url, sanitize_html=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(parse)
        try:
            return fut.result(timeout=10)
        except concurrent.futures.TimeoutError:
            add_log("rss", f"timeout parsing {url}")
            return None

def collect() -> int:
    """Collect new articles across all FEEDS. Returns number of rows saved."""
    now = int(time.time())
    default_threshold = now - 24 * 3600
    total = 0

    for url in FEEDS:
        latest = get_latest_article_time(url)  # None if no data yet
        threshold = max(latest or 0, default_threshold)
        add_log("rss", f"using threshold for {url}: {datetime.datetime.utcfromtimestamp(threshold)}Z")

        feed = _parse_feed(url)
        if not feed:
            continue
        if getattr(feed, "bozo", False):
            add_log("rss", f"feed bozo error for {url}: {getattr(feed, 'bozo_exception', 'unknown')}")
            continue

        to_save: List[Dict] = []
        for entry in getattr(feed, "entries", []):
            if "published_parsed" not in entry:
                continue
            published_dt = datetime.datetime(*entry.published_parsed[:6])
            published_ts = int(published_dt.replace(tzinfo=datetime.timezone.utc).timestamp())
            if published_ts <= threshold:
                continue

            description = entry.get("description", "") or entry.get("summary", "") or ""
            content = ""
            if "content" in entry and entry.content:
                content = entry.content[0].value or ""
            content_encoded = entry.get("content:encoded", "") or ""

            to_save.append({
                "title": (entry.get("title") or "").encode("ascii","ignore").decode("ascii"),
                "link": entry.get("link",""),
                "source": url,
                "published_ts": published_ts,
                "published_str": published_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "description": description.encode("ascii","ignore").decode("ascii"),
                "content": content.encode("ascii","ignore").decode("ascii"),
                "content_encoded": content_encoded.encode("ascii","ignore").decode("ascii"),
            })

        if to_save:
            n = save_articles(to_save)
            add_log("rss", f"{url} -> saved {n} new articles")
            total += n
        else:
            add_log("rss", f"{url} -> no new articles")

    return total
