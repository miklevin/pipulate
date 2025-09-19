### **`prompt.md`**

Hello Gemini.

You are waking up on the `steeltrap` branch. Your previous session was a success: you solidified the foundation by adding transparency to the backup and AI memory systems and created a powerful new CLI tool for database inspection.

Your new mission is to complete this foundational work by cleaning up obsolete code and verifying that your new tools function correctly.

**The Unbreakable Laws of Physics (Updated):**

1.  You are **always** in a Nix shell. You will **never** use `pip install`.
2.  You will **never** use `sed` for multi-line insertions or complex edits. You will **always** use the `read_file` -\> modify -\> `write_file` pattern for file modifications. Simple, single-line `sed` replacements are acceptable if you are confident.
3.  You will verify every change with `git diff`.
4.  You will commit after every single logical step.
5.  Your **Definition of Done** is when all steps are committed and `git status` is clean.
6.  Your **Completion Protocol** is to announce success with `echo "✅ Steeltrap protocol complete. Foundation is solid, clean, and verified."`

**The Mission: Cleanup and Verification**

-----

#### **Step 1: Architectural Cleanup**

We will remove the now-redundant and obsolete backup and migration scripts.

**Action 1: Delete the old backup system file.**

```bash
rm imports/conversation_backup_system.py
```

**Action 2: Delete the old migration script.**

```bash
rm imports/conversation_architecture_migration.py
```

**Verification:**

```bash
git status
```

**Commit:**

```bash
git commit -am "refactor(cleanup): Remove obsolete backup and migration scripts

Deletes `conversation_backup_system.py` and `conversation_architecture_migration.py`.

The durable backup system makes the former redundant, and the latter was a one-time migration script. This simplifies the codebase and removes dead code."
```

-----

#### **Step 2: Startup Verification**

Now, let's prove the transparency features you just built are working. We will restart the server and check the logs for the new summary tables.

**Action:**

```bash
touch server.py && sleep 8 && grep -E "Durable Backup Status|AI Keychain Memory" logs/server.log | tail -n 20
```

**Expected Output:** The `grep` command should display the headers and content of your two new `rich` tables from the server log, confirming they ran on startup.

-----

#### **Step 3: Tool Verification**

Finally, let's test the `db-inspect` CLI tool you created.

**Action 1: Inspect the AI Keychain.**

```bash
.venv/bin/python cli.py db-inspect keychain
```

**Action 2: Inspect the `conversation_messages` table in the discussion database.**

```bash
.venv/bin/python cli.py db-inspect discussion --table conversation_messages
```

**Expected Output:** Both commands should execute successfully and display `rich` tables in your console, proving the CLI tool is fully functional.

-----

Now, execute the `Completion Protocol`.
