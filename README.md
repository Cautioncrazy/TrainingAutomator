# Workday Course Automator

This project uses Python and Playwright to automate Workday SCORM packages and web-based training courses. It provides a simple GUI to manage the automation process, including manual login and headless execution.

## Features

*   **GUI Control**: A lightweight `tkinter` interface to manage the browser and automation lifecycle.
*   **Headless Support**: Run the automation in the background (requires a saved session state).
*   **Robust iFrame Handling**: Dynamically traverses all nested iFrames to find progression elements.
*   **Smart Waiting**: Handles built-in course timers by waiting for "Next" or "Continue" buttons to become visible and enabled.
*   **Interactive Handling**: Attempts to interact with quizzes, radio buttons, and checkboxes when the "Next" button is disabled.
*   **Completion Detection**: Automatically detects when the course is complete and stops the automation.
*   **Multi-Window Support**: Automatically detects and scans all open windows/tabs, solving issues where SCORM courses launch in new popup windows.
*   **Error Handling and Logging**: Logs all actions, errors, and timeouts to `automation.log` for easy debugging.

## Prerequisites

*   Python 3.7 or higher

## Installation

1.  Clone this repository or download the source code.
2.  Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

3.  Install the Playwright browsers:

    ```bash
    playwright install chromium
    ```

## Usage

### 1. Initial Setup and Manual Login (Headful Mode)

The first time you run the script, or whenever your Workday session expires, you must run it in "headful" mode (with the GUI visible) to log in manually and save your session state.

1.  Run the application:

    ```bash
    python main.py
    ```

2.  **Do not** check the "Run Headless" box.
3.  Click the **"1. Launch Browser (Login)"** button.
4.  A Chromium browser window will open.
5.  Navigate to your Workday login page and log in manually.
6.  Navigate to the specific training course you want to automate and open the course start page (the page where you would typically click "Start" or "Resume").
7.  Once the course is ready to begin, click the **"2. Start Automation"** button in the GUI.
8.  The script will now take over, save your session state to `state.json`, and begin automating the course.

### 2. Running Headless (Background Execution)

Once you have successfully logged in and started automation at least once (which creates the `state.json` file), you can run future courses headlessly.

1.  Run the application:

    ```bash
    python main.py
    ```

2.  Check the **"Run Headless"** box.
3.  Click the **"1. Launch Browser (Login)"** button. The browser will launch invisibly and load your saved session state.
4.  Click the **"2. Start Automation"** button.
5.  The script will attempt to navigate the course automatically in the background. Check the GUI status or the `automation.log` file to monitor progress.

### 3. Stopping Automation

At any point, you can click the **"3. Stop Automation"** button to halt the script's progress. You can then resume it by clicking **"2. Start Automation"** again.

## Logs

All actions, including clicking buttons, interacting with elements, encountering errors, or timing out (e.g., waiting more than 2 minutes for a "Next" button), are logged to `automation.log` in the same directory as the script. Check this file if the automation stops unexpectedly.

## Maintaining the Script

If Workday updates its interface, the script may fail to find the necessary buttons to progress. Refer to the `AGENTS.md` file for detailed instructions on architecture, selector strategies, and how to update the script if the DOM structure changes.
