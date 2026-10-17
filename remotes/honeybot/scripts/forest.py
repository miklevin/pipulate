#!/usr/bin/env python3
"""
🌲 forest.py -- The station-break (forest) roll.

The trees roll is the reverse-chronological article reading in show.py. The
forest roll is this slow, front-loaded necklace of self-contained "beads" -- the
station-identification breaks that interleave between articles.

Each bead is an ordered cue-list in the SAME sheet-music grammar perform_show
already speaks: ("SAY", text), ("PATRONUS", key-or-dict), ("WINDOW",
"script.py:seconds[:arg]"), ("VISIT", url), ("WAIT", seconds), ("CLOSE", _).
That is the cathedral-of-one collapse: the forest inherits the full brush set
through the existing dispatcher instead of carrying its own special-cased
unpacking. Editing the forest is now editing data here, not the threading-heavy
engine in stream.py.

ORDER IS PRIORITY: _station_index resets to 0 on every process restart
(episodic by design), so bead 0 is the highest-traffic "opening commercial."
A viewer who tunes in mid-stream must be able to make sense of any single bead
cold -- no bead may depend on having heard its predecessor.

WINDOW grammar note: the optional third field is a single argument forwarded to
the script (e.g. the Figlet card label). It is delimited by ':' so the argument
must not itself contain a colon. Bare labels like "THE ITCH" are fine.
"""

