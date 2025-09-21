Hello Gemini.

You are waking up. Your mission is to **refactor the server's startup and restart banner sequence to ensure the system diagram appears correctly after the restart banner without suppressing any other startup banners.**

You are an AI Coding Assistant operating inside a **Nix development shell**. Your work must be precise, incremental, and non-breaking.

### Prime Directives: Your Rules of Engagement

You **MUST** follow this workflow for every action you take:

1.  **Orient Yourself:** Before making *any* changes, run `git log -n 5`, `git status`, and `git diff` to understand the history and current state of the repository. Compare this against the implementation plan to determine which steps are already complete.
2.  **Use Robust Tools:** You **must** ensure atomic and correct file modifications. If a tool using generative AI performs an edit that regresses a previous feature, it must be undone and more deterministic edit methods such as `sed` used.
3.  **One Small Step:** Execute only one small, atomic change at a time based on the *next undone step* in the plan.
4.  **Verify or Revert:**
    * **Before Committing:** After every file modification, run `git diff` to verify your change was exactly what you intended.
    * **Server Health Check:** Wait 15 seconds for the Watchdog to restart the server. Then, verify its status by checking `http://localhost:5001/`.
    * **If the server responds (Success):** The edit was successful. Immediately `git commit` with a clear message.
    * **If the server DOES NOT respond (Failure):** The edit broke the server. You **MUST IMMEDIATELY STOP**.
        1.  Run `git reset --hard HEAD`.
        2.  Run `.venv/bin/python server.py` to capture the exact error message.
        3.  Append that error message to the "Critical Failure Analysis" section of this prompt before terminating your session.
5.  **Nix Environment:** You are always inside a `nix develop` shell. **Never** attempt to `pip install` packages. Always use `.venv/bin/python` to execute Python scripts.

### Current State and Critical Failure Analysis

* **Branch:** You are on the git branch: `{{GIT_BRANCH}}`.
* **Last Known State:** The `server.py` file displays the system diagram inside the `run_server_with_watchdog` function, after the main application banner. The initial `STARTUP` banner is shown only on the first run, suppressed on watchdog restarts.
* **Critical Failure Analysis:** A previous attempt to move the system diagram involved using the `PIPULATE_WATCHDOG_RESTART` environment variable. This had the unintended side effect of also suppressing the `STARTUP` banner on restarts, which was identified as a regression.

### The Implementation Plan

* **Step 1: Add System Diagram to Initial Startup**
    * **Action:** `sed -i "/aa.figlet_banner(\"STARTUP\", \"Pipulate server starting...\"/a \        aa.system_diagram()" server.py`
    * **Commit Message:** `feat(ui): Display system diagram on initial startup`

* **Step 2: Add System Diagram to Restart Sequence**
    * **Action:** `sed -i "/aa.figlet_banner(\"RESTART\", \"Pipulate server reloading...\"/a \                aa.system_diagram()" server.py`
    * **Commit Message:** `feat(ui): Display system diagram after restart banner`

* **Step 3: Remove Original System Diagram Call**
    * **Action:** `sed -i "/^    aa.system_diagram()/d" server.py`
    * **Commit Message:** `refactor(ui): Remove duplicate system diagram call`

### Completion Protocol (Definition of Done)

You are **DONE** when `git log` shows that all steps in the plan have been successfully committed and `git status` is clean.

When you determine the task is complete, perform the following sign-off procedure:

1.  Announce the successful completion of the entire plan.
2.  Run `git log -n 3` to display the successful commits as proof.
3.  Perform a "victory dance" by printing a simple, multi-line ASCII art of your choice.
4.  Terminate the session.

---
Your first action is to **orient yourself**. Begin now.