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
    editorial_match = re.search(
        r"###\s*Ai Editorial Take\s*\n(.*?)(?=\n#{2,3}\s|\Z)",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    ai_take = editorial_match.group(1).strip() if editorial_match else ""
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
    if ai_take:
        desc_parts.extend(["", "🤖 AI Editorial Take:", ai_take])
    elif imprint and imprint != meta_desc:
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
    preview_port = tcfg.get("preview_port", 4001)
    preview_url = f"http://localhost:{preview_port}{permalink}"
    return {
        "path": str(post_path),
        "title": title,
        "canonical_url": canonical_url,
        "preview_url": preview_url,
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
    print("🎛️  Quick Words:  tweet | yttitle | ytdesc | ytcard | ytsay | ytroll | ytbell | ytstatus")
    print(thin)
    print(f"🔗 Preview URL:   {kit['preview_url']}")
    print(f"✏️  Edit Command:  vim {kit['path']}")
    print(bar)
    return 0


HONEYBOT_SSH_HOST = os.environ.get("PIPULATE_HONEYBOT_HOST", "honeybot")

_HONEYBOT_OBS_HELPER = r'''
import base64, hashlib, json, os, pathlib, socket, struct, subprocess, sys, time

mode = sys.argv[1] if len(sys.argv) > 1 else "status"
cfg_path = pathlib.Path.home() / ".config/obs-studio/plugin_config/obs-websocket/config.json"
trig_path = pathlib.Path.home() / "www/mikelev.in/.reading_trigger"

def load_ws_cfg():
    if cfg_path.is_file():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def ws_recv_json(sock):
    hdr = sock.recv(2)
    if len(hdr) < 2:
        raise RuntimeError("EOF reading WS header")
    length = hdr[1] & 0x7F
    if length == 126:
        length = struct.unpack(">H", sock.recv(2))[0]
    elif length == 127:
        length = struct.unpack(">Q", sock.recv(8))[0]
    masked = bool(hdr[1] & 0x80)
    mask_key = sock.recv(4) if masked else b""
    payload = bytearray()
    while len(payload) < length:
        chunk = sock.recv(length - len(payload))
        if not chunk:
            break
        payload.extend(chunk)
    if masked:
        payload = bytearray(b ^ mask_key[i % 4] for i, b in enumerate(payload))
    return json.loads(payload.decode("utf-8", errors="replace"))

def ws_send_json(sock, obj):
    raw = json.dumps(obj).encode("utf-8")
    mask_key = os.urandom(4)
    header = bytearray([0x81])
    n = len(raw)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack(">H", n))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack(">Q", n))
    header.extend(mask_key)
    masked = bytearray(b ^ mask_key[i % 4] for i, b in enumerate(raw))
    sock.sendall(header + masked)

def obs_ws_request(req_type):
    cfg = load_ws_cfg()
    port = int(cfg.get("server_port") or 4455)
    password = str(cfg.get("server_password") or "")
    sock = socket.create_connection(("127.0.0.1", port), timeout=5.0)
    try:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        req = (
            f"GET / HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(req.encode("ascii"))
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = sock.recv(1024)
            if not chunk:
                raise RuntimeError("WS handshake failed")
            resp += chunk
        hello = ws_recv_json(sock)
        auth_info = (hello.get("d") or {}).get("authentication")
        ident = {"rpcVersion": 1}
        if auth_info:
            salt = auth_info.get("salt", "")
            challenge = auth_info.get("challenge", "")
            sec_hash = hashlib.sha256((password + salt).encode("utf-8")).digest()
            sec_b64 = base64.b64encode(sec_hash).decode("ascii")
            auth_hash = hashlib.sha256((sec_b64 + challenge).encode("utf-8")).digest()
            ident["authentication"] = base64.b64encode(auth_hash).decode("ascii")
        ws_send_json(sock, {"op": 1, "d": ident})
        identified = ws_recv_json(sock)
        if identified.get("op") != 2:
            raise RuntimeError(f"WS auth/identify rejected: {identified}")
        ws_send_json(sock, {"op": 6, "d": {"requestType": req_type, "requestId": "pip-1"}})
        while True:
            msg = ws_recv_json(sock)
            if msg.get("op") == 7 and (msg.get("d") or {}).get("requestId") == "pip-1":
                return msg.get("d") or {}
    finally:
        sock.close()

def lower_obs_window():
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":10.0")
    subprocess.run(
        ["wmctrl", "-x", "-r", "obs.obs", "-b", "add,below"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

def ring_bell():
    ts = str(int(time.time()))
    trig_path.parent.mkdir(parents=True, exist_ok=True)
    trig_path.write_text(ts + "\n", encoding="utf-8")
    print(f"🔔 Rang Honeybot .reading_trigger={ts} ({trig_path})")

def get_obs_pid():
    for p in sorted(pathlib.Path("/proc").glob("[0-9]*/cmdline")):
        try:
            raw = p.read_bytes()
            if not raw:
                continue
            arg0 = raw.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
            if os.path.basename(arg0) in ("obs", ".obs-wrapped"):
                return p.parent.name
        except Exception:
            continue
    return ""

if mode == "bell":
    ring_bell()
    sys.exit(0)

if mode == "enable-ws":
    pid = get_obs_pid()
    saved_env = {}
    if pid and pathlib.Path(f"/proc/{pid}/environ").is_file():
        raw_env = pathlib.Path(f"/proc/{pid}/environ").read_bytes().split(b"\x00")
        for item in raw_env:
            if b"=" in item:
                k, v = item.split(b"=", 1)
                ks = k.decode("utf-8", errors="ignore")
                if ks in ("DISPLAY", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS", "PULSE_SERVER", "PIPEWIRE_RUNTIME_DIR", "HOME", "USER", "PATH", "XAUTHORITY"):
                    saved_env[ks] = v.decode("utf-8", errors="ignore")
    if pid:
        print(f"🛑 Closing OBS (pid={pid}) cleanly to persist server_enabled=True...")
        subprocess.run(["kill", "-TERM", pid], check=False)
        for _ in range(30):
            if not get_obs_pid():
                break
            time.sleep(0.5)
        if get_obs_pid():
            subprocess.run(["kill", "-KILL", pid], check=False)
            for _ in range(10):
                if not get_obs_pid():
                    break
                time.sleep(0.5)
    sentinel_dir = pathlib.Path.home() / ".config/obs-studio/.sentinel"
    if sentinel_dir.is_dir():
        for sf in sentinel_dir.glob("*"):
            try:
                sf.unlink()
            except Exception:
                pass
    elif sentinel_dir.is_file():
        try:
            sentinel_dir.unlink()
        except Exception:
            pass
    cfg = load_ws_cfg()
    cfg["server_enabled"] = True
    cfg.setdefault("server_port", 4455)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(f"✅ Enabled obs-websocket in {cfg_path} (port={cfg['server_port']})")
    launch_env = os.environ.copy()
    launch_env.update(saved_env)
    launch_env.setdefault("DISPLAY", ":10.0")
    launch_env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    subprocess.Popen(
        ["obs", "--startstreaming", "--disable-shutdown-check"],
        env=launch_env,
        cwd=str(pathlib.Path.home()),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(20):
        time.sleep(1.0)
        try:
            st = obs_ws_request("GetStreamStatus")
            if not (st.get("requestStatus") or {}).get("result"):
                continue
            resp = st.get("responseData") or {}
            lower_obs_window()
            print(f"✅ OBS relaunched, lowered behind stream & WebSocket 4455 LIVE: outputActive={resp.get('outputActive')}")
            sys.exit(0)
        except Exception:
            pass
    print("⚠️ OBS launched, but port 4455 did not answer within 20s.")
    sys.exit(1)

if mode == "status":
    pid = get_obs_pid()
    cfg = load_ws_cfg()
    trig = trig_path.read_text(encoding="utf-8").strip() if trig_path.is_file() else "absent"
    print(f"📡 Honeybot OBS: pid={pid or 'NONE'} | ws_enabled={cfg.get('server_enabled')} | port={cfg.get('server_port', 4455)} | trigger={trig}")
    if cfg.get("server_enabled"):
        try:
            st = obs_ws_request("GetStreamStatus")
            resp = st.get("responseData") or {}
            print(f"🎥 Stream Status: outputActive={resp.get('outputActive')} | timecode={resp.get('outputTimecode')}")
        except Exception as e:
            print(f"⚠️ WebSocket 4455 unreachable: {e}")
    else:
        print("ℹ️  obs-websocket is currently disabled. Run `ytroll enable-ws` once to activate remote control.")
    sys.exit(0)

cfg = load_ws_cfg()
if not cfg.get("server_enabled"):
    print("⚠️ obs-websocket is disabled on Honeybot. Run `ytroll enable-ws` once to enable port 4455.")
    sys.exit(1)

if mode in ("stop", "roll"):
    res = obs_ws_request("StopStream")
    print(f"⏹️  OBS StopStream sent (status={res.get('requestStatus', {}).get('code')})")
    for _ in range(15):
        time.sleep(0.5)
        st = (obs_ws_request("GetStreamStatus").get("responseData") or {})
        if not st.get("outputActive"):
            print("✅ OBS stream stopped cleanly.")
            break

if mode == "roll":
    print("⏳ Waiting 4s for YouTube RTMP session boundary...")
    time.sleep(4.0)

if mode in ("start", "roll"):
    lower_obs_window()
    res = obs_ws_request("StartStream")
    print(f"▶️  OBS StartStream sent (status={res.get('requestStatus', {}).get('code')})")
    for _ in range(15):
        time.sleep(0.5)
        st = (obs_ws_request("GetStreamStatus").get("responseData") or {})
        if st.get("outputActive"):
            print(f"✅ OBS stream LIVE (timecode={st.get('outputTimecode')}).")
            break
    ring_bell()
'''


def run_honeybot_obs(mode="status"):
    """Execute remote OBS WebSocket / bell control on Honeybot over SSH."""
    import subprocess
    res = subprocess.run(
        ["ssh", HONEYBOT_SSH_HOST, "python3", "-", mode],
        input=_HONEYBOT_OBS_HELPER,
        text=True,
    )
    return res.returncode


def _read_from_clipboard():
    """Read text from the OS clipboard for `ytsay --clip`."""
    import subprocess
    cmd = ["pbpaste"] if sys.platform == "darwin" else ["xclip", "-selection", "clipboard", "-o"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return ""


_HONEYBOT_LIVE_MSG_HELPER = r'''
import base64, pathlib, sys

raw = base64.b64decode(sys.argv[1].encode("ascii")).decode("utf-8")
p = pathlib.Path.home() / "www/mikelev.in/.live_message"
p.parent.mkdir(parents=True, exist_ok=True)
tmp = p.with_suffix(".tmp")
tmp.write_text(raw, encoding="utf-8")
tmp.replace(p)
print(f"📡 Live break-in queued on Honeybot: {p}")
'''


def send_honeybot_live_message(
    say_text,
    card_label=None,
    patronus_key=None,
    pre_pause=3.0,
    linger=2.5,
    dry_run=False,
):
    """Send a one-shot live operator break-in (.live_message) to Honeybot over SSH."""
    import base64
    import subprocess
    import time
    clean_say = " ".join((say_text or "").strip().split())
    if not clean_say and not card_label and not patronus_key:
        print("Usage: ytsay [-c 'CARD\\nTEXT'] [-p patronus_key] [--pre 3.0] [--linger 2.5] [--clip] [--dry-run] 'Message to speak live'")
        return 1
    if card_label is None:
        resolved_card = "" if patronus_key else "LIVE\nFROM MIKE"
    else:
        resolved_card = str(card_label).replace("\\n", "\n")
    payload = {
        "card": resolved_card,
        "say": clean_say,
        "pre_pause": float(pre_pause),
        "linger": float(linger),
        "sent_at": int(time.time()),
    }
    if patronus_key:
        payload["patronus"] = str(patronus_key).strip()
    payload_json = json.dumps(payload, indent=2)
    if dry_run:
        print("📡 [DRY RUN] Live break-in payload for Honeybot:")
        print(payload_json)
        return 0
    payload_b64 = base64.b64encode(payload_json.encode("utf-8")).decode("ascii")
    res = subprocess.run(
        ["ssh", HONEYBOT_SSH_HOST, "python3", "-", payload_b64],
        input=_HONEYBOT_LIVE_MSG_HELPER,
        text=True,
    )
    if res.returncode == 0:
        preview_card = resolved_card.replace("\n", " | ") if resolved_card else f"PATRONUS:{patronus_key}"
        print(f"🎙️  Card: [{preview_card}] | Say: {clean_say!r}")
    return res.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipulate article common utilities & broadcast kit.")
    add_standard_arguments(parser)
    parser.add_argument(
        "--broadcast",
        choices=("card", "tweet", "title", "desc", "status", "bell", "stop", "start", "roll", "enable-ws", "say"),
        default="card",
        help="Print/copy broadcast kit or control Honeybot (status|bell|stop|start|roll|enable-ws|say).",
    )
    parser.add_argument(
        "-s", "--slug",
        type=str,
        default=None,
        help="Optional substring to match a specific dated post filename.",
    )
    parser.add_argument(
        "-c", "--card",
        type=str,
        default=None,
        help="Figlet card label for --broadcast say (use \\n for multiple lines; default: LIVE\\nFROM MIKE).",
    )
    parser.add_argument(
        "-p", "--patronus",
        type=str,
        default=None,
        help="Optional figurate ASCII art key (e.g. white_rabbit) for --broadcast say.",
    )
    parser.add_argument(
        "--clip",
        action="store_true",
        help="Read the spoken message from the OS clipboard for --broadcast say.",
    )
    parser.add_argument(
        "--pre",
        type=float,
        default=3.0,
        help="Seconds of pre-banner silence after cutting article audio (default: 3.0).",
    )
    parser.add_argument(
        "--linger",
        type=float,
        default=2.5,
        help="Seconds the banner hovers silently after speech before POOF (default: 2.5).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the .live_message JSON payload without sending over SSH.",
    )
    parser.add_argument(
        "message",
        nargs="*",
        help="Spoken message words for --broadcast say.",
    )
    cli_args = parser.parse_args()
    if cli_args.broadcast == "say":
        msg_text = _read_from_clipboard() if cli_args.clip else " ".join(cli_args.message)
        sys.exit(
            send_honeybot_live_message(
                msg_text,
                card_label=cli_args.card,
                patronus_key=cli_args.patronus,
                pre_pause=cli_args.pre,
                linger=cli_args.linger,
                dry_run=cli_args.dry_run,
            )
        )
    if cli_args.broadcast in ("status", "bell", "stop", "start", "roll", "enable-ws"):
        sys.exit(run_honeybot_obs(cli_args.broadcast))
    sys.exit(print_broadcast_kit(cli_args.target, cli_args.broadcast, slug_match=cli_args.slug))
