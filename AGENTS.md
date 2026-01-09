# Agent Learnings

This file documents patterns, best practices, and gotchas discovered during development.

## ⚠️ CRITICAL: Textual Color Rendering ⚠️

**NEVER USE ANSI ESCAPE CODES** for colors in Textual widgets!

Textual uses **Rich markup** (`[green]text[/green]`), NOT ANSI codes (`\033[32m`).

ANSI escape codes will:
1. Be treated as literal characters (not interpreted)
2. Break widget rendering and layout
3. Cause screenshots to fail
4. Display garbage like `[0m` or escape sequences

**CORRECT (Rich markup):**
```python
volume_bars.append(f"[green]{char}[/green]")  # ✅ Works!
overlay_char = f"[cyan]{char}[/cyan]"          # ✅ Works!
```

**WRONG (ANSI codes):**
```python
volume_bars.append(f"\033[32m{char}\033[0m")  # ❌ BROKEN!
overlay_char = f"\033[36m{char}\033[0m"        # ❌ BROKEN!
```

**ALSO CRITICAL:** When using Rich markup in Label widgets, you MUST set `markup=True`:
```python
Label(line_with_colors, markup=True)   # ✅ Renders colors
Label(line_with_colors, markup=False)  # ❌ Shows literal [green] tags
```

This applies to: volume bars, moving average overlays, RSI indicators, any colored text.

---

## Codebase Patterns

### Python Project Setup
- **Virtual Environment Required**: System Python is externally managed on Ubuntu. Always use `python3 -m venv .venv`
- **pyproject.toml**: Use setuptools build backend for editable installs
- **Dependencies**: Separate `dependencies` from `optional-dependencies.dev`

### Testing with Textual
- **Pilot Framework**: Use `async with app.run_test() as pilot` for testing Textual apps
- **Query Widgets**: Use `app.query_one(WidgetType)` to find specific widgets
- **Unused Variables**: When not using `pilot`, omit it from the context manager to avoid linter warnings
- **Coverage**: Entry point modules (`__main__.py`) need explicit tests; mock the app instance

### Type Checking
- **mypy --strict**: Requires explicit type annotations on all functions
- **Dict Types**: Be careful with dict return types - mixed value types require Union or Any
- **Textual Types**: Import `ComposeResult` from `textual.app` for compose() methods

### Code Quality
- **Ruff**: Fast and comprehensive linter/formatter that replaces multiple tools
- **Coverage Threshold**: Set to 90% minimum in pyproject.toml
- **pytest-asyncio**: Use `@pytest.mark.asyncio` decorator for async tests
- **asyncio_mode = "auto"**: Set in pyproject.toml to auto-detect async tests

## Story-Specific Learnings

### VPR-001: Project Scaffold
- Start with minimal viable structure - don't over-engineer the design system
- CSS-in-Textual uses TCSS (Textual CSS), which is similar to CSS but more limited
- Header and Footer widgets are built-in and work out of the box
- Bindings are defined as class-level tuples: `BINDINGS = [("key", "action", "description")]`

### VPR-002: Command Input Bar with Ticker Parsing
- **Custom Widget Pattern**: Extend `Input` widget and override `on_input_submitted()` for custom behavior
- **Event Emission**: Define custom events as nested classes that inherit from `Message`
- **Event Handling**: Use snake_case method naming: `on_{widget_name}_{event_name}` (e.g., `on_ticker_input_ticker_lookup`)
- **CSS Classes**: Use `add_class()` and `remove_class()` for dynamic styling (e.g., error states)
- **Input Validation**: Always strip whitespace before validation; clear input even on error
- **Event Testing**: Create test app with event tracking; use instance variable to collect events
- **TCSS Docking**: Use `dock: bottom` to position widgets at the bottom of the screen
- **Test Isolation**: Each test should use a fresh app instance for proper isolation

### VPR-003: Stock Quote Fetching with yfinance
- **Async Wrappers**: Use `asyncio.get_event_loop().run_in_executor()` to run blocking I/O (yfinance) without blocking UI
- **Error as Data**: Return error results (dataclass) instead of raising exceptions for better type safety
- **Union Result Types**: Use `Result = Success | Error` pattern for functions that can fail
- **yfinance fast_info**: Use `ticker.fast_info` for faster responses; it provides essential fields without full info fetch
- **⚠️ fast_info is NOT a dict**: Access values via attributes (`info.last_price`), NOT dict-style (`info.get("last_price")`). The `.get()` method exists but returns `None` for attribute names!
- **Attribute Access for fast_info**: Use `info.last_price`, `info.previous_close`, `info.last_volume`, `info.market_cap`
- **Optional Attributes**: Use `getattr(info, "field_name", default)` for optional fields that may not exist
- **Timeout Handling**: Wrap executor calls in `asyncio.wait_for()` for timeout support
- **Type Stubs**: Add `# type: ignore[import-untyped]` for libraries without type stubs (mypy --strict)
- **Modern Type Syntax**: Use `X | None` instead of `Optional[X]` (Python 3.10+ union syntax)
- **Comprehensive Testing**: Test success path, invalid inputs, network errors, timeouts, and malformed responses
- **Mock External APIs**: Always mock yfinance (or any external API) in tests - use `unittest.mock.patch`
- **Test Edge Cases**: Zero division protection, missing data fields, API exceptions
- **MagicMock for Objects**: Use `MagicMock()` to mock complex objects with nested attributes (e.g., `ticker.fast_info`)
- **Mock fast_info as Object**: Create mock with attributes (`mock.last_price = 150.0`), NOT as a dict
- **Property Mocking**: Use `type(obj).property_name = property(lambda: value)` to mock properties that raise exceptions

