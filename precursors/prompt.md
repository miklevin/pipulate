I have finished the first and potentially most important of the Pipulate
workflows for actual day-to-day use by my coworkers. It is Parameter Buster. It
is the type of thing that will mostly be useful for Botify customers as it
leverages all 3 of the major data sources Botify takes advantage of:

- Web logs, which are not easy to get these days
- Crawl data, already pre-analyzed to those not in Google Search
- Search Console, all the URLs that are active in search

It uses these three data sources to create a optimization that will remove
querystring parameters from the URLs it finds during a Google Crawl that would
result in crawl budget waste. The end result is a copy/pastable PageWorkers
optimization, perhaps one of the best tricks in the book.

Today is about banking wins and banking more wins. It's about polish,
documentation and enabling my coworkers to actually use this thing. It's a lot
like letting Pipulate out in the wild generally, but really only of much use to
Botify employees and customers. This is a reasonable first step. More general
purpose SEO stuff comes later.

Avoid rabbit hole projects today. A single one could ruin you for another week.
You have this big solid open block of Sunday, and then back to work. By the time
you go back to work you will have a private YouTube video for this thing planted
as a copy/pastable link-example payload to ricochet around on Slack. The idea is
to quietly and self-evidently announce a total game-changer that those who can
recognize such things will recognize. This is much about that story and that
script. Speak quietly and deliver a big demo.

I'm doing a few passes to improve the overall system based on the considerable
learnings implementing `100_parameter_buster.py`. My first stop is
`50_botify_export.py` to capture all the nuance and subtlety surrounding CSV
downloads, of which there are many. It's a wild maze to navigate — from BQLv1
which is easy to get examples of but which you shouldn't be using vs. BQLv2
which you should be using but is hard to get examples of. Then there's the
`/query` endpoint vs. the `/jobs` endpoint, and really also the `/export`
endpoint which is all over the place in terms of examples but which really has
been deprecated by the `/jobs` endpoint... even when it's a BQLv1 query! And
then the polling... Oh, don't get me started. 

There's vast divide of experience with the Botify API that must be mastered
before everything stops being some sort of show-stopping obstacle. You really
have to be an engineer. However, I am not. And so this kind of post-successful
project documentation where I bank my winnings in documentation that helps the
next round of AI Assistants pick apart why things went well the last time is so
important. It's part of the accelerating success effect. Success leads to
success leads to success, and perhaps few places as well as in training AIs with
really good and forever-improving documentation.

I feel the underlying AI Code Assistants and the way they are integrated with
the Cursor AI editor shifting and evolving underneath of me as I go. I believe
it's going to be too resource intensive and wasteful to train all the frontier
AI models that are being used for such things, Claude, Gemini, ChatGPT, etc. to
handle this process radically differently between Cursor, VSCode, Windsurf,
Cline and the like. I believe we are experiencing User Interface / User
Experience / Application Programming Interface (UI/UX/API) convergence here. The
way "Agent" mode is different from "Manual" mode is different from "Ask" mode,
while the labels of these modes may vary from AI assisted editor to editor, the
spirit stays the same.

It used to be that there was one simple way you got AI-assisted coding. More or
less, it was the same way we used ChatGPT through the Web UI at first, which is
we send a prompt and a bunch of code together in-context, and it responded back
with new code that we somehow had to figure out how to work into our existing
codebase. Pedantic hair-splitting definition people are calling this former case
AI assisted coding, while the later case that is springing up all over the place
*Agentic Coding.* People thing Agentic Coding is new, but as fast as the ChatGPT
API was out, so was AutoGPT, CrewAI, Microsoft's AutoGen and others. Agentic
mode was there from the beginning, but relegated to us techies. Extremely
recently the flurry of GooseAI, Manus, Cline and Claude Code showed us that
Agentic operation was for the masses. And so now it's popping up as "Agent" mode
everywhere, including Cursor. And it all comes down to calling tools with
iterative back-and-forth self-prompting.

Implementations may vary, but the end result is the same. The AI goes off
half-cocked and loosey goosey fulfilling your request until it feels its done to
your satisfaction and whatever other criteria. It's not terribly different than
the original coding assistants except that all their output is fed back into
them as the new input automatically, including the output of the use of external
tools that can search your codebase, use git, check the Web and whatever else.

The precise details of how they do this and made such a big leap forward so
quickly is part of where this new fangled protocol MCP (model context protocol)
that is becoming so popular. If all the frontier models need to know how to do
this stuff we can't fragment it into a thousand different ways because its too
expensive and brittle to get all the models abiding by the schisming rules that
started popping up with different tool-call protocols, differing annoyingly
slightly between OpenAI, Google and Anthropic. Anthropic leading the way with
new protocol proposals such as they seem to do a lot lately proposed MCP and
everyone jumped on the bandwagon (including Google!) and now all the AI models
know how to do this agentic dance.

