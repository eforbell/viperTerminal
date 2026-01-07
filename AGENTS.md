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