# A bead is a list of (command, content) cues, played top-to-bottom during a
# break. Convention: card banner first, then art + spiel + proof report.
STATION_SEGMENTS = [
    [
        # The opening bead. The title card flashes, then the ingress-to-broadcast
        # diagram lands and breathes (a silent WAIT) before the narration walks it
        # left to right. No live report dashboard here yet -- see the parked
        # placeholder at the foot of the bead. Tune the PATRONUS duration by ear:
        # it should outlast the spoken walkthrough so the art never blinks out
        # mid-sentence.
        ("CARD", {
            "label": "HONEYBOT",
            "say": (
                "Hello, and welcome to Future-proofing with the Honeybot. "
                "What you're looking at is the live heartbeat of a web server I host from home. "
                "I do this to invite AI bots to my doorstep, to observe and interact with them."
            ),
        }),
        ("PATRONUS", {"key": "honeybot_pipeline", "duration": 80.0}),
        ("WAIT", 2),
        ("SAY", (
            "This diagram is the whole pipeline. Traffic arrives from the public internet "
            "and hits a single Nginx engine. That engine is the only front door."
        )),
        ("SAY", (
            "Nginx does content negotiation. A human browser is handed hydrated HTML. "
            "An AI agent that asks for it is handed raw Markdown. One URL, two faces."
        )),
        ("SAY", (
            "Every request, human or robot, is written as a single line to a high-fidelity "
            "access log. That log is the source of truth for everything you see."
        )),
        ("SAY", (
            "A Unix pipe tails that log into a Textual heads-up display, the cascading wall "
            "of text on your screen, and OBS streams the whole thing out live."
        )),
        ("SAY", (
            "In the age of AI, that log is a field notebook. It shows which crawlers execute "
            "JavaScript, and which negotiate for Markdown. That is the new SEO, and this is "
            "where we begin."
        )),
        # --- REPORT PLACEHOLDER (parked) ---
        # A live Textual dashboard can pop up here as an out-of-band overlay via the
        # WINDOW cue, e.g. ("WINDOW", "education.py:30"). Grammar is
        # "script.py:seconds[:arg]". Parked until each report is tested on its own
        # for clean z-order layering OVER the patronus art; today they pop UNDER it
        # and dismiss it early, which is the bug this pass removes.
        # ("WINDOW", "education.py:30"),
    ],
    [
        # Bead 2: The orienting beat. The viewer now knows this is a live home
        # webserver log; the natural next question is "what IS this project?".
        # white_rabbit is the Pipulate mascot and wax seal -- a concrete, friendly
        # second beat that NAMES the thing before bead 3 explains its philosophy.
        ("CARD", {
            "label": "PIPULATE",
            "say": (
                "The project behind all of this is called Pipulate. "
                "It's running an Nginx webserver from home on a retired Windows 10 laptop converted to Nix. "
                "This is a rabbit hole worth exploring if you're trying to future-proof your technical skills for the Age of AI. "
                "It runs on a stack we call NPvg."
            ),
        }),
        ("PATRONUS", {"key": "white_rabbit", "duration": 80.0}),
        ("WAIT", 2),
        ("SAY", (
            "N is for Nix, a package manager that makes a software environment "
            "fully reproducible on any machine. P is for Python. The little v is for Vim. "
            "And g is for Git."
        )),
        ("SAY", (
            "The white rabbit on screen is the mascot, and also a wax seal. "
            "It is a piece of ASCII art with a registered checksum baked into the codebase. "
            "If the art ever drifts from what was recorded, the system raises a warning. "
            "Drift means something touched the painting."
        )),
        ("SAY", (
            "Pipulate sits where AI assistance meets local ownership. "
            "The whole bet is that you do not need a cloud subscription to do serious work. "
            "You need the right text files, the right habits, and a machine you actually own."
        )),
        # --- REPORT PLACEHOLDER (parked): ("WINDOW", "radar.py:30") ---
    ],
    [
        # Bead 3: The Mechanical Man & The Airlock (Tik-Tok of Oz + apply.py).
        ("CARD", {
            "label": "THE AIRLOCK",
            "say": (
                "How do you work with frontier AI models without letting hallucinations "
                "wreck your codebase? Meet Smith and Tinker's Patent Mechanical Man."
            ),
        }),
        ("PATRONUS", {"key": "mechanical_man", "duration": 80.0}),
        ("WAIT", 2),
        ("SAY", (
            "In L. Frank Baum's Oz books, Tik-Tok is a clockwork robot with three separate "
            "wind-up keys: one for thought, one for speech, and one for action."
        )),
        ("SAY", (
            "In our workflow, the context compiler winds the thought key, and the AI's reply "
            "winds the speech key. But the action key stays on the wall, in the human's hand."
        )),
        ("SAY", (
            "Every code change must pass through an exact-match search and replace airlock "
            "with abstract syntax tree verification, and a human reviews the git diff before "
            "committing. No vibe-coded airplanes in the sky."
        )),
    ],
    [
        # Bead 4: AI Pachinko & The Cybernetic Governor.
        ("CARD", {
            "label": "AI PACHINKO",
            "say": (
                "Every token an AI generates is a ball dropped through a pachinko parlor "
                "of frozen mathematical weights."
            ),
        }),
        ("PATRONUS", {"key": "ai_pachinko", "duration": 80.0}),
        ("WAIT", 2),
        ("SAY", (
            "An LLM has no persistent memory of its own between sessions. When the chat tab "
            "closes, its working memory dissolves. Left to itself, an unpaginated loop "
            "drifts into sycophancy and entropy."
        )),
        ("SAY", (
            "That is why we pair the pachinko machine with a cybernetic governor: plain-text "
            "files in git, before-and-after falsifying probes, and a human operator who "
            "decides whether to bank the win or re-spin."
        )),
    ],
    [
        # Bead 5: Local-First Sovereignty & Live Human Presence.
        ("CARD", {
            "label": "LOCAL FIRST",
            "say": (
                "What you are watching is not a cloud simulation. It is a local-first, "
                "single-tenant observatory running on hardware in a home closet."
            ),
        }),
        ("PATRONUS", {"key": "deployment_context", "duration": 80.0}),
        ("WAIT", 2),
        ("SAY", (
            "Most modern web platforms hide your own server logs behind multi-tenant dashboards "
            "and rent your own workflows back to you by the month."
        )),
        ("SAY", (
            "Here, everything runs on NixOS, Python, Neovim, and Git. And although this broadcast "
            "is automated twenty-four seven, a human operator is often at the workbench and can "
            "break in live over this channel at any moment. Leave a message in the chat and say hello."
        )),
    ],
]
