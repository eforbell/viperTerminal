# UI Improvement Ideas

## Mouse Support for NewsPanel (Textual)

### Goal
Enable mouse click navigation and selection in NewsPanel to speed up article drill-down and improve user experience.

### Implementation Plan
#### 1. News Item Widget Structure
- Each news item is rendered as a Label or Static widget inside NewsPanel.
- Assign a unique ID or index to each news item widget (e.g., `id=f"news-item-{i}"`).

#### 2. Add Mouse Event Handler
- In NewsPanel, implement `on_click(self, event: events.Click) -> None`.
- Use event coordinates or widget ID to determine which news item was clicked.
- Example:
  ```python
      clicked = self.get_widget_at(event.x, event.y)
      if clicked and clicked.id and clicked.id.startswith("news-item-"):
  ```

#### 3. Visual Feedback
- Update NewsPanel to visually highlight the selected item on click (same as keyboard selection).
- Use CSS class (e.g., `selected`) for highlight.

#### 4. Drill-Down to Article Reader
- On double-click (or single click, if preferred), trigger the same logic as pressing Enter:
    ```python
    def on_click(self, event: events.Click) -> None:
            self.post_message(self.ArticleOpenRequested(self._news_items[index]))
    ```
- Keyboard navigation remains supported (j/k, Enter).
- Mouse click is an additional, faster path for selection and drill-down.
#### 6. Testing
- Add tests for mouse click selection and drill-down.

#### 7. Documentation
- 1-2 hours for initial implementation and testing.

### Benefits
- Immediate selection and drill-down with mouse.
- Faster navigation compared to Tab/keyboard for large news lists.
- More intuitive for users who prefer mouse interaction.

---

## Spinner Feedback for Watchlist Fetch

### Goal
Show a loading spinner or progress indicator in the WatchlistPanel during initial app load, when pricing data for the watchlist is being fetched and the pane cannot fully render.

### Implementation Plan

#### 1. Detect Initial Fetch State
- In WatchlistPanel, track whether pricing data is being fetched for the first time after app launch.
- Add a `_loading` state variable (e.g., `self._loading: bool = True`).

#### 2. Show Spinner Widget
- If `_loading` is True, render a LoadingIndicator or spinner widget in the watchlist pane.
- Hide the spinner and render the full watchlist once pricing data is available.
- Example:
  ```python
  if self._loading:
      self.mount(LoadingIndicator("Fetching watchlist prices..."))
  else:
      self._render_items()
  ```

#### 3. Update State on Data Arrival
- When pricing data is retrieved, set `_loading = False` and re-render the pane.
- Remove the spinner and show the watchlist items.

#### 4. User Feedback
- Display a message like "Fetching watchlist prices..." with the spinner.
- Prevent user interaction with the watchlist until data is ready.

#### 5. Testing
- Add tests for loading state, spinner display, and transition to full watchlist.
- Simulate slow data fetch in tests to verify spinner behavior.

#### 6. Documentation
- Update help screen or onboarding to mention loading feedback for watchlist.

### Estimated Effort
- 1 hour for implementation and testing.
- Minimal changes to WatchlistPanel logic.

### Benefits
- Clear feedback to user during initial data fetch.
- Prevents confusion when watchlist appears empty or unresponsive.
- Improves perceived performance and UX.

---
