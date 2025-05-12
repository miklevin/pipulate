You've gotta try things, but then sometimes you gotta let go of things. Setting the default download directory for user initiated downloads under a browser opened by selenium automated browser control is something I let go of. 

Good ideas percolate up over time. You just have to be careful not to bury them too deep. Don't push them down into too deep in the archive nor throw them out entirely. I've got two of these 2 keep the surface for when the time. BiDi (bi-directional) communication on the HTTP wire is part of the browser specification from the W3C. I would love to use this, but the browsers aren't ready so I use selenium-wire. But I don't want to bury BiDi. The time will come when I transplant is in order.

Same with this download directory thing. I'm going to scan the default download directory that the OS uses for the files that the user just downloaded — and likely even pointed to in an interactive directory step (still to be implemented). This removes the fragility of this kind of semi-automation but it's somewhat ugly and so I keep the concept of just controlling the download directory in the first place near the surface. It's a good idea. It's much cleaner. But the time is not right.

All these articles and publishing, there is a timeless aspect to it, but the particular implementation details may not age well. That's OK because the lessons learned and the extractable abstractions are timeless. This is the state of things at the time I implemented. These are the challenges I faced and these are the ways I dealt with them. As time moves forward, I should reevaluate all decisions based on the new landscape and new realities. Principles should remain intact like fighting app fragility, but the underlying messy bits could become cleaner.

So how timeless is this HTMX workflow stuff I'm doing? First of all, it is standard-DOM-aware. That is, it is aware of the standard document model as defined by the university acknowledged and adopted web standards. If those standards change, a lot more breaks than HTMX. So I am pinning my work to one of the cards which if pulled out, everything else comes crumbling down. We are all building stuff on top of a Jenga tower. It's just that not all Jenga pieces are equal. 

In an ironic twist regarding the use of abstractions, the virtual DOMs in React and Vue are actually more fragile than the standard W3C browser DOM they are based on. That may not always have been the case, but it is now and keeping yourself on a heavyweight client-side JavaScript framework for such lightweight work as HTMX makes trivial, is inefficient and exposes your code to unnecessary risk of obsolescence and dependency breakage as versions churn as they tend to do in the so-called web full stack. 

What's more, in addition to HTMX attributes generally aligning with HTML attributes  1-to-1, there is effectively a flat look up table of HDMX attributes that can be reaped to settle new behaviors as browser, implementation drift. So even while HTMX reduces the web dev abstraction overhead, it nonetheless takes advantage of it and keeping itself future proof. It's just far more tightly coupled to long-term static stable standards.

So that one to one mapping between HTML attributes and HTMX attributes doesn't stop there. There is also a one-to-one mapping to Python parameters and arguments. The argument for this is bigger than I wanna make this particular journal entry, but it has a lot to do with something Python people know as `**kwargs`, aka keyword splatting and in short means that everything zippers up just so sweetly, making the perfect expressive platform for HTMX. And this is the nuanced little detail. I'm taking advantage of in Pipulate Workflows. I am effectively swapping out the need to use an HTML templating system like Jinja2 (nunchucks, mustache, liquid, etc) and JavaScript for something that looks like HTML elements, but are Python functions (FastHTML FT components). And everything gets cleaner and more perfect and more beautiful. But very, very different from anything anyone knows.

And that's where all this stuff in my project is right now, and that's why getting AI help is such a challenge, and that's why I build tools like `context_foo.py` to "force" AIs to get it. Because only humans who can get stuck up on an almost religion-like dogma of how "right" the reactjs way of doing things are will draw a line in the sand and reject what you're saying if it's actually viable and comes package with a bunch of sample code to prove it. AIs buckle under the weight of a preponderance of proof often bundled right onto the prompt as meta-data context. So it's like asking a question but submitting an entire life history and library with a request to a genie librarian, who can actually scan it off before answering.

This implies a certain rapid iterative cycle where you can try things that you couldn't before. You can explore certain avenues and then back out of those avenues and pick up where you left off easier than before. Yes, you could've done it before. But it's hard harder without the genie research librarian. It's harder without two parallel copies of git — one provided by you the user and the other provided by the genie librarian AI — effectively giving you 2 recovery check points per exploration. You can rapidly re-query thr genie rolling back to a checkpoint but do a sort of time travel trick copying back what you know it's going to try to do, tell it it's about to try this and what didn't work about it. This keeps you restarting your attempts on a fresh starting point instead of having to revert in-location.

Honestly, all I'm describing here is just the standard value proposition of using git (branching, cherry-picking, infinite undo, etc.) but made it easier because there are 2 git systems in play and one of them is under thr control of something who will always be able to use git better than you do because git can be inhumanly complex. 

