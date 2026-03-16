import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import time
import os
import random
import logging
from playwright.sync_api import sync_playwright

STATE_FILE = "state.json"

logging.basicConfig(
    filename='automation.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutomationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Workday Course Automator")
        self.root.geometry("450x300")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.headless_var = tk.BooleanVar(value=False)
        self.is_running = False
        self.last_advance_time = time.time()

        # UI Elements
        ttk.Label(root, text="Workday Course Automator", font=("Helvetica", 14, "bold")).pack(pady=10)

        ttk.Checkbutton(root, text="Run Headless (requires saved state)", variable=self.headless_var).pack(pady=5)

        self.launch_btn = ttk.Button(root, text="1. Launch Browser (Login)", command=self.launch_browser)
        self.launch_btn.pack(pady=5)

        self.start_btn = ttk.Button(root, text="2. Start Automation", command=self.start_automation, state=tk.DISABLED)
        self.start_btn.pack(pady=5)

        self.stop_btn = ttk.Button(root, text="3. Stop Automation", command=self.stop_automation, state=tk.DISABLED)
        self.stop_btn.pack(pady=5)

        self.status_label = ttk.Label(root, text="Status: Idle", wraplength=400, justify="center")
        self.status_label.pack(pady=15)

        # Playwright worker communication
        self.cmd_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._playwright_worker, daemon=True)
        self.worker_thread.start()

        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def on_closing(self):
        self.is_running = False
        self.cmd_queue.put({"cmd": "quit"})
        self.root.destroy()

    def update_status(self, text):
        self.root.after(0, lambda: self.status_label.config(text=f"Status: {text}"))
        logger.info(text)

    def launch_browser(self):
        self.cmd_queue.put({"cmd": "launch", "headless": self.headless_var.get()})
        self.launch_btn.config(state=tk.DISABLED)

    def start_automation(self):
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.launch_btn.config(state=tk.DISABLED)
        self.cmd_queue.put({"cmd": "start"})

    def stop_automation(self):
        self.update_status("Stopping automation...")
        self.stop_btn.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.NORMAL)
        self.cmd_queue.put({"cmd": "stop"})

    def _playwright_worker(self):
        with sync_playwright() as p:
            self.playwright = p
            while True:
                try:
                    if self.is_running:
                        try:
                            msg = self.cmd_queue.get_nowait()
                            if msg.get("cmd") == "quit":
                                break
                            self._handle_cmd(msg)
                        except queue.Empty:
                            pass

                        if self.is_running:
                            self._automation_step()
                    else:
                        msg = self.cmd_queue.get()
                        if msg.get("cmd") == "quit":
                            break
                        self._handle_cmd(msg)
                except Exception as e:
                    logger.error(f"Worker error: {e}", exc_info=True)
                    self.update_status(f"Worker Error: {e}")
                    self.is_running = False
                    self._update_ui_stopped()

    def _handle_cmd(self, msg):
        cmd = msg.get("cmd")
        if cmd == "launch":
            self._do_launch(msg.get("headless", False))
        elif cmd == "start":
            if not self.page:
                self.update_status("Error: Browser not launched!")
                self._update_ui_stopped()
                return
            self.is_running = True
            self.last_advance_time = time.time()
            self.update_status("Automation started.")
            self._save_state()
        elif cmd == "stop":
            self.is_running = False
            self.update_status("Automation stopped.")

    def _do_launch(self, headless):
        self.update_status("Launching browser...")
        try:
            self.browser = self.playwright.chromium.launch(headless=headless)
            if os.path.exists(STATE_FILE):
                self.context = self.browser.new_context(storage_state=STATE_FILE)
                self.update_status("Loaded saved session state.")
            else:
                self.context = self.browser.new_context()

            self.page = self.context.new_page()

            if not headless:
                self.update_status("Browser launched. Log in manually, navigate to the course, then click 'Start Automation'.")
            else:
                self.update_status("Headless browser launched. Ready to start.")

            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
        except Exception as e:
            logger.error(f"Launch error: {e}", exc_info=True)
            self.update_status(f"Error launching browser: {e}")
            self.root.after(0, lambda: self.launch_btn.config(state=tk.NORMAL))

    def _save_state(self):
        if self.context:
            try:
                self.context.storage_state(path=STATE_FILE)
                logger.info("Saved browser state to state.json")
            except Exception as e:
                logger.error(f"Failed to save state: {e}")

    def _get_all_frames(self, frame):
        frames = [frame]
        for child in frame.child_frames:
            frames.extend(self._get_all_frames(child))
        return frames

    def _check_completion(self, pages):
        completion_texts = [
            "you may now exit this course",
            "course completed",
            "congratulations",
            "you have successfully completed"
        ]

        for page in pages:
            frames = self._get_all_frames(page.main_frame)
            for frame in frames:
                for ct in completion_texts:
                    try:
                        locators = frame.get_by_text(ct, exact=False).all()
                        for loc in locators:
                            if loc.is_visible():
                                return True
                    except Exception:
                        pass
        return False

    def _get_active_course_pages(self):
        if not self.context or not self.context.pages:
            return []
        # Return all open pages, the script will scan all of them.
        # Often, Workday pops open a new window for the SCORM course.
        return self.context.pages

    def _automation_step(self):
        pages = self._get_active_course_pages()
        if not pages:
            self.update_status("no active course window detected")
            self.is_running = False
            self._update_ui_stopped()
            return

        if self._check_completion(pages):
            self.update_status("Course complete! Stopping automation.")
            self.is_running = False
            self._update_ui_stopped()
            return

        if time.time() - self.last_advance_time > 120:
            self.update_status("Timeout (2 min) finding Next button. Pausing.")
            logger.error("Timed out waiting for Next/Continue.")
            self.is_running = False
            self._update_ui_stopped()
            return

        advanced = self._scan_and_click_next(pages)
        if advanced:
            self.last_advance_time = time.time()
            # Minimal debounce after an action
            pages[-1].wait_for_timeout(2000)
        else:
            # Minimal poll interval
            pages[-1].wait_for_timeout(1000)

    def _update_ui_stopped(self):
        self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))

    def _scan_and_click_next(self, pages):
        all_frames = []
        for page in pages:
            all_frames.extend(self._get_all_frames(page.main_frame))

        next_selectors = [
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "button[aria-label='Next']",
            "button[aria-label='Continue']",
            "div[role='button']:has-text('Next')",
            "div[role='button']:has-text('Continue')",
            "a:has-text('Next')",
            "a:has-text('Continue')",
            ".next-button",
            "#next-btn",
            "button:has-text('Submit')"
        ]

        found_disabled = False
        button_to_click = None

        for frame in all_frames:
            for selector in next_selectors:
                try:
                    locators = frame.locator(selector).all()
                    for loc in locators:
                        if loc.is_visible():
                            if loc.is_enabled():
                                button_to_click = loc
                                break
                            else:
                                found_disabled = True
                except Exception:
                    pass
            if button_to_click:
                break

        if button_to_click:
            try:
                self.update_status("Next button is enabled. Clicking...")
                button_to_click.click()
                return True
            except Exception as e:
                logger.warning(f"Error clicking Next button: {e}")
                return False

        if found_disabled:
            self.update_status("Next button is disabled. Attempting interactions or waiting...")
            self._attempt_interactions(all_frames, pages[-1])
        else:
            self.update_status("Next button not found yet. Waiting...")

        return False

    def _attempt_interactions(self, frames, active_page):
        for frame in frames:
            try:
                radios = frame.locator("input[type='radio']").all()
                for radio in radios:
                    if radio.is_visible() and radio.is_enabled() and not radio.is_checked():
                        radio.check(force=True)
                        logger.info("Checked a radio button.")
                        active_page.wait_for_timeout(500)

                checkboxes = frame.locator("input[type='checkbox']").all()
                for cb in checkboxes:
                    if cb.is_visible() and cb.is_enabled() and not cb.is_checked():
                        if random.choice([True, False]):
                            cb.check(force=True)
                            logger.info("Checked a checkbox.")
                            active_page.wait_for_timeout(500)

                submit_selectors = [
                    "button:has-text('Submit')",
                    "button:has-text('Check Answer')",
                    "button:has-text('Verify')"
                ]
                for sel in submit_selectors:
                    submit_btns = frame.locator(sel).all()
                    for btn in submit_btns:
                        if btn.is_visible() and btn.is_enabled():
                            btn.click()
                            logger.info(f"Clicked quiz interaction button: {sel}")
                            active_page.wait_for_timeout(1000)
            except Exception:
                pass

if __name__ == "__main__":
    root = tk.Tk()
    app = AutomationApp(root)
    root.mainloop()
