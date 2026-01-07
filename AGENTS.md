# Agent Learnings

This file documents patterns, best practices, and gotchas discovered during development.

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