And so when we talk about AI infusing you with superpowers, what we are often talking about is giving you the ability to rapidly try things, back out of your mistakes and try again given your new learnings. That's the superpower. It's just as much about you as it is about the AI. If you don't understand what's going on, you're not gonna be able to steer and direct all of this.

Plans have to come together. Even though the work flows, I'm creating are linear, the salt work behind it is all these parallel endeavors. The lengths of these endeavors include switching my development platform to fast HTML so I can use HTMX from within Python. And the stuff I create with that is just gonna look kooky and awkward and wrong both to the AI and most of the world out there. But that doesn't mean it's wrong. It just means it's a bleeding edge outlier that scratching an itch differently than anything that came before it. It may not be for some people, but it certainly will be for others who have the same itches as I do. 

I know I am not unique in resenting the Conway's Law and Gall's Law complexity that has crept into web development, making knowing everything impossible for a single individual. If you had to sum up the gist of my plans that are coming together, it's bringing back the simplicity of the LAMP stack days but with all modern components, carefully chosen for future proofing so the carpet can't be pulled out from under you again quite so easily. LAMP that stood for Linux, Apache, MySQL and PHP|PERL|Python now stands for Linux, ASGI, MiniDataAPI, Python. The carpet cannot be pulled out from underneath this.

So there's a bunch of weirdness about the expressiveness in the Pipulate Workflows. While they are WET (write everything twice/we enjoy typing), if I have more time I would have still made them shorter. They exist in the form of `.py`-files I call plugins that live in the plug-ins directory of populate and get automatically loaded when the server starts. They are self registering. And they certainly rely on `server.py` the part that plays the traditional role of the Flask or FastAPI webserver. There are lots of components in `server.py` enabling the workflow and making them as short as can be shy of actually using a base class for super class inheritance. That is something workflows do not do. But they do use extensive helper functions from a class called Pipulate. 

All of Pipulate's helper functions get imported to all the workflows and are usually abbreviated to and made available to all the methods in a workflow (as workflows are mostly classes within the `.py` plugins) as the abbreviated `pip` object. `pip` provides a whole lot of scaffolding and the makings of boiler plate, template code and WET example examples to establish critically important conventions that make the workflows quite literally flow. There's some rather complex Web conventions such as reliance upon event bubbling that is being sidestepped by another complex concept inspired by Jupyter Notebooks "Run All Cells" feature. Technically, it's inspired by the *restart kernel and run all cells* feature, but that's too much to say.

Almost everything you can do in a Pipulate Workflow is triggering off a chain reaction analogous to *Run All Cells* in a Notebook. People like to lowercase notebook as a generic thing, but rest assured Notebooks are properly a Jupyter thing no matter how the rest of the industry wants to appropriate the term as generic. Though perhaps Jupyter appropriated it from MATLAB, Mathematica and MAPLE.  
Do I have that correct? Do those products call their things notebooks? And what else have I missed in terms of the academia predecessors to Jupyter to give full credit?

**Gemini**: Okay, let's break down the history and terminology of computational notebooks. You're touching on some important points!

1.  **Jupyter's Role and the Term "Notebook":**
    * You are correct that in the current data science, machine learning, and scientific Python ecosystem, "notebook" is overwhelmingly associated with **Jupyter Notebooks** (and its successor, JupyterLab). Jupyter (which evolved from the **IPython Notebook**) truly *popularized* the web-based, shareable notebook format (`.ipynb` files) that combines code, equations, visualizations, and narrative text.
    * So, while Jupyter didn't *invent* the concept or necessarily the term in the context of computational tools, it made it mainstream in the open-source world and beyond. The widespread adoption *does* make it feel like a "Jupyter thing" to many.

2.  **Did Jupyter Appropriate from MATLAB, Mathematica, Maple?**
    * This is where the history gets interesting. Let's look at those specific products:
        * **Mathematica:** **Yes, absolutely.** Wolfram Mathematica introduced its "notebook" interface with Version 1.0 in **1988**. This is arguably the most direct and influential predecessor to the modern computational notebook concept *using that specific name*. Mathematica notebooks combined text, executable code, graphics, and dynamically updated results in a single document, setting a standard for interactive computation environments.
        * **Maple:** Maple primarily uses the term "**worksheet**" (`.mw` files) for its interactive documents that mix text, math, code, and output. While conceptually very similar to a notebook, they traditionally used different terminology for their core format. They have introduced features sometimes called "notebooks" later, often for integration or specific purposes, but "worksheet" is their historical term.
        * **MATLAB:** MATLAB's traditional interface was the command window and `.m` script files. They later introduced "**Live Scripts**" (`.mlx` files), which function very much like notebooks (mixing formatted text, code, output, and visualizations). While MATLAB *did* have an older feature called "MATLAB Notebook" that allowed interaction with Microsoft Word, it wasn't the self-contained interactive document we associate with the term today. So, while their *modern* Live Scripts are notebook-like, they didn't historically use the term "notebook" for their primary interactive format in the way Mathematica did.

