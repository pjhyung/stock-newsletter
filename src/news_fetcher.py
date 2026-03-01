"""
뉴스 수집 모듈 (100% 무료)
- Yahoo Finance RSS: 빅테크 + 반도체 + 항공우주 개별 종목
- Google News RSS: 섹터 키워드 기반
- Reuters / CNBC / MarketWatch 공개 RSS
유료 API 없음. API 키 불필요.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote_plus

import feedparser

logger = logging.getLogger(__name__)

# ── Yahoo Finance RSS: 개별 종목 ─────────────────────────────
YAHOO_TICKERS = [
    # 빅테크
    "AAPL", "MSFT", "GOOGL", "META", "AMZN", "TSLA", "NVDA",
    # 반도체
    "AMD", "INTC", "QCOM", "AVGO", "MU",
    # 항공우주·방산
    "BA", "LMT", "RTX", "NOC", "PLTR",
]

YAHOO_RSS_TEMPLATE = (
    "https://feeds.finance.yahoo.com/rss/2.0/headline"
    "?s={ticker}&region=US&lang=en-US"
)

# ── Google News RSS: 섹터 쿼리 ────────────────────────────────
GOOGLE_NEWS_QUERIES = [
    "AI stocks artificial intelligence",
    "semiconductor stocks chip",
    "aerospace defense stocks",
    "S&P500 NASDAQ market",
    "Federal Reserve interest rates economy",
]

GOOGLE_NEWS_TEMPLATE = (
    "https://news.google.com/rss/search"
    "?q={query}&hl=en-US&gl=US&ceid=US:en"
)

# ── 기타 공개 RSS ─────────────────────────────────────────────
STATIC_FEEDS = {
    "Reuters Business": "https://feeds.reuters.com/reuters/businessNews",
    "CNBC Top News": (
        "https://search.cnbc.com/rs/search/combinedcms/view.xml"
        "?partnerId=wrss01&id=100003114"
    ),
    "MarketWatch": "http://feeds.marketwatch.com/marketwatch/topstories/",
    "Investing.com": "https://www.investing.com/rss/news.rss",
}


def _parse_published(entry) -> Optional[datetime]:
    """feedparser의 published_parsed(struct_time)를 UTC datetime으로 변환."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def fetch_rss_feed(url: str, hours_back: int = 12, source_label: str = "") -> list[dict]:
    """
    단일 RSS URL에서 기사를 파싱하여 정규화된 dict 리스트 반환.
    hours_back 시간 이내 기사만 포함. 발행시간 파싱 실패 시 포함.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    articles = []

    try:
        feed = feedparser.parse(url)
        feed_title = source_label or feed.feed.get("title", url)

        for entry in feed.entries:
            published_at = _parse_published(entry)

            # 시간 필터 (파싱 실패 기사는 포함)
            if published_at and published_at < cutoff:
                continue

            title = entry.get("title", "").strip()
            link = entry.get("link", "")
            summary = (entry.get("summary") or entry.get("description") or "").strip()

            # HTML 태그 간단 제거
            import re
            summary = re.sub(r"<[^>]+>", "", summary)[:500]

            if not title or not link:
                continue

            articles.append({
                "title": title,
                "url": link,
                "summary": summary,
                "published": published_at.isoformat() if published_at else "unknown",
                "source": feed_title,
            })

    except Exception as e:
        logger.warning(f"RSS fetch failed [{source_label or url[:60]}]: {e}")

    return articles


def collect_news(hours_back: int = 12, max_articles: int = 30) -> list[dict]:
    """
    모든 소스(Yahoo, Google News, 정적 RSS)에서 뉴스를 수집하고
    URL 기준 중복 제거 후 최신순 max_articles개 반환.
    소스 하나 실패해도 나머지로 계속 진행.
    """
    all_articles: list[dict] = []

    # 1) Yahoo Finance 종목별 RSS
    logger.info("Fetching Yahoo Finance RSS feeds...")
    for ticker in YAHOO_TICKERS:
        url = YAHOO_RSS_TEMPLATE.format(ticker=ticker)
        items = fetch_rss_feed(url, hours_back=hours_back, source_label=f"Yahoo Finance ({ticker})")
        all_articles.extend(items)
        if items:
            logger.debug(f"  {ticker}: {len(items)} articles")

    # 2) Google News 섹터 쿼리
    logger.info("Fetching Google News RSS feeds...")
    for query in GOOGLE_NEWS_QUERIES:
        encoded = quote_plus(query)
        url = GOOGLE_NEWS_TEMPLATE.format(query=encoded)
        items = fetch_rss_feed(url, hours_back=hours_back, source_label=f"Google News ({query[:30]})")
        all_articles.extend(items)
        if items:
            logger.debug(f"  Google News [{query[:30]}]: {len(items)} articles")

    # 3) 정적 RSS 피드
    logger.info("Fetching static RSS feeds...")
    for name, url in STATIC_FEEDS.items():
        items = fetch_rss_feed(url, hours_back=hours_back, source_label=name)
        all_articles.extend(items)
        if items:
            logger.debug(f"  {name}: {len(items)} articles")

    logger.info(f"Total raw articles collected: {len(all_articles)}")

    # URL 기준 중복 제거 + 빈 타이틀 필터
    seen_urls: set[str] = set()
    unique: list[dict] = []
    for article in all_articles:
        url = article.get("url", "")
        if url and url not in seen_urls and article.get("title"):
            seen_urls.add(url)
            unique.append(article)

    # 최신순 정렬
    unique.sort(key=lambda x: x.get("published", ""), reverse=True)

    result = unique[:max_articles]
    logger.info(f"After dedup & limit: {len(result)} articles")
    return result


if __name__ == "__main__":
    # 직접 실행 시 테스트
    logging.basicConfig(level=logging.INFO)
    news = collect_news(hours_back=24, max_articles=10)
    for i, a in enumerate(news, 1):
        print(f"\n[{i}] {a['source']}")
        print(f"    {a['title']}")
        print(f"    {a['url']}")