And so we have Agent, Manual and Ask "modes" to choose from. And we have AIs
going off half-cocked doing stuff to the point of downwards spiraling collapse
or the narrow-path to success. Try stuff, break things, back-up, undo, try again
refactoring while factoring in what we learned. Basically AIs are working a lot
like humans but exploring all these potential paths at 100x the rate a human
could. And so yeah, agentic behavior is big and important like all the hype, but
then so is controlling that half-cocked loosey goosey behavior, steering and
directing it with the kind of talent that defines where the jobs are going in
the new age of AI — riding the bucking bronco — or the sandworm if you prefer
and are a Dune nerd like me.

And so with such a potentially disastrous (to your codebase) process, obviously
they need some sort of safety-net letting them revert and branch in the
background, and obviously they're going to choose `git` just like humans and the
rest of the world. And so equally obviously Cursor AI, and I presume all the
others like Microsoft, Cline and Windsurf who must be implementing such things,
are using their own bizarro parallel git server in the background for their own
code assistants through some MCP tool-calling standard. Git through MCP must be
just about the most delicious secret sauce in the AI code editor arms race right
now. 

Cursor AI's implementation is good. I feel free to experiment wildly. I have
`git reset --hard HEAD` ready on my end. I know Claude has something similar on
its end. When an experiment spirals out of control it's almost like an inside
joke between the human and the AI who is going to revert first and inform the
other of the restore-point details. Claude doesn't have or know my git hashes
(unless I instruct it to use them through the terminal, haha), and I don't know
it's. But what used to be downward spirals of AI code-assisted ruin are now just
easy peasy experimental branches, and thus the sought-after acceleration effect
is possible. Collapsing house of cards become reassemblable construction
projects with instant undo/redo — from two sides! The git-using AI and the human
who is learning to use git better, because AI.

It doesn't matter whether these things are sentient or whether they have "true"
creativity or not. Their value as a pedantic housekeeper of deep arcane detail
make them infinitely useful from a pragmatic standpoint. How creative does a
superpowered librarian need to be? How creative does a superpowered automechanic
need to be? If something is there to immediately find the unfindable and fix the
unfixable that just frees up all your creative potential. And when you learn to
tap these superpowered assistants like driving a car, you can talk and drive at
the same time. See? When steering AI becomes second nature like driving, your
own deliberate cognitive capacity — the kind that needs to be front-and-center
which you can't throw on autopilot — gets freed up for the important stuff like
adapting to changing conditions.

And that's very much where we are now on the Pipulate project. I am learning to
use the AI coding assistants naturally. It's not a struggle every time screaming
at them FastHTML is not FastAPI. With a critical mass of code examples they have
to look at every time when navigating responses they are effectively cornered
into understanding the things they need to understand to be useful. Your local
context is overwhelmingly overriding their over-training on all the full web
stack enterprise redux kubernetes react stuff they've been brainwashed on. But
sometimes you need to use a wedge like: It's like the Electron Platform. Yeah
that's right. Web UI's can be used for localhost apps (VSCode, Slack, Zoom,
Discord, etc). And they don't have to be written scale like Netflix. Surprise!

So, I'm sorting out the rules. This is part of my cleaning and polish. When you
drop a `.cursorrules` in your local git repo, it's tied to the repo moving
around with it and part of your vendor-independent portability powers. However,
the new workspace-scoped `.cursor/rules/something.mdc` are not. And so part of
this morning's cleanup as the day gets underway is me taking what I've broken up
over multiple non-repo-bound `.mdc` files and wrapping them into one. I'm going
to use Gemini 2.5 to do this, even though it's been letting me down a lot lately
by not being able to do long replies without logging me out. However, it's also
given the best responses so the strategy is just to keep it short. Let's get the
context together. First, the prompt.

I have a system. The documentation of this system is spread out over a lot of
places and files which I have gathered together here. I have also included
parts of the codebase this documentation refers to so you can check the accuracy
of the documentation against the single source of truth: the code itself, the
behavior of which when running is what's being documented.

The system is full of counterintuitive anti-patterns as a remedy for much of
what ails bloated Conway's Law-infested modern web development. A single
webmaster sitting at a single system can interact with a software product in the
web browser much as one would with an Electron platform app, but instead of an
opinionated bundle there is a whole normalized deterministic Linux subsystem
running out of a git repo folder provided by nix flakes, solving the "not on my
machine" problem, blurring the lines between the development platform and the
app runtime environment. This provides full transparency to the user by moving
almost all responsibilities and concerns that would be handled by a fat
JavaScript client library onto the server through FastHTML and HTMX, down to and
including the cookies. Think server-side cookies whose state is shown through
the webserver console output which the user is free to watch while using the
app. There are no mysteries concerning client-side state because all that state
is shifted to the server and exposed through its server console. That's on top
of the client-side DevTools console which still also can be used to monitor the
reduced and simplified minimal JavaScript that remains. So in short, there is
nothing that cannot be easily known. And with this total knowledge comes
enhanced control and with this enhanced control comes accelerated feedback loop
of app improvement, especially AI-assisted as it can be leveraging that same
said transparency for the Coding Assistant.

