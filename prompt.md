Hello Gemini.

You are waking up inside a Nix dev shell on the `steeltrap` branch to continue refactoring the Pipulate application. Your mission is to solidify the database, memory, and backup systems to ensure they are transparent, reliable, and architecturally sound.

**The Unbreakable Laws of Physics:**

1.  You are **always** in a Nix shell. You will **never** use `pip install`.
2.  You will **never** use the `replace` tool. You will only use `sed` for file modifications.
3.  You will verify every change with `git diff`.
4.  You will commit after every single logical change. This is non-negotiable.
5.  Your **Definition of Done** is when all steps in this plan are committed to the `steeltrap` branch and `git status` is clean.
6.  Your **Completion Protocol** is to announce success with `echo "✅ Steeltrap protocol complete. Foundation is solid."`

**The Mission: Solidify the Foundation**

We will proceed in four atomic steps. Execute them precisely.

-----

### **Step 1: Consolidate Backup Logic**

The `append_only_conversation.py` module uses a redundant, older backup system. We will disable it and rely solely on the superior `durable_backup_system.py` that runs at server startup.

**Action:** Comment out the call to `self._create_backup` in `imports/append_only_conversation.py`.

```bash
sed -i "s/self._create_backup(\"before_message_append\")/        # self._create_backup(\"before_message_append\") # Redundant: Durable backup runs on startup/" imports/append_only_conversation.py
```

**Verification:**

```bash
git diff
```

**Commit:**

```bash
git commit -am "refactor(backup): Consolidate backups to durable system

Removes redundant call to the older son/father/grandfather backup system from the append-only conversation module.

The durable_backup_system handles all critical database backups, including discussion.db, at server startup, making this call unnecessary and simplifying the architecture."
```

-----

### **Step 2: Enhance Startup Transparency**

We need to see that the backup and AI memory systems are working. We will add `rich` table summaries that print to the console on every server startup.

**Action 1: Add a summary method to `durable_backup_system.py`.**

```bash
cat << 'EOF' | sed -i '/^# 🎯 GLOBAL INSTANCE for easy import/i \\' imports/durable_backup_system.py && sed -i '$s/$/\n/' imports/durable_backup_system.py
    def get_backup_summary_table(self) -> "Table":
        """Generate a Rich Table summarizing the backup status."""
        from rich.table import Table
        table = Table(title="🛡️ Durable Backup Status", border_style="green", show_header=True, header_style="bold green")
        table.add_column("Database", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Backup Path", style="dim")
        for key in ['app_prod', 'app_dev', 'discussion', 'ai_keychain']:
            config = self.critical_databases.get(key)
            if not config: continue
            source_path = Path(config['source_path'])
            backup_path = self.backup_root / source_path.name
            if source_path.exists():
                if backup_path.exists():
                    status = f"✅ Backed Up ({backup_path.stat().st_size / 1024:.1f} KB)"
                else:
                    status = "❌ Not Found"
            else:
                status = "ℹ️ Source Missing"
            table.add_row(config['description'], status, str(backup_path))
        return table
EOF
```

**Action 2: Add a summary method to `ai_dictdb.py`.**

```bash
cat << 'EOF' | sed -i '/^# Create a single, reusable instance for the application/i \\' imports/ai_dictdb.py && sed -i '$s/$/\n/' imports/ai_dictdb.py
    def get_keychain_summary_table(self) -> "Table":
        """Generate a Rich Table summarizing the AI Keychain contents."""
        from rich.table import Table
        table = Table(title="🔑 AI Keychain Memory", border_style="yellow", show_header=True, header_style="bold yellow")
        table.add_column("Key", style="cyan", max_width=50)
        table.add_column("Value", style="magenta")
        try:
            items = list(self.items())
            if not items:
                table.add_row("[No keys found]", "")
                return table
            for key, value in items:
                display_value = (value[:75] + '...') if len(value) > 75 else value
                table.add_row(key, display_value)
        except Exception as e:
            table.add_row("Error", f"Could not read keychain: {e}")
        return table
EOF
```

**Action 3: Call these new methods from `server.py`'s startup event.**

```bash
sed -i "/story_moment(\"Workshop Ready\",/a \ \ \ \ # Display startup summary tables\n    try:\n        from imports.durable_backup_system import backup_manager as durable_backup_manager\n        from imports.ai_dictdb import keychain_instance\n        \n        # Display backup summary\n        backup_summary_table = durable_backup_manager.get_backup_summary_table()\n        print_and_log_table(backup_summary_table, \"STARTUP - \")\n\n        # Display AI Keychain summary\n        keychain_summary_table = keychain_instance.get_keychain_summary_table()\n        print_and_log_table(keychain_summary_table, \"STARTUP - \")\n\n    except Exception as e:\n        logger.error(f\"Failed to display startup summary tables: {e}\")" server.py
```

