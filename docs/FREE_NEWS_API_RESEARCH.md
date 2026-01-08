# Free Financial News API Research Report

**Date:** January 7, 2026  
**Purpose:** Evaluate free (no API key) methods to fetch financial news for stock tickers

---

## Executive Summary

| Method | Reliability | Data Quality | Rate Limits | Recommended |
|--------|-------------|--------------|-------------|-------------|
| **yfinance `ticker.news`** | ⭐⭐⭐⭐⭐ | Excellent | Moderate | ✅ **Best Choice** |
| **yfinance `Search.news`** | ⭐⭐⭐⭐⭐ | Excellent | Moderate | ✅ Alternative |
| **Google News RSS** | ⭐⭐⭐⭐ | Good | Very Low | ✅ Backup Option |
| **SEC EDGAR RSS** | ⭐⭐⭐⭐⭐ | Official Only | Very Low | ⚠️ Filings Only |
| **Yahoo Finance Scraping** | ⭐⭐ | Variable | N/A | ❌ Fragile |

**Recommendation:** Use **yfinance's built-in `ticker.news`** as the primary source with **Google News RSS** as a fallback.

---

## 1. yfinance News Functionality

### 1.1 `Ticker.news` Attribute (RECOMMENDED)

yfinance provides excellent built-in news fetching via the `Ticker` class.

#### How It Works
```python
import yfinance as yf

ticker = yf.Ticker("AAPL")
news = ticker.news  # Returns list of news items
# OR
news = ticker.get_news(count=10, tab="news")  # More control
```

#### Data Format Returned
```python
{
    "id": "e2c9a6ff-f5c0-3b9c-9e43-6b72385400a4",
    "content": {
        "id": "e2c9a6ff-f5c0-3b9c-9e43-6b72385400a4",
        "contentType": "STORY",
        "title": "Article Title Here",
        "summary": "Article summary/description...",
        "pubDate": "2026-01-07T22:00:38Z",
        "displayTime": "2026-01-07T22:00:38Z",
        "provider": {
            "displayName": "Investor's Business Daily",
            "url": "http://www.investors.com/"
        },
        "thumbnail": {
            "originalUrl": "https://media.zenfs.com/...",
            "resolutions": [...]
        },
        "canonicalUrl": {
            "url": "https://www.investors.com/...",
            "site": "finance",
            "region": "US",
            "lang": "en-US"
        },
        "finance": {
            "premiumFinance": {
                "isPremiumNews": false,
                "isPremiumFreeNews": false
            }
        }
    }
}
```

#### Key Fields
- `content.title` - Headline
- `content.summary` - Article description (may contain HTML)
- `content.pubDate` - Publication timestamp (ISO 8601)
- `content.provider.displayName` - News source name
- `content.canonicalUrl.url` - Link to full article
- `content.thumbnail.originalUrl` - Image URL

#### Pros
- ✅ **No API key required**
- ✅ Reliable, actively maintained library
- ✅ Rich metadata (thumbnails, publisher info, related tickers)
- ✅ Returns up to 10+ news items per request
- ✅ Uses Yahoo Finance's internal JSON API
- ✅ Integrates with existing yfinance usage in the app

#### Cons
- ⚠️ Rate limited (HTTP 429 after ~5-10 rapid requests)
- ⚠️ Yahoo's ToS technically restricts commercial use
- ⚠️ No guarantee of API stability (unofficial)

#### Rate Limiting
- Empirical testing shows ~5-10 requests before 429 errors
- Recovery time: ~30-60 seconds
- **Mitigation:** Cache results for 2-5 minutes

---

### 1.2 `Search.news` Class

Alternative method using the Search functionality:

```python
import yfinance as yf

search = yf.Search("AAPL", news_count=10)
news = search.news
```

#### Data Format
```python
{
    "uuid": "5cc46bc2-f83c-3159-987d-ade525eb4cb2",
    "title": "AAPL: Evercore Calls Apple Top Tech Pick",
    "publisher": "GuruFocus.com",
    "link": "https://finance.yahoo.com/news/...",
    "providerPublishTime": 1767803325,  # Unix timestamp
    "type": "STORY",
    "thumbnail": {...},
    "relatedTickers": ["AAPL", "DELL", "HPE"]
}
```

#### Pros
- ✅ Same reliability as `ticker.news`
- ✅ Includes `relatedTickers` field
- ✅ Configurable news count (up to 8 default)

#### Cons
- ⚠️ Slightly different data structure
- ⚠️ Same rate limits apply

---

## 2. Yahoo Finance Direct API

### Endpoint Used by yfinance
```
https://query2.finance.yahoo.com/v1/finance/search?q=AAPL&newsCount=10&quotesCount=0
```

### Response Structure
```python
{
    "news": [...],
    "quotes": [...],
    "count": 10,
    "totalTime": 123
}
```

