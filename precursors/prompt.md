I have to break out the individual widgets that are currently all packed into a
single workflow:

/home/mike/repos/pipulate/plugins/520_widget_examples.py

...into separate stand-alone workflows based on:

/home/mike/repos/pipulate/plugins/505_widget_shim.py

...similar to how I did it with each of the PicoCSS form types:

/home/mike/repos/pipulate/plugins/710_blank_placeholder.py
/home/mike/repos/pipulate/plugins/720_text_field.py
/home/mike/repos/pipulate/plugins/730_text_area.py
/home/mike/repos/pipulate/plugins/740_dropdown.py
/home/mike/repos/pipulate/plugins/750_checkboxes.py
/home/mike/repos/pipulate/plugins/760_radios.py
/home/mike/repos/pipulate/plugins/770_range.py
/home/mike/repos/pipulate/plugins/780_switch.py

I now have to do it with each widget that appears in 520_widget_examples.py but
the challenge is considerably more significant because of their more complex
nature, dependencies, special handling and timing issues. The goal is to lift
the working implementations and transpose them each into a standalone workflow
but I know this is too much to do in one pass. So we want a strategy and
implementation plan, something we can reliably repeat to extract and make
standalone each widget type. Here they are in the order they appear in the
widget examples. I've put the filename that each should become next to them.

- Markdown MarkedJS:           800_markdown.py
- Mermaid Diagrams:            810_mermaid.py
- Pandas Table Widget:         820_pandas.py
- PrismJS Code Highlighter:    850_prism.py
- Executable JavaScript Code:  860_javascript.py
- Matplotlib Graph:            840_matplotlib.py
- URL Opener webbrowser:       880_webbrowser.py
- Rich Table:                  830_rich.py
- URL Opener selenium:         890_selenium.py
- Upload File:                 870_upload.py

By the way you will see it in `server.py` but the JavaScript files on which
several of these depend is handled like so:

```
app, rt = fast_app(
    default_hdrs=False,
    hdrs=(
        Meta(charset='utf-8'),
        Link(rel='stylesheet', href='/static/pico.css'),
        Link(rel='stylesheet', href='/static/prism.css'),
        Link(rel='stylesheet', href='/static/rich-table.css'),
        Script(src='/static/htmx.js'),
        Script(src='/static/fasthtml.js'),
        Script(src='/static/surreal.js'),
        Script(src='/static/script.js'),
        Script(src='/static/Sortable.js'),
        Script(src='/static/mermaid.min.js'),
        Script(src='/static/marked.min.js'),
        Script(src='/static/prism.js'),
        Script(src='/static/widget-scripts.js'),
        create_chat_scripts('.sortable'),
        Script(type='module')
    )
)
```

...and is thus already present and global in most cases, and no external CDN
link is required.

Please provide me a strategy and implementation plan to accomplish this
standalone widget extraction into individual workflows such that we can bank
progressive baby-step wins, each being able to be a git commit checkpoint. The
goal is to not get bogged down with complexity of re-inventing what can be
cleanly extracted and transposed from 520_widget_examples.py. There is going to
be a lot of desire to invent and get clever which we must keep under control.
There is a fragile arrangement of nuanced timings and dependencies here that
must be kept intact. The instructions to the AI Coding Assistant should lay out
the overarching plan, explicitly describe the first extraction and then
explicitly tell it to stop so we can git commit and prepare for the next one,
and so on with a repeat until complete process.
