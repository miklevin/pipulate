import subprocess
import sys
import time
import shlex
import shutil
import argparse
from pathlib import Path
import common


def brand_markdown_files(target_path, verbose=False):
    """Sweeps the posts directory and swaps **Me**: for the semantic brand."""
    if verbose:
        print("\n--- 🏷️  Branding Markdown Files ---")
    count = 0
    # Search all markdown files in the target directory
    for md_file in target_path.glob("*.md"):
        content = md_file.read_text(encoding='utf-8')
        if "**Me**:" in content:
            content = content.replace("**Me**:", "**MikeLev.in**:")
            md_file.write_text(content, encoding='utf-8')
            count += 1
    
    if count > 0:
        print(f"🏷️  Applied semantic branding to {count} file(s).")
    elif verbose:
        print("✅ All files are perfectly branded.")


def prune_orphan_shards(target_path, verbose=False):
    """Delete _context/<stem>.json whose post no longer sits in _posts."""
    # THE ORPHAN PRUNE (2026-09-26, the day a post changed lanes). A post
    # moved to another lane, renamed or deleted leaves its shard behind, and
    # nothing reads an orphan except a census. Runs before the pipeline in
    # every lane, so a lane never carries a shard for a post it does not
    # hold, and the shard for the post's new home is written by that lane's
    # own contextualizer pass. Only dated stems are touched: anything else
    # that may live in _context is not a shard and is left alone.
    context_dir = target_path / "_context"
    if not context_dir.is_dir():
        return
    removed = 0
    for shard in sorted(context_dir.glob("*.json")):
        if not (shard.stem[:4].isdigit() and shard.stem[4:5] == "-"):
            continue
        if any((target_path / f"{shard.stem}{ext}").exists() for ext in (".md", ".markdown")):
            continue
        shard.unlink()
        print(f"🧹 Orphan shard removed: {shard.name}")
        removed += 1
    if removed == 0 and verbose:
        print("✅ No orphan shards.")


def run_step(script_name, target_key, extra_args=None, verbose=False):
    if verbose:
        print(f"\n--- 🚀 Step: {script_name} ---")
    start = time.time()

    # We pass the target key to every script. Pipeline entries may carry
    # their own flags (e.g. "googledocizer.py --yes --latest"); shlex keeps
    # bare "script.py" entries byte-identical in behavior.
    cmd = [sys.executable, *shlex.split(script_name), "-t", target_key]

    # Now all scripts accept standard arguments, safely pass them down
    if extra_args:
        cmd.extend(extra_args)

    try:
        # check=True ensures we stop if a step fails
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(f"❌ Critical Failure in {script_name}. Stopping pipeline.")
        sys.exit(1)
        
    duration = time.time() - start
    print(f"✅ {script_name} complete ({duration:.2f}s).")

