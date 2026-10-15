import json
import os
import re
import argparse
import getpass
from datetime import datetime
from pathlib import Path
import sys

# Standard Config Location
CONFIG_DIR = Path.home() / ".config" / "pipulate"
TARGETS_FILE = Path(os.environ.get("PIPULATE_BLOGS_CONFIG", CONFIG_DIR / "blogs.json")).expanduser()
KEYS_FILE = CONFIG_DIR / "keys.json"
LAST_PUBLISHED_FILE = CONFIG_DIR / "last_published.json"

DEFAULT_TARGETS = {
    "1": {
        "name": "Trimnoir (Personal Journal)",
        "path": str(Path.home() / "repos" / "trimnoir" / "_posts"),
        "base_url": "https://mikelev.in",
        "permalink_prefix": "futureproof"
    }
}

def load_targets():
    """Loads targets from JSON or returns defaults."""
    if TARGETS_FILE.exists():
        try:
            with open(TARGETS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Warning: {TARGETS_FILE} is corrupt. Using defaults.")
    return DEFAULT_TARGETS


def canonical_target(spec):
    """argparse `type=` for -t: one key or alias in, the canonical key out.

    THE NAME IS THE KEY (2026-09-27). Every publishing script reads -t
    through add_standard_arguments below, so this one callable is where
    `-t grim` becomes `-t 2` for all of them at once, before any script
    looks a target up, records a marker under it, or hands it to the next
    script in a pipeline. The resolver is lsa.parse_target_spec, the same
    one `posts` and `rgx` read, so a name means the same thing in every
    lane; a spec naming several blogs is refused here, because a publish
    is one blog at a time and the many-blog spelling belongs to the
    readers. argparse applies a type to a string default too, so the
    default "1" passes through this as well. Raises ArgumentTypeError so
    argparse prints the roster the resolver already spells (2=grim ...).
    """
    import lsa
    targets = load_targets()
    try:
        keys = lsa.parse_target_spec(str(spec), targets)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc))
    if len(keys) != 1:
        raise argparse.ArgumentTypeError(
            f"-t names one blog here (got {spec!r} -> {', '.join(keys)}); "
            "posts and rgx take the many-blog spelling")
    return keys[0]


