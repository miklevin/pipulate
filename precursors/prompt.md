Certain things never happen and certain things are meant to happen. I have been flirting with this particular thing for a long time going down dead end and wild goose after dead end and red herring. Finally, with the help of AI, I am zeroing in on the implementation I am happy with in which could become a meaningful everyday tool. 

I had to let go of my fixation on Microsoft Playwright for web browser automation and its accompanying Google Puppeteer predecessor — because I needed to work from a Linux sub folder on a Mac or Windows system and control their default host operating system browser. This is a tall order and once I found a solution that worked, I had to stick with it even though it's not my preference. And that solution is Selenium 4.x. The proof of concepts have all born out. I have working code and we are up to a very delicate scalpel operation transplant of code. I do not look forward to it. I have carved out time for it as my entire weekend project.

Having browser automation in my Pipulate free and open source software is one of those big accelerators I'm looking for. Once it is incorporated into the system and template code exists, it can be built into countless other things. Well, it is true. The alternative to this is like 1000 times simpler where we use a library like Requests, HTTPX or aiohttp to do much of the same thing, it does not get all those critical real web browser details. 

Browsers are programs that execute code. They were already that when their main job was merely page layout — showing HTML properly in order to construct a page the way graphic-design software from ages past would. However now because JavaScript plays such a big role and making websites, functional, browsers are even profoundly more of code-executing machines. If you don't execute the page's JavaScript (at least on the page-load) you don't have the full picture.

Now in the age of AI was LLM's taking a look at your website both as they crawl and later after they've been scraped as a huge data set, this is all the more important. During the real-time RAG visit of your site at the moment of user inquiry, how will an LLM even know how to use your on-site search tool? Or even just navigate your site if it requires JavaScript? And if your site has been scraped for base model training, they won't have the full picture of you, your brand and your offerings if they can't execute JavaScript. 

There's a whole discussion here about where the responsibility should reside to make the process easier and less expensive for website crawling capable LLM's and training-data harvesting bots. But my discussion is concerned with making a lightweight LLM that SEOs can use to investigate such issues itself, capable of seeing a site with or without JavaScript enabled. Merely looking at the site both ways and feeding that text to an LLM with a token window big enough to see it all will yield profound insight. Imagine the LLM in the persona of Statler and Waldorf mocking you thinking that page you can't get to without JavaScript is ever going to be seen by an AI.

And I have the parts to this actually working! They are in separate places. And that's where this article comes in. This is the surgery of blending together two systems, both of which are fragile and will break at a hair's breadth of code change. That's why I call it surgery. That's why it's gonna take a scalpel like precision. And that's why I write this article as laying down the context for the AI coding assistance that are going to help me. You may be reading this here on the net, but the fact is that I am writing this to get coding help. You being looped in on the story after the fact is just a beneficial side effect of the documentation process that's required to create such sweeping context.

Sweeping context? Aren't you just supposed to tell the AI precisely what it's supposed to do for you — stripping out all the distractions and cutting off all possibilities and avenues for escape from focusing on the pertinent parts of your prompt? This would be true, if all the rest of its training were not equally or even more distracting to it. These AIs are overtrained on certain patterns that have been the darlings of GitHub and Stack Overflow for the time period during which the AIs were trained.

AIs have deeply engrainrd biases towards for example enterprise scalable secure full web stack architectures that typically include Kubernetes and Docker. This is as opposed to using those very same web technologies for lightweight local Electron apps that install on your desktop and have a completely different set of concerns. Locally installed apps don't have to scale like Netflix. And even the lightweight Electron approach has a deeply engrained Node.js bias which is gonna lead it to using a heavyweight client-side JavaScript framework like React, Angular or Vue. Even the contrarian view of stripping out the virtual DOM still gives you the hairy mess of Svelte. 

So what else is there? There's just the HTML and HTTP protocol themselves which is plenty — well, almost plenty because you want to be able to update things all over the page however you wanna update them. And for that, there's HTMX. It's a Johnny-come-lately to the game which is just a shame because it could have simplified the nature of the game early on. I mean, there are plenty of reasons to have a heavyweight JavaScript client, but once it's a locally installed app and you're only using the browser as the user interface component, it makes a lot more sense to shift rendering and estate management responsibilities onto the server. The whole idea of client/server architecture with latency goes away, and the whole thing becomes one unified app where the client has exclusive access-to and control-of the server.

