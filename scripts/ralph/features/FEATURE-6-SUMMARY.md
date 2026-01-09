# Feature 6: In-App Article Reader Mode

## Summary

Fetch and display news article content directly in the terminal instead of opening a browser. Reader mode strips ads, navigation, and boilerplate to render clean, readable text. Essential for headless/server environments and reduces eye strain from bright browser windows.

## Target Architecture

```
NewsPanel (existing)
│
├── User presses Enter on article
│   └── Posts ArticleOpenRequested(news_item)
│
└── User presses 'o' on article
    └── Opens in browser (existing behavior)

App.py
│
├── Handles ArticleOpenRequested
│   └── Shows ArticleReaderPanel, triggers fetch
│
└── ArticleReaderPanel
    ├── Header: title, source, date, reading time
    ├── Content: scrollable extracted article text
    └── Footer: keybinding hints

ArticleReader Service
│
├── fetch_article(url) -> ArticleResult | ArticleError
│   ├── HTTP fetch with httpx (async)
│   ├── Extract with trafilatura
│   └── Cache result (30 min TTL)
│
└── Handles: timeouts, paywalls, extraction failures
```

## Key Behavior Change

| Key | Old Behavior | New Behavior |
|-----|--------------|--------------|
| **Enter** | Open in browser | Open in reader panel |
| **o** | (none) | Open in browser (fallback) |
| **Escape** | (in reader) | Close reader, return to news |
| **j/k** | (in reader) | Scroll line up/down |
| **PageUp/PageDown** | (in reader) | Scroll page up/down |
| **Home/End** | (in reader) | Jump to top/bottom |
| **r** | (in reader) | Retry fetch |

## Stories (5 total)

| ID | Title | Effort | Dependencies |
|----|-------|--------|--------------|
| VPR-060 | Create ArticleReader service | Medium | - |
| VPR-061 | Create ArticleReaderPanel widget | Medium | VPR-060 |
| VPR-062 | Integrate with NewsPanel | Medium | VPR-061 |
| VPR-063 | Error handling & fallback | Small | VPR-062 |
| VPR-064 | Polish & testing | Small | VPR-063 |

### Dependency Graph (Linear)

```
VPR-060 → VPR-061 → VPR-062 → VPR-063 → VPR-064
(service)  (widget)  (integrate) (errors)  (polish)
```

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Extraction** | trafilatura | Best accuracy, Apache 2.0, used by HuggingFace/Microsoft |
| **HTTP** | httpx (async) | Non-blocking, modern, timeout support |
| **Fallback** | newspaper3k | Widely compatible backup extractor |
| **Rendering** | Rich Markdown | Native Textual support, clean formatting |

## ArticleReader Service Design

```python
@dataclass
class ArticleResult:
    title: str
    content: str           # Extracted article text (markdown)
    author: Optional[str]
    date: Optional[datetime]
    source_url: str
    word_count: int

    @property
    def reading_time_minutes(self) -> int:
        return max(1, self.word_count // 200)

@dataclass
class ArticleError:
    error_type: str        # "timeout", "paywall", "extraction_failed", "network"
    message: str
    url: str

async def fetch_article(url: str, timeout: float = 10.0) -> ArticleResult | ArticleError:
    # Check cache first
    # HTTP fetch with httpx
    # Extract with trafilatura.extract()
    # Cache and return
```

## Error Handling Strategy

| Error | Detection | User Message |
|-------|-----------|--------------|
| **Timeout** | httpx.TimeoutException | "Article took too long to load" |
| **Network** | httpx.RequestError | "Could not connect to site" |
| **Paywall** | Content < 100 words or keywords | "Article may be behind a paywall" |
| **Extraction** | trafilatura returns None | "Could not extract article content" |
| **404** | HTTP 404 response | "Article not found" |

All errors show: **"Press 'o' to open in browser"**

## Files to Create

```
viper/services/article_reader.py    # Extraction service
viper/widgets/article_reader_panel.py   # Reader widget
tests/test_article_reader.py        # Service tests
tests/test_article_reader_panel.py  # Widget tests
```

## Files to Modify

```
viper/widgets/news_panel.py    # Enter → reader, 'o' → browser
viper/app.py                   # Handle ArticleOpenRequested
viper/viper.tcss               # Reader panel styles
viper/widgets/help_screen.py   # Document new keybindings (see below)
pyproject.toml                 # Add trafilatura, httpx
```

## Help Screen Updates (VPR-062)

Specific changes required in `help_screen.py`:

**KEYBINDINGS section:**
- Change: `Enter` → "Read article / Select item" (was "View selected item / Open in browser")
- Add: `o` → "Open in browser (news panel)"

**NEWS section:**
- Update: "Enter to open in browser" → "Enter to read in terminal"
- Add: "Press 'o' to open article in browser instead"

**New ARTICLE READER section** (after NEWS):
```
ARTICLE READER
Press Enter on a news item to read the full article in the terminal.

Esc / q              Close reader, return to news
j / k                Scroll line down/up
PageDown / PageUp    Scroll page down/up
Home / End           Jump to top/bottom
o                    Open article in browser
r                    Retry fetch if failed

Articles are extracted and cleaned for distraction-free reading.
If extraction fails, press 'o' to open in browser.
```

**FEATURES section:**
- Add: "• In-app article reader for distraction-free news reading"

## Success Criteria

- [ ] Enter on news item opens readable article in terminal
- [ ] Article text is clean (no ads, navigation, boilerplate)
- [ ] Loading state shows within 100ms
- [ ] Content displays within 5 seconds for most sites
- [ ] Extraction succeeds for 80%+ of major news sources
- [ ] Graceful fallback to browser when extraction fails
- [ ] All tests pass, coverage ≥ 90%
- [ ] Works at 80x24 minimum terminal size

## Out of Scope

- Offline article saving/bookmarking
- Article search within reader
- Text-to-speech
- Image display (terminal limitation)
- Login/authentication for paywalled sites

## Difficulty Assessment

**Medium-Low** - This feature follows existing patterns in the codebase:
- NewsPanel pattern for keybindings and panel structure
- ChartPanel pattern for loading states and async fetching
- trafilatura does the heavy lifting for extraction

Main risk: Some sites may block scrapers or have unusual formatting. Mitigated by fallback to browser.