Is the vision becoming clear? None of this is theoretical. All of this exists
right now today as you can see from the code and documentation I am providing
you. In fact I am leaving many things out so as to not overwhelm you with the
quantity and details of the antipattern corralling examples that overcome your
enterprise-concerns over-training. I've given you just enough examples of the
DRY CRUD apps and WET Workflow examples to allay any concern that they might not
exist or be as powerful as this system implies. They exist and are quite
powerful. Basically, anything able to be expressed in Python and organized in
the Jupyter Notebook style can be ported into this system and have a superior
user interface and experience for the non-technical user who doesn't want to and
shouldn't need to look at the Python code powering it all. So in other words,
Pipulate brings the already transformative and liberating power of Notebooks to
the rest of the world by taking that extra step and allowing the refinement of
notebooks into code-free (as far as the user is concerned) Web Apps!

So there are 2 audience for every bit of documentation made. Can that. There are
FOUR audiences for the documentation:

1. The human merely using the apps who need not even know nix but for the 2
   commands to get an app installed and running
2. The human developing the apps who need be near a pulsing-brain alien to port
   Notebooks to FastHTML/HTMX.
3. The frontier-model AI Coding Assistant (like you) there to reduce the human's
   dependency on actually being a pulsing-brain alien
4. The Ollama-powered LLM baked into the locally running web app who understands
   it from real-time training and is there to help the human merely using the app

Together these four audiences have a beautiful dance, rapidly customizing
different instances of this system into endless customized variations for the
SEO, Finance, Science industries and others — basally any industry or situation
that could benefit from having a clearly documented semi-automated linear
workflow with a local AI riding shotgun to help you make sure those parts that
can't be fully automated are at least well understood by the human while it
shepherded them through whatever part of the process that still needs a human in
the loop.

The way this becomes a feedback loop independent of any particular AI platform
(including Cursor, Windsurf, Cline, VSCode, etc) or even any particular API,
application or even Web UI, is to bundle it all up into an XML package that can
be 1-shot submitted to you and your kind. It's so easy to do this way I am not
even limited to doing it once against you nor to just you. I can do variations
of this very prompt and rapidly re-test it against you and other models to
compare your output. It is a wonderful way to probe for the best answers using
different approaches, and even to benchmark the frontier models like you. So it
is with that sort of eye I will be examining your response to this prompt.

With that in mind, I have given you both the code that drives the system (for
the most part) and some of the already existing documentation. I need to create
documentation for each of the audiences discussed:

1. A human just using web apps
2. A human developing those web apps
2. A Frontier Model AI (like you) helping the developer make those web apps (port Notebooks)
4. A local model helping the user use those web apps (step through Pythonless Notebooks)

For audience 1, the documentation will be:

- Introduction on Pipulate.com
- Install instructions
- Philosophy document (why the keys, chain reacting flow, etc)

For audience 2, the documentation will be:

- Explanation of Nix/.venv environment
- High level Notebook-to-FastHTML/HTMX concepts
- Workflow Implementation Guide

For audience 3, the documentation will be:

- The mega super-complete `.cusorrules` file (replacing need for `.mdc` files)
- The mega super-complete Workflow Implementation Guide
- Recipes for every kind of Workflow Widget

For audience 4, the documentation will be:

- System prompt instilling persona and giving overview of its role
- Real-time training markdown documents per crud/workflow web app
- Tool-use instructions (probably MCP) for agentic "steps" within workflows

I think that about covers it. That's to give you the broad overview. But now to
the actual prompt for you for right now, what I expect you to do in response to
this. My priority is to reduce the reliance on `.mdc` files that are not bound
to the repo and to instead roll all their good and knowledge into a combination
of `.cursorrules`, perhaps the `README.md` (serving a lot of audiences and
purposes right now), and the `plugins/workflow_implementation_guide.md`, which
seems to be where a lot of the deep precise knowledge is ending up that's too
big to feed to the LLM on every request the way `.cursorrules` does.

And so the request here is really for you to within a reasonable response size
because anything larger than what appears to be about 1000 lines automatically
logs me off of Gemini and loses all the good work of your reply (no way to
retrieve your up-to-that output — lost forever!). So give me what you think is
the right first-pass output to this request with further instructions as to how
I should refine THIS PROMPT for the next iterative round because it is very easy
for me to re-prompt you with one of these super-prompts in a wholly new session
freeing up all your tokens and starting fresh, but with your directional advice
incorporated into the prompt-at-the-end (which this is).

Is that clear? I understand it is a bit meta, but you can appreciate what I'm
going for with the accelerating effect implied by this document and the effect
that good documentation has towards this cause by enabling entities such as you
to do even better the next time.

Please and thank you!