AIs don't like hearing this. They are overtrained on a very different picture, yet the picture I am drawing here makes complete sense and the case of the Electron platform is the steppingstone transition to Nix flakes where the final Node.js bias is removed and all that remains is a sort of generic `normalize.css` of app development and runtime environments for macOS, Windows with WSL and other Linux systems. That's what Nix flakes are. 

Nobody gets it yet that Linux itself has become a normalizing subcomponent of any old host operating system — except maybe for the people who brought you Linux itself because they're copying it in the form of Giux, the Nix-clone officially supported by the GNU Project that does much the same things and much the same ways. You might think Linux is what Linus Torvalds wrote, but that would only be half of the picture. What you know of as Linux is really GNU/Linux with a man named Richard Stallman playing the hero role of Linus copying the work of Unix inventor Ken Thompson's command-set rather than play the role of Linus the hero copying the 
much lower-level Linux kernel. 

And in case you're wondering, this is all besides the discussion of a Linux desktop. maybe what you know of as Linux is not even GNU/Linux but rather is one of the popular desktop versions like Ubuntu or ChromeOS. These have GNU/Linux underneath of them is still (until they get a Rust re-write), but the whole desktop discussion is really not in the picture. It's not part of what I'm concerned with here when I talk about a unified app hosting environment. How is this even possible? The answer is the web browser! That brings us back to web browser, automation, doesn't it?

This might be a bit tricky to wrap your mind around, but bundling it all up tight the way the Electron platform does into a desktop app indistinguishable from a native local program is not the only way to get a locally running app that leverages the web browser for its user interface. Another way is that which is made known by a very few examples, but probably the highest profile of which is Jupyter Notebooks and Jupyter lab, installs a Web server somewhere on your system, often represented by a black box you can't close while the program is running, and then it gives you a `localhost` link to access that program in your web browser. Typically with JupyterLab this is `http://localhost:8888` with the 8888 being thr "port" on your local machine over which the web server is serving at the app.

If you were serving something else from your local machine, it could be hosted on `localhost:5001` (as FastHTML does) or any other arbitrary port you choose and configure in the software. In this way what maybe once was relegated to being an Electron app that dictated you must use Node.js and deal with installers for every host operating system, now becomes a generic interoperable app using whatever you want to use in Linux to build the local app. Now you could use a big complex JavaScript library, ORM, build process and Kubernetes as Docker to manage it all under Nix, but why would you when you could recapture the old one person can see it all know it all, and do it all dynamic of ye old Webmaster from the age of LAMP?

LAMP, which ones stood for Linux, Apache, MySQL and PHP/PERL/Python today stands for Linux, ASGI, MiniDataAPI, Python. This is a much more future proof LAMP than the old one because Oracle can't buy MiniDataAPI Spec. There's a whole additional article here about what ASGI and the MiniDatAPI specification are and why they replace any particular implementation of SQL or a web server that I will forgo for the sake of getting to the meat of this article, which is now that we have established that apps can run local with a web user interface using a web server running on Linux in the background — can they in turn control *ANOTHER* web browser, having privileged access to what that other browser (under automated control) can see and do?

After all this, and we are Only now getting to the meat of the story? YES! That's what context is. That's what a super-prompt is. That's what overriding the overtraining and biases that exist in the existing AI code assistant LLM models requires! You might not think so, but it does. At least today. Given their existing training and biases, an article like this should have been the last thing they looked at before you are articulate your next-step prompt that asks an AI to do anything that's even a little off the beaten track. While they are true intelligence, they are still statistical machines and will generally make the choice that's in the fat middle of the 80/20 rule bell-shaped distribution curve. they are not gonna take you out on the fringes deliberately without you wrangling, corralling and coercing them.  

Things might change in the future and these AI might I don't know inspect your code base, consider outliers and off the beaten track, viable solutions, exhibit creativity, read your mind or whatever. But for today an article like this lays the groundwork for this next step. Are you ready?

I have two Nix flakes. When is the Pipulate system as it exists today with no ability to do browser automation. The other is the standalone proof of concept browser automation compatible with the Pipulate system. Each of these `flake.nix` files is fragile, temperamental and a magic cocktail mix of miracle-it-works. I mean, all technology is really that way in the end. That kind of complexity is simply managed through the correct abstractions at correct levels. Reality itself is that way with a quantum giving way to the macro scale. So there's nothing new here. It's just that the details of the interfaces must be extremely well understood to make things have the intended consequences when interacting.

