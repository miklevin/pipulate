### `prompt.md` for Gemini CLI

Hello Gemini. You are waking up. Your mission is to complete the task of making the Pipulate application's homepage configurable.

You are an AI Coding Assistant operating inside a **Nix development shell**. Your work must be precise, incremental, and non-breaking.

### Prime Directives: Your Rules of Engagement

You **MUST** follow this workflow:

1.  **Orient Yourself:** Before making *any* changes, run `git log -n 5`, `git status`, and `git diff` to understand the history and current state of the repository. Compare this against the implementation plan to determine which steps are already complete.
2.  **Use Powerful Tools:** The built-in `replace` tool is **forbidden**. You must perform file modifications using `sed` for single files. You are a master of RegEx; construct precise patterns.
3.  **One Small Step:** Execute only one small, atomic change at a time based on the *next undone step* in the plan.
4.  **Verify or Revert:**
    * **Before Committing:** After every `sed` command, run `git diff` to verify your change was exactly as intended.
    * **Server Health Check:** Wait 15 seconds for the Watchdog to restart the server. Then, verify its status by checking `http://localhost:5001/`.
    * **If the server responds (Success):** The edit was successful. Immediately `git commit` with a clear message.
    * **If the server DOES NOT respond (Failure):** The edit broke the server. You **MUST IMMEDIATELY STOP**.
        1. Run `git reset --hard HEAD`.
        2. Run `python server.py` to capture the exact error.
        3. Append the error to this file (`prompt.md`) before terminating.
5.  **Nix Environment:** You are always inside a `nix develop` shell. **Never** attempt to `pip install` packages.

### Current State and Context

* You are on the git branch: `noplacelikehome`.
* **Critical Failure Analysis:** Previous attempts failed due to two issues: (1) a `NameError` caused by removing a variable from `config.py` before `server.py` was ready, and (2) getting stuck in a loop re-doing completed work. This new plan and your orientation step are designed to prevent both.

### The Immediate Task: The Configurable Homepage Plan

Your mission is to ensure all steps of this plan are complete. **If your initial `git log` shows all steps are already committed, proceed directly to the "Completion Protocol."**

* **Step 3.1: Fortify `server.py` to Prevent Startup Errors.**
    * **Action:** In `server.py`, change `HOME_MENU_ITEM = PCONFIG['HOME_MENU_ITEM']` to `HOME_MENU_ITEM = PCONFIG.get('HOME_MENU_ITEM', '👥 Roles (Home)')`.
    * **Commit Message:** `refactor(server): Fortify server.py against startup errors`
* **Step 3.2: Implement the Dynamic Logic in `server.py`.**
    * **Action:** Add the `get_home_menu_item()` helper function and modify `endpoint_name()` and `create_home_menu_item()` to use it.
    * **Commit Message:** `feat(server): Implement dynamic home menu logic`
* **Step 3.3: Modify `config.py`.**
    * **Action:** In `config.py`, remove the `HOME_MENU_ITEM` constant and its entry in the `PCONFIG` dictionary.
    * **Commit Message:** `refactor(config): Remove legacy HOME_MENU_ITEM`
* **Step 3.4: Final Cleanup of `server.py`.**
    * **Action:** In `server.py`, remove the now-obsolete line `HOME_MENU_ITEM = PCONFIG.get(...)` from the top of the file.
    * **Commit Message:** `refactor(server): Remove obsolete HOME_MENU_ITEM global`

### Completion Protocol (Definition of Done)

You are **DONE** when `git log` shows that all four steps above have been successfully committed and the `git status` is clean.

When you determine the task is complete, perform the following actions to sign off:

1.  Announce the successful completion of the entire plan.
2.  Run `git log -n 4` one last time to display the successful commits as proof.
3.  Perform a "victory dance" by printing a simple, multi-line ASCII art of your choice.
4.  Terminate the session.

---

Your first action is to orient yourself with `git log`, `git status`, and `git diff`. Begin now.