def record_last_published(target_key, file_path, target_name=None):
    """Record the article articleizer.py just wrote, keyed by target.

    confluenceizer.py --latest reads this to sync ONLY the freshly published
    file instead of sweeping the whole directory. Keying by target means a
    public-side publish (target 1) never shadows a private-side one (target 4).
    """
    target_key = str(target_key)
    data = {}
    if LAST_PUBLISHED_FILE.exists():
        try:
            with open(LAST_PUBLISHED_FILE, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    if not isinstance(data, dict):
        data = {}
    data[target_key] = {
        "path": str(Path(file_path).resolve()),
        "name": target_name,
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
    }
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LAST_PUBLISHED_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_last_published(target_key):
    """Return the recorded path for a target, or None if absent/stale/invalid."""
    target_key = str(target_key)
    if not LAST_PUBLISHED_FILE.exists():
        return None
    try:
        with open(LAST_PUBLISHED_FILE, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    entry = data.get(target_key) if isinstance(data, dict) else None
    if not entry:
        return None
    path = entry.get("path") if isinstance(entry, dict) else entry
    if path and Path(path).is_file():
        return path
    return None


def load_keys_dict():
    """Loads the entire keys dictionary from keys.json."""
    if KEYS_FILE.exists():
        try:
            with open(KEYS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"❌ Error: {KEYS_FILE} is corrupt.")
            sys.exit(1)
    return {}

def get_api_key(key_name=None):
    """Gets a specific named API key, falling back to 'default' or prompt."""
    key_name = key_name or "default"
    keys_dict = load_keys_dict()

    if key_name in keys_dict:
        return keys_dict[key_name]

    # Interactive fallback
    print(f"⚠️ API Key '{key_name}' not found in {KEYS_FILE}.")
    new_key = getpass.getpass(f"Enter the API key for '{key_name}' (any provider; --model names which): ").strip()

    if new_key:
        save = input(f"Save key '{key_name}' to config? (y/n): ").lower()
        if save == 'y':
            keys_dict[key_name] = new_key
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(KEYS_FILE, 'w') as f:
                json.dump(keys_dict, f, indent=2)
            KEYS_FILE.chmod(0o600)
            print(f"✅ Key '{key_name}' saved.")
        return new_key
    else:
        print("❌ No key provided. Exiting.")
        sys.exit(1)

def add_target_argument(parser):
    """Legacy helper - redirects to add_standard_arguments for backwards compatibility."""
    add_standard_arguments(parser)


def get_target_path(cli_args=None):
    """
    Determines the active project path.
    Priority:
    1. CLI Argument (--target)
    2. Default (Target "1")
    3. Interactive Selection (Fallback)
    """
    targets = load_targets()
    
    # If args provided and key exists, use it
    if cli_args and getattr(cli_args, 'target', None):
        key = str(cli_args.target)
        if key in targets:
            # Polish: Tell the user if it was explicit or defaulted
            if '-t' in sys.argv or '--target' in sys.argv:
                print(f"🎯 Target set via CLI: {targets[key]['name']}")
            else:
                print(f"🎯 Default target auto-selected: {targets[key]['name']}")
            return Path(targets[key]['path']).expanduser()
        else:
            print(f"❌ Invalid target key: {key}")
            sys.exit(1)

    # Interactive Mode (Fallback if cli_args is completely missing)
    print("\nSelect Target Repo:")
    for k, v in targets.items():
        print(f"  [{k}] {v['name']} ({v['path']})")
    
    choice = input("Enter choice (default 1): ").strip() or "1"
    
    if choice in targets:
        path = Path(targets[choice]['path']).expanduser()
        print(f"✅ Active Target: {targets[choice]['name']}")
        return path
    else:
        print("❌ Invalid selection.")
        sys.exit(1)

def add_standard_arguments(parser):
    """Unified API for all scripts."""
    # CRITICAL FIX: Inject default="1" here
    parser.add_argument('-t', '--target', type=canonical_target, default="1",
                        help="Target key or alias from blogs.json: 1 or article, 2 or grim (default: '1')")
    parser.add_argument('-k', '--key', type=str, help="API key alias from keys.json (e.g., 'pipulate')")


# ----------------------------------------------------------------------------
# Frontmatter stamping -- the 1-to-1 ledger (Jekyll post <-> Google Doc)
# ----------------------------------------------------------------------------
GDOC_URL_KEY = "gdoc_url"


def gdoc_share_url(file_id):
    """Canonical anyone-with-link share URL for a Google Doc file id."""
    return f"https://docs.google.com/document/d/{file_id}/edit?usp=sharing"


def gdoc_id_from_frontmatter(metadata):
    """Extract the Doc file id from a post's gdoc_url, or None if unstamped."""
    url = str((metadata or {}).get(GDOC_URL_KEY) or "").strip()
    match = re.search(r"/document/d/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None


def stamp_frontmatter_value(md_path, key, value, preserve_mtime=True):
    """Surgically upsert one single-line `key: value` in a post's YAML block.

    Deliberately NOT a parse->mutate->dump round-trip: pushing 1,200+ posts
    through a YAML dumper would churn quoting, folding, and key order across
    the whole corpus. This touches exactly one line inside the leading
    `--- ... ---` block, leaves every other byte alone, and (by default)
    restores the file's mtime so a bookkeeping stamp never masquerades as a
    content edit to mtime-based freshness logic.

    Returns one of: "ADDED", "UPDATED", "UNCHANGED", "NO_FRONTMATTER".
    """
    path = Path(md_path)
    original = path.read_text(encoding="utf-8")
    lines = original.split("\n")
    if not lines or lines[0].strip() != "---":
        return "NO_FRONTMATTER"
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return "NO_FRONTMATTER"

    new_line = f"{key}: {value}"
    key_re = re.compile(rf"^{re.escape(key)}\s*:")
    for i in range(1, end):
        if key_re.match(lines[i]):
            if lines[i] == new_line:
                return "UNCHANGED"
            lines[i] = new_line
            _write_text_preserving_mtime(path, "\n".join(lines), preserve_mtime)
            return "UPDATED"

    lines.insert(end, new_line)
    _write_text_preserving_mtime(path, "\n".join(lines), preserve_mtime)
    return "ADDED"


def _write_text_preserving_mtime(path, text, preserve_mtime):
    st = path.stat() if preserve_mtime else None
    path.write_text(text, encoding="utf-8")
    if st is not None:
        os.utime(path, (st.st_atime, st.st_mtime))


# ----------------------------------------------------------------------------
# Go-Go-Gadget Broadcast Kit (X.com Promo Tweet + YouTube Live Cut-and-Roll)
# ----------------------------------------------------------------------------
YT_TITLE_LIMIT = 100


def _yt_sanitize(text):
    """YouTube rejects '<' and '>' in both titles and descriptions."""
    return (text or "").replace("<", "[").replace(">", "]")


def format_youtube_title(title):
    """Build a <=100-char YouTube Live title from the article title."""
    clean = " ".join(_yt_sanitize(title).split())
    if not clean:
        return "LIVE: Honeybot AI Observatory"
    prefixed = f"LIVE: {clean}"
    if len(prefixed) <= YT_TITLE_LIMIT:
        return prefixed
    if len(clean) <= YT_TITLE_LIMIT:
        return clean
    cut = clean[: YT_TITLE_LIMIT - 3]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "..."


_DATED_POST_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-.+\.md$")


def _post_sort_key(md_path):
    """Sort dated posts by (YYYY-MM-DD, frontmatter sort_order, mtime)."""
    date_part = md_path.name[:10]
    sort_order = 0
    try:
        head = md_path.read_text(encoding="utf-8")[:2048]
        if head.startswith("---"):
            m = re.search(r"^sort_order:\s*(\d+)", head, re.MULTILINE)
            if m:
                sort_order = int(m.group(1))
    except Exception:
        pass
    try:
        mtime = md_path.stat().st_mtime
    except OSError:
        mtime = 0.0
    return (date_part, sort_order, mtime, md_path.name)


def _latest_post_for_target(target_key="1", slug_match=None):
    """Resolve the newest dated markdown post for target_key (or matching slug_match)."""
    targets = load_targets()
    tcfg = targets.get(str(target_key), targets.get("1", DEFAULT_TARGETS["1"]))
    posts_dir = Path(tcfg["path"]).expanduser()
    dated = [
        p for p in (posts_dir.glob("*.md") if posts_dir.is_dir() else [])
        if _DATED_POST_RE.match(p.name)
    ]
    if slug_match:
        needle = slug_match.lower().strip()
        dated = [p for p in dated if needle in p.name.lower()]
        if not dated:
            return None, tcfg
        dated.sort(key=_post_sort_key)
        return dated[-1], tcfg
    if not dated:
        return None, tcfg
    max_date = max(p.name[:10] for p in dated)
    recorded = get_last_published(target_key)
    if recorded and Path(recorded).is_file():
        rec_path = Path(recorded)
        if _DATED_POST_RE.match(rec_path.name) and rec_path.name[:10] >= max_date:
            return rec_path, tcfg
    same_day = [p for p in dated if p.name[:10] == max_date]
    same_day.sort(key=_post_sort_key)
    return same_day[-1], tcfg


def get_broadcast_kit(target_key="1", slug_match=None):
    """Extract {path, title, canonical_url, tweet, yt_title, yt_description} from the latest post."""
    import yaml
    post_path, tcfg = _latest_post_for_target(target_key, slug_match=slug_match)
    if not post_path or not post_path.is_file():
        return None
    raw = post_path.read_text(encoding="utf-8")
    fm = {}
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
            except Exception:
                fm = {}
            body = parts[2]
    title = str(fm.get("title") or post_path.stem)
    base_url = (tcfg.get("base_url") or "https://mikelev.in").rstrip("/")
    permalink = str(fm.get("permalink") or "")
    canonical_url = str(fm.get("canonical_url") or (f"{base_url}{permalink}" if permalink else base_url))
    meta_desc = str(fm.get("meta_description") or fm.get("excerpt") or "").strip()
    imprint = str(fm.get("description") or "").strip()
    tweet_match = re.search(
        r"###\s*🐦\s*X\.com Promo Tweet\s*\n```[a-zA-Z0-9]*\n(.*?)\n```",
        body,
        re.DOTALL,
    )
    if tweet_match:
        tweet = tweet_match.group(1).strip()
    else:
        tweet = f"{title}\n\n{canonical_url}"
    tags = " ".join(re.findall(r"#[A-Za-z0-9_]+", tweet))
    yt_title = format_youtube_title(title)
    desc_parts = [
        f"📖 Read the full article: {canonical_url}",
        "",
        f"🎙️ Now reading live on the Honeybot AI Observatory: \"{title}\"",
    ]
    if meta_desc:
        desc_parts.extend(["", meta_desc])
    if imprint and imprint != meta_desc:
        desc_parts.extend(["", imprint])
    desc_parts.extend([
        "",
        "---",
        "🔭 About this 24/7 Home-Hosted NixOS Broadcast:",
        "You are watching real-time Nginx access logs and AI crawler telemetry from mikelev.in.",
        "• Agents sending 'Accept: text/markdown' (RFC 9110) receive clean raw Markdown.",
        "• Agents executing JavaScript trigger the DOM trapdoor sensor.",
        f"• AI Context Manifest: {base_url}/llms.txt",
        "• Stack: NPvg (Nix, Python, Neovim, Git) — https://pipulate.com | https://qamy.ai",
    ])
    if tags:
        desc_parts.extend(["", tags])
    yt_description = _yt_sanitize("\n".join(desc_parts).strip())
    return {
        "path": str(post_path),
        "title": title,
        "canonical_url": canonical_url,
        "tweet": tweet,
        "yt_title": yt_title,
        "yt_description": yt_description,
    }


def _copy_to_clipboard(text):
    """Copy text to OS clipboard when interactive; detach xclip so pipes never hang."""
    if not sys.stdout.isatty():
        return False
    import subprocess
    cmd = ["pbcopy"] if sys.platform == "darwin" else ["xclip", "-selection", "clipboard"]
    try:
        subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except Exception:
        return False


def print_broadcast_kit(target_key="1", mode="card", slug_match=None):
    """Print or copy the broadcast kit (mode: card | tweet | title | desc)."""
    kit = get_broadcast_kit(target_key, slug_match=slug_match)
    if not kit:
        print("⚠️ No published post found for broadcast kit.")
        return 1
    if mode == "tweet":
        copied = _copy_to_clipboard(kit["tweet"])
        print(kit["tweet"])
        print(f"\n{'📋 Copied X.com Promo Tweet to clipboard!' if copied else 'ℹ️  (Non-TTY: printed only)'}")
        return 0
    if mode == "title":
        copied = _copy_to_clipboard(kit["yt_title"])
        print(kit["yt_title"])
        print(f"\n{'📋 Copied YouTube Live Title' if copied else 'ℹ️  YouTube Live Title'} ({len(kit['yt_title'])}/{YT_TITLE_LIMIT} chars)")
        return 0
    if mode == "desc":
        copied = _copy_to_clipboard(kit["yt_description"])
        print(kit["yt_description"])
        print(f"\n{'📋 Copied YouTube Live Description to clipboard!' if copied else 'ℹ️  (Non-TTY: printed only)'}")
        return 0
    bar = "=" * 72
    thin = "-" * 72
    print(f"\n{bar}")
    print(f"📡 GO-GO-GADGET BROADCAST KIT ({Path(kit['path']).name})")
    print(thin)
    print("🐦 X.COM PROMO TWEET (type `tweet` to copy):")
    print(kit["tweet"])
    print(thin)
    print(f"📺 YOUTUBE LIVE TITLE [{len(kit['yt_title'])}/{YT_TITLE_LIMIT} chars] (type `yttitle` to copy):")
    print(kit["yt_title"])
    print(thin)
    print("📝 YOUTUBE LIVE DESCRIPTION (type `ytdesc` to copy):")
    print(kit["yt_description"])
    print(thin)
    print("🎛️  Quick Copy Words:  tweet  |  yttitle  |  ytdesc  |  ytcard")
    print(bar)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipulate article common utilities & broadcast kit.")
    add_standard_arguments(parser)
    parser.add_argument(
        "--broadcast",
        choices=("card", "tweet", "title", "desc"),
        default="card",
        help="Print the broadcast card or copy tweet/title/desc to clipboard.",
    )
    parser.add_argument(
        "-s", "--slug",
        type=str,
        default=None,
        help="Optional substring to match a specific dated post filename.",
    )
    cli_args = parser.parse_args()
    sys.exit(print_broadcast_kit(cli_args.target, cli_args.broadcast, slug_match=cli_args.slug))
