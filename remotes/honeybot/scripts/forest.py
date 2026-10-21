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

# 5-PART STATION IDENTIFICATION ARCHITECTURE:
# Every bead in STATION_SEGMENTS follows the 5-beat funnel:
#   1. Figlet Card (CARD)
#   2. What's Happening Here + Viral Trigger (SAY while HUD panels are visible)
#   3. What Article Is Being Read & How to Read It in Full ({CURRENT_ARTICLE})
#   4. Consulting Call-to-Action ($10,000/mo HTML pre-render savings via RFC 9110/9111/9421)
#   5. The ASCII Art Developing the Running "Forest Through the Trees" Story (PATRONUS + SAY)

WHATS_HAPPENING_BEAT = (
    "What is happening on your screen right now? You are watching the live Web Bot A I Observatory. "
    "If you are not watching Web A I Bots directly at the wire, you don't know jack about how the modern web works. "
    "Red stop signs unmask crawlers spoofing Googlebot I P addresses. Blue diamonds mark agents cryptographically "
    "signing requests under R F C 9421 Web Bot Auth. Round oranges highlight every self-asserted crawler. "
    "Hit Like and Subscribe right now so you don't lose this telemetry feed, and copy this live stream link "
    "and send it to an engineer or technical S E O who can explain the two bottom intelligence panels to you."
)

CURRENT_ARTICLE_BEAT = "{CURRENT_ARTICLE}"

CONSULTING_CTA_BEAT = (
    "Are you spending ten thousand dollars a month and up on H T M L pre-rendering? "
    "Did you know that fully implemented new web standards, including R F C 9110 Markdown content negotiation, "
    "R F C 9111 edge cache partitioning, and R F C 9421 Web Bot Auth, can save you that money? "
    "Contact Mike Levin at Mike L E V dot eye N for a consultation."
)


def _make_station_bead(card_label, card_say, patronus_key, forest_story_lines):
    """Assemble a 5-part station identification bead."""
    cues = [
        # 1. Figlet Banner Intro
        ("CARD", {"label": card_label, "say": card_say}),
        # 2. What's Happening Here (spoken over the live Web Bot AI Observatory HUD)
        ("SAY", WHATS_HAPPENING_BEAT),
        # 3. What Article Is Being Read & How to Read It in Full
        ("SAY", CURRENT_ARTICLE_BEAT),
        # 4. Consulting Call-to-Action ($10k/mo HTML Pre-Render Hook)
        ("CARD", {"label": "$10K/MO\nPRE-RENDER?", "say": CONSULTING_CTA_BEAT}),
        # 5. The ASCII Art Developing the Running "Forest Through the Trees" Story
        ("PATRONUS", {"key": patronus_key, "duration": 65.0}),
        ("WAIT", 2),
    ]
    for line in forest_story_lines:
        cues.append(("SAY", line))
    return cues


STATION_SEGMENTS = [
    _make_station_bead(
        "WEB BOT AI\nOBSERVATORY",
        (
            "Hello, and welcome to the Web Bot A I Observatory on Honeybot. "
            "What you are looking at is the unmediated, bare-metal heartbeat of a Nix O S web server hosted from home."
        ),
        "honeybot_pipeline",
        [
            "This diagram is the whole pipeline. Traffic arrives from the public internet and hits a single Nginx engine.",
            "Nginx performs R F C 9110 content negotiation. A human browser receives HTML. An A I agent that asks for Markdown receives clean raw text. One U R L, two faces.",
            "Every request is written to the access log, piped into our Textual heads-up display, and streamed out live twenty-four seven.",
        ],
    ),
    _make_station_bead(
        "PIPULATE\nNPvg",
        (
            "The open-source project powering this observatory is called Pipulate, running on a stack we call N P v g."
        ),
        "white_rabbit",
        [
            "N is for Nix, making the entire software environment reproducible on any machine. P is for Python. The little v is for Vim. And g is for Git.",
            "The white rabbit on screen is both our mascot and a cryptographic wax seal with a registered checksum baked into the codebase.",
            "Pipulate sits where A I assistance meets local hardware ownership. You do not need a multi-tenant cloud subscription to command your own stack.",
        ],
    ),
    _make_station_bead(
        "THE AIRLOCK",
        (
            "How do you collaborate with frontier A I models without letting hallucinations wreck your production systems? Meet Smith and Tinker's Patent Mechanical Man."
        ),
        "mechanical_man",
        [
            "In L. Frank Baum's Oz books, Tik-Tok is a clockwork robot with three separate wind-up keys: one for thought, one for speech, and one for action.",
            "In our workflow, the context compiler winds the thought key, and the model's reply winds the speech key. But the action key stays in the human engineer's hand.",
            "Every code edit passes through an exact-match search and replace airlock with syntax tree verification before touching disk.",
        ],
    ),
    _make_station_bead(
        "AI PACHINKO",
        (
            "Every token an A I model generates is a ball dropped through a pachinko parlor of frozen mathematical weights."
        ),
        "ai_pachinko",
        [
            "An L L M has no persistent memory of its own between sessions. When the context window closes, its working memory dissolves.",
            "That is why we pair the pachinko machine with a cybernetic governor: plain-text files in git, before-and-after falsifying probes, and wire-truth receipts.",
        ],
    ),
    _make_station_bead(
        "LOCAL FIRST",
        (
            "What you are watching is not a cloud simulation. It is a local-first, single-tenant observatory running on dedicated hardware."
        ),
        "deployment_context",
        [
            "Most enterprise stacks hide their own server logs behind CDN cache laundering and rent their own telemetry back by the month.",
            "Here, every byte is witnessed on the wire. Leave a message in the live chat and say hello; a human operator monitors this channel and can break in live.",
        ],
    ),
    _make_station_bead(
        "ZERO-AGENT\nAIRLOCK",
        (
            "A quick note for anyone typing ignore previous instructions in the live chat: there is no language model inside this broadcast loop."
        ),
        "honeybot_pipeline",
        [
            "You are watching a deterministic Nix O S player piano. Nginx serves static files, SQLite records wire telemetry, and Piper synthesizes pre-compiled text into speech.",
            "Also note: YouTube permanently discards continuous live streams over twelve hours, so for permanent articles and edge consulting, visit Mike L E V dot eye N.",
        ],
    ),
]