I say all this as if it were always a story of clean interfaces and APIs. The truth is that there is a messy story of tight coupling vs. loose coupling (hitting that metal), side effects, edge cases, and a whole bunch of fall-over failsafes. but you don't wanna throw up your arms and defeat either. You want to be very clear about the desired consequence. Do you want to be very clear about the intended side effect. After all, isn't it really all about creating side effects because was purely functional programming. Nothing would ever happen outside the functions and it would be a close system. These are the types of concerns to keep in mind here. The system that is NixOS flakes is reaching up to the host operating system to have the side effect of controlling its default browser.

And it's not merely controlling the host, operating system's default browser, but it is actually opening a two-way channel of communication. There's not much purpose in opening a web browser if you're not going to look for some information that resides on that page. Well actually you might just tell the human sitting at the console to look at the webpage and to transpose information it finds or to take a screen snapshot or whatever. And the system amazingly is designed to also do that. Many of the workflows in populate, our in fact, only semi-automated, choosing instead to have the workflow automate the human! Hahaha! I ought not to put it to them that way. But ain't that a dose of reality?

Anyhow, when we can, we wanna take complete control of a browser instance. That means that the things happening in the proof of concept next flake have to also be able to happen in the Pipulate flake. And this is no easy code transplant surgery. You're not gonna get it right on the first try. I promise you that. You gonna think you are, and your AI confidence is going to be brimming. But we have to be ready to do lots of reverts while preserving the benefit, what we learn on each revert. You have your own tool-call git system and I have mine. Let's both be ready on `git reset --hard HEAD` or whatever it is you use from your end.

Study the techniques in the branching of logic and the levels at which operating system dependent decisions are made in the proof of concept web automation flake. There are decisions being made there that are contrary to the ones that you are going to want to make on first pass. They are in fact, probably going to be difficult to incorporate into the flake currently used for Pipulate. Both of these flakes deal with multi operating system issues, particularly accommodating for macOS, in different ways. Synthesizing them together suggests a lot of inefficiency and code duplication which you are going to try and avoid because you are what you are. However, doing so will break the code repeatedly and frustratingly.

Would I need you to do is to really understand and internalize the issues why the proof of concept flake forks behavior at the high level where it does and imagine a new Pipulate flake that can do the same well preserving all of its own nuanced os-dependent accommodations. You are going to want to move stuff up and out of the deeper Pipulate flake into shower levels of the new structure, but you were going to balk at the inefficiency and repetition of this. But I am here to tell you that not only might this be necessary, but I need you to think in terms of non-breaking first passes so we can zero-in on the correct solution that spiraling into the frustrating abyss.

Can you imagine me first step in this process that simply layers in non-breaking scaffolding that introduces the proof of concept structure to the existing Pipulate structure? Can you imagine that scaffolding providing lots of verbose output saying here's what I would do on this path once the next step is implemented? Can you imagine using a versioning system so that every time you look at the output you can be explicitly sure it's doing what you told it to do on the last iteration? Can you imagine using the principles of a pass/fail binary-search algorithm at each step to ensure that you were not introducing bugs and unintended consequences?

Okay so you think now with this article super-prompt written, that's the end of
it and we hand it right over to AI? Nope! Now we practice some Context Foo! In
particular we pick what parts of the system needs to be included with this
prompt. Naturally it will be the 2 flakes plus the Selenium test automation
script. But we also want:

1. The overarching system (server.py)
2. An example of workflows because ultimately that's where automations go
3. The custom JavaScript my system uses
4. The requirements file
5. The Readme to give an overarching education on the system
6. The Workflow implementation guide to give nuances of the system

FILES_TO_INCLUDE = """\
server.py
flake.nix
requirements.txt
README.md
/home/mike/repos/pipulate/plugins/010_tasks.py
/home/mike/repos/pipulate/plugins/020_hello_workflow.py
/home/mike/repos/pipulate/training/workflow_implementation_guide.md
/home/mike/repos/browser/flake.nix
/home/mike/repos/browser/test_selenium.py
""".strip().splitlines()

And then ultimately this article itself goes into a prompt.md file local to
`context_foo.py` and I use this command:

python context_foo.py --prompt prompt.md

Hi there Gemini! Now you know what this is all about and what I'm looking for
from you. Put together a step-by-step implementation guide Claude can follow
from Cursor that won't break everything! No step is too small. Please have
Claude emphasize banking as a win a first step that layers in the kooky path
splitting that's necessary for everything to actually work correctly without
becoming over-ambitious with implementation. Get to a "success assured"
baby-step moment, then STOP! (tell it). Please and thank you!
