Of course. Based on your detailed request and the context from your technical journal, I've architected the precise `prompt.md` file for Gemini CLI to execute this next mission.

This prompt follows your "SNEFU to ROFSA" playbook, prioritizing clarity, atomic steps, and a resilient, verifiable workflow. It correctly identifies the filtering logic in `server.py` as the target and outlines the simplest possible change to restore the `roles` and `profiles` apps to the menus, just as you requested.

Here is the content for your `prompt.md` file.

-----

### `prompt.md` for Gemini CLI

Hello Gemini. You are waking up inside a Nix development shell. Your previous mission to make the Pipulate application's homepage configurable was a success.

Your new mission is to restore the 'roles' and 'profiles' apps to the main **APPS menu** and the **plugin search results**.

You are an AI Coding Assistant. Your work must be precise, incremental, and non-breaking.

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
        1.  Run `git reset --hard HEAD`.
        2.  Run `python server.py` to capture the exact error.
        3.  Append the error to this file (`prompt.md`) before terminating.
5.  **Nix Environment:** You are always inside a `nix develop` shell. **Never** attempt to `pip install` packages.

### Current State and Context

  * You are on the git branch: `noplacelikehome`.
  * **Critical Failure Analysis:** The successful homepage configuration introduced a side-effect: the 'roles' and 'profiles' apps were deliberately filtered from the menus to avoid duplication when 'roles' was the homepage. Now that the homepage is 'introduction', this filtering is no longer necessary and prevents access to these core apps. We will remove this special-case filtering in favor of simplicity and consistent access.

### The Immediate Task: Restore Core Apps to Menus

Your mission is to ensure all steps of this plan are complete. **If your initial `git log` shows all steps are already committed, proceed directly to the "Completion Protocol."**

  * **Step 1: Restore 'roles' and 'profiles' to the main APPS Menu.**

      * **Action:** In `server.py`, remove the two lines that filter `roles` and `profiles` from the `group_apps_by_role` function using this exact `sed` command:
        ```bash
        sed -i "/if plugin_key in \['profiles', 'roles'\]:/,+1d" server.py
        ```
      * **Commit Message:** `refactor(server): Remove filter excluding roles & profiles from app menu`

  * **Step 2: Restore 'roles' and 'profiles' to the Plugin Search.**

      * **Action:** In `server.py`, remove the two lines that filter `roles` and `profiles` from the `search_plugins` function using this exact `sed` command:
        ```bash
        sed -i "/if module_name in \['profiles', 'roles'\]:/,+1d" server.py
        ```
      * **Commit Message:** `refactor(server): Remove filter excluding roles & profiles from search`

### Completion Protocol (Definition of Done)

You are **DONE** when `git log` shows that both steps above have been successfully committed and the `git status` is clean. The 'roles' and 'profiles' apps should now be visible in both the "APPS" dropdown menu and the search results.

When you determine the task is complete, perform the following actions to sign off:

1.  Announce the successful completion of the entire plan.
2.  Run `git log -n 2` one last time to display the successful commits as proof.
3.  Perform a "victory dance" by printing a simple, multi-line ASCII art of a key.
4.  Terminate the session.

-----

Your first action is to orient yourself with `git log`, `git status`, and `git diff`. Begin now.