# THE ARTIFACT GUARD (2026-09-26). This copied whatever graph.json, llms.txt
# and sitemap*.xml were lying in scripts/articles into the target's site
# root, with no check on which lane had made them: `preview -t 3` after a
# public preview would have dropped the public site's llms.txt and sitemaps
# into the private repo. `since` is the run's start time; an artifact older
# than that was made by another lane's run and stays where it is, and the
# skip is printed so a missing sync is never silent.
# WITNESSED 2026-09-26: the first guarded `preview -t 3` printed thirteen
# skips and copied nothing. The existence of graph.json or llms.txt in a
# private site root does NOT witness this guard: a pre-guard run had
# already left the public lane's copies there, so a probe on existence
# reads the same before and after, and only the skip lines discriminate.
# Those leftovers are removed by hand; nothing here deletes in a site root.
def sync_data_to_jekyll(target_path, since=0.0, verbose=False):
    """
    Copies the generated artifacts to the Jekyll SITE ROOT.
    """
    if verbose:
        print("\n--- 📦 Syncing Data to Jekyll ---")
    
    # Source is local to this script
    script_dir = Path(__file__).parent
    
    # Artifacts to sync
    artifacts = {
        "graph.json": "graph.json",
        "llms.txt": "llms.txt",
        "robots.txt": "robots.txt",
    }
    
    # target_path is usually .../trimnoir/_posts
    # We want the site root: .../trimnoir/
    repo_root = target_path.parent
    
    # ONE LINE FOR THE SKIPS (2026-10-05): a lane whose pipeline makes none
    # of these printed one skip per file, twelve lines each preview -t bot.
    # The count still says the guard fired; a nonzero count is the receipt.
    stale = []
    synced = []
    # Sync static artifacts
    for filename, dest_name in artifacts.items():
        source = script_dir / filename
        dest = repo_root / dest_name
        
        if source.exists() and source.stat().st_mtime < since:
            stale.append(filename)
            continue
        if source.exists():
            shutil.copy2(source, dest)
            synced.append(filename)
            if verbose:
                print(f"✅ Synced {filename} -> {dest}")
        else:
            print(f"⚠️ Warning: {filename} not found. Skipping sync.")

    # Sync dynamic sitemaps (sitemap.xml, sitemap-core.xml, sitemap-branch-0.xml, etc.)
    for sitemap in script_dir.glob("sitemap*.xml"):
        if sitemap.stat().st_mtime < since:
            stale.append(sitemap.name)
            continue
        dest = repo_root / sitemap.name
        shutil.copy2(sitemap, dest)
        synced.append(sitemap.name)
        if verbose:
            print(f"✅ Synced {sitemap.name} -> {dest}")
    if synced and not verbose:
        print(f"📦 Synced {len(synced)} artifact(s) -> {repo_root.name}/")
    if stale:
        print(f"⏭️  {len(stale)} artifact(s) predate this run; another lane made them. Not synced.")


def sync_observatory_metrics(target_key, target_path, verbose=False):
    """Sync live Honeybot AI Observatory metrics into _data/observatory.json and index.md for Target 1."""
    if str(target_key) != "1":
        return
    import json
    import re
    repo_root = target_path.parent
    pipulate_root = Path(__file__).resolve().parents[2]
    if str(pipulate_root) not in sys.path:
        sys.path.insert(0, str(pipulate_root))
    try:
        import prompt_foo
        stats = prompt_foo.fetch_honeybot_stats()
    except Exception as exc:
        if verbose:
            print(f"⚠️ Could not fetch Honeybot stats: {exc}")
        return
    metrics = (stats or {}).get("metrics") or {}
    md_raw = metrics.get("markdown", "")
    hyd_raw = metrics.get("hydration", "")
    if "|" not in md_raw or "|" not in hyd_raw:
        return
    md_count_s, md_pct_s = (p.strip() for p in md_raw.split("|", 1))
    hyd_ips_s, hyd_trig_s = (p.strip() for p in hyd_raw.split("|", 1))
    try:
        md_count_fmt = f"{int(md_count_s):,}"
    except ValueError:
        md_count_fmt = md_count_s
    try:
        hyd_trig_fmt = f"{int(hyd_trig_s):,}"
    except ValueError:
        hyd_trig_fmt = hyd_trig_s
    try:
        hyd_ips_fmt = f"{int(hyd_ips_s):,}"
    except ValueError:
        hyd_ips_fmt = hyd_ips_s
    fetched_at = str((stats or {}).get("fetched_at") or "unknown")
    payload = {
        "markdown_reads": md_count_fmt,
        "markdown_pct": f"{md_pct_s}%",
        "js_trapdoor_triggers": hyd_trig_fmt,
        "js_trapdoor_ips": hyd_ips_fmt,
        "fetched_at": fetched_at,
    }
    data_dir = repo_root / "_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    obs_file = data_dir / "observatory.json"
    new_json = json.dumps(payload, indent=2) + "\n"
    old_json = obs_file.read_text(encoding="utf-8") if obs_file.exists() else ""
    if new_json != old_json:
        obs_file.write_text(new_json, encoding="utf-8")
    index_file = repo_root / "index.md"
    if index_file.exists():
        idx_text = index_file.read_text(encoding="utf-8")
        banner = (
            "<!-- START_OBSERVATORY_METRICS -->\n"
            '<div class="observatory-metrics-banner" role="region" aria-label="Live AI Crawler Telemetry">\n'
            "  <strong>🔭 Live Bare-Metal AI Observatory Telemetry (No CDN · Direct Nginx Wire Truth):</strong>\n"
            "  <ul>\n"
            f"    <li><strong>Do AI Crawlers Execute JavaScript? (DOM Hydration Trapdoor):</strong> <strong>{hyd_trig_fmt}</strong> verified client-side JS executions across <strong>{hyd_ips_fmt}</strong> non-local crawler IPs (including <code>OAI-SearchBot</code> and <code>GPTBot</code> triggering <code>js_confirm.gif</code>).</li>\n"
            f"    <li><strong>Which AI Bots Negotiate Raw Markdown? (RFC 9110 <code>Accept: text/markdown</code>):</strong> <strong>{md_count_fmt}</strong> proactive Markdown reads (<strong>{md_pct_s}%</strong> of all origin responses served as raw <code>text/markdown</code>).</li>\n"
            "  </ul>\n"
            f'  <small>Snapshot: <code>{fetched_at}</code> · Watch live bot hits in real time on <a href="https://www.youtube.com/@MikeLevin/live">YouTube Live</a>.</small>\n'
            "</div>\n"
            "<!-- END_OBSERVATORY_METRICS -->"
        )
        new_idx, n = re.subn(
            r"<!-- START_OBSERVATORY_METRICS -->.*?<!-- END_OBSERVATORY_METRICS -->",
            banner,
            idx_text,
            flags=re.DOTALL,
        )
        if n and new_idx != idx_text:
            index_file.write_text(new_idx, encoding="utf-8")
    print(f"🔭 AI Observatory metrics synced: {md_count_fmt} RFC 9110 Markdown reads ({md_pct_s}%), {hyd_trig_fmt} JS trapdoor triggers ({fetched_at}).")