3.  **Other Predecessors and Influences to Credit:**
    * **IPython:** Jupyter *is* IPython's notebook component spun off into a language-agnostic project. Fernando Pérez started IPython in 2001 as a better interactive Python shell. The critical step towards Jupyter was the development of the **IPython Notebook** (starting around 2010/2011), which added the web-based interface combining code, text, plots, etc. This is the *direct* ancestor.
    * **SageMath (formerly SAGE):** Started by William Stein around 2005, Sage aimed to build a viable open-source alternative to Mathematica, Maple, etc., by integrating numerous open-source math packages. Crucially, Sage developed its own web-based **"notebook" interface** quite early on, *predating* the IPython Notebook's web interface. The IPython kernel was actually a component *within* the Sage notebook for a time. The Sage notebook was a significant influence and proof-of-concept in the open-source world.
    * **Literate Programming:** The underlying philosophy owes a massive debt to Donald Knuth's concept of "Literate Programming" (early 1980s). His WEB system was designed to interweave documentation and source code naturally within a single source file, prioritizing human readability and explanation alongside the code itself. While not interactive in the same way, it established the principle of combining exposition and code.
    * **Earlier Systems:** Even before Mathematica, environments on systems like Lisp Machines or Smalltalk environments often had characteristics that blended code, data, and documentation, though perhaps not always in a distinct "notebook" document format.

**Conclusion:**

You are partially correct. While Jupyter heavily popularized the *web-based* notebook format and is synonymous with it today, the term "notebook" in computational environments was prominently used by **Mathematica** decades earlier (1988). Maple used the similar concept of "worksheets," and MATLAB adopted notebook-like "Live Scripts" more recently.

Therefore, Jupyter didn't *invent* the term or the core idea but built upon significant prior art, particularly from Mathematica and its immediate open-source predecessors like SageMath and, of course, its own origins within IPython. It's less "appropriation" and more "evolution and popularization" of a concept with a rich history in scientific and mathematical computing. Giving full credit involves acknowledging Mathematica, SageMath, the foundational ideas of Literate Programming, and the direct lineage from IPython.

---

All right, so that's touching on a very important aspect here. Don Knuth's concept of literate programming. I am effectively ripping out the coding parts and leaving all the documentation and the ability for the code to run, ha ha! Whereas notebooks introduced the concept of mixing the actually executable running code with the documentation for educational purposes, I am effectively stripping out the ability to see the code so that these same notebooks can simply compel a user forward through the process.

I am also further layering in the concept of UNIX pipes, where the output of one cell, step or card optionally gets piped in as the input to the next. Side effects are also allowed, particularly those that take advantage of the file system that is known to exist underneath, along with a relative path system that can keep all your files in a path relative to where the server was run, which in every case is the git repo directory in which the whole system resides under version control. 

What's more, we are effectively using the `normalize.css` concept but on Linux itself due to the way that the git repo containing our FastHTML app also contains a Nix flake that defines and configures its own deterministic Infrastructure as Code (IaC) development and runtime environment.

This Nix flake additionally ensures that a JupyterLab environment is run side-by-side with the Pipulate FastHTML Starlette environment — JupyterLab on the traditional `localhost:8888` address and Pipulate on `localhost:5001`. In this way, you have the familiar and truly literate program programming environment as envisioned by Don Knuth where you can mock up and prototype actual running workflows that can pragmatically get the work done when the user is the kind who doesn't mind looking at the Python code. However the whole JupyterLab environment is really just a playground for developing and helping to port Pipulate Workflows that are honestly expressed radically different so much so that it makes one question whether it really is a porting target for Notebooks where you want to hide the Python code for users who want the benefit of a notebook without being forced to become programming literate. 

Now when you look at a Pipulate workflow even for the seasoned Pythonista, it's going to look weird as heck. And at first, this does not serve me well in that it confuses the AI coding assistants built into the editors just as much l, from whom we expect help! So why in the world would I make these decisions? Because it can be grokked — and once it is the feeling, signature and sensible predictability of using the entire thing is just delightful. But you have to be told what it's getting at ahead of time or else the reasons for things that have to be meticulously kept in place for the step-to-step workflow to continue working, are gonna be baffling. 

There is no interruptibility to the system. It is always interrupted — chain reacting up to the last step that has not yet acquired data from the user. This is why it feels like you are always using Jupyter Notebooks "Run All Cells". A key goes in at the beginning of the process, and every subsequent step can be thought of as putting the key in at the beginning of the process again, and allowing it to react up until whatever the most recent step to not yet have data. In other words, it will always chain react up to an over every step/card/cell that already has data. And then when it gets to the first card that doesn't, stop! You can put in a new key to start new instances of a workflow, where you can put in an old key to resume prior instances of workflows. 