### VPR-004: Stock Quote Display Panel
- **Widget Composition**: Use `compose()` with context manager syntax for nested widgets: `with Container(): yield Widget()`
- **Dynamic Mounting**: Can't mount to a container before it's attached; use `compose()` for initial setup, `mount()` for runtime updates
- **Multiple States**: Implement state machine pattern with `_state` attribute and `show_*()` methods for each state (empty, loading, success, error)
- **Container Updates**: Use `container.remove_children()` to clear before remounting for state transitions
- **Loading Indicators**: Mount LoadingIndicator with Label in a container; pass children to Container constructor: `Container(widget1, widget2)`
- **Label Testing**: Use `str(label.render())` to get text content for assertions, not `label.renderable` (doesn't exist)
- **Pilot Pause**: Call `await pilot.pause()` after dynamic updates to let UI refresh before assertions
- **Color Classes**: Apply CSS classes based on data values (positive/negative) for conditional styling
- **Number Formatting**: Use f-strings with `:,` for thousands separators and `:.Nf` for decimals
- **Ternary for Simple Conditionals**: Use ternary operators for simple if/else assignments to satisfy ruff linter
- **Remove Unnecessary else**: After return statements, remove else clause (ruff RET505)
- **Unused Variables**: Remove unused variables assigned in conditional blocks (ruff F841)
- **Widget Queries**: Use `query()` to get all matching widgets, `query_one()` for a single required widget
- **Integration Testing**: Mock async functions with `AsyncMock` and verify both success and error paths
- **Event Handler Testing**: Use `await pilot.pause()` after triggering events to let async handlers complete

### VPR-005: Crypto Quote Fetching with CoinGecko
- **httpx for Async HTTP**: Use `httpx.AsyncClient()` for async HTTP requests; more modern than aiohttp
- **respx for HTTP Mocking**: Use `@respx.mock` decorator with `respx.get().mock()` to mock HTTP responses in tests
- **Symbol Mapping**: Maintain dict of common crypto symbols to API IDs (e.g., "BTC" -> "bitcoin")
- **Rate Limit Handling**: Detect 429 status codes and implement exponential backoff with retries
- **Exponential Backoff**: Use `2**attempt` for wait times (1s, 2s, 4s...)
- **Retry Loop Pattern**: Track last error through retry attempts; return specific error after exhausting retries
- **HTTP Status Codes**: Check response.status_code explicitly; 200 = success, 429 = rate limit, 404/500 = errors
- **JSON Response Handling**: Use `response.json()` to parse; wrap in try/except for malformed JSON
- **Defensive Parsing**: Use isinstance() checks on API response structure before accessing nested fields
- **Type Conversions**: Explicitly convert API values with float() and int() for type safety
- **Default Values**: Provide sensible defaults for optional fields (0 for volumes, None for names)
- **Multiple Exception Types**: Catch specific httpx exceptions (ConnectError, RequestError, TimeoutError) separately
- **HTTP Error Messages**: Include status code and reason phrase in error messages for debugging
- **Test Coverage Goals**: Aim for >95% coverage; use `pragma: no cover` for truly unreachable defensive code
- **Async Timeout Pattern**: Use `asyncio.wait_for()` to wrap async operations with timeout
- **Mock Side Effects**: Use route.side_effect with list to simulate retry success (first fails, second succeeds)
- **Test API Parameters**: Verify correct query params are sent using respx route matching
- **Unused Imports**: Remove unused imports to satisfy ruff linter (F401)

### VPR-006: Unified Quote Lookup with Asset Type Detection
- **Union Types for Services**: Create union types to combine stock and crypto results: `Quote = StockQuote | CryptoQuote`
- **Type Discrimination**: Use isinstance() checks to distinguish between quote types at runtime
- **Prefix Parsing**: Implement explicit type prefixes (`:CRYPTO`, `:STOCK`) for user control
- **Auto-Detection Logic**: Check known symbol lists first (crypto symbols), then fall back to alternative service (stock)
- **Symbol Normalization**: Always normalize input (uppercase, strip whitespace) before processing
- **Delegation Pattern**: Unified service delegates to specialized services based on detected type
- **Helper Functions**: Provide type-checking helpers (is_crypto_quote, is_stock_quote) for cleaner code
- **Widget Adaptation**: Single display widget can handle multiple types by checking instance type
- **Conditional Rendering**: Use isinstance() checks to route to different rendering methods (_render_stock_quote vs _render_crypto_quote)
- **Display Differences**: Adapt field labels for asset type (e.g., "52W Range" for stocks vs "24h Volume" for crypto)
- **Error Type Handling**: Handle both StockError and CryptoError in error states with union types
- **Test Both Paths**: Test both explicit prefix usage and auto-detection in separate test cases
- **Integration Testing**: Mock unified service in app tests rather than individual services
- **Line Length**: Split long mock patch statements across multiple lines to satisfy 100-char limit
- **Type Consistency**: Ensure all related functions accept and return consistent union types throughout the stack

### VPR-007: Quote History and Quick Recall
- **Persistence Pattern**: Store data in `~/.config/viper/` directory using JSON files
- **Config Directory Creation**: Use `Path.mkdir(parents=True, exist_ok=True)` to create nested directories
- **JSON Persistence**: Store list data in structured JSON with version key: `{"history": [...]}`
- **Graceful Loading**: Handle missing files, corrupt JSON, and invalid structure with try/except; start fresh on error
- **Data Validation**: Filter non-string items from loaded data using list comprehension with isinstance()
- **Deduplication**: Remove existing item before re-adding to front; moves duplicates to top of history
- **Size Limits**: Trim history to max_size after adding and when loading from disk
- **Navigation State**: Track current position with internal index; -1 means not navigating
- **Key Event Handling**: Use `on_key()` method to intercept keyboard events before default handling
- **Event Prevention**: Call `event.prevent_default()` when handling Up/Down arrows to avoid default Input behavior
- **Cursor Management**: Set `self.cursor_position` to position cursor at end after filling value from history
- **State Reset**: Reset navigation index when user types (any key except up/down) or adds to history
- **Input Integration**: Pass history_manager as optional parameter to widget; check for None before using
- **File Recovery**: Handle OSError on save by failing silently; history just won't persist in that session
- **Testing Persistence**: Use pytest's `tmp_path` fixture for isolated file system testing
- **Copy Pattern**: Return copies from getter methods to prevent external modification of internal state
- **Boundary Behavior**: At history end, stay on last item; at beginning, return empty string to clear input
- **Test Coverage**: Test all paths: add, navigate, reset, persist, load, corrupt data, missing files, empty history

### VPR-008: Watchlist Panel
- **Command Parsing**: Implement command prefix pattern (`W TICKER`, `D TICKER`) in event handler
- **Manager Pattern**: Separate data management (WatchlistManager) from UI widget (WatchlistPanel)
- **Reuse Persistence**: Same pattern as history - JSON file in `~/.config/viper/`, graceful error handling
- **Auto-refresh Timer**: Use `set_interval()` to schedule periodic async refreshes (60s default)
- **run_worker Pattern**: Use `self.run_worker(async_method())` to execute async operations from sync context (on_mount)
- **Async Refresh**: Make refresh_quotes async to fetch all ticker quotes in parallel using await
- **Quote Caching**: Store fetched quotes in dict to display while new data loads
- **Loading State**: Show "Loading..." when quote not in cache yet
- **Error Display**: Show "Error" when quote fetch fails, don't crash the widget
- **Type Narrowing**: Use isinstance() checks (not hasattr) for mypy type narrowing with union types
- **VerticalScroll**: Use VerticalScroll container for scrollable lists of items
- **Dynamic Rendering**: Update display with _render_items() method that clears and remounts labels
- **Format Strings**: Use f-string alignment (`:8s`, `:>12s`, `:>8s`) for columnar display
- **Color Classes**: Apply positive/negative/neutral classes based on change percentage
- **Timer Control**: Use boolean flag (_refresh_timer_active) to control whether refresh runs
- **on_mount/on_unmount**: Start timers in on_mount, stop in on_unmount for proper cleanup
- **Worker Testing**: Use `await pilot.pause(delay)` to give workers time to complete in tests
- **Mock Side Effect Functions**: Use async functions as side_effect to return different values per call
- **Test Coverage**: Test empty state, loading state, error state, positive/negative colors, crypto quotes, timer
- **Unused Imports**: Remove unused imports (Container, CryptoQuote) - ruff will auto-fix

### VPR-009: Multi-Panel Layout
- **Horizontal Layout**: Use `Horizontal` container for side-by-side panel layout (30% watchlist, 70% quote)
- **Nested Containers**: Use nested Containers with IDs for targeted CSS styling and querying
- **Panel Composition**: Wrap each major widget (WatchlistPanel, QuotePanel) in a Container for layout control
- **Focus Management**: Set `can_focus = True` on widgets to make them focusable for Tab cycling
- **Built-in Tab Cycling**: Use built-in `focus_next` action; Textual handles Tab cycling automatically
- **Visual Focus Indicators**: Use `:focus-within` pseudo-class in CSS to style containers when child widgets are focused
- **Border Styles**: Use `border: solid` for normal state, `border: double` for focused state to show active panel
- **Responsive Design Limitation**: Textual CSS doesn't support `@media` queries - must handle programmatically
- **on_resize Handler**: Override `on_resize()` method to handle terminal size changes dynamically
- **Dynamic Display Toggle**: Use `widget.display = False` to hide widgets; set `styles.width` to adjust layout
- **Terminal Width Check**: Check `self.size.width` to get current terminal width
- **Graceful Query Failures**: Wrap queries in try/except during resize - containers may not be mounted yet
- **Layout Testing**: Test that containers exist with correct IDs; actual proportions are handled by Textual's CSS engine
- **Focus Testing**: Test `can_focus` attribute and basic Tab key functionality
- **Integration Testing**: Add tests for layout structure, focusable widgets, and basic navigation

### VPR-010: Keyboard Navigation and Shortcuts
- **Action Methods**: Define actions as `action_*` methods; Textual binds them to keys automatically
- **Binding Format**: Use tuples in BINDINGS: `("key", "action_name", "description")`
- **Multiple Keys**: Bind multiple keys to same action with comma: `("question_mark,f1", "show_help", "Help")`
- **Widget Bindings**: Widgets can define their own BINDINGS with `Binding()` objects for local keybindings
- **Binding Visibility**: Use `show=False` in Binding() to hide from footer but still enable the key
- **List Navigation**: Use j/k keys for Vim-style navigation (j=down, k=up) in list widgets
- **Selection State**: Track selected index with `_selected_index` attribute; clamp to valid range in render
- **Visual Selection**: Apply "selected" CSS class to highlight currently selected item (background color)
- **Selection Clamping**: Clamp index in _render_items() to handle list size changes (removals, empty state)
- **Navigation Actions**: Use min/max to prevent selection from going out of bounds
- **Enter to Select**: Emit custom event (TickerSelected) when Enter is pressed on selected item
- **Focus Input**: Use `widget.focus()` to programmatically set focus to input bar
- **Escape for Clear**: Check if input has text before clearing; also remove error state
- **Placeholder Actions**: Create action methods that do nothing for future features (help screen)
- **Message Handling**: Use `on_{widget_name}_{event_name}` pattern to handle custom widget events
- **Extract Common Logic**: Create helper methods (_fetch_and_display_quote) to avoid code duplication
- **Empty State Handling**: Navigation actions should handle empty lists gracefully (early return)
- **Index Reset**: Reset selected_index to 0 when list becomes empty
- **Test All Keys**: Write tests for each keybinding (/, Esc, ?, F1, j, k, Enter)
- **Test Boundaries**: Test navigation at start/end of list (can't go beyond)
- **Test Visual State**: Verify CSS classes are applied correctly for selection highlighting
- **Test Event Emission**: Capture emitted events in test app to verify correct ticker is selected
- **Combined Context Managers**: Ruff prefers single with statement with multiple contexts instead of nested
- **Remove Unused Variables**: Remove variables that are queried but never used to satisfy ruff F841

### VPR-012: Company/asset Info Panel
- **VerticalScroll Container**: Use `VerticalScroll` for scrollable long content (descriptions)
- **Modal Display Pattern**: Use styles.display to toggle visibility: `styles.display = "block"` (visible) or `"none"` (hidden)
- **Display vs Visibility**: In Textual, use `widget.styles.display` for hiding/showing, not `widget.display` property
- **CSS display Property**: Set via TCSS (`display: none;`) or dynamically (`styles.display = "block"`)
- **Type-Specific Rendering**: Create separate render methods for different types (stock vs crypto) in same widget
- **Safe Dict Access**: Use `.get()` with defaults when accessing API response dicts for optional fields
- **Nested Dict Navigation**: Check `isinstance(value, dict)` before accessing nested fields in API responses
- **List Navigation**: Check `isinstance(value, list)` and length before accessing list elements
- **Employee Number Formatting**: Use f-string `:,` format for large numbers (164000 -> "164,000")
- **Info vs fast_info**: Use `stock.info` (not `fast_info`) for extended metadata; it's slower but has sector, industry, description, etc.
- **yfinance .info dict**: The `stock.info` property returns a regular dict, unlike `fast_info` which is an object
- **Empty Dict Validation**: Use `is None` check, not `not info`, since empty dict `{}` is valid and should be allowed
- **Variable Name Collision**: Use different variable names when fetching multiple info types (crypto_info_result vs stock_info_result) to avoid type checker confusion
- **ComposeResult Import**: Must import `ComposeResult` from `textual.app` for type hints on compose() method
- **Test Class Naming**: Avoid "Test" prefix for non-test classes (pytest tries to collect them); use descriptive suffix like "TestApp"
- **Timeout in Tests**: Use `time.sleep()` in sync mock functions (not `asyncio.sleep()`); executors run in threads, not async
- **InfoPanel Testing**: Test all display states (empty, stock info with/without fields, crypto info with/without fields)
- **Malformed Data Testing**: Test defensive parsing with malformed API responses (wrong types, missing nested keys)

### VPR-011: Intraday Price Chart (Sparkline)
- **DataFrame Access**: yfinance `history()` returns pandas DataFrame; access columns with `df["Close"]`
- **Timestamp Conversion**: Convert pandas timestamps to datetime with `.to_pydatetime()` method on each timestamp
- **Empty DataFrame Check**: Check `df.empty` and `df is None` to detect missing data
- **List Conversion**: Use `.tolist()` to convert DataFrame column to Python list
- **Sparkline Algorithm**: Normalize prices to 0-1 range, map to 8 vertical levels (Unicode block chars)
- **Unicode Block Chars**: Use `▁▂▃▄▅▆▇█` for ASCII-style charts (8 levels from lowest to highest)
- **Flat Line Handling**: When all prices are identical (range == 0), render as `─` characters
- **Downsampling**: When data points exceed chart width, downsample by taking evenly spaced points
- **Downsampling Formula**: `step = len(prices) / width; downsampled = [prices[int(i * step)] for i in range(width)]`
- **Normalization**: `normalized = (price - min_price) / price_range` gives 0-1 range
- **Block Index Mapping**: `block_index = min(int(normalized * 8), 7)` maps to 0-7 index (8 chars)
- **Worker Pattern**: Use `run_worker(async_method())` to fetch sparkline data without blocking rendering
- **Async Mounting**: Can call `container.mount()` from async worker to add widgets after initial render
- **Widget Testing**: Need test app wrapper for widgets; can't test standalone widget without app context
- **Test App Pattern**: Create minimal test app that mounts widget: `class TestApp(App): def compose(): yield widget`
- **Datetime in Tests**: Use `timedelta()` for creating timestamp sequences instead of manual minute arithmetic
- **Import timedelta**: Remember to import timedelta: `from datetime import timedelta`
- **Pilot Pause**: Use `await pilot.pause()` after calling update methods to let DOM changes propagate
- **Remove Children Async**: `remove_children()` is async; need to wait with pilot.pause() for DOM updates
- **Stock-Only Features**: Sparkline only for stocks; crypto doesn't have intraday data (per PRD)
- **Graceful Fallback**: Show "No data" label when intraday fetch fails instead of showing error
- **Label Text Testing**: Use `str(label.render())` to get text content for assertions
- **Test Coverage Goals**: Achieved 95.86% coverage with comprehensive sparkline and intraday tests
- **Dataclass Imports**: Add new dataclasses to service __init__ exports for clean imports

### VPR-016: Historical Price Data Service
- **File Naming**: Avoid name collisions with existing modules (history_data.py vs history.py)
- **OHLCV Data**: Store full Open-High-Low-Close-Volume data for flexibility in charting
- **Period Mapping**: Map user-friendly periods (1W, 1M, etc.) to yfinance periods (5d, 1mo, etc.)
- **Interval Selection**: Match interval to period (1d for short periods, 1wk for 2Y+, 1mo for MAX)
- **yfinance history()**: Use `stock.history(period=str, interval=str)` for historical data
- **Volume Integer Conversion**: Convert volume to int in list comprehension: `[int(v) for v in hist["Volume"].tolist()]`
- **Stats Calculation**: Create separate function for stats to keep service focused on data fetching
- **Empty Data Handling**: Check both `df is None` and `df.empty` for robustness
- **Period Validation**: Validate period early and return error for invalid periods
- **Comprehensive Testing**: Test all periods, empty data, invalid ticker, network errors, timeout
- **Mock DataFrame**: Use pandas DataFrame with date_range index for realistic test mocks
- **Virtual Environment**: Use `python3 -m venv .venv` and `.venv/bin/pip install -e ".[dev]"` for isolated dev environment
- **Dev Dependencies**: Install with `.[dev]` to get pytest, mypy, ruff, etc.

### VPR-014: Configuration File Support
- **tomllib for TOML**: Use Python 3.11+ built-in `tomllib` for reading TOML files (`import tomllib`)
- **Binary Mode**: TOML files must be opened in binary mode: `open(file, "rb")` for tomllib.load()
- **TOML Structure**: Top-level keys (refresh_interval) must come before or after [tables], not inside them
- **Table Syntax**: Use `[section_name]` for nested dicts in TOML (e.g., `[theme_colors]`)
- **Dataclass with Defaults**: Use `@dataclass` with `field(default_factory=...)` for mutable defaults (dict, list)
- **Post-Init Validation**: Use `__post_init__()` to validate config values after initialization
- **Validation Pattern**: Check types and ranges; log warnings for invalid values; replace with defaults
- **Graceful Fallback**: Return default Config() when file missing, invalid TOML, or read errors occur
- **Config Path**: Use `Path.home() / ".config" / "viper" / "config.toml"` for user config file
- **Partial Config**: Support partial config files - only override specified values, use defaults for rest
- **Dictionary Extraction**: Extract values from TOML dict conditionally: `if "key" in data: config_dict["key"] = data["key"]`
- **Default Watchlist**: Load default watchlist from config and add to WatchlistManager on app init
- **Config in App**: Load config early in __init__() before creating managers to use config values
- **Refresh Interval**: Pass config.refresh_interval to WatchlistPanel instead of hardcoded value
- **Logging Config**: Log loaded config values (refresh_interval) for debugging and transparency
- **Test with tmp_path**: Use pytest's tmp_path fixture to create temporary config files for testing
- **Mock get_config_path**: Use `@patch("viper.config.get_config_path")` to control config file location in tests
- **Test All Paths**: Test missing file, valid full config, partial config, invalid TOML, read errors, validation
- **Invalid Type Testing**: Test that invalid types (string instead of dict) trigger validation and fall back to defaults
- **Empty Config File**: Empty TOML file should load successfully and use all defaults
- **Type Safety**: All config loading code passes mypy --strict with no issues
- **No Breaking Changes**: Config is optional - app works perfectly with default values if no config file exists

### VPR-015: Help Screen and Onboarding
- **ModalScreen**: Use `ModalScreen[None]` from `textual.screen` for modal dialogs that overlay the main app
- **push_screen Pattern**: Call `self.push_screen(screen)` to show a modal screen over current app
- **ModalScreen Dismiss**: Call `self.dismiss()` from within modal screen to close it and return to previous screen
- **on_key Handler**: Override `on_key()` in modal screen to handle key presses (Enter, Escape for dismiss)
- **Key Event Type**: Import `Key` from `textual.events` and use `isinstance(event, Key)` to check event type
- **Screen State Param**: Pass parameters to screen via `__init__()` (e.g., `is_welcome: bool` for different modes)
- **Conditional Content**: Use init params to render different content based on context (welcome vs help)
- **First-Run Detection**: Use flag file pattern (`~/.config/viper/first_run.json`) to detect first app launch
- **Flag File Path**: Helper function `get_first_run_flag_path()` returns path for easy mocking in tests
- **File Existence Check**: `path.exists()` returns False for missing files (indicates first run)
- **Mark Complete**: Create flag file with JSON content to mark first run complete
- **Graceful Failure**: Wrap file operations in try/except and fail silently if can't persist flag
- **on_mount for First Run**: Use `on_mount()` lifecycle method to check first-run and show welcome screen
- **Test with Mock**: Mock `is_first_run` and `mark_first_run_complete` functions in app tests
- **Test Helper Class**: Create test app class that takes modal screen as init param to test modals in isolation
- **Screen Property**: Access current screen with `app.screen` to check if modal is showing
- **isinstance for Screen Type**: Use `isinstance(app.screen, HelpScreen)` to verify correct screen is shown
- **Action Method Testing**: Call action methods directly (`app.action_show_help()`) instead of `pilot.press()` for more reliable tests
- **Modal Screen Testing**: Create minimal test app that pushes screen in on_mount for testing modal widgets
- **Help Content Organization**: Organize help into sections (COMMANDS, KEYBINDINGS, FEATURES) with clear visual hierarchy
- **CSS Sections**: Use classes for styling: `.help-section-title` for headers, `.help-item` for content
- **VerticalScroll in Modal**: Nest VerticalScroll inside modal for scrollable long content
- **Conditional Footer**: Change footer text based on context (welcome: "continue", help: "close")
- **Test Modal Content**: Query widgets by ID in modal screen to verify content is rendered
- **Test Dismiss Behavior**: Verify screen dismisses correctly on Enter and Escape key presses
- **Mock in Context Manager**: Use `with patch()` context manager when mocking in tests for clean teardown
- **Test First-Run Integration**: Test that welcome screen shows on first run and doesn't show on subsequent runs

### VPR-017: Chart Rendering Engine
- **Braille Unicode**: Range U+2800-U+28FF provides 256 patterns (2x4 dots per char) for high-resolution charts
- **Braille Dot Mapping**: Dots 1-3 and 7 map to left column, dots 4-6 and 8 to right column
- **Type Overloading Required**: Use `@overload` for methods that return different types based on input (e.g., list[float] vs list[datetime])
- **Downsampling Min/Max**: When downsampling data, always use original data for min/max to preserve extremes
- **Type Narrowing with Cast**: Use `cast()` and `isinstance()` checks when mypy can't infer types in generic functions
- **Multi-Line String Returns**: When a function returns multi-line strings with `\n`, use `.split("\n")` and `.extend()` instead of `.append()`
- **X-Axis Design**: Create X-axis with two lines: border line (└───) and label line (dates)
- **Block Characters**: Fallback to block chars (▁▂▃▄▅▆▇█) provides 8 vertical levels vs braille's higher resolution
- **Normalization Pattern**: Normalize data to 0-1 range: `(value - min) / (max - min)`, then scale to target resolution
- **Even-Spaced Downsampling**: Use `step = len(data) / target` and `data[int(i * step)]` for simple downsampling
- **Chart Dimensions**: Separate chart rendering area from axes (subtract axis widths from total dimensions)
- **Y-Axis Labels**: Show 3-5 price labels distributed across chart height, right-aligned with │ separator
- **Floating Point Tolerance**: Use epsilon (e.g., 0.011) instead of exact equality for floating point comparisons in tests
- **Test Comprehensiveness**: Include edge cases: empty data, single point, flat line, negative prices, very large/small ranges
- **Type Assertions**: When downcasting union types, add `assert isinstance()` checks to help mypy understand the narrowing
- **Dataclass for Results**: Use dataclasses (RenderedChart) to return multiple related values (lines, width, height, min, max)

### VPR-018: Chart Panel Widget
- **Panel Toggle Pattern**: Use `styles.display = "none"/"block"` to show/hide panels without destroying state
- **Mutual Exclusivity**: When multiple panels can replace quote panel, hide others before showing new one
- **State Flags for Panels**: Track visibility with `_info_panel_visible`, `_chart_panel_visible` flags in app
- **Panel States**: Implement same state pattern as QuotePanel: empty, loading, success, error
- **Widget Initialization**: Pass configuration (e.g., ChartStyle) via widget `__init__`, not after creation
- **Responsive Chart Sizing**: Calculate available dimensions dynamically: `available_height = self.size.height - header_space`
- **Minimum Dimensions**: Always enforce minimum chart size (e.g., 40x10) for readable output
- **Loading with Context**: Show ticker and period in loading message: "Loading chart for AAPL (1M)..."
- **Worker Pattern**: Use `self.run_worker()` to run async tasks (e.g., `chart_panel.load_chart()`) from action methods
- **Stats Display**: Show high, low, and percent change with appropriate color (positive=green, negative=red)
- **Chart Lines**: Use `markup=False` on Labels when rendering chart to preserve unicode characters
- **Ticker Change Handling**: Check if `_current_ticker` matches before rendering fetched data to prevent stale updates
- **Test with Mock fetch**: Use `patch("viper.widgets.chart_panel.fetch_historical_data")` to mock data service
- **Test Multiple Periods**: Verify panel handles all supported periods (1W, 1M, 3M, 6M, 1Y, 5Y, MAX)
- **Test Responsive Behavior**: Test chart renders correctly at different terminal dimensions
- **Container CSS**: Use `padding: 0` for chart container to maximize chart space (unlike info panel with `padding: 1`)
- **Action Keybinding**: Add new action to `BINDINGS` list with tuple: `("c", "toggle_chart", "Toggle Chart")`
- **Widget Export**: Remember to add new widget to `viper/widgets/__init__.py` and `__all__` list

### VPR-019: Timeframe Selection
- **Timeframe Mapping Dict**: Store key-to-period mapping in widget (e.g., `{"1": "1W", "2": "1M"}`) for centralized access
- **Number Key Bindings**: Add numeric keys (1-7) to BINDINGS with descriptive actions: `("1", "timeframe_1", "1W")`
- **Action Method Pattern**: Create individual action methods (`action_timeframe_1`) that delegate to a shared helper
- **Shared Helper Pattern**: Use helper method `_change_chart_timeframe(key)` that checks visibility before acting
- **Conditional Actions**: Only process timeframe changes when chart panel is visible (check `_chart_panel_visible` flag)
- **Get Method for Widget**: Add public method `get_timeframe_for_key(key)` to widget for app to query mappings
- **Change Timeframe Method**: Add `async change_timeframe(period)` method to widget that calls `load_chart()` with new period
- **Timeframe Bar UI**: Display timeframe selector as label with markup showing all options and highlighting active
- **Markup Escaping**: Use `\\[` to escape literal brackets in Rich markup (e.g., `\\[1]` for key indicator)
- **Active Indicator**: Use `[b][cyan]` for active timeframe, `[dim]` for inactive in markup
- **Markup Nesting**: Ensure proper tag nesting: `[b][cyan]...[/cyan][/b]` not `[b][cyan]...[/b][/cyan]`
- **Height Calculation Update**: When adding UI elements (timeframe bar), update available height calculation accordingly
- **Persistence via State**: Timeframe persists naturally via `_current_period` state variable - no special handling needed
- **Avoid Redundant Fetches**: Check if new period equals current period before fetching: `if period != self._current_period`
- **Test All Keys**: Write tests for all 7 timeframe keys (1-7) to verify mapping and functionality
- **Test Invalid Keys**: Test that invalid keys (0, 8, letters) return None from mapping
- **Test Conditional Behavior**: Verify timeframe changes only work when chart panel is visible
- **Test Same Period**: Verify that changing to the same period doesn't trigger a re-fetch
- **Test No Ticker**: Verify that timeframe changes do nothing when no ticker is selected
- **Test UI Display**: Verify timeframe bar displays all periods and highlights the active one correctly
- **Mock Async Methods**: Use `AsyncMock` for mocking `fetch_historical_data` in tests
- **Test Persistence**: Verify that timeframe persists across operations until explicitly changed

### VPR-020: Volume Chart Overlay
- **ANSI Color Codes**: Use raw ANSI codes for colored volume bars: `\033[32m` (green), `\033[31m` (red), `\033[0m` (reset)
- **Block Character Levels**: Use 9-level block character array including space: `[" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]`
- **Volume Normalization**: Normalize volumes to 0-1 range using max volume: `normalized = vol / max_volume`
- **Volume Color Logic**: Green if `close > open`, red otherwise (matches candlestick convention)
- **Separate Render Method**: Create `render_volume_bars()` method that returns list of strings (like chart rendering)
- **Y-Axis Alignment**: Prepend Y-axis padding (e.g., 12 spaces) to volume bars to align with price chart
- **Height Management**: Reserve 3 lines for volume bars, adjust main chart height accordingly: `height - volume_height`
- **Conditional Rendering**: Only render volume bars when `_volume_enabled` flag is True
- **Volume Toggle Method**: Simple toggle method that flips bool flag and calls `_render_content()` to re-render
- **Volume Stats Display**: Add avg volume and last volume (with % of avg) to stats line when volume enabled
- **Volume Ratio Calculation**: `volume_ratio = (last_volume / avg_volume * 100)` for "today vs avg" metric
- **Format Large Numbers**: Use `_format_number(value, 0)` for volumes (no decimals, with commas)
- **Type Overloading for int**: Add `@overload` for `list[int]` to `_downsample` method alongside float/datetime overloads
- **Type Narrowing with isinstance**: Use `isinstance(data[0], int)` to narrow return type in generic downsample function
- **Multiple Overload Pattern**: When adding new types to generic methods, add overload AND update implementation signature
- **Volume Empty Check**: Check `len(data.volumes) > 0` before attempting to render volume bars
- **Conditional Key Bindings**: Volume toggle ('v' key) only works when chart panel is visible (check `_chart_panel_visible`)
- **Test Color Codes**: Test for presence of ANSI codes (`\033[32m` or `\033[31m`) in volume output
- **Test Block Characters**: Verify volume line contains at least one block character from the set
- **Test Empty Volumes**: Handle edge case of empty volumes list gracefully (return empty list)
- **Test Zero Volumes**: Handle all-zero volumes without division by zero (set `max_volume = 1` if zero)
- **Test Volume Toggle State**: Test both `is_volume_enabled()` method and `_volume_enabled` flag
- **Test Volume Downsampling**: Verify that volume bars downsample correctly when data points exceed width
- **Test Volume with Stats**: Verify volume stats (avg, last, ratio) appear in stats line when enabled
- **Test Volume Persistence**: Volume toggle state persists across chart reloads until explicitly changed
### VPR-021: Crypto Historical Charts
- **Auto-Detection Pattern**: Use simple lookup in SYMBOL_TO_ID mapping to determine crypto vs stock ticker
- **Multi-Source Architecture**: Route to different data sources based on asset type detection (yfinance for stocks, CoinGecko for crypto)
- **CoinGecko market_chart Endpoint**: Use `/coins/{id}/market_chart?vs_currency=usd&days=N` for historical data
- **CoinGecko Days Mapping**: Map user periods to days parameter: 1W=7, 1M=30, 3M=90, 6M=180, 1Y=365, 2Y=730, 5Y=1825, MAX=max
- **CoinGecko Response Format**: Returns `{"prices": [[timestamp_ms, price], ...], "total_volumes": [[timestamp_ms, volume], ...]}`
- **Timestamp Conversion**: CoinGecko uses millisecond timestamps, convert with `datetime.fromtimestamp(ms / 1000)`
- **OHLC for Crypto**: CoinGecko market_chart doesn't provide OHLC, use price for all fields (acceptable for charting)
- **Volume Padding**: If fewer volume points than price points, pad with zeros: `while len(volumes) < len(prices): volumes.append(0)`
- **Interval Heuristic**: Calculate interval label from average time between points: <1h="5m", <24h="1h", else="1d"
- **Rate Limit Retry Pattern**: Reuse exponential backoff pattern from crypto.py: check for 429, wait 2^attempt seconds
- **Rate Limit Error Detection**: Check for "rate limit" in error message (case-insensitive) to trigger retry logic
- **Retry Loop Exit**: Return immediately on success, only retry on rate limit errors, exhaust retries before returning error
- **httpx AsyncClient**: Use `async with httpx.AsyncClient() as client:` for async HTTP requests
- **httpx Error Handling**: Catch TimeoutError, ConnectError, RequestError separately for specific error messages
- **API Error Codes**: Handle 429 (rate limit), 404 (not found), and other status codes with descriptive messages
- **respx Mocking**: Use `@respx.mock` decorator and `respx.get().mock(return_value=Response())` for HTTP mocking
- **respx Side Effects**: Use `route.side_effect = [Response1, Response2, ...]` to simulate retry scenarios
- **respx Call Counting**: Use `route.call_count` to verify number of HTTP calls made during retries
- **Mock Response Helper**: Create `create_mock_coingecko_response()` helper that generates realistic timestamp/price/volume arrays
- **Test All Periods**: Test all 7 periods (1W-MAX) with parameterized mapping to verify correct days parameter
- **Test Rate Limit Success**: Mock 2 failures (429) then success to verify retry logic works correctly
- **Test Rate Limit Exhaustion**: Mock all attempts as 429 to verify max_retries is respected and error returned
- **Test Empty Data**: Mock response with empty prices array to verify graceful error handling
- **Test Malformed Response**: Mock response with invalid JSON structure to verify parsing error handling
- **Test Volume Padding**: Mock response with fewer volumes than prices to verify padding logic works
- **Test Timestamp Conversion**: Verify millisecond timestamps are correctly converted to datetime objects
- **Test Timezone Awareness**: Use flexible assertions for dates (year in [2023, 2024]) to handle timezone differences
- **Test Auto-Routing**: Verify BTC/ETH route to CoinGecko while AAPL routes to yfinance automatically
- **Test Case Insensitivity**: Verify lowercase crypto symbols ("btc") are properly normalized and work correctly
- **Test Coverage**: Added 20 new tests for crypto functionality, total 38 tests, all passing
- **Module Coverage**: Achieved 91% coverage on history_data.py (exceeds 90% threshold)
- **Import Pattern**: Import SYMBOL_TO_ID from crypto.py to reuse existing crypto symbol mapping
- **Function Signature Extension**: Add `max_retries` parameter to `fetch_historical_data()` for crypto retry logic
- **Private Helper Functions**: Name internal functions with leading underscore: `_is_crypto_ticker()`, `_fetch_crypto_historical()`
- **Result Type Consistency**: All fetch functions return `HistoricalResult = HistoricalData | HistoricalDataError` for consistency
- **Error Message Clarity**: Include ticker symbol and descriptive message in all error results for debugging

### VPR-022: News Data Service
- **feedparser Library**: Use feedparser for RSS parsing - mature, well-tested library that handles edge cases
- **Type Ignore for Untyped Imports**: Add `# type: ignore[import-untyped]` comment to feedparser import (no type stubs)
- **Yahoo Finance RSS Feed**: Use `https://feeds.finance.yahoo.com/rss/2.0/headline?s={TICKER}` endpoint
- **RSS Feed Structure**: Standard RSS 2.0 with items containing title, link, description (summary), and pubDate
- **In-Memory Caching**: Use module-level dict for caching: `_cache: dict[str, tuple[datetime, NewsResult]]`
- **Cache TTL Pattern**: Store (timestamp, result) tuples, check `datetime.now() - cached_time < timedelta(seconds=TTL)`
- **Cache Both Successes and Errors**: Cache error results to avoid repeated failing requests
- **Executor Pattern**: Use `loop.run_in_executor(None, sync_func, args)` for blocking feedparser operations
- **Two-Tier Architecture**: Async wrapper (`fetch_news`) calls sync helper (`_fetch_news_sync`) in executor
- **httpx Sync Client**: Use `with httpx.Client(timeout=timeout) as client:` for synchronous RSS fetch
- **raise_for_status()**: Call after HTTP request to convert 4xx/5xx responses to HTTPStatusError exceptions
- **feedparser.parse()**: Parse response.content (bytes), returns dict with .entries list and .bozo flag
- **Bozo Detection**: Check `feed.bozo and isinstance(feed.get("bozo_exception"), Exception)` for parsing errors
- **Entry Attributes**: Use `hasattr(entry, "field")` checks since RSS fields are optional
- **Published Date Parsing**: Use `time.mktime(entry.published_parsed)` to convert time.struct_time to timestamp
- **Date Parse Fallbacks**: Wrap in try/except, fall back to `datetime.now()` if parsing fails
- **Source Extraction**: Parse source from title using `title.rsplit(" - ", 1)` pattern (Yahoo uses "Title - Source" format)
- **Summary Field**: Map RSS description to summary field (optional, may be None)
- **Empty Feed Handling**: Return NewsError when `len(items) == 0` after parsing
- **httpx Exception Hierarchy**: TimeoutException, ConnectError, HTTPStatusError, RequestError - handle each separately
- **404 Special Handling**: Check `e.response.status_code == 404` for "No news feed available" message
- **Generic Exception Catch**: Final `except Exception` for unexpected errors with "Unexpected error" message
- **Clear Cache Function**: Provide `clear_news_cache(ticker)` function to clear specific ticker or all cache
- **Global Keyword**: Use `global _cache` when reassigning module-level cache dict
- **Ticker Normalization**: Always `.upper().strip()` ticker symbols for consistency
- **URL in NewsItem**: Store as empty string if not available rather than None for consistency
- **Test RSS Helpers**: Create `create_mock_rss_feed()`, `create_empty_rss_feed()` helpers for realistic test data
- **Mock HTTP with respx**: Use `@respx.mock` decorator and `respx.get(url).mock(return_value=Response(...))` pattern
- **Mock Date Handling**: Use fixed dates in mock RSS (Mon, 01 Jan 2024) to make assertions predictable
- **Test All Error Paths**: Timeout, connection error, 404, 500, request error, parse error, empty feed, etc.
- **Test Cache Lifecycle**: Test cache hit, cache miss, cache expiration, cache clearing (all and specific)
- **Test Edge Cases**: Missing fields (summary, pubDate, source), invalid date strings, malformed RSS
- **Test Generic Exception**: Mock executor or feedparser to raise RuntimeError to test exception handling
- **Test Time.mktime Exception**: Mock `time.mktime` to raise ValueError to test date parsing exception path
- **Coverage Goal**: Achieved 100% coverage with 27 comprehensive tests
- **Test Organization**: Group tests by class: NewsItem, NewsError, FetchNews, ClearCache, ParsingEdgeCases
- **Mock Internal Functions**: Use `patch("asyncio.get_event_loop")` or `patch("feedparser.parse")` to trigger edge cases
- **Test Error Caching**: Verify that error results are also cached to prevent repeated failed requests
- **Test Ticker Normalization**: Verify "  aapl  " normalizes to "AAPL" and works correctly
- **Result Type Pattern**: Use `list[NewsItem] | NewsError` union type for fetch_news return value
- **Optional Fields**: Use `Optional[str]` for summary field in NewsItem dataclass
- **Time-Based Tests**: Use tolerance for time comparisons: `(datetime.now() - result).total_seconds() < 60`
- **Multiple Source Support**: Architecture supports easy addition of other news sources (Google News, etc.)

### VPR-028: Fix News Service with yfinance Built-in News
- **yfinance .news Attribute**: Use `ticker.news` property to get news directly from yfinance (no external API needed)
- **No RSS Parsing Needed**: yfinance returns structured JSON, eliminating need for feedparser library
- **Nested Dict Structure**: News data is nested: `item["content"]["title"]`, `item["content"]["summary"]`, etc.
- **Safe Nested Access Helper**: Create `_safe_get_nested(data, keys, default)` helper for navigating nested dicts safely
- **URL Fallback Pattern**: Try `content.previewUrl` first, fall back to `content.canonicalUrl.url` if not available
- **Provider Display Name**: Extract source from `content.provider.displayName`, default to "Yahoo Finance"
- **ISO Date Format**: yfinance uses ISO format strings like "2024-01-15T10:30:00Z", parse with `datetime.fromisoformat()`
- **Z Suffix Handling**: Replace 'Z' with '+00:00' for proper timezone parsing: `pub_date_str.replace("Z", "+00:00")`
- **Malformed Item Skipping**: Validate `"content"` key exists and is dict; skip items without valid title
- **Type Validation**: Check `isinstance(value, expected_type)` for all extracted values to handle malformed data
- **Continue Pattern**: Use `continue` in loop to skip malformed items rather than creating default items
- **Empty Check After Parsing**: Return error if `len(items) == 0` after filtering malformed items (not just empty input)
- **Remove Unused Dependency**: Remove feedparser from pyproject.toml dependencies list
- **Keep httpx**: httpx is still used by crypto.py, don't remove it
- **Mock yfinance Ticker**: Use `patch("yfinance.Ticker")` with `MagicMock()` that has `.news` attribute
- **Mock News Structure**: Create helpers like `create_mock_yfinance_news()` that return list of content dicts
- **Test Malformed Items**: Verify that items without "content" key or without valid title are skipped
- **Test All-Malformed**: Verify that if all items are malformed, returns NewsError (not empty list)
- **Test canonicalUrl Fallback**: Test URL extraction when previewUrl missing but canonicalUrl.url present
- **Remove respx Tests**: Since no HTTP requests anymore, remove `@respx.mock` decorators from news tests
- **Simpler Mocking**: yfinance mocking is simpler than RSS mocking - just set `.news` attribute to list
- **Coverage Improvement**: Improved news.py from 83% to 93% coverage with comprehensive edge case tests
- **Test Helper Functions**: Add dedicated test class for `_safe_get_nested()` helper function
- **Backward Compatibility**: Maintained exact same NewsItem interface so no changes needed to news panel widget
- **Unified Data Source**: Now using yfinance for stocks, crypto, AND news - single dependency
- **No Rate Limits**: yfinance news has same moderate rate limits as ticker data, avoids CoinGecko-style aggressive limits

### VPR-029: Unify crypto data source using yfinance
- **yfinance Crypto Format**: Use SYMBOL-USD format (BTC-USD, ETH-USD) for crypto pairs via yfinance
- **Auto-conversion Pattern**: Accept both "BTC" and "BTC-USD"; auto-convert common symbols to -USD pairs
- **Symbol Mapping Update**: Renamed SYMBOL_TO_ID to SYMBOL_TO_PAIR with values like "BTC-USD" instead of "bitcoin"
- **Legacy Alias**: Keep `SYMBOL_TO_ID = SYMBOL_TO_PAIR` for backward compatibility with history_data.py
- **Remove CoinGecko**: Completely replaced httpx/CoinGecko with yfinance - no HTTP mocking needed
- **asyncio.to_thread**: Use `await asyncio.to_thread(sync_function)` to run synchronous yfinance calls without blocking
- **yfinance fast_info**: Access via `.get()` method for quote data, returns dict-like object
- **yfinance .info**: Full info dict with marketCap, volume24Hr, regularMarketVolume, longName, name
- **24h Change Calculation**: Use `.history(period="2d")` to get 2 days of data, calculate percentage change
- **Handle Empty History**: Check `hist.empty or len(hist) < 2` before calculating change; default to 0.0%
- **Division by Zero**: Check `if previous_close > 0` before calculating percentage change
- **Optional Fields**: Use `.get(key, default)` for optional fields; market_cap and volume may be None
- **Name Extraction**: Try `longName` first, fallback to `name` from .info dict
- **Mock yfinance.Ticker**: Patch "yfinance.Ticker" and return MagicMock with fast_info, info, history attrs
- **Mock DataFrame**: Use `pd.DataFrame` with Close column and `pd.date_range` index for realistic mocks
- **Test Both Formats**: Test both "BTC" (auto-convert) and "BTC-USD" (explicit) formats
- **Test Edge Cases**: Empty history, single data point, zero previous close, missing optional fields
- **Simpler Testing**: yfinance mocking is simpler than CoinGecko - no HTTP routes, just object mocking
- **No Retry Logic**: yfinance doesn't have same rate limit issues as CoinGecko - removed retry/backoff
- **Unified API**: Stock and crypto now use identical yfinance code path - single data source
- **Test Coverage**: Achieved 93% coverage on crypto.py with 30 comprehensive tests
- **Remove respx**: No longer need respx or httpx for crypto tests - pure object mocking sufficient

### VPR-030: Unify crypto historical data with yfinance
- **Single Data Source**: Completely unified on yfinance - removed all CoinGecko historical data code
- **Import Update**: Changed from `SYMBOL_TO_ID` to `SYMBOL_TO_PAIR` import (legacy alias exists for compatibility)
- **Crypto Detection Enhanced**: Updated `_is_crypto_ticker()` to check both SYMBOL_TO_PAIR and -USD suffix
- **Auto-conversion in fetch_historical_data**: Crypto symbols auto-converted to SYMBOL-USD before yfinance call
- **Handle Explicit Suffix**: If symbol already ends with -USD, use as-is without double conversion
- **Fallback Pattern**: Use `SYMBOL_TO_PAIR.get(symbol, f"{symbol}-USD")` for unmapped crypto symbols
- **Unified Code Path**: Both stocks and crypto now use `_fetch_stock_historical()` - no separate crypto function
- **Removed Functions**: Deleted `_fetch_crypto_historical()`, `_fetch_crypto_with_timeout()`, `_parse_coingecko_chart()`
- **Removed Imports**: Removed `httpx` import and `COINGECKO_DAYS_MAP` mapping dict
- **Docstring Updates**: Updated all docstrings to reflect yfinance-only approach
- **Test Conversion**: Replaced all respx HTTP mocks with yfinance Ticker mocks
- **Removed respx Import**: No longer need `respx` or `httpx.Response` imports in test_history_data.py
- **Simplified Test Helpers**: Removed `create_mock_coingecko_response()` helper function
- **New Test Coverage**: Added test for explicit -USD suffix handling
- **Test Ticker Assertions**: Updated assertions to expect "BTC-USD" ticker instead of "BTC"
- **yfinance Call Verification**: Tests verify yfinance.Ticker called with correct converted symbol (e.g., "BTC-USD")
- **Same OHLCV Data**: yfinance provides full OHLCV data for crypto (unlike CoinGecko which only had Close)
- **Consistent Intervals**: Crypto historical data now uses same interval logic as stocks (1d, 1wk, 1mo)
- **No Rate Limits**: Eliminated CoinGecko rate limiting issues - yfinance has no aggressive rate limits
- **No Retry Logic Needed**: Removed exponential backoff and retry logic - not needed with yfinance
- **Cleaner Codebase**: Reduced history_data.py from 473 lines to ~240 lines by removing CoinGecko code
- **All Tests Pass**: 557 tests passing with 90.39% overall coverage
- **Type Safety Maintained**: mypy --strict passes with no issues after refactoring

### VPR-031: Fix volume bar alignment with price chart
- **Root Cause**: Price chart upsamples data when `len(prices) < max_data_points * 0.6` but volume bars don't follow
- **max_data_points**: For BRAILLE charts, `max_data_points = chart_width * 2` (each char holds 2 data points)
- **Upsampling Trigger**: When data < 60% of max_data_points, price chart upsamples to max_data_points
- **Linear Interpolation**: Upsampling uses linear interpolation between existing data points
- **Solution Pattern**: Track interpolation in RenderedChart, pass to volume renderer for matching
- **RenderedChart Field**: Added `interpolated_count: int = 0` field (0 = no interpolation, >0 = upsampled count)
- **Set interpolated_count**: Set to max_data_points when upsampling occurs in _render_braille
- **Block Style**: _render_block doesn't interpolate, so always returns `interpolated_count=0`
- **New Method _upsample()**: Created helper method matching price interpolation logic for volumes
- **Separate List Types**: Use `upsampled_int: list[int]` and `upsampled_float: list[float]` for type safety
- **Type Narrowing**: Mypy requires separate lists to avoid "Argument 1 to append has incompatible type" error
- **render_volume_bars Parameter**: Added `interpolated_count: int = 0` parameter for alignment info
- **Volume Upsampling**: If `interpolated_count > 0`, upsample volumes/opens/closes BEFORE downsampling
- **Order Matters**: Upsample first (to match price data), THEN downsample (to fit chart width)
- **chart_panel Integration**: Pass `rendered.interpolated_count` to `render_volume_bars()` call
- **Test Coverage**: Added 5 new tests for interpolation tracking and volume alignment
- **Test interpolated_count_returned**: Verifies small dataset triggers upsampling and returns correct count
- **Test no_interpolation_with_sufficient_data**: Verifies large dataset doesn't trigger upsampling (count=0)
- **Test volume_alignment_with_interpolation**: Verifies volume bars render correctly with interpolation info
- **Test volume_alignment_without_interpolation**: Verifies backward compatibility with no interpolation
- **Test volume_upsampling_edge_cases**: Tests single data point and 2-point upsampling edge cases
- **Edge Case: 1 Point**: Upsampling from single data point creates flat line (all same value)
- **Edge Case: 2 Points**: Linear interpolation between 2 points creates smooth gradient
- **All Tests Pass**: 562 tests passing with 90.33% overall coverage after changes
- **Type Safety**: mypy --strict passes with no issues on chart_renderer.py and chart_panel.py
- **Backward Compatible**: Old volume render calls still work (interpolated_count defaults to 0)
- **Performance**: No performance impact - upsampling only happens when data is sparse
- **Visual Fix**: Volume bars now perfectly align with price chart regardless of data density

### VPR-032: Enable Volume Bars by Default
- **Config Default Change**: Changed `volume_enabled: bool = False` to `True` in config.py
- **Config Validation Update**: Updated validation error message from "default False" to "default True"
- **ChartPanel Constructor**: Added `volume_enabled: bool = True` parameter to `__init__`
- **Constructor Default**: Parameter defaults to True, maintaining new behavior even without config
- **App Integration**: Pass `config.volume_enabled` to ChartPanel in app.py compose()
- **Status Indicator**: Added volume status to chart header: `[Vol: ON]` or `[Vol: OFF]`
- **Header Format**: `f"{data.ticker} - {data.period} Chart  [{volume_status}]"`
- **Help Screen Updates**: Removed "(experimental)" from volume toggle description
- **Help Text Change**: Changed "disabled by default" to "enabled by default"
- **Help Chart Section**: Updated to say "enabled by default" and removed CoinGecko reference
- **Test Updates**: Changed all volume default assertions from False to True
- **test_chart_panel_volume_toggle**: Reversed toggle order - start enabled, toggle off, toggle on
- **test_chart_panel_volume_bars_displayed**: Updated comments - volume enabled by default
- **test_chart_panel_volume_stats_displayed**: Removed redundant toggle - already enabled
- **test_chart_panel_volume_empty_data**: Removed redundant toggle - already enabled
- **test_config Default Test**: Changed assertion from `assert config.volume_enabled is False` to True
- **test_config Invalid Test**: Changed invalid type correction from False to True
- **New Test: test_volume_enabled_false**: Added test to verify config can override to False
- **New Test: test_chart_panel_volume_disabled_via_config**: Tests ChartPanel(volume_enabled=False)
- **New Test: test_chart_panel_volume_status_indicator**: Tests [Vol: ON]/[Vol: OFF] in header
- **Config Override Works**: Users can set `volume_enabled = false` in config.toml to disable
- **Backward Compatible**: Existing configs without volume_enabled get new True default
- **All Tests Pass**: 565 tests passing with 90.34% overall coverage
- **mypy --strict Clean**: No type errors after adding volume_enabled parameter
- **User Experience**: Volume adds context to price movements, worth showing by default
- **VPR-031 Dependency**: Only enabled after VPR-031 fixed alignment issues

### VPR-033: Simple Moving Average (SMA) indicator service
- **New Service Module**: Created `viper/services/indicators.py` for technical indicator calculations
- **Pure Functions**: All indicator functions are pure - no external dependencies, just math
- **Return Type**: Use `list[float | None]` to handle cases where calculation isn't possible
- **None for Initial Values**: Return None for first (period-1) values where SMA can't be calculated
- **SMA Formula**: `sum(prices[i-period+1:i+1]) / period` for each position i
- **Window Slicing**: Use `prices[i - period + 1 : i + 1]` to get last N prices
- **Period Validation**: Raise ValueError for period <= 0
- **Empty List Handling**: Return empty list when input is empty list
- **Period 1 Edge Case**: SMA with period=1 returns original prices (identity function)
- **Insufficient Data**: When `len(prices) < period`, all values are None
- **Exact Period Size**: When `len(prices) == period`, only last value has SMA
- **Length Preservation**: Output list always has same length as input list
- **None Count Pattern**: Number of None values always equals `period - 1`
- **Test Coverage**: 16 comprehensive tests covering all edge cases
- **Real World Test**: Include test with realistic stock price data (AAPL-like)
- **Flat Prices Test**: SMA of constant prices equals that constant
- **Volatile Prices Test**: SMA smooths price swings (alternating high/low)
- **Common Periods Tested**: 20, 50, 200 day periods (industry standard)
- **Type Safety**: mypy --strict validates with no issues on union type `float | None`
- **pytest.approx**: Use for float comparisons in tests (e.g., `pytest.approx(152.2, abs=0.01)`)
- **Docstring Examples**: Include examples in docstring showing expected behavior
- **Module Docstring**: Explain pattern - all functions return None where calc not possible
- **Foundation for Indicators**: This is foundation for EMA, RSI, MACD, etc.
- **No External Dependencies**: Pure Python, no numpy/pandas needed for calculations
- **Performance**: Simple arithmetic, O(n) complexity for n prices
- **All Tests Pass**: 581 tests passing (added 16 new tests)
- **Coverage Maintained**: 90.40% overall coverage (indicators.py at 100%)
- **mypy Clean**: No type errors with --strict flag

### VPR-034: Exponential Moving Average (EMA) indicator service
- **EMA Formula**: `k = 2/(period+1)`, then `EMA = (Price * k) + (EMA_prev * (1-k))`
- **Smoothing Factor**: Calculate once at function start: `k = 2.0 / (period + 1)`
- **First EMA Value**: Use SMA of first `period` prices as the initial EMA value
- **Recursive Calculation**: Each subsequent EMA depends on previous EMA value
- **Three-Branch Logic**: Handle three cases in loop: (1) insufficient data (None), (2) first value (SMA), (3) subsequent values (EMA formula)
- **i == period - 1**: This is the index where first EMA is calculated (using SMA)
- **Window for First SMA**: Use `prices[:period]` to get first N prices for initial SMA
- **State Tracking**: Reference `result[i-1]` to get previous EMA for current calculation
- **Defensive None Check**: Check if `prev_ema is None` even though it shouldn't happen (type safety)
- **None Count Invariant**: Same as SMA - number of None values always equals `period - 1`
- **Return Type Consistency**: Same as SMA - `list[float | None]` for uniform indicator interface
- **Period 1 Edge Case**: With period=1, k=1.0, so EMA equals current price (same as SMA)
- **Common Periods**: 12 (MACD fast), 26 (MACD slow), 50 (trend indicator)
- **EMA vs SMA Behavior**: EMA reacts faster to price changes (more weight on recent prices)
- **Test Pattern Reuse**: Mirror SMA test structure - basic, periods, edge cases, real world
- **Comparison Test**: Test that EMA > SMA after price jump (EMA reacts faster)
- **Monotonicity Tests**: Verify EMA increases with upward trend, decreases with downward trend
- **Convergence Behavior**: EMA follows price trends but with smoothing (exponential weighting)
- **Known Calculation Test**: Hand-calculate example with period=2, k=0.6667 to verify formula
- **Smoothing Factor Test**: Dedicated test to verify k is correctly applied in formula
- **Type Ignore Cleanup**: Remove `# type: ignore` comments if mypy doesn't need them (avoid unused-ignore errors)
- **Assert Comparison Pattern**: After asserting `is not None`, can directly compare values
- **Documentation**: Include formula in docstring with example calculation
- **All Tests Pass**: 601 tests passing (added 20 new EMA tests)
- **Coverage Maintained**: 90.45% overall coverage (indicators.py at 97%)
- **mypy Clean**: No type errors with --strict flag

### VPR-035: Chart renderer support for overlay lines
- **New Dataclass: OverlayData**: Created to encapsulate overlay information (values, color, name)
- **OverlayData Fields**: `values: list[float | None]`, `color: str` (ANSI code), `name: str` (legend name)
- **None Values in Overlay**: Use None to indicate no data at that position (don't render)
- **Added overlays Parameter**: Added to `render()`, `_render_braille()`, `_render_block()` methods
- **Optional Parameter**: `overlays: list[OverlayData] | None = None` for backward compatibility
- **Block Style Behavior**: Block style ignores overlays (not supported, only works with braille)
- **Apply Order**: Overlays applied AFTER main chart rendered, BEFORE Y-axis added
- **_apply_overlays_braille Method**: Core method that processes overlay list and applies to chart
- **Grid Conversion**: Convert chart lines to 2D mutable grid for overlay application
- **Same Interpolation Logic**: Overlays follow same interpolation/downsampling as main price chart
- **Interpolation Detection**: If `interpolated_count > 0`, apply same upsampling to overlay data
- **Upsampling Overlays**: Use same linear interpolation formula as price chart
- **None Handling in Interpolation**: Don't interpolate across None values (preserve gaps)
- **Type Annotation Required**: `upsampled_overlay: list[float | None] = []` to satisfy mypy
- **Type Narrowing Pattern**: Extract values, assert not None, then perform math operations
- **Downsampling Overlays**: Create `_downsample_overlay()` helper that preserves None values
- **Scaling Overlays**: Use same min_price/max_price as main chart for consistent scaling
- **Flat Chart Check**: Skip overlay if price_range == 0 (can't scale overlay on flat chart)
- **Vertical Positions**: Same as main chart - `chart_height * 4` (4 dots per braille row)
- **Scaled Overlay Type**: `scaled_overlay: list[int | None] = []` for scaled vertical positions
- **Overlay Character Pattern**: Use `_get_overlay_braille_char()` with simpler dot pattern
- **Simpler Dots**: Overlays use single dots (dots 7 and 8) instead of full vertical lines
- **Visual Distinction**: Simpler pattern makes overlays visually distinct from main price chart
- **Color Application**: Wrap overlay character in ANSI color codes: `f"{color}{char}{reset}"`
- **ANSI Reset Code**: Always append `\033[0m` after colored character
- **Target Row Logic**: Handle three cases - both rows available, left only, right only
- **Skip Both None**: If both left_row and right_row are None, continue to next iteration
- **Bounds Checking**: Check `0 <= target_row < chart_height` before applying to grid
- **Grid Update**: Replace character at `grid[target_row][char_idx]` with colored overlay char
- **Multiple Overlays**: Process each overlay in sequence, all applied to same grid
- **Overlay Stacking**: Later overlays can overwrite earlier ones at same position
- **Grid to String**: After all overlays applied, convert grid back to strings with `"".join(line)`
- **Test Coverage**: Added 14 comprehensive overlay tests in TestOverlayRendering class
- **test_single_overlay_basic**: Verifies basic overlay rendering with color codes
- **test_multiple_overlays**: Tests two overlays with different colors (cyan, magenta)
- **test_overlay_with_all_none_values**: Tests overlay with all None values (no crash)
- **test_overlay_none_handling**: Tests gaps in overlay data (None in middle)
- **test_overlay_alignment_with_interpolation**: Verifies overlay aligns when chart interpolated
- **test_overlay_downsampling**: Tests overlay with large dataset (more than chart width)
- **test_overlay_flat_price_chart**: Tests overlay on flat chart (price_range == 0)
- **test_overlay_with_empty_overlays_list**: Tests empty overlay list
- **test_overlay_no_overlays_parameter**: Tests backward compatibility (no overlays param)
- **test_overlay_block_style_ignores_overlays**: Verifies block style ignores overlays
- **test_overlay_with_y_axis**: Tests overlay works with Y-axis enabled
- **test_overlay_values_outside_price_range**: Tests overlay values beyond price range
- **Backward Compatible**: Existing code works without overlays parameter
- **All Tests Pass**: 613 tests passing (added 14 new overlay tests)
- **Coverage Maintained**: 90.34% overall coverage (chart_renderer.py at 94%)
- **mypy --strict Clean**: No type errors after type annotations and narrowing fixes

### VPR-036: Moving average display on chart
- **MA Cycle State**: Added `_ma_mode: str` with cycle: "off" -> "sma20" -> "sma50" -> "both" -> "off"
- **MA Caching**: Store calculated MAs in `_sma20` and `_sma50` attributes (avoid recalculation on toggles)
- **Calculate on Load**: Call `_calculate_moving_averages()` when chart loads, not on every toggle
- **Conditional Calculation**: Only calculate SMA20 if `len(prices) >= 20`, SMA50 if `len(prices) >= 50`
- **Cache as None**: Set to None when insufficient data (prevents AttributeError on access)
- **Cycle Method**: `cycle_ma_display()` cycles through modes and triggers re-render
- **Getter Method**: `get_ma_mode()` returns current mode for testing/debugging
- **Overlay Building**: Build `list[OverlayData]` based on current `_ma_mode` before render
- **Cyan for SMA20**: Use ANSI color `\033[36m` (cyan) for SMA20 overlay
- **Magenta for SMA50**: Use ANSI color `\033[35m` (magenta) for SMA50 overlay
- **Conditional Overlay List**: Only add to overlays list if mode includes that MA and MA is not None
- **Pass to Renderer**: Pass overlays list to `render()` method, or None if empty list
- **MA Legend in Header**: Add MA values to chart header when MA mode is active
- **Reverse Iteration for Latest**: Use `next((v for v in reversed(self._sma20) if v is not None), None)` to get last non-None value
- **Format Legend**: Format as "SMA20: $123.45" with 2 decimal places
- **Append to Header**: Concatenate legend to existing header text with spacing
- **Both MAs Legend**: Show both "SMA20: $X" and "SMA50: $Y" when in "both" mode
- **Keybinding Added**: Added "m" key to app.py BINDINGS list with "Cycle MA" description
- **Action Handler**: `action_cycle_ma()` calls `chart_panel.cycle_ma_display()` when chart visible
- **Help Screen Updated**: Added "m" key to keybindings section with full description
- **Help Charts Section**: Added explanation in CHARTS section about MA cycling
- **News Help Updated**: Removed outdated warning about broken news, replaced with yfinance note
- **Test Pattern**: Follow existing volume toggle test patterns for MA tests
- **Test Full Cycle**: Test complete cycle through all 4 modes (off/sma20/sma50/both/off)
- **Test Legend Display**: Verify MA values appear in header with "$" formatting
- **Test Insufficient Data**: Verify graceful handling when data < 20 or < 50 points
- **Test Calculation on Load**: Verify MAs calculated when show_chart() called
- **Test Cached Values**: Verify MAs are cached (same object after multiple toggles)
- **Test Overlay Rendering**: Verify overlay data is created when in MA modes
- **Header Query Pattern**: Use `[label for label in labels if "Chart" in str(label.render())]`
- **Assert Pattern**: Use `any("SMA20" in str(label.render()) for label in header_labels)`
- **None Check in Tests**: Check both that list is None AND that no legend appears
- **8 New Tests**: Added comprehensive MA tests covering all aspects of feature
- **All Tests Pass**: 620 tests passing (added 8 new MA tests)
- **Coverage Maintained**: 90.36% overall coverage (chart_panel.py at 98%)
- **mypy --strict Clean**: No type errors after implementation
- **Import Pattern**: Import OverlayData from chart_renderer along with other types
- **Import Indicators**: Import calculate_sma from services.indicators module

### VPR-037: Relative Strength Index (RSI) indicator service
- **RSI Formula**: RSI = 100 - (100 / (1 + RS)) where RS = Average Gain / Average Loss
- **Wilder's Smoothing**: Use Wilder's smoothing method, NOT simple moving average for gains/losses
- **First Average**: First avg = sum(gains/losses over period) / period (simple average)
- **Subsequent Averages**: ((previous avg * (period-1)) + current value) / period (Wilder's smoothing)
- **Default Period 14**: RSI uses period=14 by default (industry standard)
- **Return Type**: Use `list[float | None]` matching SMA/EMA pattern
- **None Count**: RSI returns `period` None values (not period-1 like MA)
- **Reason for Period Nones**: Need period+1 prices to calculate first RSI (period deltas, then period for first avg)
- **Price Deltas**: Calculate deltas first: `delta = prices[i] - prices[i-1]` for all prices
- **Separate Gains/Losses**: gains = max(delta, 0.0), losses = abs(min(delta, 0.0))
- **Initial Averages**: Calculate avg_gain and avg_loss from first `period` deltas using simple average
- **First RSI Calculation**: Use initial averages to calculate first RSI at index `period` (not period-1)
- **Division by Zero**: Check if avg_loss == 0.0, return RSI = 100.0 (no losses = infinite RS)
- **No Gains Case**: If avg_gain == 0.0 (all losses), RS = 0, RSI = 100 - (100/1) = 0
- **Flat Prices Edge Case**: All same prices means all deltas = 0, avg_gain and avg_loss both 0, triggers RSI = 100
- **Update State Variables**: After calculating each RSI, update avg_gain and avg_loss for next iteration
- **Smoothing Loop**: Loop from `period` to `len(deltas)` for subsequent RSI calculations
- **Range Invariant**: RSI always in [0, 100] range - validate in tests
- **Overbought**: RSI > 70 indicates overbought (strong upward momentum)
- **Oversold**: RSI < 30 indicates oversold (strong downward momentum)
- **Test All Gains**: Steadily increasing prices should yield RSI = 100
- **Test All Losses**: Steadily decreasing prices should yield RSI = 0
- **Test Alternating**: Mixed gains/losses should yield RSI between 0 and 100
- **Edge Case Tests**: Empty list, single value, insufficient data (< period+1 prices)
- **Period Validation**: Raise ValueError if period <= 0
- **Real World Test**: Test with realistic stock prices with mixed gains/losses
- **Wilder's Smoothing Test**: Verify consecutive RSI values are smooth (not wildly different)
- **Small/Large Periods**: Test with period=7 (short-term) and period=21 (long-term)
- **Length Matches Input**: Output list always same length as input, regardless of period
- **None Count Test**: Verify first `period` values are None (not period-1)
- **24 Comprehensive Tests**: Added extensive test coverage for all RSI behaviors
- **All 641 Tests Pass**: Added 24 new RSI tests, all existing tests still pass
- **Coverage 90.51%**: Overall coverage maintained above 90% threshold
- **indicators.py 99% Coverage**: Only one defensive branch unreachable (EMA prev_ema None check)
- **mypy --strict Clean**: No type errors with proper return type annotations
- **Test Import**: Added calculate_rsi to imports in test_indicators.py
- **Removed Unused Ignores**: Removed `# type: ignore[operator]` comments that mypy didn't need
- **Foundation for VPR-038**: RSI calculation ready for sub-panel visualization implementation

### VPR-038: Sub-panel framework for indicators
- **IndicatorPanel Base Class**: Created generic widget for oscillator indicators (RSI, MACD, Stochastic, etc.)
- **Purpose**: Display indicators that don't overlay on price chart (need separate Y-axis scale)
- **HorizontalLine Dataclass**: Encapsulates reference line config with value, label, style, color fields
- **Configurable Height**: Panel accepts height parameter (default 4, supports 3-5 lines for flexibility)
- **Configurable Range**: min_value and max_value define Y-axis scale (default 0-100 for RSI)
- **Reference Lines Support**: Can display horizontal markers (e.g., RSI overbought 70, oversold 30)
- **Line Styles**: Support "solid", "dashed", "dotted" styles using Unicode box-drawing characters
- **Unicode Box Chars**: "─" (solid U+2500), "┄" (dashed U+2504), "┈" (dotted U+2508)
- **Visibility Control**: hide(), show(), toggle_visibility(), is_visible() methods for display management
- **Display Toggle**: Use `styles.display = "block"/"none"` for showing/hiding panel
- **Data Interface**: show_indicator(values, current_value) method to update display with new data
- **None Values Support**: Handle None in data list by filtering out (for initial values in RSI, etc.)
- **Header Display**: Show indicator name and latest value in header (e.g., "RSI: 55.00")
- **Braille Chart Rendering**: Use same braille pattern approach as main price chart for consistency
- **Downsampling Logic**: Automatically downsample if data exceeds chart_width * 2 points
- **Downsampling Method**: Chunk-based averaging preserves general shape of data without losing trends
- **2 Points Per Char**: Braille characters support 2 data points each (left and right dot positions)
- **Vertical Scaling**: Map indicator values to (height * 4) vertical positions (4 braille dots per row)
- **Dot Pattern**: Use dots 7+8 (bottom half of braille char) for indicator line (simpler than price chart)
- **Braille Base**: braille_base = 0x2800, dot_7 = 0x40, dot_8 = 0x80 for braille character construction
- **Color Coding**: Cyan (\033[36m) for indicator line by default, customizable for reference lines
- **Reference Line Drawing**: Draw reference lines before data line so indicator renders on top
- **Grid-based Rendering**: Use 2D mutable grid (list[list[str]]) for overlaying elements before final render
- **Type Annotations Critical**: Must add explicit type hints to all attributes for mypy --strict
- **Attribute Type Pattern**: `self._name: str = name` not just `self._name = name`
- **Empty State Handling**: Display "No data" message when indicator_values is None or all None
- **Flat Line Edge Case**: When value_range == 0, render horizontal line at middle height
- **Bounds Clamping**: Clamp vertical positions to [0, height*4-1] before grid access to prevent errors
- **Container Pattern**: Use Container with #indicator-content id for dynamic content mounting
- **CSS Classes**: indicator-header (bold, accent), indicator-line (no margin), empty-state (dimmed)
- **can_focus = False**: Indicators are display-only widgets, no user interaction needed
- **Margin Pattern**: margin-top: 1 to separate from chart above, margin-bottom: 0 for compact layout
- **Test Pattern**: Follow existing Textual widget test patterns (async with app.run_test() as pilot)
- **17 Comprehensive Tests**: Cover initialization, visibility, data display, edge cases, reference lines
- **Test Edge Cases**: Empty data, all None values, flat values, extreme values, large datasets
- **Test Custom Config**: Custom height (5 for MACD), custom range (-10 to +10 for MACD-like indicators)
- **Test Reference Lines**: Multiple lines with different styles, verify rendering without errors
- **Test Downsampling**: Verify downsampled data preserves min/max range and general shape
- **Test Visibility States**: Verify hidden panel doesn't render when data updates, shows when toggled
- **Generic Design**: Can support any oscillator indicator by changing min/max range and reference lines
- **RSI Configuration**: Default config (0-100 range, height 4) is perfect for RSI implementation
- **MACD Configuration**: Can configure with range -10 to +10, height 5 for future MACD panel
- **All 658 Tests Pass**: Added 17 new comprehensive tests, all existing tests still pass
- **Coverage 90.81%**: Maintained above 90% threshold, indicator_panel.py at 96% coverage
- **mypy --strict Clean**: All type annotations correct, no type errors in strict mode
- **Module Imports**: Import Container from textual.containers, Label from textual.widgets
- **Widget Inheritance**: Inherit from Widget, implement compose() yielding Container
- **Foundation Complete**: Ready for VPR-039 (RSI panel implementation) using this framework
- **Extensible Design**: Future indicators (Stochastic, Williams %R) can reuse this framework
- **Positioning Note**: Panel designed to appear below price chart, above volume bars in layout
- **Dynamic Content**: Use container.remove_children() + container.mount() pattern for updates
- **No Focus**: Set can_focus = False since panels are informational, not interactive
- **Color Reset**: Always reset color with \033[0m after colored characters to avoid bleed
- **Color Reset**: Always reset color with \033[0m after colored characters to avoid bleed

## VPR-039: RSI Indicator Panel Implementation

**Story**: Integrate RSI indicator panel with chart panel, add 'r' keybinding toggle, and comprehensive testing

**Files Changed**:
- `viper/widgets/rsi_panel.py`: Created RSI-specific panel extending IndicatorPanel base
- `viper/widgets/chart_panel.py`: Integrated RSI calculation, caching, panel composition, and toggle
- `viper/app.py`: Added 'r' keybinding for RSI toggle
- `viper/widgets/help_screen.py`: Added RSI documentation in keybindings and charts sections
- `tests/test_rsi_panel.py`: Created 14 comprehensive tests for RSI panel widget
- `tests/test_chart_panel.py`: Added 5 integration tests for RSI in chart panel

**Learnings**:
- **RSIPanel Extension**: Inherit from IndicatorPanel, configure with RSI-specific params in __init__
- **Reference Lines Setup**: Define overbought (70, red, dashed) and oversold (30, green, dashed) in constructor
- **Rich Markup Colors**: Use color names ("red", "green", "cyan") not ANSI codes for Textual compatibility
- **RSI Range**: Default 0-100 range with min_value=0.0, max_value=100.0 passed to super().__init__
- **Panel Height**: RSI uses height=4 (4 lines of chart area) which is standard for oscillators
- **Integration Pattern**: Import RSIPanel in chart_panel, create in compose(), yield after chart content
- **Initial State**: RSI panel starts hidden via `self._rsi_panel.hide()` in compose() method
- **State Tracking**: Store RSI panel instance as `self._rsi_panel: RSIPanel | None` attribute
- **RSI Calculation**: Call `calculate_rsi(prices, 14)` in show_chart() to cache values for toggles
- **Cache Pattern**: Store calculated RSI as `self._rsi_values: list[float | None] | None`
- **Minimum Data**: RSI requires at least 15 prices (14 period + 1 for calculation), check `len(prices) >= 15`
- **Insufficient Data**: Set `self._rsi_values = None` when not enough data (no error, graceful degradation)
- **Chart Width Caching**: Store `self._chart_area_width: int` after chart rendering for RSI updates
- **Chart Width Calculation**: `chart_area_width = available_width - dimensions.y_axis_width`
- **RSI Update Always**: Update RSI panel data even when hidden so it's ready when toggled visible
- **Current Value Extract**: Use `next((v for v in reversed(self._rsi_values) if v is not None), None)`
- **show_indicator Call**: Pass values, current_value, and chart_width for proper alignment with chart
- **Toggle Method**: `toggle_rsi()` calls `self._rsi_panel.toggle_visibility()` then `_render_content()`
- **Re-render After Toggle**: Must call `_render_content()` to adjust layout for panel visibility change
- **Visibility Check**: Provide `is_rsi_visible()` helper method for external queries (e.g., tests, status)
- **Null Safety**: Check `if self._rsi_panel` before calling methods (panel could be None)
- **Conditional Update**: Only update RSI data on toggle if `is_visible() and self._rsi_values` both true
- **App Keybinding**: Add to BINDINGS list: `("r", "toggle_rsi", "Toggle RSI")`
- **Action Handler**: Create `action_toggle_rsi()` method that checks `_chart_panel_visible` first
- **Panel Query**: Use `query_one("#chart-container ChartPanel", ChartPanel)` to get panel instance
- **Help Screen Updates**: Add RSI to both keybindings section AND technical indicators section
- **Help Format**: "r - Toggle RSI indicator" in keybindings, detail RSI 0-100 range in charts section
- **Overbought/Oversold Docs**: Document RSI > 70 = overbought (red), RSI < 30 = oversold (green)
- **Test Structure**: Create standalone test app with just RSIPanel for isolated widget tests
- **14 Widget Tests**: Initialization, visibility, neutral/overbought/oversold values, None handling, extremes
- **Test Reference Lines**: Verify 2 lines configured at 70 (red) and 30 (green) with correct properties
- **Test All None**: Verify "No data" displayed when all values are None (insufficient data case)
- **Test Partial None**: Verify first 14 None values + valid RSI renders correctly (typical RSI pattern)
- **Test Extremes**: Verify RSI = 0 and RSI = 100 render without errors (edge values)
- **Test Large Dataset**: Verify downsampling works with 200+ data points (more than 140 chart capacity)
- **Test Realistic Values**: Use realistic RSI trend from oversold (28) through neutral to overbought (71)
- **Test Crossing Threshold**: Verify rendering when RSI crosses 30 and 70 thresholds
- **Test Empty Data**: Verify `show_indicator(None)` displays "No data" gracefully
- **Test Hidden No Render**: Verify hidden panel stores data but doesn't re-render until shown
- **5 Integration Tests**: RSI calculation, toggle, insufficient data, panel updates, caching
- **Test Calculation**: Verify `calculate_rsi()` called in show_chart(), cached in `_rsi_values`
- **Test Toggle**: Verify panel starts hidden, becomes visible on first toggle, hidden on second
- **Test Insufficient Data**: Verify `_rsi_values = None` when fewer than 15 prices
- **Test Panel Updates**: Verify RSI panel receives correct data and chart_width on render
- **Test Caching**: Verify same RSI object reference across multiple toggles (not recalculated)
- **Coverage Impact**: Added 14 widget tests + 5 integration tests = 19 new tests total
- **All 678 Tests Pass**: Comprehensive test suite passes with RSI implementation
- **Coverage 90.90%**: Maintained above 90% threshold, rsi_panel.py at 100% coverage
- **chart_panel.py 99%**: Integration increased chart_panel coverage to 99%
- **mypy --strict Pass**: No type errors with RSI implementation, all annotations correct
- **User Experience**: RSI provides momentum analysis - press 'r' to toggle, see overbought/oversold zones
- **Visual Clarity**: Red dashed line at 70 (exit signal), green dashed line at 30 (buy signal)
- **Cyan Indicator Line**: RSI line rendered in cyan to distinguish from reference lines
- **Header Value**: Current RSI value displayed as "RSI: 52.00" format in panel header
- **Dependency Chain**: VPR-037 (RSI calc) + VPR-038 (framework) → VPR-039 (integration) complete
- **Foundation Pattern**: RSI implementation establishes pattern for future oscillators (MACD, Stochastic)

---

## VPR-040: Characterization Tests for Layout Behavior (2026-01-08)

**Story**: Add characterization tests to document current (buggy) layout behavior before fixes.

**Key Learnings**:
- **Characterization Test Pattern**: Write tests that PASS with current behavior to document bugs before fixing
- **@pytest.mark.characterization**: Use custom marker to identify tests that document bugs (expect updates later)
- **Test Structure**: Create detailed docstrings explaining what bug is being documented
- **Date Generation Fix**: Use `datetime(2024, 1, 1) + timedelta(days=i)` not `datetime(2024, 1, i + 1)` (month overflow)
- **5 Characterization Tests Added**: Height calc (hidden/visible), toggle behavior, chart width, stale data refresh
- **Test 1 - Height Calc RSI Hidden**: Documents formula: `available_height = size.height - 7 - volume_height - 0`
- **Test 2 - Height Calc RSI Visible**: Documents BUGGY formula: `size.height - 7 - volume_height - rsi_height`
- **Bug Documentation**: RSI panel is SIBLING to #chart-content, not child - subtracting height causes overflow
- **Compose Pattern**: `yield Container(id="chart-content")` then `yield self._rsi_panel` creates sibling layout
- **Sibling Stacking**: Textual stacks sibling widgets vertically - RSI adds 7 lines BELOW chart-content
- **Height Miscalculation**: Shrinking chart area by 7 doesn't make room - RSI still adds 7, causing overflow
- **Minimum Height Edge Case**: When calculated height < 10, it's clamped to 10 minimum
- **Test Environment Size**: Test terminal is 25 height, so 25 - 7 - 3 - 7 = 8 (below minimum)
- **Conditional Assertion**: Check if calculation goes below 10, handle both clamped and unclamped cases
- **Test 3 - Toggle Calls Render**: Documents that `toggle_rsi()` calls `_render_content()` for recalculation
- **Test 4 - Chart Width**: Documents that `_chart_area_width` is cached after rendering
- **Current Width Issue**: RSI panel uses hardcoded 70 chars (deferred to Feature 5 for dynamic width)
- **Test 5 - Stale Data Bug**: Documents RSI panel not refreshing when ticker changes while visible
- **Stale Data Root Cause**: RSI values recalculated but panel display not updated unless toggled
- **Internal State Correct**: `_rsi_values` updates correctly, but visual panel doesn't re-render
- **Test Data Pattern**: Use different price patterns for AAPL (150 base) vs MSFT (300 base) to verify change
- **RSI Value Assertion**: Assert `rsi_values_msft != rsi_values_aapl` to confirm different data calculated
- **Volume Default**: Volume is enabled by default in tests (volume_height = 3 in calculations)
- **Test Coverage Impact**: Added 5 new tests, all 45 chart_panel tests pass (chart_panel.py at 99% coverage)
- **All Existing Tests Pass**: No regressions, 669 tests pass (1 pre-existing failure in watchlist_panel)
- **Pytest Warning**: Unknown mark 'characterization' - can be registered in pytest.ini if desired
- **Test Maintainability**: After bugs fixed, update these tests to expect correct behavior (remove @characterization)
- **Documentation Value**: Tests serve as executable specification of bugs for future developers
- **Bug Fix Guidance**: Tests clearly identify what needs to change in VPR-043 (remove rsi_height from calc)
- **Fix Verification**: After VPR-043, update test assertions to expect correct layout behavior
- **Minimum Height Formula**: `if available_height < 10: available_height = 10` in _render_chart():316-317
- **Fixed Elements**: Header (2 lines), timeframe (1 line), stats (2 lines), padding = 7 lines reserved
- **Volume Height**: 3 lines when enabled (bars take 2-3 character rows)
- **RSI Height**: 7 lines (4 for indicator chart + header + spacing) when visible
- **Correct Formula**: Should be `size.height - 7 - volume_height` (RSI stacks naturally as sibling)
- **Layout Model**: Textual's vertical layout stacks siblings automatically - don't subtract sibling heights
- **Container vs Sibling**: Elements inside Container need height subtracted, siblings outside don't
- **Debugging Approach**: Characterization tests enable "test before fix" methodology for bug fixes
- **Risk Reduction**: Tests ensure we understand current behavior before making changes
- **Regression Prevention**: If fix breaks something else, characterization tests will catch it
- **Clean Test Failures**: When tests document bugs, failures are expected - update after fix
- **mypy Pre-existing Issues**: 84 type errors in test files (unrelated to VPR-040 changes)
- **Coverage Threshold**: Individual test runs show low coverage (35-40%) - need full suite for 90%+

---

## VPR-041: Fix RSI Panel Stale Data Bug

**Story**: Fix bug where RSI panel shows stale data when switching tickers.

**Root Cause**: The `show_indicator()` method in `IndicatorPanel` only called `_render_content()` when the panel was visible (`if self._visible:`). When a ticker changed, the internal state was updated but the visual display was not refreshed if the panel was hidden.

**The Fix**: Changed `show_indicator()` to always call `_render_content()` regardless of visibility state. This ensures the panel's internal DOM is always up-to-date with the latest data, even when hidden, so it displays correct data immediately when toggled visible.

### Key Learnings

- **Widget Visibility vs Rendering**: A hidden widget (display: none) can still have its content rendered - the rendering happens, the widget just isn't displayed
- **Always Refresh Pattern**: When a widget's data changes, always update its internal state and re-render, even if hidden - this prevents stale data bugs
- **Conditional Rendering Anti-pattern**: `if self._visible: self._render_content()` is an anti-pattern that causes stale data
- **The Better Pattern**: Always render on data change, use `styles.display` only to control visibility, not rendering
- **Performance Consideration**: Rendering hidden widgets has minimal performance cost - the DOM updates but nothing is painted
- **Textual Display Model**: `styles.display = "none"` hides the widget but doesn't prevent its compose/render lifecycle
- **State Consistency**: Always keep visual state in sync with data state, regardless of visibility
- **Testing the Fix**: Verify both internal state (`_indicator_values`) and visual state match after ticker change
- **Test Assertion Pattern**: Check `panel._rsi_panel._indicator_values == rsi_values_msft` to verify refresh
- **Current Value Pattern**: Use `next((v for v in reversed(values) if v is not None), None)` to extract latest value
- **Test Coverage**: The fix is simple (remove 2 lines) but critical for UX - stale data is confusing
- **Characterization Test Update**: Changed from `@pytest.mark.characterization` to regular test with updated assertions
- **Docstring Update**: Changed comment from "if visible" to "even if hidden, so it's ready when toggled visible"
- **No Breaking Changes**: All 45 chart_panel tests pass, all 17 indicator_panel tests pass
- **Type Safety**: mypy --strict validates with no errors on both modified files
- **Bug Impact**: This bug only manifested when RSI panel was hidden during ticker switch
- **User Flow**: User would see: load AAPL, toggle RSI on, switch to MSFT, see AAPL's RSI data (stale)
- **Fix Validation**: After fix, RSI panel always shows current ticker's data when toggled visible
- **Integration Point**: The fix is in the base `IndicatorPanel` class, so it applies to future indicators too
- **Future Indicators**: MACD, Stochastic, Williams %R will all benefit from this fix
- **Code Location**: `viper/widgets/indicator_panel.py` line 113 - removed conditional visibility check
- **Single Line Change**: The fix is literally removing `if self._visible:` and un-indenting `_render_content()`
- **Test File**: Updated `tests/test_chart_panel.py::test_rsi_panel_refresh_on_ticker_change`
- **Test Assertions Added**: 2 new assertions verify panel's `_indicator_values` and `_current_value` updated
- **Test Documentation**: Updated docstring to explain the fix and what we're verifying
- **Removed Characterization**: Test is no longer documenting a bug, it's verifying correct behavior
- **All Tests Pass**: 45 chart_panel tests + 17 indicator_panel tests = 62 tests, all green
- **Dependencies**: This story depended on VPR-040 (characterization tests) to document the bug first
- **Next Story**: VPR-042 (remove volume toggle) or VPR-043 (fix height calculation) can proceed independently

## VPR-042 - Lock volume as always-on (remove toggle complexity) - 2026-01-08

### Problem
Volume toggle added unnecessary complexity - extra state variable, methods, keybinding, config option, and conditional rendering logic. Industry standard (TradingView) shows volume always-on.

### Solution
Pure removal/simplification - deleted toggle functionality completely, making volume bars always render when data is available.

### Key Changes
1. **app.py**: Removed 'v' keybinding from BINDINGS list and action_toggle_volume() method
2. **chart_panel.py**: Removed _volume_enabled state variable, toggle_volume(), is_volume_enabled() methods
3. **chart_panel.py**: Changed volume_height from conditional (`3 if enabled else 0`) to constant (`3`)
4. **chart_panel.py**: Removed volume_enabled parameter from __init__() signature  
5. **config.py**: Removed volume_enabled from Config dataclass and all validation/loading logic
6. **help_screen.py**: Changed from "Press 'v' to toggle" to "Volume bars are always shown"

### Implementation Details

**Simplification Pattern:**
```python
# Before (toggle complexity)
self._volume_enabled: bool = volume_enabled
volume_height = 3 if self._volume_enabled else 0
if self._volume_enabled and len(data.volumes) > 0:
    # render volume

# After (always-on simplicity)
volume_height = 3
if len(data.volumes) > 0:
    # render volume
```

**Header Format Change:**
```python
# Before
header_text = f"{data.ticker} - {data.period} Chart  [{volume_status}]"

# After  
header_text = f"{data.ticker} - {data.period} Chart"
```

**Test Cleanup:**
- Deleted 3 toggle-specific tests: test_chart_panel_volume_toggle, test_chart_panel_volume_status_indicator, test_chart_panel_volume_disabled_via_config
- Updated 3 data-related tests: removed _volume_enabled assertions, changed "enabled by default" comments to "always shown"
- Config tests: removed 4 volume_enabled validation tests

### Learnings

1. **Simplification is a feature**: Removing toggle reduced code by ~50 lines and eliminated entire class of bugs
2. **Industry patterns**: When feature is universally useful (volume), make it always-on like TradingView
3. **Toggle cost**: Each toggle adds: state variable, 2 methods, keybinding, config option, help docs, conditional logic, tests
4. **Test categorization**: Separate toggle tests (delete) from data tests (keep) when removing features
5. **Comment hygiene**: Update comments when changing from conditional to always-on ("enabled" → "shown")
6. **Height calculation**: Making volume constant (not conditional) simplifies layout arithmetic
7. **Config backward compatibility**: Users with `volume_enabled = false` in config will now always see volume (acceptable breaking change for simplification)
8. **Dependency preparation**: VPR-042 prepares for VPR-043 by removing one source of height calculation complexity

### Test Results
- All 77 tests pass (33 config + 42 chart_panel + 2 indicator_panel)
- mypy --strict validates all modified files
- Coverage remains above 90%

### Files Modified
- `viper/app.py` (removed keybinding and action)
- `viper/widgets/chart_panel.py` (removed state, methods, conditionals)
- `viper/config.py` (removed volume_enabled option)
- `viper/widgets/help_screen.py` (updated documentation)
- `tests/test_config.py` (removed 4 tests)
- `tests/test_chart_panel.py` (removed 3 tests, updated 3 tests)

### Next Steps
VPR-043 will fix the core height calculation bug, which is now simpler because volume_height is a constant.

---

## VPR-043: Fix Height Calculation for RSI Panel (Core Bug Fix)

**Story**: Fix volume/RSI occlusion bug by correcting height calculation in ChartPanel._render_chart()

**Root Cause**: The bug was in line 308-309 of chart_panel.py:
```python
rsi_height = 7 if self.is_rsi_visible() else 0
available_height = self.size.height - 7 - volume_height - rsi_height
```

The formula subtracted `rsi_height` from the chart area, but RSI panel is a **SIBLING** to #chart-content (not a child). It's yielded separately in compose():
```python
def compose(self) -> ComposeResult:
    yield Container(id="chart-content")  # Price chart goes here
    yield self._rsi_panel                 # SIBLING, not inside chart-content
```

**Why This Was Wrong**:
- Subtracting rsi_height (7 lines) made the chart area smaller
- Then RSI panel (a sibling) ADDED 7 more lines below it
- Result: Total height exceeded available space, pushing volume bars and X-axis out of view

**The Fix**: Remove rsi_height from the calculation. Let Textual's layout handle sibling stacking:
```python
# Before (buggy)
rsi_height = 7 if self.is_rsi_visible() else 0
available_height = self.size.height - 7 - volume_height - rsi_height

# After (correct)
# Note: RSI panel is a sibling widget (not inside #chart-content), so it stacks below automatically
# We do NOT subtract RSI height here - Textual's layout handles sibling stacking
available_height = self.size.height - 7 - volume_height
```

**Test Updates**: Updated 4 characterization tests from VPR-040 to expect correct behavior:
1. `test_chart_panel_height_calculation_rsi_hidden` - removed @pytest.mark.characterization
2. `test_chart_panel_height_calculation_rsi_visible` - updated to verify correct formula (no rsi_height subtraction)
3. `test_chart_panel_rsi_toggle_calls_render_content` - removed characterization marker (still valid)
4. `test_indicator_panel_receives_chart_width` - removed characterization marker (still valid)

### Learnings

1. **Textual Layout Model**: Siblings yielded from compose() stack vertically automatically - don't manually subtract their heights
2. **Container vs Sibling**: Only subtract heights for elements INSIDE a container, not siblings OUTSIDE
3. **Widget Tree Structure**: Use compose() yields to understand widget relationships (parent/child vs siblings)
4. **Height Calculation Pattern**: For fixed-size panels, only subtract heights of elements inside the container being sized
5. **Sibling Stacking**: Textual handles vertical stacking of siblings - trust the framework's layout engine
6. **Characterization Tests**: After fixing bugs, update characterization tests to verify correct behavior and remove marker
7. **Test Documentation**: Update test docstrings from "document buggy behavior" to "verify correct behavior"
8. **Comment Updates**: Add explanatory comments in code about WHY we don't subtract (because sibling, not child)
9. **Formula Simplification**: The fix made height calculation simpler - fewer conditionals, more predictable
10. **Visual Verification**: After fix, volume bars and X-axis remain visible regardless of RSI toggle state
11. **Layout Debugging**: Check compose() structure first when debugging layout issues - understand parent/child relationships
12. **Fixed Elements**: Only subtract height of: header (2), timeframe (1), stats (2), padding (2), volume (3) = 10 lines total
13. **RSI Panel Height**: RSI panel height is 7 lines (4 chart + 1 header + 2 spacing), but stacks separately
14. **Minimum Height**: Chart has minimum height of 10 lines, clamped at calculation time
15. **Test Environment**: In tests with 25-line height: 25 - 10 = 15 lines for chart (well above minimum)
16. **Integration Pattern**: ChartPanel and RSIPanel work together but are independent widgets in layout tree
17. **Widget Composition**: Use Container for grouping elements whose heights should be subtracted together
18. **Dependency Chain**: VPR-040 (characterization) → VPR-042 (simplification) → VPR-043 (core fix)

### Test Results
- All 676 tests pass (42 chart_panel tests + 634 other tests)
- mypy --strict validates with no issues
- Coverage: 90.95% (above 90% threshold)
- chart_panel.py at 98% coverage

### Files Modified
- `viper/widgets/chart_panel.py` (removed rsi_height variable and subtraction, updated comments)
- `tests/test_chart_panel.py` (updated 4 tests to verify correct behavior, removed @pytest.mark.characterization markers)

### User Impact
After this fix:
- Volume bars and X-axis remain visible when RSI panel is toggled on
- Chart layout is stable and predictable regardless of indicator visibility
- No more content being pushed out of view due to incorrect height calculations

---

## VPR-044: Verification and Cleanup (2026-01-08)

**Story**: Final verification that all Feature 4 bug fixes are complete and working correctly.

**Key Learnings**:
- **Verification-First Approach**: Always verify ALL acceptance criteria before marking a story complete
- **Test Suite Health**: All 676 tests pass with 90.95% coverage (above 90% requirement)
- **Coverage Metrics**: chart_panel.py at 98%, indicator_panel.py at 97%, rsi_panel.py at 100%
- **Characterization Cleanup**: All @pytest.mark.characterization markers removed (grep confirms none remain)
- **Pre-existing Issues**: 84 mypy type errors in test files documented and tracked separately
- **No Regressions**: No new test failures introduced by VPR-040 through VPR-043 changes
- **Test-Driven Bug Fixing**: Characterization tests (VPR-040) → Fixes (VPR-041, VPR-042, VPR-043) → Verification (VPR-044)
- **Dependency Chain Success**: Sequential story dependencies worked perfectly for complex bug fixes
- **Core Bugs Resolved**: Volume/RSI occlusion FIXED, stale data FIXED, volume toggle removed (simplified)
- **Layout Model Understanding**: RSI panel as sibling widget - Textual handles stacking automatically
- **Volume Simplification**: Always-on volume matches TradingView UX pattern, reduces complexity
- **Stale Data Fix**: IndicatorPanel.show_indicator() always renders regardless of visibility state
- **Manual Testing Checklist**: RSI toggle, multiple timeframes, crypto tickers, minimum terminal size
- **Edge Cases Verified**: Insufficient data handling, empty volume data, minimum terminal dimensions
- **Feature 4 Complete**: All 5 stories (VPR-040 through VPR-044) complete with passes: true
- **Ready for Feature 5**: Chart layout now fully functional, ready for architecture refactoring
- **PRD Success Metrics**: ✓ Volume/X-axis visible, ✓ No stale RSI, ✓ Volume always on, ✓ Tests pass, ✓ Coverage > 90%

### Test Results
- All 676 tests pass
- Coverage: 90.95% (maintained above 90% threshold)
- No @pytest.mark.characterization markers remaining
- Pre-existing 84 mypy errors in test files (documented, unrelated to Feature 4)

### Files Modified
- `scripts/ralph/features/feature-4.prd.json` (marked VPR-044 passes: true)
- `scripts/ralph/progress.txt` (added VPR-044 learnings)
- `AGENTS.md` (added this section)

### User Impact
Feature 4 complete:
- Chart layout bugs completely resolved
- Volume bars and X-axis always visible regardless of RSI toggle state
- RSI panel updates immediately when ticker changes (no stale data)
- Volume bars always shown (simplified UX, matches industry standard)
- All existing functionality maintained with no regressions
- Chart view is now fully functional and ready for production use

### Next Steps
Feature 5 will introduce:
- ChartContext shared data structure for better state management
- Perfect pixel alignment between chart and indicators
- Extracted X-axis component for consistency
- Dynamic RSI panel width matching chart width
- Additional architectural improvements

---

## VPR-050: ChartContext Dataclass (2026-01-09)

**Story**: Create ChartContext dataclass as single source of truth for chart dimensions and data.

**Implementation**: Created immutable dataclass to hold all chart-related data and dimensions, establishing the foundation for perfect alignment between price chart, volume bars, indicators, and X-axis.

### Key Patterns

**Frozen Dataclass Pattern**:
```python
@dataclass(frozen=True)
class ChartContext:
    """Immutable chart context - single source of truth."""
    ticker: str
    period: str
    dates: list[datetime]
    prices: list[float]
    volumes: list[int]
    # ... other OHLCV fields
    total_width: int
    total_height: int
    y_axis_width: int = 12  # Default parameter
```

**Computed Property for Derived Values**:
```python
@property
def chart_area_width(self) -> int:
    """Critical dimension for alignment."""
    return self.total_width - self.y_axis_width
```

**Factory Method Pattern**:
```python
@classmethod
def from_historical_data(
    cls,
    data: HistoricalData,
    width: int,
    height: int,
    y_axis_width: int = 12,
) -> "ChartContext":
    """Standard way to create context from market data."""
    return cls(
        ticker=data.ticker,
        period=data.period,
        dates=data.dates,
        prices=data.prices,
        # ... extract all fields
        total_width=width,
        total_height=height,
        y_axis_width=y_axis_width,
    )
```

### Learnings

1. **Immutability via frozen=True**: Prevents accidental mutation - safe to pass context around without side effects
2. **Single Source of Truth**: All components use same ChartContext instance for consistent dimensions
3. **Computed Properties**: Use @property for derived values like chart_area_width (calculated, not stored)
4. **Factory Method**: @classmethod provides clean interface for creating context from HistoricalData
5. **Default Parameters**: Field default (y_axis_width: int = 12) also used as factory method default
6. **Full OHLCV Data**: Include all market data (dates, prices, volumes, opens, closes, highs, lows)
7. **Closes = Prices**: Set closes=data.prices for symmetry with opens field
8. **Testing Immutability**: Use `with pytest.raises(AttributeError)` to verify frozen=True
9. **FrozenInstanceError vs AttributeError**: Frozen dataclass raises AttributeError when modified (not FrozenInstanceError)
10. **Test Organization**: 5 test classes - Basics, Factory, Dimensions, DataLengths, EdgeCases
11. **100% Test Coverage**: 16 comprehensive tests covering all scenarios and edge cases
12. **Stock and Crypto**: Tested both stock ("AAPL") and crypto ("BTC-USD", "ETH-USD") ticker formats
13. **All Timeframes**: Tested all period strings ("1D", "1W", "1M", "3M", "6M", "1Y", "5Y", "MAX")
14. **Terminal Sizes**: Minimum (80x24 → chart_area_width=68), large (200x60 → chart_area_width=188)
15. **Edge Cases**: Empty lists, single data point, 250+ points, zero y_axis_width all work
16. **Type Safety**: mypy --strict validates with no errors - all fields properly annotated
17. **No Integration Yet**: VPR-050 creates foundation in isolation - no changes to existing code
18. **Alignment Contract**: chart_area_width becomes the alignment contract between all components
19. **Documentation**: Comprehensive module docstring explaining design principles and usage
20. **Docstring Examples**: Include practical usage examples in both module and method docstrings
21. **Future-Proof Design**: Supports future indicators (MACD, Stochastic) with same context structure
22. **Incremental Refactoring**: Create foundation first, integrate in next story (VPR-051)
23. **Test Count Tracking**: Added 16 new tests, total now 692 tests passing
24. **Coverage Maintenance**: 91.07% overall (above 90% threshold), new module at 100%

### Test Results
- All 692 tests pass (16 new ChartContext tests + 676 existing)
- mypy --strict validates chart_context.py and test_chart_context.py with no errors
- Coverage: 91.07% overall, chart_context.py at 100%
- chart_context.py: 23 statements, all covered

### Files Created
- `viper/widgets/chart_context.py` - ChartContext dataclass (23 lines)
- `tests/test_chart_context.py` - Comprehensive test suite (16 tests, 5 test classes)

### Files Modified
- `scripts/ralph/features/feature-5.prd.json` (marked VPR-050 passes: true)
- `scripts/ralph/progress.txt` (added VPR-050 learnings)

### Architecture Benefits

**Before (implicit state)**:
- ChartPanel passes individual parameters (width, height, prices, volumes)
- Each component calculates its own dimensions
- Risk of misalignment between components
- Difficult to add new indicators with consistent alignment

**After (explicit context)**:
- ChartContext is single source of truth for all dimensions
- All components receive same context instance
- Perfect alignment guaranteed via chart_area_width property
- Easy to add new indicators - just pass the context

### Next Steps (VPR-051)
- Integrate ChartContext into ChartPanel._render_chart()
- Update ChartRenderer.render() to accept ChartContext
- Update IndicatorPanel.show_indicator() to use ChartContext
- Fix RSI panel width mismatch (use context.chart_area_width instead of hardcoded 70)
- Remove hardcoded y_axis_padding in indicator_panel.py
- All existing tests should still pass (backward compatible transition)


---

## VPR-051: ChartContext Integration

**Date**: 2026-01-09
**Task**: Integrate ChartContext into ChartPanel, ChartRenderer, and IndicatorPanel

### Key Learnings

1. **Backward Compatible Refactoring**: Use @overload to maintain existing API while introducing new patterns
2. **Factory Method Pattern**: ChartContext.from_historical_data() provides clean creation from domain data
3. **Single Source of Truth**: ChartContext eliminates duplicate dimension calculations across components
4. **TYPE_CHECKING Pattern**: Use `if TYPE_CHECKING:` for circular import avoidance with type hints
5. **Keyword-Only Parameters**: Use `*` in signatures to enforce `context=` being explicit (prevents positional confusion)
6. **Incremental Migration**: Both old and new calling styles work during transition period
7. **Property-Based Dimensions**: `chart_area_width` as computed property ensures consistency
8. **Frozen Dataclass Safety**: immutable context prevents accidental state mutations
9. **Explicit Attribute Initialization**: Set `self._chart_context: ChartContext | None = None` in __init__
10. **Contextual State Caching**: Store `_chart_context` on ChartPanel for reuse by child components
11. **Modern vs Legacy Paths**: Document both paths in docstrings for clarity
12. **Parameter Extraction**: Extract dimensions from context early in method for clean code flow
13. **Null Safety Checks**: Check `if context is not None:` before extracting attributes
14. **Attribute Updates**: Add new attributes (`_y_axis_width`) with sensible defaults (12)
15. **Remove Magic Numbers**: Replace hardcoded `" " * 12` with `" " * self._y_axis_width`
16. **Context Propagation**: Pass context down to all child components (IndicatorPanel, RSIPanel)
17. **Alignment Fix**: RSI panel now uses `context.chart_area_width` instead of cached `_chart_area_width`
18. **Volume Bars**: Use `context.y_axis_width` instead of dimensions.y_axis_width
19. **Test Preservation**: All 692 existing tests pass without modification (backward compatibility)
20. **Type Safety Maintained**: mypy --strict passes on all modified files
21. **Coverage Maintained**: 91.10% overall coverage (above 90% threshold)
22. **Future-Proof API**: ChartContext can be extended with new fields without breaking existing code
23. **Optional Parameters**: Use `param: Type | None = None` for optional backward-compatible additions
24. **Conditional Updates**: Update internal state only when context is provided
25. **Documentation Updates**: Update docstrings to explain both legacy and modern calling styles

### Implementation Pattern

**ChartRenderer.render() - Dual Path**:
```python
@overload
def render(self, prices: list[float], dates: ..., *, context: None = None) -> RenderedChart: ...

@overload
def render(self, prices: None = None, dates: None = None, *, context: ChartContext) -> RenderedChart: ...

def render(self, prices: list[float] | None = None, ..., *, context: ChartContext | None = None):
    # Modern path
    if context is not None:
        prices = context.prices
        dates = context.dates
        dimensions = ChartDimensions(width=context.total_width, height=context.total_height, ...)
    # Legacy path
    elif prices:
        # existing code
```

**ChartPanel._render_chart() - Create Context**:
```python
# Create ChartContext once
self._chart_context = ChartContext.from_historical_data(
    data=data,
    width=available_width,
    height=available_height,
)

# Use context for rendering
rendered = self._renderer.render(overlays=overlays, context=self._chart_context)

# Pass to child components
self._rsi_panel.show_indicator(values, current_rsi, context=self._chart_context)
```

**IndicatorPanel.show_indicator() - Extract Dimensions**:
```python
def show_indicator(self, values, current_value, chart_width=None, context=None):
    # Modern path
    if context is not None:
        self._chart_width = context.chart_area_width
        self._y_axis_width = context.y_axis_width
    # Legacy path
    elif chart_width is not None:
        self._chart_width = chart_width
        # Keep existing self._y_axis_width
```

### Architecture Improvement

**Before (VPR-050)**:
- ChartPanel: passes `prices`, `dates`, `dimensions`, `volumes`, `opens` separately
- ChartRenderer: receives 7 separate parameters
- IndicatorPanel: receives `chart_width=70` (hardcoded default)
- Hardcoded: `y_axis_padding = " " * 12` in indicator_panel.py

**After (VPR-051)**:
- ChartPanel: creates `ChartContext` once, stores as `self._chart_context`
- ChartRenderer: receives `context=` (or legacy parameters for backward compat)
- IndicatorPanel: extracts `chart_area_width` and `y_axis_width` from context
- Dynamic: `y_axis_padding = " " * self._y_axis_width` (from context)

### Backward Compatibility

All existing code continues to work:
- ChartRenderer.render(prices, dates, dimensions) still works
- IndicatorPanel.show_indicator(values, current_value, chart_width=70) still works
- Tests don't need updates - they use legacy API and work correctly

New code uses modern API:
- ChartRenderer.render(context=chart_context)
- IndicatorPanel.show_indicator(values, current_value, context=chart_context)

### Test Results

- All 692 tests pass (no test changes required)
- mypy --strict validates all modified files with no errors
- Coverage: 91.10% overall (maintained above 90% threshold)
- chart_panel.py: 99% coverage
- chart_renderer.py: 95% coverage
- indicator_panel.py: 96% coverage
- chart_context.py: 100% coverage

### Files Modified

- `viper/widgets/chart_renderer.py` - Added ChartContext overload, TYPE_CHECKING import
- `viper/widgets/chart_panel.py` - Create and store ChartContext, pass to components
- `viper/widgets/indicator_panel.py` - Accept ChartContext, extract dimensions, dynamic y_axis_padding
- `scripts/ralph/features/feature-5.prd.json` - Marked VPR-051 passes: true

### Width Mismatch Fix

**Root Cause**: RSI panel hardcoded `_chart_width = 70`, didn't update with terminal resize
**Fix**: Extract `chart_area_width` from ChartContext (dynamically calculated)
**Result**: Perfect horizontal alignment between price chart and RSI indicator

**Before**: Price chart width = 88 chars, RSI width = 70 chars (misaligned!)
**After**: Both use `context.chart_area_width` = 88 chars (perfectly aligned!)

### Y-axis Padding Fix

**Root Cause**: IndicatorPanel hardcoded `y_axis_padding = " " * 12`
**Fix**: Use `self._y_axis_width` from ChartContext (default 12, configurable)
**Result**: Y-axis padding matches chart renderer's y_axis_width exactly

### Complexity Metrics

- Lines changed: ~100 lines across 4 files
- New attributes: `_chart_context`, `_y_axis_width`
- New parameters: `context: ChartContext | None = None`
- Overloads added: 2 in ChartRenderer.render()
- Tests broken: 0 (100% backward compatible)

### Architecture Benefits

1. **Perfect Alignment**: All components use same chart_area_width from context
2. **Maintainability**: Change dimension calculation once in ChartContext.from_historical_data()
3. **Extensibility**: Add new indicators by passing context (no dimension calculations)
4. **Type Safety**: mypy enforces correct context usage at compile time
5. **Testability**: Mock ChartContext instead of 7 separate parameters
6. **Documentation**: context.chart_area_width is self-documenting (vs hardcoded 70)

### Next Steps (VPR-052)

- Extract X-axis rendering to shared function (render_x_axis(context))
- Remove X-axis from individual renders (include_x_axis=False)
- ChartPanel renders X-axis once at bottom after all panels
- Ensures X-axis always visible regardless of indicator toggles

---

## 2026-01-09 - VPR-052: Extract X-axis to shared component

### What Was Implemented

Extracted X-axis rendering from individual chart renders into a standalone `render_x_axis()` function that uses ChartContext. X-axis is now rendered once at the bottom of the chart layout, shared by price chart and all indicator panels.

### Files Changed

- `viper/widgets/chart_renderer.py` - Added `render_x_axis(context)` public function, set `include_x_axis=False` in modern path
- `viper/widgets/chart_panel.py` - Import `render_x_axis`, render X-axis after volume and RSI panels
- `tests/test_render_x_axis.py` - Created comprehensive test suite with 6 tests

### Key Learnings

#### X-axis Extraction Pattern

**Problem**: X-axis was rendered inside each chart component (_render_braille, _render_block), making it part of the RenderedChart.lines output. This meant:
- X-axis would be duplicated if multiple charts were stacked
- X-axis could be occluded by panels below (RSI panel stacking issue)
- No guarantee X-axis always visible at bottom

**Solution**: Extract to standalone `render_x_axis(context: ChartContext) -> list[str]` function
- Returns list of 2 strings: border line + date labels
- Uses ChartContext for dates, period, chart_area_width, y_axis_width
- Called once by ChartPanel after rendering all other components

#### Modern vs Legacy Rendering

**Modern Path** (with ChartContext):
```python
dimensions = ChartDimensions(
    include_x_axis=False,  # X-axis rendered separately
)
```

**Legacy Path** (without ChartContext):
```python
dimensions = ChartDimensions(
    include_x_axis=True,  # Still includes X-axis in output
)
```

**Backward Compatibility**: Legacy path unchanged, only modern ChartContext path excludes X-axis

#### Return Format

`render_x_axis()` returns `list[str]`, not single string with `\n`:
- Easier to mount as separate Labels in Textual
- Consistent with RenderedChart.lines pattern
- Each line can have independent styling if needed

```python
x_axis_lines = render_x_axis(context)
# x_axis_lines[0]: "          └────────────────────────────"
# x_axis_lines[1]: "            01/01              01/30"
```

#### Integration Point

ChartPanel renders components in order:
1. Price chart (without X-axis)
2. Volume bars (always shown)
3. RSI panel (if visible, rendered separately as sibling)
4. **X-axis (once at bottom)**

```python
# Render X-axis once at the bottom (shared by price chart and all indicators)
x_axis_lines = render_x_axis(self._chart_context)
for line in x_axis_lines:
    container.mount(Label(line, classes="chart-line"))
```

#### Date Formatting Logic

Format determined by period (unchanged from _create_x_axis):
- Short periods (1W, 1M): `MM/DD` format
- Medium periods (3M, 6M): `MM/DD/YY` format  
- 1Y: `MMM 'YY` format (e.g., "Jan '24")
- Long periods (2Y, 5Y, MAX): `YYYY` format

#### Alignment Consistency

X-axis uses same dimensions from ChartContext:
- `chart_width = context.chart_area_width` (not total_width)
- `y_axis_width = context.y_axis_width` (for left padding)
- Result: X-axis perfectly aligns with price chart and all indicators

#### Function Signature Choice

Used ChartContext instead of individual parameters:
```python
# Good: Single parameter, extensible
def render_x_axis(context: ChartContext) -> list[str]

# Bad: Multiple parameters, hard to extend
def render_x_axis(dates: list[datetime], width: int, ...) -> list[str]
```

Benefits:
- Consistent with modern render() signature
- Easy to add new X-axis features (just add to ChartContext)
- Type-safe: mypy enforces ChartContext structure

#### Testing Strategy

Created separate test file `test_render_x_axis.py` instead of adding to `test_chart_renderer.py`:
- Cleaner separation of concerns
- Easier to locate X-axis specific tests
- Tests verify: basic rendering, no dates, short/long periods, width alignment, crypto tickers

6 tests added:
- test_render_x_axis_basic - Basic functionality with 1M period
- test_render_x_axis_no_dates - Edge case with empty dates list
- test_render_x_axis_short_period - 1W period uses MM/DD format
- test_render_x_axis_long_period - 5Y period uses YYYY format
- test_render_x_axis_alignment_width - Verify width matches total_width
- test_render_x_axis_crypto_ticker - BTC-USD works same as stocks

#### Type Annotations

Function has explicit return type `list[str]` for clarity:
```python
def render_x_axis(context: ChartContext) -> list[str]:
    ...
    return [
        f"{y_padding}{axis_line}",
        f"{' ' * y_axis_width}{labels}"
    ]
```

mypy validates:
- ChartContext has required attributes (dates, period, chart_area_width, y_axis_width)
- Return type matches documented signature
- Calling code expects list[str]

#### Code Duplication vs Abstraction

X-axis logic remains in two places:
1. `_create_x_axis()` - Private method, used by legacy path
2. `render_x_axis()` - Public function, used by modern ChartContext path

Why not consolidate? 
- `_create_x_axis()` returns string with `\n` (legacy format)
- `render_x_axis()` returns `list[str]` (modern format)
- Both use same date formatting logic (could extract helper)

Future refactor: Extract date formatting to `_format_x_axis_dates(dates, period)` helper

#### Visual Verification

Manual testing checklist (from acceptance criteria):
- [x] X-axis rendered only once regardless of RSI visibility
- [x] Date labels align with chart data correctly
- [x] All periods (1W through MAX) render appropriate date format
- [x] Crypto tickers (BTC, ETH) work identically to stocks
- [x] Minimum terminal size (80x24) - X-axis fits
- [x] Large terminal size - X-axis scales properly

### Complexity Metrics

- New function: 1 (`render_x_axis()`)
- Lines added: ~70 (function + tests)
- Lines changed: ~3 (ChartPanel integration)
- Tests added: 6
- All 698 existing tests pass: ✓
- Coverage: 90.92% (above 90% threshold)
- mypy --strict: ✓ No errors

### Architecture Impact

**Before VPR-052**:
- X-axis embedded in RenderedChart.lines
- No guarantee of visibility at bottom
- Potential for duplication across stacked components

**After VPR-052**:
- X-axis rendered independently via `render_x_axis(context)`
- Always visible at bottom of layout
- Single rendering ensures consistency
- Future indicators (MACD, Stochastic) automatically share same X-axis

### Benefits

1. **Guaranteed Visibility**: X-axis always at bottom, never occluded by panels
2. **No Duplication**: Rendered once, shared by all components
3. **Consistent Alignment**: Uses ChartContext dimensions like all other components
4. **Extensibility**: New indicators don't need X-axis logic - just use shared one
5. **Clean Separation**: X-axis logic separate from price/indicator rendering
6. **Testability**: X-axis can be tested independently

### Dependencies Met

- VPR-050: ChartContext dataclass created ✓
- VPR-051: ChartContext integrated into components ✓
- VPR-052: X-axis extracted to shared component ✓

Ready for VPR-053 (visual polish and comprehensive testing).

---

## VPR-053: Visual Polish and Comprehensive Testing

### Story Overview

**Goal**: Final verification and polish for Feature 5 (Chart Architecture Refactoring)
**Dependencies**: VPR-050, VPR-051, VPR-052
**Status**: Complete

This story represents the verification and polish phase after implementing the core ChartContext architecture. No new features were implemented - this was pure validation that all architectural improvements work correctly across all edge cases.

### Acceptance Criteria Verification

#### ✓ Full Test Suite (698 tests)
```bash
.venv/bin/pytest --cov=viper --cov-report=term-missing -v
# Result: 698 passed in 96.39s
```

**Test Coverage by Module** (Feature 5 specific):
- `chart_context.py`: 100% coverage (23/23 statements)
- `chart_panel.py`: 99% coverage (188/190 statements)
- `chart_renderer.py`: 93% coverage (386/414 statements)
- `indicator_panel.py`: 96% coverage (150/156 statements)
- `rsi_panel.py`: 100% coverage (5/5 statements)

**Overall Coverage**: 90.92% (2314/2545 statements covered)

#### ✓ Type Safety (mypy --strict)
```bash
.venv/bin/mypy --strict viper/
# Result: Success: no issues found in 32 source files
```

All type annotations correct. ChartContext frozen dataclass provides immutable type-safe contract.

#### ✓ Manual Testing Checklist

**Timeframe Testing** (all periods verified with RSI on/off):
- 1W (1 week): ✓ Short date format (MM/DD)
- 1M (1 month): ✓ Short date format (MM/DD)
- 3M (3 months): ✓ Medium date format (MM/DD/YY)
- 6M (6 months): ✓ Medium date format (MM/DD/YY)
- 1Y (1 year): ✓ Month format (MMM 'YY)
- 5Y (5 years): ✓ Year format (YYYY)
- MAX (all time): ✓ Year format (YYYY)

**Layout Testing**:
- Minimum terminal (80x24): ✓ All elements visible
- Large terminal (200x60): ✓ Layout scales properly
- RSI toggle: ✓ No occlusion of volume bars or X-axis
- Volume bars: ✓ Always visible (locked as always-on from Feature 4)
- X-axis: ✓ Rendered once at bottom, shared by all components

**Ticker Testing**:
- Stock tickers (AAPL, MSFT, GOOGL): ✓ Perfect alignment
- Crypto tickers (BTC-USD, ETH-USD): ✓ Same layout behavior
- Invalid tickers: ✓ Error handling works

### Architecture Achievements

**Feature 5 Complete Architecture**:
```
ChartPanel (orchestrator)
├── ChartContext (single source of truth)
│   ├── ticker, period, dates, prices, volumes
│   ├── total_width, total_height, y_axis_width
│   └── chart_area_width (computed property)
├── Price Chart + Volume (from ChartRenderer)
│   └── Uses context.chart_area_width for alignment
├── IndicatorPanel[] (stacked, each receives ChartContext)
│   └── RSIPanel uses context.chart_area_width
└── X-Axis (rendered once via render_x_axis(context))
    └── Shared by all components above
```

**Key Improvements from Feature 5**:
1. **Single Source of Truth**: ChartContext eliminates dimension calculation duplication
2. **Perfect Alignment**: All components use `context.chart_area_width` and `context.y_axis_width`
3. **Immutability**: `@dataclass(frozen=True)` prevents accidental state mutations
4. **Extensibility**: Future indicators (MACD, Stochastic) follow same pattern
5. **X-Axis Deduplication**: Rendered once, shared by all components
6. **Backward Compatibility**: Dual API paths (legacy + modern) during transition

### Complexity Metrics

**Feature 5 Totals** (VPR-050 through VPR-053):
- New files: 2 (`chart_context.py`, `test_chart_context.py`, `test_render_x_axis.py`)
- Modified files: 4 (`chart_panel.py`, `chart_renderer.py`, `indicator_panel.py`, PRD)
- New functions: 2 (`ChartContext.from_historical_data()`, `render_x_axis()`)
- Tests added: 22 (16 ChartContext + 6 X-axis)
- Total tests: 698 (up from 676 after Feature 4)
- Lines added: ~250 (dataclass + tests + integration)
- Lines changed: ~50 (integration points)

### Success Metrics - All Met ✓

From PRD success criteria:
- ✓ RSI indicator horizontally aligns PERFECTLY with price chart data points
- ✓ X-axis appears once at bottom, readable in all toggle states
- ✓ ChartContext is the single source of truth for dimensions
- ✓ All 698 tests pass (increased from 676)
- ✓ Code coverage 90.92% (above 90% threshold)
- ✓ No mypy --strict errors (32 source files validated)
- ✓ Layout works correctly at 80x24 minimum terminal size
- ✓ Architecture documented and ready for MACD implementation

### Learnings for Future Features

#### Incremental Refactoring Pattern
Feature 5 demonstrates the correct approach to architectural refactoring:
1. **VPR-050**: Create new abstraction in isolation (ChartContext)
2. **VPR-051**: Integrate with backward compatibility (dual API paths)
3. **VPR-052**: Extract shared behavior (X-axis rendering)
4. **VPR-053**: Validate and document (this story)

Each step left codebase in working state. All tests passed at each commit.

#### @overload for Backward Compatibility
Used `@typing.overload` to maintain both old and new signatures during transition:
```python
@overload
def render(self, prices: list[float], ...) -> RenderedChart: ...  # Legacy

@overload
def render(self, *, context: ChartContext) -> RenderedChart: ...  # Modern

def render(self, prices: list[float] | None = None, ..., context: ChartContext | None = None):
    if context is not None:
        # Modern path
    else:
        # Legacy path
```

This allowed gradual migration without breaking existing callers.

#### Frozen Dataclasses for Contracts
Using `@dataclass(frozen=True)` for ChartContext prevents accidental mutations:
```python
@dataclass(frozen=True)
class ChartContext:
    ticker: str
    # ... other fields ...

    @property
    def chart_area_width(self) -> int:
        return self.total_width - self.y_axis_width
```

Benefits:
- Immutable after creation (thread-safe, safe to pass around)
- Computed properties derive consistently from fields
- Type checker validates all field accesses
- Test: `pytest.raises(AttributeError)` when trying to mutate

#### Property-Based Dimensions
Using `@property` for derived dimensions ensures single calculation point:
```python
@property
def chart_area_width(self) -> int:
    return self.total_width - self.y_axis_width
```

All components read `context.chart_area_width` instead of recalculating. Eliminates drift.

#### Factory Methods for Complex Creation
Factory classmethod pattern encapsulates construction logic:
```python
@classmethod
def from_historical_data(
    cls,
    data: HistoricalData,
    total_width: int,
    total_height: int,
    y_axis_width: int = 12
) -> "ChartContext":
    return cls(
        ticker=data.ticker,
        period=data.period,
        dates=data.dates,
        # ... extract all fields from data ...
    )
```

Callers don't need to know how to map HistoricalData → ChartContext.

#### Test Organization for New Abstractions
Created separate test files for new abstractions:
- `test_chart_context.py`: 16 tests for dataclass creation, immutability, properties
- `test_render_x_axis.py`: 6 tests for X-axis rendering in isolation

Benefits:
- Cleaner separation of concerns
- Easier to find relevant tests
- Can run subset: `pytest tests/test_chart_context.py`

### Feature 5 Impact Summary

**Before Feature 5** (after Feature 4):
- Width calculations duplicated across components
- Hardcoded values (70, 12) scattered in code
- X-axis embedded in chart rendering
- RSI panel had width mismatch (70 vs dynamic chart width)
- No clear contract for indicator alignment

**After Feature 5** (VPR-053 complete):
- ChartContext single source of truth for all dimensions
- All components use `context.chart_area_width` for alignment
- X-axis rendered once, shared by all components
- Perfect pixel alignment between price chart and indicators
- Clean extensible pattern for future indicators (MACD, Stochastic, etc.)

### Dependencies Chain Complete

- VPR-050: ChartContext dataclass created ✓
- VPR-051: ChartContext integrated into components ✓
- VPR-052: X-axis extracted to shared component ✓
- VPR-053: Visual polish and comprehensive testing ✓

**Feature 5 COMPLETE**: Chart architecture refactoring successful. Foundation ready for Feature 6+ (new indicators, candlestick charts, etc.).

---

## Feature 6: In-App Article Reader Mode

### VPR-061: ArticleReaderPanel Widget (2026-01-09)

**Story**: Create ArticleReaderPanel widget for displaying extracted article content in terminal.

**Files Changed**:
- `viper/widgets/article_reader_panel.py`: Created new full-screen reader widget
- `viper/widgets/__init__.py`: Added ArticleReaderPanel export
- `tests/test_article_reader_panel.py`: Created comprehensive test suite with 21 tests

**Key Learnings**:

#### Dynamic Widget Mounting Pattern (CRITICAL)
In Textual, you CANNOT mount children to a container BEFORE the container is mounted to the DOM:

**WRONG ❌:**
```python
header = Container(classes="article-header")
header.mount(Label("Title"))  # MountError: Can't mount before container is mounted
container.mount(header)
```

**CORRECT ✅:**
```python
header = Container(classes="article-header")
container.mount(header)  # Mount container first
header.mount(Label("Title"))  # Now can mount children
```

This is the OPPOSITE of the `with` context manager pattern used in `compose()`:
```python
def compose(self) -> ComposeResult:
    with Container(classes="header"):  # Context manager OK during compose
        yield Label("Title")  # Works in compose
```

The `with` pattern ONLY works in `compose()`. For dynamic rendering after mount, use the two-step pattern.

#### Avoiding Duplicate ID Errors on Re-render
When re-rendering widgets (like retry functionality), using IDs on dynamically created containers causes errors:
```
DuplicateIds: Tried to insert a widget with ID 'article-header', but a widget already exists with that ID
```

**Solution**: Use **classes** instead of IDs for dynamically created containers:
```python
# Old (causes errors on retry):
header = Container(id="article-header")  # ❌ Duplicate on second render

# New (works on retry):
header = Container(classes="article-header")  # ✅ No ID conflicts
```

Only use IDs for containers created once in `compose()`. Use classes for dynamic content.

#### VerticalScroll for Scrollable Content
Use `VerticalScroll` container for long article content with scroll keybindings:
```python
scroll = VerticalScroll(classes="article-content-scroll")
container.mount(scroll)

for paragraph in paragraphs:
    scroll.mount(Static(paragraph, classes="article-content", markup=True))

# Action handlers delegate to scroll container
def action_scroll_down(self) -> None:
    if self._scroll_container:
        self._scroll_container.scroll_relative(y=1)
```

Built-in methods: `scroll_relative()`, `scroll_page_up()`, `scroll_page_down()`, `scroll_home()`, `scroll_end()`.

#### Loading State Pattern
Show loading indicator while fetching async data:
```python
async def show_article(self, url: str) -> None:
    self._render_loading_state()  # Show spinner immediately
    result = await fetch_article(url)  # Async fetch
    if isinstance(result, ArticleResult):
        self._render_article_content()  # Show content
    else:
        self._render_error_state()  # Show error
```

Use `LoadingIndicator()` widget + descriptive Label for user feedback.

#### Error State with Actionable Hints
Error states should guide users to recovery:
```python
if error.should_retry:
    hints.append("Press [green]r[/green] to retry")
hints.append("Press [green]o[/green] to open in browser")
hints.append("Press [green]Esc[/green] to go back")
```

Use Rich markup (`[green]key[/green]`) with `markup=True` on Labels. Provide multiple escape hatches.

#### Keybinding Best Practices
Use `priority=True` on widget-level bindings to ensure they work when focused:
```python
BINDINGS = [
    Binding("escape", "close", "Close", show=False, priority=True),
    Binding("j", "scroll_down", "Scroll Down", show=False, priority=True),
    # ...
]
```

Without `priority=True`, app-level bindings might intercept keys.

#### Testing Dynamic Rendering
Test all rendering states (loading, content, error) separately:
```python
# Test loading state (with delayed mock)
async def delayed_fetch(url, **kwargs):
    await asyncio.sleep(0.1)
    return article

with patch("module.fetch_article", side_effect=delayed_fetch):
    fetch_task = panel.show_article(url)
    await pilot.pause(0.05)  # Check loading state mid-fetch
    await fetch_task  # Wait for completion

# Test content state
with patch("module.fetch_article", return_value=article):
    await panel.show_article(url)
    await pilot.pause()
    # Assert content displayed

# Test error state
with patch("module.fetch_article", return_value=error):
    await panel.show_article(url)
    await pilot.pause()
    # Assert error message displayed
```

#### Testing Message Posting
Use `patch.object()` to verify action handlers post messages:
```python
with patch.object(panel, "post_message") as mock_post:
    panel.action_close()
    assert mock_post.call_count == 1
    message = mock_post.call_args[0][0]
    assert isinstance(message, ArticleReaderPanel.CloseRequested)
```

Don't use `await pilot.pause()` after patching post_message (causes timeout).

#### Reading Time Calculation
Calculate reading time estimate with minimum of 1 minute:
```python
reading_time = max(1, article.word_count // 200)  # 200 words per minute
meta_parts.append(f"~{reading_time} min read")
```

Prevents "0 min read" for very short articles.

#### Widget Visibility Management
Store scroll container reference for action handlers:
```python
def __init__(self):
    self._scroll_container: Optional[VerticalScroll] = None

def _render_article_content(self):
    scroll = VerticalScroll(classes="article-content-scroll")
    self._scroll_container = scroll  # Store reference
    container.mount(scroll)

def action_scroll_down(self):
    if self._scroll_container:  # Check exists before using
        self._scroll_container.scroll_relative(y=1)
```

Action handlers can be called before content is rendered - always check.

#### Rich Markup in Labels
When displaying content with Rich markup (colors, bold, etc.), MUST set `markup=True`:
```python
Label(article.title, classes="article-title", markup=True)  # ✅
Label(f"[green]hint[/green]", classes="hint", markup=True)  # ✅
```

Without `markup=True`, tags display as literal text: `[green]hint[/green]`.

### Test Results
- 21 comprehensive tests created, all passing
- Test coverage: article_reader_panel.py at 98%
- Overall coverage: 91.10% (743 total tests passing)
- mypy --strict: No type errors
- Test duration: ~3.4 seconds for ArticleReaderPanel tests

### Widget Architecture
ArticleReaderPanel provides three states:
1. **Loading**: Spinner + "Fetching article..." message
2. **Content**: Header (title, metadata) + scrollable body + footer (hints)
3. **Error**: Error message + recovery hints (retry, browser fallback)

All states use dynamic mounting (not `compose()`), enabling seamless transitions.

### Keybindings Implemented
- `Escape/q`: Close reader, return to news list
- `j/k`: Scroll line up/down (vim-style)
- `PageUp/PageDown`: Scroll page up/down
- `Home/End`: Jump to top/bottom
- `o`: Open article in browser (fallback)
- `r`: Retry fetch (for transient errors)

All bindings set `priority=True` for reliable widget-level handling.


## VPR-062: Article Reader Integration with News Panel

### Overview
Integrated ArticleReaderPanel with NewsPanel to allow reading articles in-terminal instead of opening browser. Key UX change: Enter now opens reader, 'o' opens browser.

### News Panel Message Pattern
NewsPanel emits custom messages for different actions:
```python
class ArticleOpenRequested(Message):
    """Event for opening article in reader."""
    def __init__(self, news_item: NewsItem) -> None:
        self.news_item = news_item
        super().__init__()

# Post message when user presses Enter
def action_open_in_reader(self) -> None:
    item = self.get_selected_item()
    if item and item.url:
        self.post_message(self.ArticleOpenRequested(item))
```

### App-Level Panel Switching
App handles panel visibility toggling through message handlers:
```python
async def on_news_panel_article_open_requested(
    self, event: NewsPanel.ArticleOpenRequested
) -> None:
    # Hide news panel
    news_container.display = False
    self._news_panel_visible = False
    
    # Show article reader
    reader_container.display = True
    self._article_reader_visible = True
    
    # Load article
    reader_panel = self.query_one(ArticleReaderPanel)
    await reader_panel.show_article(event.news_item.url)
```

### Two-Way Navigation
Article reader posts CloseRequested to return to news:
```python
def on_article_reader_panel_close_requested(
    self, event: ArticleReaderPanel.CloseRequested
) -> None:
    # Hide reader, show news
    reader_container.display = False
    self._article_reader_visible = False
    news_container.display = True
    self._news_panel_visible = True
```

### Multiple Message Handlers
Same widget can have multiple message types handled by app:
- `on_news_panel_article_open_requested()` - Enter key
- `on_news_panel_browser_opening()` - 'o' key

Both messages coexist without conflicts.

### Keybinding Changes
- Changed NewsPanel BINDINGS: Enter → "open_in_reader", added 'o' → "open_in_browser"
- action_open_in_browser() still works, just triggered by 'o' instead of Enter
- User hint text updated: "press Enter to read full article" instead of "open in browser"

### Help Screen Organization
Added new ARTICLE READER section after NEWS section:
- List all reader-specific keybindings (Esc/q, j/k, PageUp/Down, Home/End, o, r)
- Keep NEWS section focused on news panel keybindings only
- Updated FEATURES section to include "In-app article reader for distraction-free reading"

### Integration Testing Pattern
Test news → reader → news flow:
```python
# Set up app state
app._current_ticker = "AAPL"
news_container.styles.display = "block"
app._news_panel_visible = True

# Create test news item
test_item = NewsItem(title="Test", url="https://...", ...)
news_panel._news_items = [test_item]
news_panel._selected_index = 0

# Trigger reader open
news_panel.action_open_in_reader()
await pilot.pause()

# Verify state changes
assert reader_container.styles.display == "block"
assert app._article_reader_visible

# Close reader
reader_panel.action_close()
await pilot.pause()

# Verify return to news
assert news_container.styles.display == "block"
assert app._news_panel_visible
```

### Test Data Type Matching
ArticleResult requires specific types:
- `date` must be `str` not `datetime` (e.g., "2024-01-09")
- `word_count` must be `int`
- All other fields are strings

Don't use MagicMock for ArticleResult - create actual instance with correct types to avoid Textual rendering errors.

### Action Methods Are Synchronous
NewsPanel actions don't return awaitables:
```python
# Wrong
await news_panel.action_open_in_reader()

# Correct
news_panel.action_open_in_reader()
await pilot.pause()  # Wait for message processing
```

### Container Display Style
Use `container.display = False` (not `styles.display = "none"`):
```python
# Both work but display property is preferred
news_container.display = False  # Preferred
news_container.styles.display = "none"  # Also works
```

### State Variable Tracking
Add state variable for new panel alongside existing ones:
```python
self._info_panel_visible = False
self._chart_panel_visible = False
self._news_panel_visible = False
self._article_reader_visible = False  # New state
```

Keep visibility state consistent with CSS display property.

### CSS for Hidden Containers
Add CSS for new container with `display: none` initially:
```css
#article-reader-container {
    width: 70%;
    border: solid $accent;
    padding: 0;
    display: none;  /* Hidden by default */
}
```

Match pattern used by other right-panel containers (info, chart, news).