### Rate Limiting
- HTTP 429 (Too Many Requests) after 5-10 rapid calls
- No `X-RateLimit` headers exposed
- Recommended: 1 request per 10 seconds minimum

### Legal/ToS Considerations
> "yfinance is not affiliated, endorsed, or vetted by Yahoo, Inc. It's an open-source tool that uses Yahoo's publicly available APIs, and is intended for **research and educational purposes**."
>
> "The Yahoo! finance API is intended for **personal use only**."

**Recommendation:** For production apps, cache aggressively and add rate limiting. Consider this a "gray area" for commercial use.

---

## 3. Google News RSS

### How It Works
```python
import feedparser
import urllib.parse

ticker = "AAPL"
query = urllib.parse.quote(f"{ticker} stock")
url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

feed = feedparser.parse(url)
for entry in feed.entries[:10]:
    print(entry.title)
    print(entry.source.title)  # Publisher name
    print(entry.published)
    print(entry.link)
```

### Data Format
```python
{
    "title": "AAPL Stock: Why Apple Got a Double Thumbs-Up - TipRanks",
    "link": "https://news.google.com/rss/articles/CBMi...",  # Redirects to source
    "published": "Tue, 06 Jan 2026 15:03:42 GMT",
    "source": {"title": "TipRanks", "href": "https://tipranks.com"}
}
```

### Pros
- ✅ **100% free, no API key**
- ✅ Very low rate limits (100+ requests observed)
- ✅ Returns up to 100 articles per query
- ✅ Wide source coverage
- ✅ Standard RSS/Atom format (feedparser compatible)

### Cons
- ⚠️ Less stock-specific (general financial news)
- ⚠️ No thumbnails or rich metadata
- ⚠️ Links redirect through Google (not direct)
- ⚠️ Can include non-financial articles matching the ticker
- ⚠️ No summary/description field

### Advanced Query Options
```python
# More specific queries
"AAPL stock news"          # General stock news
"AAPL earnings"            # Earnings-related
"AAPL+intitle:Apple"       # Must contain "Apple" in title
"AAPL site:reuters.com"    # Specific source only
```

### URL Parameters
- `q=` - Search query (URL encoded)
- `hl=en-US` - Language
- `gl=US` - Country/region
- `ceid=US:en` - Edition ID

---

## 4. SEC EDGAR RSS Feeds

### How It Works
SEC EDGAR provides Atom feeds for company filings. Requires CIK (Central Index Key).

```python
import httpx
import feedparser

# AAPL CIK: 0000320193
cik = "0000320193"
url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=&dateb=&owner=include&count=10&output=atom"

# IMPORTANT: SEC requires User-Agent identification
headers = {
    "User-Agent": "YourApp/1.0 (your-email@example.com)"
}

response = httpx.get(url, headers=headers, timeout=10)
feed = feedparser.parse(response.text)

for entry in feed.entries:
    print(entry.title)   # "8-K  - Current report"
    print(entry.updated) # "2026-01-02T16:30:52-05:00"
    print(entry.link)    # Direct link to filing
```

### Data Available
- 8-K: Material events (earnings, leadership changes)
- 10-K: Annual reports
- 10-Q: Quarterly reports
- 4: Insider trading
- SC 13G/D: Institutional ownership changes

### Pros
- ✅ **100% free, official source**
- ✅ No rate limits (with proper User-Agent)
- ✅ Direct, unmodified official filings
- ✅ Reliable and stable

### Cons
- ⚠️ **SEC filings only, not news articles**
- ⚠️ Requires CIK lookup (ticker → CIK mapping)
- ⚠️ Must include User-Agent header (SEC requirement)
- ⚠️ Limited to regulatory filings

### CIK Lookup
```python
# You can lookup CIK by ticker
url = f"https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={ticker}&type=&owner=include&count=1&action=getcompany"
# Parse HTML response to extract CIK
```

---

## 5. Yahoo Finance HTML Scraping (NOT RECOMMENDED)

### Why Not Recommended
- ❌ HTML structure changes frequently (breaks scrapers)
- ❌ JavaScript-rendered content requires Selenium/Playwright
- ❌ Explicitly against Yahoo ToS
- ❌ High maintenance burden
- ❌ yfinance already provides structured API access

### If You Must Scrape
The news page (`https://finance.yahoo.com/quote/AAPL/news`) uses React/JavaScript rendering. Static HTML scraping with BeautifulSoup won't work.

Would require:
- Selenium/Playwright for JavaScript execution
- Regular maintenance as UI changes
- Risk of IP blocking

**Verdict:** Don't do it. Use yfinance instead.

---

## 6. Other Free Sources (Limited Value)