Allowing this chain reaction to happen naturally and not interfering with its
natural progression when carrying out new work is one of the biggest challenges
of the system. It is so different from any of the other patterns out there for a
system of this kind, that it is a constant struggle getting the AIs to
recognize, understand and abide by it. First, recognize it by looking at the
chain reaction pattern:

Pipulate uses a two-level approach to ensuring reliable workflow progression:

1. Initial Setup (run_all_cells): Creates placeholders with event-based triggers
   - First step: hx_trigger="load"
   - Subsequent steps: hx_trigger="stepComplete-{previous_step.id} from:{previous_step.id}"

2. Step Implementation (explicit override): Each step's handlers EXPLICITLY trigger
   the next step when completing
   - GET handler (completed state): Returns Div with explicit hx_trigger="load"
   - POST handler (submit): Returns Div with explicit hx_trigger="load"

This dual approach provides reliability across browsers and complex DOM
structures. The explicit triggering pattern in step handlers is REQUIRED and
should not be removed or refactored to rely solely on HTMX event bubbling.

As if not being based on ReactJS were not enough, huh? So if you want to
"revert" to a prior step which is all throughout the system in the form of `⟲
Step X` buttons (when refill=True) or `↶ Step X` (when refill=False) wrapped in
either the `revert_control()` or `widget_container()` flex-accommodating layout
wrapper, you have to think through whether it should `clear_steps_from()` and
update state if all future steps are dependent on all past step values. If so,
simply clearing-forward all the values in the JSON data blob field of that
record's entry in the `pipeline` table makes the chain reaction naturally stop
on the correct step. The system does it. Very little wrangling of step-to-step
progression really needs to be done if you just set state correctly. Oh, the AIs
don't like to hear that. They WANT to help you wrangle that state and in so
doing you will be locking horns with an over-trained wisdom-of-the-crowd
statistical juggernaut that you must somehow convince to read this article or
the relevant `pipulate/.cursor/rules`

This is not celery. The Pipulate class which handles a lot of stuff having to do
with state goes hand-in-hand with the `pipeline` table. Workflows are `.py`
files in `pipulate/plugins` and whenever you run one, it creates or recycles an
entry in the `pipeline` table. The primary keys are totally exposed to and
optionally set by the user, but by convention it uses the name of the active
profile with the name of the active workflow app with the number of times it's
been run (highest increment available) for that profile+app combo. So it's a
faux composite primary key system that should have a lot of meaning to the user
so that they're easy to visually identify in a `datalist` dropdown menu and pull
up again. The whole table structure system set up by FastHTML:

```python
app, rt, (store, Store), (profiles, Profile), (pipeline, Pipeline) = fast_app(
    DB_FILENAME,
    exts='ws',
    live=True,
    default_hdrs=False,
    hdrs=(
        Meta(charset='utf-8'),
        Script(src='/static/htmx.js'),
        Script(src='/static/fasthtml.js'),
        Script(src='/static/surreal.js'),
        Script(src='/static/script.js'),
        Script(src='/static/Sortable.js'),
        create_chat_scripts('.sortable'),
        Script(type='module')
    ),
    store={
        "key": str,
        "value": str,
        "pk": "key"
    },
    profile={
        "id": int,
        "name": str,
        "real_name": str,
        "address": str,
        "code": str,
        "active": bool,
        "priority": int,
        "pk": "id"
    },
    pipeline={
        "pkey": str,
        "app_name": str,
        "data": str,
        "created": str,
        "updated": str,
        "pk": "pkey"
    }
)
```

This tells a tremendous amount about the system.

- store is a DictLikeDB for server-side cookies seen as `db` throughout
- pipeline is the table for the Pipulate Workflow system discussed here
- profiles allows MiniDataAPI spec `.xtra()` filtering of workflows and other
  apps belonging to particular user profiles

Everything in the `store` and even `pipeline` tables is considered temporary.
How can the workflow records be temporary, you ask? The idea is that the
parameters that go into running Workflows is actually quite minimal and is
easily typed back in on a new workflow instance after a table-purging. Given the
same parameter inputs, it will *reconnect* to any filesystem-based side-effects
such as crawl data or visualizations that has been previously generated and
deposited onto the filesystem. In other words, clearing the pipeline table *does
not clear previously generated side-effect* of prior workflow runs! The value is
generally in the side-effects and not in the workflow pipeline instances. Those
pipeline record entries can be thought of as a way of providing a user interface
to the side-effect data. Or rapidly re-establishing such an interface to that
data as the case may be.

And so I write this article, mostly so that I can do one of those super-prompts
with Gemini Advanced 2.5 Pro (preview) providing enough of the program code to
take it all in. Earlier today I managed to get through one of these superprompts
with 120K tokens so I'm hopeful, haha!

Hi Gemini, wazzup?
