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