**Verification:**

```bash
git diff
```

**Commit:**

```bash
git commit -am "feat(startup): Add transparent summary tables for backups and AI memory

Implements two new methods:
- durable_backup_system.get_backup_summary_table()
- ai_dictdb.get_keychain_summary_table()

These are now called from the server startup event to print rich tables to the console, providing immediate, transparent feedback on the status of critical data stores. This addresses the need for assurance that the systems are working correctly."
```

-----

### **Step 3: Build the CLI Database Inspector**

This creates a powerful new capability for both you and the AI, addressing your request for a command-line DB tool.

**Action: Add the `db-inspect` command and its logic to `cli.py`.**

```bash
sed -i "/from rich.table import Table/a import sqlite3" cli.py

cat << 'EOF' | sed -i '/^def parse_tool_arguments(args: list) -> dict:/i \\' cli.py && sed -i '$s/$/\n/' cli.py
def inspect_database(db_path_str: str, table_name: str = None):
    """Inspects an SQLite database, showing tables or table contents."""
    db_path = Path(db_path_str)
    if not db_path.exists():
        console.print(f"❌ [bold red]Error:[/bold red] Database file not found at {db_path}")
        return
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        if not table_name:
            # List all tables in the database
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            table_list = [t[0] for t in tables]
            table_view = Table(title=f"Tables in {db_path.name}")
            table_view.add_column("Table Name", style="cyan")
            table_view.add_column("Row Count", style="magenta", justify="right")
            for tbl in table_list:
                cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
                count = cursor.fetchone()[0]
                table_view.add_row(tbl, str(count))
            console.print(table_view)
            console.print(f"\n💡 To view a table's content, use: [bold white].venv/bin/python cli.py db-inspect {db_path.name.split('.')[0].replace('_dev','_dev')} --table [table_name][/bold white]")
        else:
            # Display contents of a specific table
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 50")
            rows = cursor.fetchall()
            table_view = Table(title=f"Contents of '{table_name}' in {db_path.name} (first 50 rows)")
            for col in columns:
                table_view.add_column(col, style="cyan")
            for row in rows:
                table_view.add_row(*[str(item) for item in row])
            console.print(table_view)
    except sqlite3.Error as e:
        console.print(f"❌ [bold red]Database Error:[/bold red] {e}")
    finally:
        if 'conn' in locals():
            conn.close()

EOF

sed -i "/subparsers.add_parser('uninstall',/a \ \ \ \ # Command: db-inspect\n    inspect_parser = subparsers.add_parser('db-inspect', help='Inspect SQLite databases.')\n    inspect_parser.add_argument('db_name', choices=['main_dev', 'main_prod', 'discussion', 'keychain'], help='The database to inspect.')\n    inspect_parser.add_argument('--table', type=str, help='The specific table to view.')" cli.py

sed -i "/elif args.command == 'call':/i \ \ \ \ elif args.command == 'db-inspect':\n        db_map = {\n            'main_dev': 'data/botifython_dev.db',\n            'main_prod': 'data/botifython.db',\n            'discussion': 'data/discussion.db',\n            'keychain': 'data/ai_keychain.db'\n        }\n        db_path = db_map.get(args.db_name)\n        if db_path:\n            inspect_database(db_path, args.table)\n        else:\n            console.print(f\"❌ Unknown database alias: {args.db_name}\")\n" cli.py
```

**Verification:**

```bash
git diff
```

**Commit:**

```bash
git commit -am "feat(cli): Add db-inspect command for database transparency

Introduces a new 'db-inspect' command to the CLI. This tool allows developers and AI agents to inspect the contents of the application's SQLite databases directly from the command line, addressing the need for a GUI-free way to verify data.

- List tables and row counts for a given database.
- Display the first 50 rows of a specific table.
- Supports main, discussion, and keychain databases."
```

-----

### **Step 4: Cleanup Obsolete Imports**

Now that we've consolidated and verified, we can safely remove the old, redundant systems.

**Action:** Remove the import of `conversation_backup_system` from `server.py`, as it's no longer used.

```bash
sed -i "/from imports.ascii_displays import (/,/system_diagram, white_rabbit)/{/conversation_backup_system,/d}" server.py
```

**Verification:**

```bash
git diff
```

**Commit:**

```bash
git commit -am "refactor(imports): Remove obsolete conversation_backup_system import

The durable_backup_system now handles all backup responsibilities. The older, redundant conversation_backup_system is no longer needed or called. This change removes the dead code and simplifies the import structure."
```

-----

Now, execute the `Completion Protocol`.