### Reddit (r/stocks, r/wallstreetbets)
```python
# Reddit JSON API (no auth for read)
url = "https://www.reddit.com/r/stocks/search.json?q=AAPL&sort=new&limit=10"
```
- ⚠️ Social sentiment, not news
- ⚠️ Low signal-to-noise ratio
- ⚠️ Rate limited without OAuth

### Finviz News (Scraping Required)
- ❌ No public API
- ❌ Anti-scraping measures
- ❌ ToS prohibits scraping

### MarketWatch RSS
- MarketWatch has removed most RSS feeds
- ❌ Not recommended

---

## 7. Implementation Recommendations

### Recommended Architecture

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import yfinance as yf
import feedparser
import urllib.parse

@dataclass
class NewsItem:
    title: str
    source: str
    url: str
    published_at: datetime
    summary: Optional[str] = None
    thumbnail_url: Optional[str] = None

async def fetch_news_yfinance(ticker: str, count: int = 10) -> list[NewsItem]:
    """Primary: Fetch news via yfinance (Yahoo Finance API)."""
    try:
        t = yf.Ticker(ticker)
        raw_news = t.get_news(count=count)
        
        items = []
        for item in raw_news:
            content = item.get("content", {})
            items.append(NewsItem(
                title=content.get("title", ""),
                source=content.get("provider", {}).get("displayName", "Unknown"),
                url=content.get("canonicalUrl", {}).get("url", ""),
                published_at=datetime.fromisoformat(
                    content.get("pubDate", "").replace("Z", "+00:00")
                ),
                summary=content.get("summary"),
                thumbnail_url=content.get("thumbnail", {}).get("originalUrl")
            ))
        return items
    except Exception as e:
        # Fallback to Google News on error
        return await fetch_news_google(ticker, count)

async def fetch_news_google(ticker: str, count: int = 10) -> list[NewsItem]:
    """Fallback: Fetch news via Google News RSS."""
    query = urllib.parse.quote(f"{ticker} stock news")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:count]:
        # Parse published date
        pub_date = entry.get("published_parsed")
        if pub_date:
            published_at = datetime(*pub_date[:6])
        else:
            published_at = datetime.now()
        
        items.append(NewsItem(
            title=entry.get("title", ""),
            source=entry.get("source", {}).get("title", "Unknown"),
            url=entry.get("link", ""),
            published_at=published_at,
            summary=None,  # Google RSS doesn't provide summaries
            thumbnail_url=None
        ))
    return items
```

### Caching Strategy
```python
from datetime import timedelta

# Cache news for 2-5 minutes to avoid rate limits
CACHE_TTL = timedelta(minutes=2)

# Store: {ticker: (timestamp, news_items)}
_news_cache: dict[str, tuple[datetime, list[NewsItem]]] = {}
```

### Rate Limiting Best Practices
1. Cache results for 2-5 minutes minimum
2. Implement exponential backoff on 429 errors
3. Add random jitter between requests (0.5-2s)
4. Consider request queuing for multiple tickers

---

## 8. Comparison Matrix

| Feature | yfinance | Google News RSS | SEC EDGAR |
|---------|----------|-----------------|-----------|
| API Key Required | ❌ No | ❌ No | ❌ No |
| Rate Limits | Moderate | Very Low | Very Low |
| News Quality | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | N/A (filings) |
| Metadata | Rich | Basic | Minimal |
| Thumbnails | ✅ Yes | ❌ No | ❌ No |
| Summaries | ✅ Yes | ❌ No | ❌ No |
| Reliability | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Stability | Medium | High | Very High |
| ToS Risk | Medium | Low | None |

---

## 9. Final Recommendations

### For Viper Terminal

1. **Primary Source:** `yfinance.Ticker.news`
   - Already using yfinance in the project
   - Rich metadata (thumbnails, summaries, sources)
   - Good data quality
   
2. **Fallback Source:** Google News RSS
   - No rate limits
   - 100% free and reliable
   - Use when yfinance fails or is rate-limited

3. **Optional Enhancement:** SEC EDGAR RSS
   - Add as separate "SEC Filings" section
   - Official regulatory documents
   - Useful for serious investors

### Implementation Priority
1. Replace current broken RSS implementation with yfinance
2. Add 2-minute caching
3. Add Google News RSS fallback
4. (Optional) Add SEC filings tab

### Code Changes Required
- Update `viper/services/news.py` to use yfinance
- Add Google News RSS fallback
- Remove dead Yahoo RSS feed code
- Update news panel widget to handle new data format

---

## 10. Legal Disclaimer

This research is for educational purposes. Users should:
- Review Yahoo's Terms of Service before production use
- Implement proper rate limiting and caching
- Not use for high-frequency or commercial data redistribution
- Consider that unofficial APIs may change without notice

---

*Report generated for Viper Terminal project*