def main():
    parser = argparse.ArgumentParser(description="Update all Pipulate graphs")
    common.add_standard_arguments(parser)
    parser.add_argument('-m', '--keys', type=str, help="Pass a comma-separated list of keys for rotation")
    parser.add_argument('-v', '--verbose', action='store_true', help="Verbose output (show routine announcements and individual file syncs).")

    args = parser.parse_args()
    
    # 1. Resolve the Target Key ONCE
    targets = common.load_targets()
    target_key = args.target

    if target_key not in targets:
        print(f"❌ Invalid target key: {target_key}")
        sys.exit(1)

    # Resolve actual path for file operations
    target_path = Path(targets[target_key]['path']).expanduser().resolve()
    
    # THE JIU-JITSU SWEEP: Dynamically pull the pipeline array from the JSON config
    # THE PRIVATE LANES HAVE NO PUBLISH WORD (banked 2026-09-26, the day
    # the Grimoire's backlog closed at 151 posts, 151 shards). Lanes 1 and
    # 4 are dismounted by `publish` and `gobot`, which run this pipeline
    # and commit; lanes 2 and 3 are dismounted by nothing, so `preview -t N`
    # IS their dismount, typed by hand, and a shard backlog on a private
    # lane means nobody typed it. The per-lane list below is the whole of
    # what a lane gets; the word that runs it is the whole of when.
    pipeline_scripts = targets[target_key].get('pipeline', [])
    
    print(f"\n🔒 Locked Target: {targets[target_key]['name']}")
    print(f"🛤️  Active Pipeline: {len(pipeline_scripts)} steps")

    # Pack the extra arguments
    extra_args = []
    if args.key:
        extra_args.extend(['-k', args.key])
    if args.keys:
        extra_args.extend(['-m', args.keys])

    # 1.5 THE BRANDING SWEEP (Run this right before the JIU-JITSU Sweep!)
    brand_markdown_files(target_path, verbose=args.verbose)
    prune_orphan_shards(target_path, verbose=args.verbose)
    common.ensure_indexnow_key_file(target_key)
    sync_observatory_metrics(target_key, target_path, verbose=args.verbose)

    # 2. Run the sequence
    total_start = time.time()
    
    for script in pipeline_scripts:
        run_step(script, target_key, extra_args, verbose=args.verbose)
    
    # 3. Sync Data
    sync_data_to_jekyll(target_path, since=total_start, verbose=args.verbose)
        
    total_duration = time.time() - total_start
    print(f"\n✨ All steps completed successfully in {total_duration:.2f}s.")

if __name__ == "__main__":
    main()
