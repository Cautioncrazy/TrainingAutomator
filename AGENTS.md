# Workday Course Automator Architecture & Guidelines

## Overview

This project uses Python and Playwright to automate Workday SCORM packages and web-based training courses. It utilizes a `tkinter` GUI to allow manual login before handing control over to a Playwright worker thread for automated navigation and interaction.

## Architecture

1.  **GUI Thread (`tkinter`)**:
    - The main thread runs the `tkinter` application.
    - It provides a visual interface with a headless toggle, and buttons to launch the browser, start automation, and stop automation.
    - It communicates with the Playwright worker thread via a thread-safe `queue.Queue`.
    - It handles graceful shutdowns by passing a "quit" command to the queue.

2.  **Playwright Worker Thread**:
    - Runs in the background (daemon thread) to prevent blocking the GUI.
    - Uses Playwright's synchronous API (`sync_playwright`).
    - Receives commands from the GUI thread (`launch`, `start`, `stop`, `quit`).
    - Once the "start" command is received, it enters an `_automation_step` loop.
    - Handles state management by saving session cookies and local storage to `state.json` when automation starts, allowing for future headless runs without manual login.

## Execution Flow

1.  **Launch**: The user clicks "Launch Browser". The worker thread spins up a Chromium instance (either headful or headless based on the toggle). If `state.json` exists, it loads the saved session state.
2.  **Manual Login**: If running headful, the user manually logs into Workday and navigates to the specific course's start page.
3.  **Handoff**: The user clicks "Start Automation". The GUI tells the worker to begin. The worker saves the current browser state to `state.json`.
4.  **Automation Loop**:
    - **Completion Check**: Scans all frames for text indicating course completion (e.g., "you may now exit this course"). If found, stops.
    - **Multi-Window Check**: Scans all `context.pages` dynamically to find active course windows. Returns "no active course window detected" if none are found.
    - **Timeout Check**: If no "Next" button has been successfully clicked within 2 minutes, the script logs an error and pauses.
    - **Scan and Click**: Recursively gathers all iFrames across all active pages. Scans each frame for common "Next" or "Continue" selectors.
        - If an enabled button is found, it clicks it and uses `wait_for_timeout` for a minimal 2-second debounce to let the next page load.
        - If only a *disabled* button is found (indicating a timer or a required interaction), it triggers `_attempt_interactions`.
        - If no button is found, it uses `wait_for_timeout` for a 1-second polling interval and loops again.
    - **Interaction Handling**: If the "Next" button is disabled, the script searches all frames for enabled radio buttons, checkboxes, and "Submit"/"Verify" buttons. It checks the first available unselected radio button or randomly checks checkboxes, then attempts to submit, using short `wait_for_timeout` debounces to simulate human click speed.

## Selector Strategies and iFrame Traversal

Workday courses heavily utilize nested iFrames.

-   **Traversing iFrames**: The script dynamically discovers all nested iFrames using a recursive function `_get_all_frames(frame)` starting from `page.main_frame`. It does not rely on specific frame names or URLs, making it highly resilient to structural changes.
-   **Selectors**: The script uses a robust list of selectors to find progression buttons. Instead of specific IDs, it primarily relies on text content (`has-text('Next')`), ARIA labels (`aria-label='Next'`), and common class names.
-   **Dynamic Waiting**: Playwright's built-in auto-waiting handles waiting for elements to be attached to the DOM and become visible. The script explicitly checks `loc.is_enabled()` before attempting a click.

## Maintenance Guidelines

If Workday updates its DOM structure and the script fails to advance, follow these steps:

1.  **Check Logs**: Open `automation.log` to see if the script is timing out or failing to find selectors.
2.  **Inspect the DOM**: Open the course manually in Chrome, right-click the "Next" or "Continue" button, and select "Inspect".
3.  **Update Selectors**: If the element uses a new class, ID, or text format, add the new selector to the `next_selectors` list in `main.py` -> `_scan_and_click_next()`.
    - *Example*: If they change the button text to "Proceed", add `"button:has-text('Proceed')"` to the list.
4.  **Update Completion Texts**: If the final page message changes, update the `completion_texts` list in `main.py` -> `_check_completion()`.
5.  **Interactive Elements**: If new interactive elements (like drag-and-drop or specific dropdowns) are added that block progress, logic for handling those specific element types will need to be added to `main.py` -> `_attempt_interactions()`.
