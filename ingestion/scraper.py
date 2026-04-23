# ============================================================
# ingestion/scraper.py – Multi-Source News Ingestion Engine
# Sources: RSS, NewsAPI, BSE/NSE filings, web scraping
# ============================================================

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

import aiohttp
import feedparser
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

# ── Data Structures ─────────────────────────────────────────────────────────────

@dataclass
class RawArticle:
    title: str
    content: str
    url: str
    source: str
    published_at: Optional[datetime] = None
    author: Optional[str] = None
    external_id: str = ""
    raw_metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.external_id:
            self.external_id = hashlib.sha256(self.url.encode()).hexdigest()[:32]

    def word_count(self) -> int:
        return len(self.content.split()) if self.content else 0


# ── RSS Scraper ─────────────────────────────────────────────────────────────────

class RSSIngester:
    """
    Ingests articles from RSS feeds concurrently.
    Handles: ET, Moneycontrol, Business Standard, LiveMint, Reuters India, NDTV Profit
    """

    def __init__(self):
        self.feeds = settings.RSS_FEEDS
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=30, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; NewsAlphaBot/1.0)",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            }
        )
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_feed(self, feed_url: str) -> list[RawArticle]:
        articles = []
        try:
            async with self.session.get(feed_url) as resp:
                if resp.status != 200:
                    logger.warning(f"Feed {feed_url} returned {resp.status}")
                    return []
                content = await resp.text()

            parsed = feedparser.parse(content)
            source = self._infer_source(feed_url)

            for entry in parsed.entries:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                # Strip HTML tags
                summary = re.sub(r"<[^>]+>", " ", summary).strip()
                link = entry.get("link", "")

                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    import calendar
                    pub_date = datetime.fromtimestamp(
                        calendar.timegm(entry.published_parsed), tz=timezone.utc
                    )

                if not title or not link:
                    continue

                article = RawArticle(
                    title=title,
                    content=summary,
                    url=link,
                    source=source,
                    published_at=pub_date,
                    author=entry.get("author", ""),
                    raw_metadata={"feed_url": feed_url, "entry_id": entry.get("id", "")}
                )
                articles.append(article)

            logger.info(f"✓ {source}: {len(articles)} articles from {feed_url}")

        except Exception as e:
            logger.error(f"Feed error {feed_url}: {e}")

        return articles

    async def fetch_full_article(self, url: str) -> str:
        """Fetch full article body using trafilatura-like extraction."""
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return ""
                html = await resp.text()
            # Use regex-based extraction for speed (trafilatura in real use)
            # Remove script/style tags
            html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
            html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
            # Extract paragraph text
            paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.DOTALL)
            text = " ".join(re.sub(r"<[^>]+>", "", p).strip() for p in paragraphs)
            return text[:5000]  # limit to 5000 chars
        except Exception:
            return ""

    async def ingest_all(self, fetch_full_text: bool = False) -> list[RawArticle]:
        """Fetch all RSS feeds concurrently."""
        tasks = [self.fetch_feed(url) for url in self.feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles: list[RawArticle] = []
        for r in results:
            if isinstance(r, list):
                all_articles.extend(r)

        # Optional: enrich with full article text
        if fetch_full_text:
            enrich_tasks = []
            for art in all_articles:
                if len(art.content) < 300:  # short summary, fetch full
                    enrich_tasks.append(self._enrich(art))
            if enrich_tasks:
                await asyncio.gather(*enrich_tasks, return_exceptions=True)

        # Deduplicate by external_id
        seen = set()
        unique = []
        for art in all_articles:
            if art.external_id not in seen:
                seen.add(art.external_id)
                unique.append(art)

        logger.info(f"📰 Total unique articles fetched: {len(unique)}")
        return unique

    async def _enrich(self, article: RawArticle):
        full = await self.fetch_full_article(article.url)
        if full and len(full) > len(article.content):
            article.content = full

    @staticmethod
    def _infer_source(feed_url: str) -> str:
        domain_map = {
            "reuters.com": "Reuters",
            "economictimes": "Economic Times",
            "moneycontrol": "Moneycontrol",
            "livemint": "LiveMint",
            "business-standard": "Business Standard",
            "ndtv": "NDTV Profit",
            "financialexpress": "Financial Express",
            "hindustantimes": "Hindustan Times",
            "thehindu": "The Hindu Business",
        }
        for key, name in domain_map.items():
            if key in feed_url:
                return name
        return urlparse(feed_url).netloc.replace("www.", "")


# ── BSE/NSE Filing Scraper ───────────────────────────────────────────────────────

class BSEFilingIngester:
    """
    Scrapes BSE corporate announcements API.
    Covers: Results, Dividends, Bonus, Splits, Board Meetings, Insider Trading.
    """
    BSE_ANNOUNCEMENTS_URL = (
        "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
        "?pageno=1&strCat=-1&strPrevDate={prev}&strScrip=&strSearch=P"
        "&strToDate={today}&strType=C&subcategory=-1"
    )

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bseindia.com/",
                "Accept": "application/json",
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def fetch_announcements(self, days_back: int = 1) -> list[RawArticle]:
        today = datetime.now().strftime("%Y%m%d")
        prev = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
        url = self.BSE_ANNOUNCEMENTS_URL.format(today=today, prev=prev)

        articles = []
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    logger.warning(f"BSE API returned {resp.status}")
                    return []
                data = await resp.json(content_type=None)

            announcements = data.get("Table", [])
            logger.info(f"BSE: {len(announcements)} announcements")

            for ann in announcements:
                title = ann.get("HEADLINE", "")
                body = ann.get("CATEGORYNAME", "") + ". " + ann.get("SUBCATNAME", "")
                ticker = ann.get("SCRIP_CD", "")
                company_name = ann.get("LONG_NAME", "")
                date_str = ann.get("NEWS_DT", "")

                if not title:
                    continue

                pub_date = None
                if date_str:
                    try:
                        pub_date = datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    except Exception:
                        pass

                article = RawArticle(
                    title=f"[BSE Filing] {company_name}: {title}",
                    content=body + f" Company: {company_name} ({ticker})",
                    url=f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{ann.get('ATTACHMENTNAME', '')}",
                    source="BSE Filing",
                    published_at=pub_date,
                    raw_metadata={
                        "bse_code": ticker,
                        "company": company_name,
                        "category": ann.get("CATEGORYNAME", ""),
                        "subcategory": ann.get("SUBCATNAME", ""),
                    }
                )
                articles.append(article)

        except Exception as e:
            logger.error(f"BSE scraper error: {e}")

        return articles


# ── NewsAPI Ingester ─────────────────────────────────────────────────────────────

class NewsAPIIngester:
    """
    Pulls articles from NewsAPI.org for Indian business news.
    """
    BASE_URL = "https://newsapi.org/v2/everything"

    QUERIES = [
        "India stock market NSE BSE Nifty",
        "Sensex Indian shares earnings",
        "RBI monetary policy India economy",
        "India infrastructure government spending",
        "India pharma IT TCS Infosys earnings",
    ]

    def __init__(self):
        self.api_key = settings.NEWSAPI_KEY

    async def fetch(self) -> list[RawArticle]:
        if not self.api_key:
            logger.warning("NEWSAPI_KEY not set – skipping NewsAPI")
            return []

        articles = []
        async with aiohttp.ClientSession() as session:
            for query in self.QUERIES:
                params = {
                    "q": query,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 100,
                    "from": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                    "apiKey": self.api_key,
                }
                try:
                    async with session.get(self.BASE_URL, params=params) as resp:
                        data = await resp.json()
                    for item in data.get("articles", []):
                        pub = None
                        if item.get("publishedAt"):
                            try:
                                pub = datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00"))
                            except Exception:
                                pass
                        art = RawArticle(
                            title=item.get("title", ""),
                            content=(item.get("description") or "") + " " + (item.get("content") or ""),
                            url=item.get("url", ""),
                            source=item.get("source", {}).get("name", "NewsAPI"),
                            published_at=pub,
                            author=item.get("author", ""),
                        )
                        if art.title:
                            articles.append(art)
                except Exception as e:
                    logger.error(f"NewsAPI error for query '{query}': {e}")

        logger.info(f"NewsAPI: {len(articles)} articles")
        return articles


# ── Master Ingestion Runner ──────────────────────────────────────────────────────

class IngestionEngine:
    """
    Orchestrates all scrapers and persists to DB.
    Target: 800+ articles in < 5 minutes.
    """

    def __init__(self):
        self.rss = RSSIngester()
        self.bse = BSEFilingIngester()
        self.newsapi = NewsAPIIngester()

    async def run(self, save_to_db: bool = True) -> list[RawArticle]:
        logger.info("🚀 Starting ingestion engine...")
        start = datetime.now()

        # Run all sources concurrently
        async with self.rss as rss, self.bse as bse:
            rss_task = asyncio.create_task(rss.ingest_all(fetch_full_text=True))
            bse_task = asyncio.create_task(bse.fetch_announcements(days_back=1))
            newsapi_task = asyncio.create_task(self.newsapi.fetch())

            rss_articles, bse_articles, newsapi_articles = await asyncio.gather(
                rss_task, bse_task, newsapi_task
            )

        all_articles = rss_articles + bse_articles + newsapi_articles

        # Global dedup
        seen_ids = set()
        unique = []
        for art in all_articles:
            if art.external_id not in seen_ids:
                seen_ids.add(art.external_id)
                unique.append(art)

        elapsed = (datetime.now() - start).seconds
        logger.info(f"✅ Ingestion complete: {len(unique)} unique articles in {elapsed}s")

        if save_to_db:
            await self._save(unique)

        return unique

    async def _save(self, articles: list[RawArticle]):
        """
        Bulk-insert articles into PostgreSQL.
        Uses ON CONFLICT DO NOTHING to handle duplicates.
        """
        from models.db_session import get_async_session
        from models.database import NewsArticle as NewsArticleModel, ArticleStatus
        from sqlalchemy.dialects.postgresql import insert

        async with get_async_session() as session:
            rows = []
            for art in articles:
                rows.append({
                    "external_id": art.external_id,
                    "title": art.title[:1000],
                    "content": art.content[:10000] if art.content else "",
                    "url": art.url[:2000] if art.url else "",
                    "source": art.source[:100],
                    "author": (art.author or "")[:200],
                    "published_at": art.published_at,
                    "status": ArticleStatus.RAW.value,
                    "word_count": art.word_count(),
                    "raw_metadata": json.dumps(art.raw_metadata),
                    "is_duplicate": False,
                })

            if rows:
                stmt = insert(NewsArticleModel).values(rows)
                stmt = stmt.on_conflict_do_nothing(index_elements=["external_id"])
                await session.execute(stmt)
                await session.commit()
                logger.info(f"💾 Saved {len(rows)} articles to DB")
