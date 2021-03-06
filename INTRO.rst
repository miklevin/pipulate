===============
pipulate v0.2 - Automate Google Sheets with Python for Data Dashboards
===============

:Author: `Mike Levin, HitTail Inventor & SEO in New York City <http://mikelev.in>`_

- Are you already drinking the Google Koolaid with Analytics, Search Console?
- Are you still paying for Google Sheet automation with expensive plug-ins?
- Do you feel there's some sort of missing "glue" to hold it all together?
- Would you like that glue to be career-advantageous future-proofing coolness?

If you've answered yes to one or more of these questions, then Pipulate is for
you— or in a broader sense, Python and the SQL-alternative, Pandas. Go install
the Python 3.6 version of Anaconda from https://www.anaconda.com/download/ and
then run Jupyter Notebook. It'll pop up in a tab in your browser. Then get used
to the following magical incantations::

    import pipulate as gs  # Install from console with: pip install pipulate
    import pandas as pd
    import numpy as np

Then hold onto your hat, because you've just jumped onto the bandwagon of a
lifetime. Here is my `love letter to Python <http://mikelev.in/2011/01/python-programming-language-advantages/>`_.

.. image:: https://raw.githubusercontent.com/miklevin/Pipulate/master/pipulate-logo.svg?sanitize=true

There's a reason spreadsheets remain as popular as they do in the face of more
capable databases and reporting systems. Spreadsheets are designed for humans—
you don't need a developer for every little thing. You can use ledgers in many
places where a database would be overkill. However, as anyone who's tried to
build durable long-term automations around spreadsheets using VBA, AppScript
(or any of the other obvious choices), it ain't so easy. I fix that here.

First, I plan to open the mysterious world of Python-driven data-automation to
newbs simply by having you import a library that auto-prompts you for Google's
OAuth web-login, getting you right over the first show-stopping hurdle. After
that, I advocate a simple convention of selecting ranges out of a spreadsheet,
modifying them, and pushing the results back in.  And that's mostly done with
Pandas; the one data manipulation tool every SEO should right now be mastering.

Congratulations! You're about to learn to program Python (easily) for SEO::

    #  _____ _     _       _       ____  _             _       _       
    # |_   _| |__ (_)___  (_)___  |  _ \(_)_ __  _   _| | __ _| |_ ___ 
    #   | | | '_ \| / __| | / __| | |_) | | '_ \| | | | |/ _` | __/ _ \
    #   | | | | | | \__ \ | \__ \ |  __/| | |_) | |_| | | (_| | ||  __/
    #   |_| |_| |_|_|___/ |_|___/ |_|   |_| .__/ \__,_|_|\__,_|\__\___|
    # There are many frameworks like it,  |_| but this one is mine. --MikeL

.. contents::
    :backlinks: none

.. sectnum::

########################################
Background & Philosophy
########################################
::

    You gotta pay the Python toll
    If you want out of the vendor hole.

Congratulations to Conductor for the acquisition by WeWork. This should bring a
normally inaccessible tier of SEO-product into the reach of exactly the sorts
of people who can use it. For everyone else cobbling it together, I'm here.

.. highlight:: python

****************************************
A better way
****************************************

I've done ad hoc and scheduled data-churning work for a long time, where
investigation becomes automated system becomes generalized tool. I've invented
my own systems for this sort of stuff that have gone obsolete in the face of a
rapidly changing world so often that it hurts. No really, it hurts. Having now
experienced almost-framework packages like Flask that merely help you connect
the dots begging to be connected (Requests & Workzeug in their case / GData &
GSpread in mine), I'm like Yeah! Pipulate should be like that— almost not
there. Focus on what's important: Pandas! Think light-touch framework mentality
as pretty much the opposite of Django, which is what most of my framework
creations of the past more-or-less resembled. This is I think a better way.

****************************************
Of Stacked Decks & Killer Card Combinations
****************************************

So now, instead of inventing my own systems, I leverage the strength of the
cards I'm dealt. This is familiar to anyone who place the Magic The Gathering
card battle-game where certain card-combinations can't be played because they
are too powerful and throw of the balance (and fairness) of the game.
Thankfully for us SEOs, in real-life thankfully such killer combinations are
not so easy to ban— such as that of Google Sheets, Jupyter Notebook and
Pandas. It's like resurrecting elves from your graveyard for unlimited
fireballs the gift that keeps on giving.

****************************************
It's Pandas all the way down
****************************************

An Ode to Pandas::

    I'm a #Python #pandas person'
    'Cause #SEO will worsen
    With each day the #AI's
    Waking uuuup!
    Solutions?
    I've a' plenty!
    But none are
    Muscle-friendly;
    Because
    from #vim
    I must reach
    Juuuupyter!

I used to be an amateur (very amateur) magician. You know, it's all the same
feeling for me; magic, art and coding... 3 sides of an eternal golden braid...
and a bit of performance art, the constant hunt for a good paying gig, and
getting down an bunch of cool new moves that will serve you for a few years
until they stop working. Well, this pandas trick has got quite a few good years
ahead of it as it replaces SQL as the ad hoc data langua franca du jour— and
that ain't no fad. Legit bandwagon here that's perfect for SEO's, so ya had
better get a jumpin. If you weren't a data-tech before, you are one now.

****************************************
From SEO to Data Tech to Datamaster
****************************************

Once you can manipulate Pandas DataFrames, you have super-powers and are no
longer an SEO. Your bullshit will smell more like statistically convincing
correlations, though you will always attach the standard disclaimer, that does
not mean causation. Therefore, our field remains Kung Fufu. Anyone who doesn't
want to be called out on bad-science better be able to walk the walk. Show
process. KNOW process. Invent process. Make process your own secret sauce in
such a way where you can EVEN STILL jump-on and benefit from some pretty
grown-up and destined to succeed bandwagons.

****************************************
That's where Pipulate comes in
****************************************

Here's the basic API-invocation for Pipulate::

    cl, df = gs.pipulate(tab, rows, cols)     # pulls range from GSheet

    # Do stuff to df object using pandas,
    # the new "must know" SQL-alternative.
    # Just keep the row x col "shape" intact, then...

    gs.populate(tab, cl, df)                  # pushes range to GSheet

That's it. That's Pipulate— it's just the rectangular data-range pull & push
stuff (nothing in-between). So, `go get Anaconda 3.6 <https://www.anaconda.com/download/>`_ 
and help me reposition SEO somewhere more than the gut-feeling Intuiters of
yesteryear and Data Scientists of tomorrow— the **Datamaster** with a
Python/Pandas industry-standard skill-set has vast room for creative expression
and career-path flexibility (hedging your bet on SEO). 

****************************************
there's nothing to see here. please move along.
****************************************

If you're reading this, you're among the first who knows what's going on with
me here with my latest version of Pipulate— which amounts to yielding to the
staggeringly cool process put into motion by Fernando Perez (invented iPython
that's become Jupyter Notebook) and Continuum Analytics who put together the
Anaconda FOSS equivalent to Mathematica, MATLAB, SAS or whathaveyou. It's data
analysis stuff so scientists can solve their crisis of reproducibility a few
years back that really shook 'em up and gave "the other side" a lot of ammo. 

If you want to fight data with data, you better have some seriously good Kung
Fu. I'm the type of SEO who survives just fine at places like 360i with clients
like Apple and JCPenney (I helped pull them out of the fire), and these are my
tools now in their modern form. I prefer to work in-house where I can slip in
work like this and not have to bill it evenly against each account I work on
(yuck!). I can get into my grove, walking the walk as I talk the talk...
in-house SEO-style... yeah. Good stuff.

****************************************
Be a Lightweight Pandas-speaking API-Monkey in the Middle
****************************************

And so, here is my little gift to you, world of SEO. It's not DeepCrawl or
Conductor or ahrefs. No, but it can connect to any of them. It could draw
exactly the dashboard you want from out of all 3 systems (if you've got 'em)
and give you just the dashboard you need under simple GMail security context,
and not some per-seat license login nonsense. Innovate new reports in Jupyuter
Notebook. Refine them. Copypasta them over to Linux scheduling where you fit it
togehter like Tetris, squeezing every dollars worth out of your EC2 instance.

This project is just the medicine that a highly stressed SEO field needs. I got
your cure right here, and it's really just the minimum baseline technical
capabilities you should have today so that you may interact...  with...
anything.

****************************************
All The Bands Whose Wagon's You're Hitching Your Star Too Are Belong To Us
****************************************

Track your SEO rankings, Social Media views and counts, whatever!  Start in the
shallow end with Jupyter Notebook and "graduate" your work to generic scheduled
Linux jobs that you can run almost anywhere. If you're a successful YouTuber
worried about the gravy-train running dry, diversify your skills with something
you'll probably love and can definitely self-learn. This is your chance to jump
with me onto the following surprisingly fun bandwagons:

- **Python** - programming for humans
- **Jupyter Notebook** - programming for even more humans
- **Pandas** - data manipulation for humans
- **GSheets** - data manipulation for even more humans

...but mostly Python. Go read my love letter to Python even though I have to
update it for 2018: http://mikelev.in/2011/01/python-programming-language-advantages/

****************************************
You Would Not, Could Not Learn to Code?
****************************************

I'm talking to YOU, Animation Gang! Sure, it's fun to animate today, but you
will always be at the mercy of people who can express automation concepts as
naturally as you speak English. Coding is not what you think. You already do
it. You express your creative dynamic right-brained selves in an overwhelmingly
technical and meticulous left-brained medium. I'm not sure if you understand
what's giving you super-powers on YouTube, but when that foolish dancing gets
tired and your energy runs out, come back here, sit down and learn to code
Python. You'll green eggs and ham.

- Automate Gimp
- Automate Inkscape
- Automate Blender
- Automate ImageMagik
- Automate Robots

****************************************
The Million-Follower YouTube Challenge... Accepted
****************************************

I could go on, but I think I make my point. My daughter challenged me to a
million followers on YouTube by VidCon. I'm like, haha, not likely. No one's
really interested in your dad's opinion that you're either either doing it
old'skool or you're fresh meat. Your dad can reach a million followers by
VidCon 2019 if I really focus and work on it. First step is to just catch
Jaiden's or James' or Becca's or Tony's attention and mention my channel in one
of their videos— a 7 year old YouTuber's super-nerd Dad in New York trying to
teach kids Python before their brains are poisoned with JavaScript. Oh... he
was the first to unbox a Raspberry Pi on YouTube and got a million-view video
out of it... then dropped the ball, because kid. Now kid loves YouTube and is
challenges me from a million views to a million followers.

Challenge accepted, Adi. https://www.youtube.com/mikelevin

****************************************
Did I Mention You're Either Old's Kool or Fresh Meat?
****************************************

And while it's definitely **not** required, I'll also teach you the timeless
badass tools of tech: **Linux**, **vim** and **git**— or at least the minimum
you need to know about each to project that "I'm Tony Stark" feeling.

Pipulate is about repositioning careers as SEO continues to change. Some tools
are like shiny new pennies (Jupyter Notebook & pandas), while others have
ascended to be the very fabric of our modern infotech-world— the true Samurai
Kung Fu vorpal light saber weapons of tech where developing muscle-memory makes
you dangerous... to your competitors.

########################################
Installing Pipulate
########################################

Step #1: Install https://www.anaconda.com/download/ start Jupyter Notebook.
Make a new Python 3 notebook and type::

    !pip install pipulate --upgrade

This command executes as an operating system command (because of the
exclamation mark) and not Python code. It may take awhile, but you will
eventually get the output of the pip program vomit out a bunch of messages
about installing this-and-that dependency. Most Pipulate requirements are
already met by Anaconda, but if you're in some other Python environment, you
can install all the rest of the requirements for Pipulate with pip install
pandas (a VERY BIG install).

########################################
For the impatient
########################################

The quickest way to pipulate is as follows, but I suggest you read through this
documentation where I cover creating Pipulate functions. The pandas concept of
df.apply() is very important to grok. If you don't grok the word grok, go read
Stranger in a Strange Land and return::

    import pipulate as gs
    import pandas as pd
    tab = gs.name('Your Sheet Name').sheet1
    cl, df = gs.pipulate(tab, rows=(1, 20), cols=('a', 'b'))
    df['B'] = 'foo'
    gs.populate(tab, cl, df)

Or the slightly longer-form, but probably easy for maintenance::

    import pipulate as gs
    import pandas as pd
    key = 'gobbledygookdockeyhere'
    name = 'Sheet1'
    rows = (1, 20)
    cols = ('a', 'b')
    sheet = gs.key(key)
    tab = sheet.worksheet(name)
    cl, df = gs.pipulate(tab, rows, cols)
    df['B'] = 'foo'
    gs.populate(tab, cl, df)

****************************************
Things even the impatient must know
****************************************

- You must be on Python >= 3.x.
- You must be using a Google Spreadsheet in online mode.
- You must exactly match 'Your Sheet Name' with your actual sheet name (or
  switch to keys).
- You must be able to recognize row and column indexes when you see them.
- When you import pipulate as gs, Google will (1-time) throw up a giant blue
  link that you must click and login with the same Google account you used to
  make the Google Sheet with.
- The meaning of the word grok.

****************************************
Things about OAuth2 you should eventually know
****************************************

Upon first-run, Pipulate asks you once for access and then not again until
things goes wrong and you have to login again. You should be aware that a file
named ouath.dat is dropped in your working directory (where you Jupyter
Notebook .ipynb files save) which allows full access to your Google stuff.
There is a refresh token there that grants new rapidly-expiring access tokens,
but which itself doesn't expire. It is used to frequently re-log you in
invisibly in the background. If you're interested in seeing these tokens, you
can open oauth.dat in a text editor. It really helps to start to demystify
OAuth2. Occasionally, Google WILL make even the refresh token have to be
recreated with a new Web login, so just be aware of that especially if you
build real automations (non-Jupyter Notebook) around Pipulate.

########################################
A tour through Pipulate
########################################

After you've installed Anaconda, run Jupyter Notebook by either looking for an
icon named Jupyter Notebook in your Start Menu (Windows) after an Anaconda
install, or select Anaconda-Navigator from your Applications folder (Mac) and
Launch Jupyter Notebook from there. There's a few ways to get Jupyter Notebook
running, but so long as something pops up in your web browser where you can
choose New / Notebook: Python 3, then you found it. After you have a new
Notebook, if you haven't done step #1 already, then execute::

    !pip install pipulate --upgrade

Once pipulate is installed, you don't have to do that again, so after it's done
(it can take awhile), you can delete the command and it's ugly output and get
onto the real action. There are alternative ways to do pip installs in
"Anaconda Prompts" (with more control outside the browser) but details vary on
Macs vs. Windows vs. Linux, so I prefer to tell people how to do pip installs
from within Anaconda. The --upgrade parameter ensures you always have the
latest because I will be updating it often. Step #2, execute::

    import pipulate as gs

This will cause an enormous Google Web login-link to appear in your Jupyter
Notebook that you must click, which will open another tab in your browser
presenting a Google login prompt. Choose which Google account you want to use
to access Sheets. It must have permission to the sheet you're manipulating. It
also asks for various other Google Service permissions while it has the chance,
in case you plan on using Pipulate to track your YouTube view-counts and such,
which you should totally do.

****************************************
Pipulate naming conventions
****************************************

In case you're wondering why I recommend the convention of importing pipulate
as gs, it's because my other Github module GoodSheet got fully wrapped in here,
and I like reminding everyone Pipulate is in fact GoodSheet. I also got very
fond of how gs.pipulate() looks, and I think it helps that gs also stands for
Google Sheet. It also avoids the verbosity of pipulate.pipulate() or
abbreviation-confusion of pi.pipulate() or pip.pipulate() or any of the other
choices not nearly as beautiful as gs.pipulate().

For those familiar with the Flask web microframework, it might help to think of
Pipulate as something lightly sprinkled in to connect GSpread and Pandas, and
not really trying to do all that much itself except a few API innovations to
help. The act of pipulating is just picking up an Excel-style rectangular
spreadsheet range as both a GSpread cell_list and a Pandas DataFrame, altering
the df completely with Pandas, and then using the symmetrical act of POPULATING
to push the changes back into Google Sheet.

****************************************
Of Pandas & dependencies
****************************************

Pipulate is designed to let you do all your challenging data-manipulation work
in Pandas. Pandas is not part of Python "core", but then neither is Google
Sheets or GSpread, so don't complain. You're drinking deep of both the Google
and Python Koolaid with Pipulate. You could do a lot worse. Any disenfranchised
SQL-users out there, Python Pandas is where you should be going. Not to put too
fine a point on it, but SQL has let you down. You need a more universal
lightweight "general case" data manipulation tool, and Pandas is it whether you
realize it yet or not. It's not like Oracle's going to buy Python too. So just
go ahead and import Pandas::

    import pandas as pd

****************************************
Configuring a job
****************************************

In that same Jupyter Notebook that you imported pipulate and pandas into, you
can now set the values that will allow you to connect to our spreadsheet (file)
and worksheet (tab), along with the cell range defined as a set of row and
column indexes, using row-numbers and column-letters that display in
spreadsheet user interfaces::

    key = '[Your GSheet key]'
    name = 'Sheet1'
    rows = (1, 20)
    cols = ('a', 'b')

It's good to switch from using GSheet file-names to their unique "keys" for the
sake of avoiding future confusion about which document you're actually working
on. It's far too easy to have 2 files with the same name. Be sure to use the
long string of characters copied out of a Google Sheet URL for the key. That's
the long string of alphanumeric gobbledygook not broken up by slashes. The
name is always "Sheet1" on a freshly-made sheet. If you rename it or want
to manipulate a different tab, be sure to make it match this. The rows and cols
tuple defines the rectangular region you will want to manipulate.

Okay, let's generate some text to manipulate with Pipulate. Enter and execute::

    import this

...and you will now have 20 nice new lines about the Zen of Python to
copy/paste from Jupyter Notebook to a newly-made Google Sheet you can use for
the below exercise. In other words, create a new Google Sheet and paste the 20
Zen of Python lines into cells A1:A20. You are now ready to pipulate.

****************************************
Connecting to sheet
****************************************

Open the connection to the Google Sheet (as if it were a database) and copy a
rectangular range in both the GSpread cell_list format and as a Pandas
DataFrame. This is setting the stage to pipulate, by creating two identical
shapes, but of different types (one from GSpread and the other from Pandas)::

    sheet = gs.key(key)
    tab = sheet.worksheet(name)
    cl, df = gs.pipulate(tab, rows, cols)

Even though the cl is a cell_list from GSpread, it is also very similar to
Python's core datatype called list. Jupyter Notebook lets you inspect the
contexts of cl or df simply by running them on their own line. Type this and
hit Enter::

    cl

As you can see, GSpread cell_lists are just what one might call a
one-dimensional array in other languages, which is the same as a normal Python
list datatype. However, a few extra attributes have been layered onto each
cell, such as cl[0]._row to see what row a cell belongs to and cl[0]._col for
its column. In this way, GSpread avoids more complex shapes like a list of
lists or a list of tuples, but it does make manipulating it directly as if a
spreadsheet a challenge, which is pretty frustrating because that's the entire
reason you use a library like GSpread.

Have no fear; Pandas to the rescue! It's not the cl we're going to manipulate.
It's the df, which is a Pandas DataFrame and has a lot of powerful
database-like tricks built-in. All we have to do is NOT TOUCH the cl until such
time as we push our changes back to the spreadsheet. You can also inspect the
df with Jupyter Notebook::

    df

****************************************
And now a word about Jupyter Notebook and REPL enviornments
****************************************

You can inspect objects like cl and df this way because you are in a REPL
(read, eval, print, loop) for Python code execution where the contents of a cl
or df is just sort of "hanging around" frozen in memory MID-EXECUTION for your
casual perusal. This is both a small miracle, and makes Jupyter Notebook the
ideal place for for scientists and marketers to "feel their way around" data
before building resilient automations.

I'm also helping you jump on the same bandwagon that's helping scientists solve
the crisis of reproducibility that hit their field a few years back when they
realized that 70% of published scientific research was unreproducible. While
much credit goes to Jupyter Notebook, it's really Anaconda that gets it all
installed and erases that pesky multi-platform issues that usually become very
major stumbling blocks—even for scientists.

****************************************
Your first pipulation
****************************************

Say you wanted to just plug the value "foo" into column B::

    df['B'] = 'foo'

You can now "push" your changed dataframe object back into the still
compatibly-shaped cell_list object, but peek at it first "in memory" by just
typing df all by itself::

    df

Make the changes that you see in memory push back out to the spreadsheet. Watch
the browser as you populate to see the changes occur!::

    gs.populate(tab, cl, df)

Congratulations. You've just pipulated.

Plugging data dynamically into Google Sheets is nothing new. Pipulate just
simplifies it. To do something slightly more interesting, you can simply copy
the contents of column A to B::

    df['B'] = df['A']
    gs.populate(tab, cl, df)

****************************************
Working with numbers
****************************************

Say there were numbers in column A and you wanted column be to be that number
times 2. Notice I have to convert column A to integers even if they look like
numbers in the spreadsheet, because GSpread converts all numbers to strings::

    df['B'] = df['A'].astype(int) * 2

This example will throw an error if you try it on the Zen of Python data, you
would get ValueError: invalid literal for int() with base 10: 'The Zen of
Python, by Tim Peters'. But you can put numbers in column A and execute this to
see a simple *2 operation and acquaint yourself with how automate-able things
start to become when you replace tedious manual Excel processes with
automation.

****************************************
Appending strings
****************************************

If you wanted to append foo to column A and put the result in column B (like
above, but appending strings to an already already string-type column).::

    df['B'] = df['A'] + 'foo'


****************************************
Alternatives to Pipulate
****************************************

Embedded application languages like Microsoft's VBA or Google's AppScript can
achieve similar results, but if I need to explain to you why these are not as
good as using Python on the back-end, you're in the wrong place. The same goes
for the ever-increasing selection of paid-for Excel and GDocs plug-ins and
other proprietary vendor products which probably don't quite do what you need.

Pipulate is mostly about Python and Pandas. You could replace gs.pipulate() and
gs.populate() with pd.read_csv() and pd.to_csv() and take Google Sheets out of
the equation entirely, or use Excel instead of GSheets by swapping PyExcel for
GSpread. There's also a new library pygsheets that does a few more things like
named ranges and limited formatting I may switch to. Doesn't matter, because
Pipulate is a lightweight wrapper to provide a lightweight spreadsheet
manipulation API.

My thinking is that if you have to learn and master one tool for this sort of
data manipulation, it might as well be Python/Pandas. Shove all the complexity
onto pandas... it's going to be around for awhile... and not cost you anything.

****************************************
Cheerleading for Anaconda, Jupyter Notebook and Pandas
****************************************

The above example with .astype() also shows that even if you know Python,
there's some new learning to do here for things like casting datatypes, which
is actually different from pure Python. Pandas sits on NumPy which is a popular
C-optimized Python library that provides N-dimensional arrays for the same kind
of work that IBM dinosaurs still do in Fortran for science and stuff. Pandas is
a FRAMEWORK on top of NumPy for such work, but which turns out to be perfectly
designed for what I used to use Pipulate for when it was a Flask-based Web app.

****************************************
Applying a Python function to every row of a Google Sheet
****************************************

Now say you wanted to apply a function to every line of the DataFrame to do
something like retrieve a title tag from a web address, and you had a function
that looked like::

    def status_code(url):
        import requests
        rv = 'failed'
        try:
            rv = requests.get(url).status_code
        except:
            pass
        return rv

Now you can get the status code of every URL in column A with::

    df['B'] = df['A'].apply(status_code)

This is where the "framework" known as Pandas steps in with its own
conventions. Pandas knows to take the function named in the apply method and
for every row of the dataframe, plug the value found in column A into the
function called status_code and plug the resulting value into column B. Look
carefully at what's going on here, because it's about to get a lot more
complicated.

****************************************
Giving Python function entire row of Google Sheet as input
****************************************

While the above example is powerful, it's not nearly as powerful as feeding TWO
arguments to the function using values from out of each row of the dataframe.
To do that, we simply call the .apply() method of the ENTIRE DATAFRAME and not
just a row::

    df['B'] = df.apply(func, axis=1)

There's a few things to note here. First, we HAVE TO include the axis=1
argument or else each COLUMN will be fed to the function by default as it
iterates through the dataframe. When you use the df.apply() method, you can
step through the entire dataframe row-by-row or column-by-column, and we simply
have to include axis=1 to PRESERVE the row-by-row behavior of calling the apply
method directly from a row (when it's implicit). Now, we can select a 3-column
range::

    key = '[Your GSheet key]'
    name = 'Sheet1'
    rows = (1, 4)
    cols = ('a', 'c') # <--Switched "b" to "c"
    sheet = gs.key(key)
    tab = sheet.worksheet(name)
    cl, df = gs.pipulate(tab, rows, cols)

Now we plan on putting a URL in column A and some text that we're going to look
for on the page in column B. Instead of just returning a response code, we will
return how many times the text was found in the retrieved HTML of the page. So,
we will desire to apply this command::

    df['C'] = df.apply(count_times, axis=1)

****************************************
CAVEAT! Row-aware Pipulate functions grab values from row by index
****************************************

However now the count_times function has more responsibility than the
status_code function. Specifically, it needs to know to get the URL from column
A and the keyword from column B, so we rewrite status_code as follows::

    def count_times(row):
        import requests
        url = row[0]
        keyword = row[1]
        rv = None
        try:
            ro = requests.get(url)
        except:
            pass
        rv = '--'
        if ro and ro.status_code == 200:
            rv = ro.text.count(keyword)
        return rv

With the above example, you put the URL you want to examine in column A and the
text whose occurrences you want to count on the page in column B. The results
appear in column C. This is where it starts getting more complex, and there are
ALWAYS costs to complexity. Mapping has to go somewhere, and I currently choose
to put it INSIDE Pipulate functions, which is not necessarily the best
long-term decision, but complex as it may be, you're going to be able to follow
everything that's going on right there in front of you without maintaining
some awful set of per-project externalized mapping tables... ugh! You'll suffer
through that sort of thing soon enough. For here, for now; MAGIC NUMBERS!

****************************************
FYI: Python execution-context choices
****************************************

Remember that the Python code is running under your control so you are not
limited as you would be using Google's own built-in Apps Script (Google's
answer to VBA) for the same purposes. Your Python code is running on your local
machine (via Jupyter Notebook) and can easily be moved to the cloud or on cheap
hardware like Raspberry Pi's. Truth be told, Jupyter Notebook is optional.

All your data manipulation or "creative work" is taking place in Pandas
DataGrids which you are "painting" onto in memory. Aside from copying the
initial range out of a spreadsheet and then pasting the identically-shaped but
altered rectangular spreadsheet range back in, this entire system is just
becoming adept at Pandas using GSheets instead of CSVs.

****************************************
Giving your function "extra" argument data per row (a tale of 2 splats)
****************************************

When stepping row-by-row through a Python Pandas DataFrame, it is often
desirable to insert "meta" attributes that can be used in the function WITHOUT
putting those numbers wastefully on every row of the spreadsheet you're
manipulating. Say the data we wanted to add is a date and it was the same dates
for every row.

===== === ========== ==========
one   com 2018-10-01 2018-10-31
two   net 2018-10-01 2018-10-31
three org 2018-10-01 2018-10-31
===== === ========== ==========

Since the date would be the same all the way down, using a whole column in a
Google Sheet for it would be a waste. In fact, GSheets has some limit to how
many cells you can have, so an extra column with nothing but repeated data is
very "expensive" quota-wise and slows your sheet down. Instead, only keep the
unique data per-row in the sheet. The Pandas API (and Python API in a broader
sense) provides for passing in both fixed-position arguments and labeled
arguments by sort of "side-loading" them in as follows::

    df['C'] = df.apply(func, axis=1, start='2018-01-01', end='2018-01-31')

APIs are weird. They work different ways in different languages, and this is
how Python works. It's weird, but wonderful. There are subtle rules you have to
get down here that just comes with experience. It's called learning to think
Pythonically, If you're in Jupyter Notebook, take a moment to run this::

    import this

--------------------
Splat type #2: \**kwargs by label (easier to explain first)
--------------------

The argument named (\*\*kwargs) accepts as a parameter EITHER a Python
dictionary object (called a dict, which looks a lot like JSON) or it will
accept the more common command-line convention of name=value, name2=value2...
as if being typed-in a terminal. I had a lot of difficulty grokking this, but
it's one of the reasons Python is used to create user-loved "API-wrappers" to
every non-Python API out there. Look at how you're going to have to ACCESS
those values from inside a function::

    df['C'] = df.apply(func, axis=1, start='2018-01-01', end='2018-01-31')

    def func(row, **kwargs):
        number = row[0]
        tld = row[1]
        kwarg1 = kwargs['start']
        kwarg2 = kwargs['end']
        # Do stuff here
        return stuff

--------------------
Splat type #1: \*args by label
--------------------

That was an example where you have multiple labeled arguments like start and
end dates. But if it's being side-loaded in a similar fashion similar to the
row, then you use the other type of splat that only uses a single asterisk in
the function argument definition::

    df['c'] = df.apply(func, axis=1, args=('two', 'peas'))

    def func(row, *args):
        number = row[0]
        tld = row[1]
        arg1 = args[0]
        arg2 = args[1]
        # do stuff here
        return stuff

--------------------
Splat types 1 & 2 together
--------------------

And then as you would imagine, you can mix positional \*splatting with labeled
\**splatting. You just have to use positional first and labeled second (or
last, actually), because if you think about it, that's how it must be::

    df['c'] = df.apply(func, axis=1, args=('two', 'peas'),
                       start='2018-01-01', end='2018-01-31')

    def func(row, *args):
        number = row[0]
        tld = row[1]
        kwarg1 = kwargs['start']
        kwarg2 = kwargs['end']
        arg1 = args[0]
        arg2 = args[1]
        # do stuff here
        return stuff

--------------------
One bourbon one scotch one beer
--------------------

Just to put a fine point on it, because it's really that important, the very
common way to define a pipulate function and its arguments is::

    def func(row, *args, **kwargs):

...which gets invoked stand-alone like this::

    func(one_row, one_tuple, one_dict)

...or via Pandas like this::

    df.apply(func, axis=1, one_tuple, one_dict)

...or possibly like this::

    df.apply(func, axis=1, ('two', 'peas'), foo='bar', spam='eggs', ping='pong')

...is the same as saying:

1. Define a function named "func".
2. Require something in position 1.
3. Optionally expect a tuple next.
4. Optionally expect a dictionary or sequence of labeled values as the last thing(s).

--------------------
Automatic unpacking of tuples and dicts in \*args and \*\*kwargs
--------------------

If passing all these lists and name/value pairs starts to get ugly, remember
Python actually likes to unpack for tuples and dicts for you as you splat. So
this ugly form of the above API-call::

    df['C'] = df.apply(func, axis=1, args=('two', 'peas'),
                       start='2018-01-01', end='2018-01-31')

...can be re-written in Python as::

    pod = ('two', 'peas')
    dates = {'start' : '2018-01-01', 'end': '2018-01-31'}
    df['C'] = df.apply(func, axis=1, pod, dates)

So the common pattern for a Pipulate function which you plan to apply to every
row of a Pandas DataFrame using the .apply() method is::

    my_val = func(a_list, a_tuple, a_dict)

--------------------
Putting it all together
--------------------

So say you were starting out with this data, but you needed to use start and
end dates with it, along with 2 more pieces of standard information per row.

===== ===
one   com
two   net
three org
===== ===

The Pipulate function to could look like::

    def func(row, *pod, **dates):
        postion = row[0]
        tld = row[1]
        pea1 = pod[0]
        pea2 = pod[1]
        start = dates['start']
        end = dates['end']

...and calling it from Pandas, again, like this::

    df['C'] = df.apply(func, axis=1,
                        od=('two', 'peas'),
                       dates={'start' : '2018-01-01',
                               'end': '2018-01-31'
                             }
                       )

Aren't you glad Python doesn't HAVE TO look like JavaScript?

--------------------
Testing functions without DataFrame.apply()
--------------------

If you don't really want to connect to Google Sheets and you just want to test
your Pipulate function with dummy data to simulate the DataFrame.apply() call,
you can use the function directly like this::

    my_val = func(['three', 'org'],
                  ('two', 'peas'),
                  start='2018-01-01',
                  end='2018-01-31')

But when the time comes to use it with Panda's DataFrame.apply(), it would look
like this. Just a reminder, the word "func" is actually the name of the
function that you've defined (with def) and axis=1 is what makes ROWS get fed
in on each step through the DataFrame::

    df['C'] = df.apply(func, axis=1,
                       pod=('two', 'peas'),
                       start='2018-01-01',
                       end='2018-01-31')

Whether you label the tuple or not in the call is optional, but if you do, it
has to match the definition. Otherwise, its position is enough.

--------------------
How parts like to snap together
--------------------

Some pretty cool concepts of bundling and unbundling of attributes between
Python objects and more common command-line API style is going on here. You
don't have to use the Python objects as the argument parameters. You can break
out and unbundle them yourself. If we only have one date parameter for example,
we could feed it in an unlabeled fixed position::

    pod = ('two', 'peas')
    dates = {'start' : '2018-01-01', 'end': '2018-01-31'}

...which leads to the simplest form to look at::

    df['C'] = df.apply(func, axis=1, pod, dates)

And there you have it. That's pretty much the basic use of Pipulate for
completely open-ended semi-automated Python Kung Fu in Google Sheets. If you're
anything like me, you're feeling chills running down your back at the
possibilities. If jumping onto the SCIENCE bandwagon that's occurring (to fix
their "crisis of accountability") isn't also the future of SEO, then I don't
know what is. All Pipulate does is let you get it in and out of GSheets easily,
so you can focus on the hard parts. Let the crazy ad hoc SEO investigations of
your dreams begin!

########################################
Working with very large lists
########################################

Google Sheet is not always the best place to process very large lists, but the
alternative is often worse, so the trick is to just decide by what size chunks
you should process at a time. This concept is sometimes called step-by-stride.
To use step-by-stride with Pipulate we take a basic example and simply add a
"stride" variable and edit out the last 2 lines that set and push the values::

    import pandas as pd
    import pipulate as gs
    stride = 100
    key = '[Your GSheet key]'
    name = 'Sheet1'
    rows = (1, 10000)
    cols = ('a', 'b')
    sheet = gs.key(key)
    tab = sheet.worksheet(name)
    cl, df = gs.pipulate(tab, rows, cols)
    #df['B'] = 'foo'
    #gs.populate(tab, cl, df)

****************************************
Step by stride
****************************************

In the above example, we only added a "stride" variable and edited out the last
2 lines that updates the sheet. Say the sheet were 10,000 rows long. Updating A
LOT of data with one of these AJAX-y data-calls is never a good idea. The
bigger the attempted update of a GSheet in one-pass, the more mysterious things
are going on while you wait, and the likelihood of an entire update failing
because of a single row failing goes up. The solution is to travel 10,000 rows
by 100-row strides (or smaller) and we wanted it to take 1000 steps. We replace
the last 2 lines with the following step-by-stride code::

    steps = rows[1] - rows[0] + 1
    for i in range(steps):
        row = i % stride
        if not row:
            r1 = rows[0] + i
            r2 = r1 + stride - 1
            rtup = (r1, r2)
            print('Cells %s to %s:' % rtup)
            cl, df = gs.pipulate(tab, rtup, cols)
            df['B'] = 'foo'
            gs.populate(tab, cl, df)

And that's pretty much it. All together, the code to process 10,000 rows by
100-row long strides directly in Google Sheets for accomplishing almost
anything you can write in a function to replace 'foo' with one of the fancier
pandas API calls described above::

    import pandas as pd
    import pipulate as gs
    stride = 100
    key = '[Your GSheet key]'
    name = 'Sheet1'
    rows = (1, 10000)
    cols = ('a', 'b')
    sheet = gs.key(key)
    tab = sheet.worksheet(name)
    cl, df = gs.pipulate(tab, rows, cols)
    steps = rows[1] - rows[0] + 1
    for i in range(steps):
        row = i % stride
        if not row:
            r1 = rows[0] + i
            r2 = r1 + stride - 1
            rtup = (r1, r2)
            print('Cells %s to %s:' % rtup)
            cl, df = gs.pipulate(tab, rtup, cols)
            df['B'] = 'foo'
            gs.populate(tab, cl, df)

########################################
SQL Data Sources
########################################

It's easiest to pipulate when you only have to apply one quick function to
every line of a list because it takes advantage of the Pandas framework
conventions; how the .apply() method works in particular. HOWEVER, if your
per-row query is a slow and expensive SQL query INSIDE a pipulate function like
this (the WRONG way)::

    def hits(row, **kwargs):
        import psycopg2
        import apis
        url = row[1]
        start = kwargs['start']
        end = kwargs['end']
        a = apis.constr
        atup = tuple(a[x] for x in a.keys())
        user, password, host, port, dbname = atup
        constr = "user='%s' password='%s' host='%s' port='%s' dbname='%s'" % atup
        conn = psycopg2.connect(constr)
        sql = """SELECT
            url,
            sum(hits) as hits
        FROM
            table_name
        WHERE
            url = '%s'
            AND date >= '%s'
            AND date <= '%s'
        GROUP BY
            url
        """ % (url, start, end)
        df = pd.read_sql(sql, con=conn)
        return df['hits'].iloc[0]

****************************************
Connecting to SQL from Pandas
****************************************

We now want to move the SQL query OUTSIDE the function intended to be called
from .apply(). Instead, you get all the records in one go and plop them onto
your drive as a CSV file and hit THAT later in the function from .apply().
Getting psycopg2 installed is usually easiest through Anaconda's conda repo
system (not covered here). First we connect to SQL::

    a = apis.constr
    atup = tuple(a[x] for x in a.keys())
    user, password, host, port, dbname = atup
    constr = "user='%s' password='%s' host='%s' port='%s' dbname='%s'" % atup
    conn = psycopg2.connect(constr)

****************************************
Building very long SQL WHERE's
****************************************

Next, we're going to need to build a string fragment for use in the SQL query
that calls out every single URL that we want to get data back on. One of the
worst parts about SQL is "in list" manipulations. The only way to be sure is a
pattern like this::

    WHERE
        url = 'example1'
        OR url = 'example2'
        OR url = 'example3'
        OR url = 'example4'

...and so on for as many URLs as you have to check. They're probably in your
Google sheet already, so let's grab them into a list in a way that creates
almost the exact above pattern (yay, Python!)::

    urls = df['A'].tolist()
    urls = "url = '%s'" % "' OR url = '".join(urls)

The 2 lines above convert a Pandas DataFrame into a standard Python list and
then into a fragment of a SQL statement. When people talk about being
expressive AND brief in Python, this is what they mean. Being able to read and
write statements like those above is a pure joy. You can look at the urls value
in Jupyter Notebook to confirm it's good (if a bit wordy) valid SQL that will
slip right into a query. Now, we unify the SQL fragment above with the rest of
the SQL statement using the endlessly beautiful possibilities of the Python
API::

    def sql_stmt(urls, start, end):
        return """SELECT
            url,
            sum(hits) as hits
        FROM
            table_name
        WHERE
            %s
            AND date >= '%s'
            AND date <= '%s'
        GROUP BY
            url
        """ % (urls, start, end)

****************************************
Using Pandas CSVs as SQL temp table
****************************************

You can now use the above function that really only returns the not-executed
multi-line text string which is used to populate a Pandas DataFrame and cache
the results locally just in case you come back during a separate Jupyter
Notebook session, you won't have to re-execute the query (unless you want the
freshet data)::

    df_sql = pd.read_sql(sql_stmt(urls, start='2018-01-01', end='2018-01-31'), con=conn)
    df_sql.to_csv('df_sql.csv') #In case you need it later
    df_sql = pd.read_csv('df_sql.csv', index_col=0) #Optional / already in memory

****************************************
Correlating URLs in Google Sheet and Pandas Dataframe
****************************************

We will now use this data source which now contains the "result" list of URLs
with the accompanying the number of hits each got in that time-window to create
your own Pipulate data source (or service). The GROUP BY in the query and
sum(hits) is aggregating all the hit counters into one entry per URL. The
correlation here is similar to an Excel VLookup. We make a pipualte function
for the DataFrame.apply() method to use THIS local data::

    def hits(row, **kwargs):
        url = row[1]
        df_obj = kwargs['df_obj']
        retval = 'Not found'
        try:
            retval = df_obj.loc[df_obj['url'] == url]
            retval = retval['hits'].iloc[0]
        except:
            pass
        return retval

****************************************
Using local Pandas DataFrame as "external" datasource
****************************************

Now instead of hitting the remote, slow, expensive SQL database every time, we
execute the SQL once at the beginning and can use the local data to pipulate::

    key = '[Your GSheet key]'
    name = 'Sheet1'
    rows = (1, 1000)
    cols = ('a', 'b')
    sheet = gs.key(key)
    tab = sheet.worksheet(name)

    cl, df = gs.pipulate(tab, rows, cols)
    df['B'] = df.apply(hits, axis=1, df_obj=df_sql)
    gs.populate(tab, cl, df)

Or if it's over a huge list or is error-prone and will need rows entirely
skipped because of bad data or whatever, we can step by stride by replacing the
above 3 lines with::

    stride = 10
    steps = rows[1] - rows[0] + 1
    for i in range(steps):
        row = i % stride
        if not row:
            r1 = rows[0] + i
            r2 = r1 + stride - 1
            rtup = (r1, r2)
            print('Cells %s to %s:' % rtup)
            cl, df = gs.pipulate(tab, rtup, cols)
            try:
                df['B'] = df.apply(hits, axis=1, df_obj=df_sql)
                gs.populate(tab, cl, df)
            except:
                pass

########################################
Developing Pipualte functions
########################################

Because Pipulate functions are really just Python functions (generally being
called through the Pandas DataFrame.apply() method), you can develop Pipulate
functions just as you would any other Python function.

The only unusual concern is how when you feed an entire "row" of a dataframe to
a Python function, it takes the form of an arbitrary variable name (usually
row) containing a numerically indexed list of values (the values from the row,
of course). This only means that a wee bit of "mapping" need be done inside the
function. So say you needed to apply an arbirary function to column C using the
data from both columns A and B in this form::

    df['C'] = df.apply(arbitrary_function, axis=1)

...then you would need to write the arbitrary function like this::

    def arbitrary_function(row):
        value_from_A = row[0]
        value_from_B = row[1]
        # Do something here to
        # populate return_value.
        return return_value

...so when you're developing functions, the idea is to simulate a Pandas
DataFrame row in default Python list syntax to feed into the function for
testing... which is this easy::

    simulated_row = ['foo', 'bar']

So in Jupyter Notebook actually feeding the simulated row to the arbitrary
function for actually running and testing OUTSIDE the Pipulate framework looks
like this::

    arbitrary_function(simulated_row)

...so developing functions for Pipulate is easy-peasy. Just design your
functions to always just take in the first argument as a list whose values have
meaning because of their fixed positions — which naturally represent the cell
values from rows you'll be pulling in from a spreadsheet.

By the way, namedtuples are the superior way of doing this when not bound by a
pre-existing framework, but whatever. Pandas is worth it.

########################################
Scraping Google Search Engine Result Pages (SERPs)
########################################

Well, you knew it was coming. Let's scrape some SERPs. It's sooo easy. But I
suggest you get yourself an anonymous proxy server or twenty. Put them in a
file named proxies.txt, 1-per-line. If ports are used, include them after the
IP like this::

    152.190.44.178:8080
    53.117.213.95
    250.227.39.116:8000
    20.15.5.222

Now load the file called get_search_results.ipynb. If you cloned the github
repo and are working in Jupyuter Notebook, you can work directly in your cloned
pipulate folder. I would suggest making a copy of files such as
get_search_results.ipynb and keep the originals around as a sort of template.

Anonymous web proxies go bad fast, so before you start a session, you should do
a one-time refreshing of your proxy servers. Do that by running this block of
code with update_proxies set to True. It will create a file in your repo folder
called goodproxies.txt::

    update_proxies = True
    if update_proxies:
        import pipulate.update_proxies as up
            up.Main()

After you have a good new list of proxies

########################################
Scheduling
########################################

Everything so far has been in Jupyter Notebook, and that's great for ad hoc
work, but when it comes to "promoting" a good report to daily use, you need
scheduling. And that's never pleasant, because you need a machine running
somewhere with as much reliability as you can get paying as little as possible.
That's just sort of a life lesson there. No matter how powerful you feel in
Jupyter Notebook, you're not all that if you can't automated. The answer?

****************************************
Get yourself a Linux in the Cloud
****************************************

Cloud... EC2 or whatever. Pick your poison. Whatever it is, being server-like
(as it should be), you're going to need to get into it... and for that you're
likely to receive a key from Amazon or your devops Dept. Figure out how to
login to that machine. It should be TOTALLY YOURS. This is your EC2 instance.
There are others like it, but this one is yours. Learn how to get in and out of
it fast, from almost anywhere. You can do this on a Raspberry Pi too if you
don't even want Amazon and a key in the picture.

****************************************
Logging into your server
****************************************

Once you figure out the ssh command to log in to your server, and do it
manually a few times. This follows the model of putting the key file in a
usually hidden directory on your system called .ssh which is usually in your
home directory::

    ssh -i ~/.ssh/id_rsa_yourname ubuntu@55.25.123.156

****************************************
Making it a pleasure to log into your server
****************************************

Once this works for you, create a text file and name it something like go.sh
and put it in your sbin. What's an sbin? It's a place you put little text-files
that work a lot like commands, but you write them. They're really useful. This
is your first Linux lesson from the Pipulate project. Linux (and Unix) won; get
used to it. It'll be your next stop after Jupyter Notebook. Scheduling
something you set-up in Jupyter Notebook is your natural "bridge" project. So
by this point, you struggled through that ssh command; congratulations.
Everything else is easy. Find your sbin by looking at your path::

    echo $PATH

Find your sbin in that gobbledygookdthen, then put something that looks like
this text (your info) in a file called go.sh (or whatever) there. Do the chmod
+x trick to make it executable, and then whenever you need to reach your
server, just type go. It's really nice to open a shell and to be in your
scheduling-environment just like that. We want to do everything immediately
reasonable to make the text-based Linux shell environment as totally cool as
Jupyter Notebook is::

    #!/bin/bash

    ssh -i ~/.ssh/id_rsa_yourname ubuntu@55.25.123.156

****************************************
A scheduler with a better API is a better scheduler
****************************************

We are not using crontab as our next step to achieve scheduling as some
googling about how to do this on a stock Linux server may indicate. We DON'T
like APIs where you have to drive nails through your head here at Pipulate. No,
we side with RedHat and others on the matter of default Linux system service
management and encourage you to use systemd. It's not the principles of the
least moving parts but rather the principle of not having to learn advanced
BASH script that's at play here. Thankfully, crontab's replacement systemd is
considered a highly supported mainstream alternative.
https://en.wikipedia.org/wiki/Systemd

****************************************
/etc/systemd/service/servicename.service
****************************************

You need a file in /etc/systemd/system which is the name of your service dot
service, like mysched.service. To create it, you may have to sudo vim or
whatever command because its a protected system location. The contents of your
file to kick-off Pipulate (or any other) Python scheduling job like this::

    [Unit]

    Description=Run Python script to handle scheduling

    [Service]
    Type=forking
    Restart=always
    RestartSec=5
    User=ubuntu
    Group=ubuntu
    WorkingDirectory=/home/ubuntu/mysched/
    ExecStart=/usr/bin/screen -dmS mysched /home/ubuntu/py35/bin/python /home/ubuntu/mysched/mysched.py
    StandardOutput=syslog
    StandardError=syslog

    [Install]
    WantedBy=multi-user.target

You you've just dropped this file in location, but now it needs to be enabled.
This is a one-time thing (unless you want it off for debugging or whatever)::

    sudo systemctl enable zdsched.service

Once you start playing around with the invisible background system services
(named daemons in Linux), the temptation is to keep rebooting your server to
make sure your changes "took" (similar to Apache/IIS webserver issues).
Whenever you're unsure and want to avoid a reboot, you can type::

    sudo systemctl daemon-reload

If you want to just restart YOUR scheduling service and not all daemons, you
can optionally do::

    sudo systemctl restart mysched.service

Who wants to type a longer command when you can type a shorter command? Since
we're in a location where we're typically cd' into, we don't need to do that
sbin trick we did on your local machine. In fact, I included r.sh in the repo,
so just cd into the repo directory and make sure the service names I'm using
match the ones you're using, and type::

    r[Enter]

...and it should reboot the service keeping mysched.py running. For your
curiosity, this is what it's doing::

    #!/bin/bash
    # This belongs in your sbin

    sudo systemctl daemon-reload
    sudo systemctl restart mysched.service

****************************************
Shoving the work around to where it belongs
****************************************

This r.sh file comes into play again later, because in order to ensure the
health of your scheduling server, we're going to give it a "clean slate" every
morning by rebooting it, and we're going to schedule the running of this BASH
script FROM PYTHON to do it. This is an example of doing each thing in the
place where it best belongs. Reboot from a bash script, respwan from systemd,
and actually SCHEDULE from within a single master Python script.

After such a reboot (and on any boot, really), we hand all scheduling
responsibility immediately over to Python (even though systemd could do more)
because as much better as it is over crontab, Python APIs are better still. We
actually are only using systemd as a pedantic task respawner. Think of it as
someone watching for your python-script to exit that can 100% reliably re-start
it. That's systemd in our scenario. After mysched.py is running, control is
immediately handed over to the 3rd party "Schedule" package from PyPI/Github
because it's API is better than the default sched module built-into Python.
Such things on my mind are:

- Period vs. Exact scheduling (every-x minutes vs every-day at y-o'clock)
- Concurrency when I need it and crystal clarity when I don't
- Minimal new "framework" language. If it feels like Django, turn and run.
- Optional ability to "lock" long-running jobs. General collision handling.
- Calls for little-enough code that if I make a mistake, I can easily recode.
- Crystal clear clarity of what's going on, no matter where I may be.

For now, "pip install schedule" seems to do the job.

****************************************
Scheduling issues are more complex than you think.
****************************************

When restarting a scheduling-script, you need to know that when it springs back
to life it may be in the middle or even towards the end of the daily time-cycle
you're probably used to thinking in, so "today's" reports may never get a
chance to run. You need to accommodate for this. You also need to be very
realistic about how many reports you're going to be able to run on a given
server on a given day. It can be like playing a giant game of Tetris, so it
would be nice to have concurrency.

Concurrency, you say? Are you suuuuure? There might be order-dependencies and
race-conditions in your script runs that you haven't thought about. I find that
it's always a good idea to avoid concurrency and to keep it simple (much good
karma) if the situation doesn't really call for concurrency. As hardware and
hosting gets cheaper, you can always slam out more EC2 instances and put less
work per server. Everything scales if you just size your work to fit one unit
of generic Linux server.

Staying conservative with your estimates and modest with your promises is
always a good idea, specially given how flaky all those APIs you're pulling
from could be, you ought to size out the job, then half it. Maybe even quarter
it. You won't be sorry. All that extra capacity in the server could be used for
temp tables or other unexpected resource hogs you'll run into that you don't
see today.

****************************************
In the beginning...
****************************************

The idea here with Pipulate is to make a very generic and almost organic (with
a heart-beat) place to start plugging your scheduled extractions from Jupyter
Notebook into, with the least muss and fuss... but also, the most power.
Pipulate only exists to make GSheets easier; a 3rd party package from
Github/PyPI which itself only exists to make gdata easier; a cryptic but
GOOGLE-PROVIDED API to Google Sheets. GData is most definitely NOT made for
humans. GSpread is made for those slightly more human. And for those entirely
human, there's Pipulate. In fact, there's something other than GSpread that I
just discovered which may have either tremendous impact or no impact at all
here at Pipulate. I'll let you know, but go take a look in either case. Real
kindred spirits over at https://github.com/nithinmurali/pygsheets

Oh yeah, so in the beginning::

    #Do whatever virtualenv stuff you do here
    pip install schedule
    pip install logzero
    pip install pyfiglet
    pip install colorama
    cd ~/
    mkdir mysched
    cd mysched
    vim mysched.py

****************************************
And then there was ASCII Art
****************************************

You can create your mysched.py however you like. I use vim, and it's spiritual
and life-changing. It also solves how to be really productive on pretty much
any machine you sit down at when doing tasks like this. Anyway, I just added
that file to the github repo, but for ease-of-use, I'll show the development of
our scheduling script here. First::

    from pyfiglet import figlet_format
    from colorama import Fore
    from logzero import logger, setup_logger

    font = 'standard'
    subfont = 'cybermedium'
    green = Fore.GREEN
    white = Fore.WHITE
    blue = Fore.BLUE

    ascii_art1 = figlet_format('Congratulations!', font=font)
    ascii_art2 = figlet_format('Welcome to Wonderland.!', font=subfont)
    print('%s%s%s' % (green, ascii_art1, white))
    print('%s%s%s' % (blue, ascii_art2, white))

    logger = setup_logger(logfile='mysched.log', maxBytes=1000000, backupCount=3)
    logger.info('This is some logger info.')

This should give you a good starting point for scheduling... none! By stripping
out everything that actually does scheduling, you can see how flashy
color-coded ASCII art can color your day, your view, and your perception of
time, rightness, and generally keep you on-track. Don't down-play the titles.
It should only ever be visible when you're restarting the script a lot for
testing, or at around 1:00 AM, or whenever your daily reboot occurs.

Keep in mind that later-on, we're going to "seize" the command-line output
stream (your view of the log-file) from anywhere you have a terminal program
and ssh program. That could very well be (and often is in my case) your mobile
phone. It's easier than you think; you don't even have to look at the actual
log files; it just sort of streams down the screen like the Matrix. That's the
effect I was going for (thank you LogZero).

You can ALSO see the log-file output that is also being written into
mysched.log which you can look at if say the script stopped running and the
real-time output went away::

    [I 180222 19:36:56 mysched:20] This is some logger info.
    [I 180222 19:47:07 mysched:20] This is some logger info.

****************************************
The first scheduled event
****************************************

Going from this "blank" scheduling file to the next step really highlights a
lot of the default power of the scheduling module.::

    import schedule as sched
    from pyfiglet import figlet_format
    from colorama import Fore
    from logzero import logger, setup_logger
    from datetime import date, datetime, timedelta
    import time

    UTCRebootTime = '06:00' # Generally, 1-AM for me
    beat_count = 0
    font = 'standard'
    subfont = 'cybermedium'
    green = Fore.GREEN
    white = Fore.WHITE
    blue = Fore.BLUE

    ascii_art1 = figlet_format('Congratulations!', font=font)
    ascii_art2 = figlet_format('Welcome to Wonderland.!', font=subfont)
    print('%s%s%s' % (green, ascii_art1, white))
    print('%s%s%s' % (blue, ascii_art2, white))

    the_time = str(datetime.now().time())[:5]
    logger = setup_logger(logfile='mysched.log', maxBytes=1000000, backupCount=3)
    logger.info("We're not in Jupyter Notebook anymore. The time is %s." % the_time)


    def main():
        sched.every(10).minutes.do(heartbeat)
        next_min = minute_adder(1).strftime('%H:%M')
        logger.info("When the clock strikes %s, down the rabbit hole with you!" % next_min)
        sched.every().day.at(next_min).do(the_queue)
        sched.every().day.at(UTCRebootTime).do(reboot)
        while True:
            sched.run_pending()
            time.sleep(1)


    def heartbeat():
        global beat_count
        beat_count += 1
        logger.info("Heartbeat %s at %s" % (beat_count, datetime.now()))


    def the_queue():
        logger.info("This is a scheduled event. Jump! Down the rabbit hole...")


    def reboot():
        logger.info("Rebooting system.")
        import subprocess
        p = subprocess.Popen(['sh', 'r.sh'], cwd='/home/ubuntu/pipulate/')


    def minute_adder(minutes):
        the_time = datetime.now().time()
        today = date.today()
        beat = timedelta(minutes=minutes)
        return_value = datetime.combine(today, the_time) + beat
        return return_value


    if __name__ == '__main__':
        main()

You can, and I encourage you to run this directly with the standard Python
command-line way of running it. If you haven't been doing it already, cd into
that directory and run::

    python mysched.py

****************************************
GNU screen, your portal to your scheduled world.
****************************************

Webmasters are dead. Long live the Datamaster! This is kind of like the LAMP
stack, but for scheduling in the modern world with (what I consider) the least
moving parts pushing around the "responsibilities". SQL-ish stuff goes to
Pandas, logic stuff to Python, Task-respawning to Linux, Data-UI to Google
Sheets... but what about WATCHING your scripts being run? What about getting
that at-one Zen feeling with all those invisible plates you have spinning?

If you put the service file in location at /etc/systemd/service/[mysched.py]
and reboot already, then this script is running in the background right now.
Wanna see it? It may be up to a bunch of those 10-minute heartbeats already.
Type::

    screen -d -r mysched

That's the gnu screen program. It's a lot like tmux, but if you don't know what
that is either, then it's a terminal server just like remote desktop software
like RDP or VNC, but instead of being for Graphical Desktops like Windows or
Mac, it's just for those type-in command-line terminals. It's a lot to type and
remember, so drop this into your /usr/local/sbin, or maybe your ~/ home folder
if sbin gives you trouble. I call it "ing.py" so that all together to see
what's going on (starting from a terminal on Mac, Windows, whatever), I type::

    go[Enter]
    do[Enter]

****************************************
Get used to using Ctrl+A (let go) then d to detach
****************************************

And then if I want to just immediately exit out, I type::

    Ctrl+A, D [Enter]

If you want to activate the "do.sh" just make this file by that name, chmod +x
it and drop it in your sbin or home::

    #!/bin/bash
    # Put this in your sbin or ~/ to be useful.

    screen -d -r mysched

This means that a secret invisible command-line task starts whenever the
machine reboots that you can "connect to" with that command. The -d parameter
means force it to detach from whatever other device it's showing on (the
"seizing" the display I mentioned earlier) and the -r parameter means
reconnect. Together, you can pretty much pull up your scheduling output
anywhere anytime.

But once you do, you are inside a terminal window session created by gnu screen
and NOT by the original login-session you had. The -d parameter means force it
to detach from whatever other device it's showing on (the "seizing" the
display I mentioned earlier) and the -r parameter means reconnect. This gives
you quite a bit of power to just scroll up and down the log-output (without
having to load a single file) using GNU screen's buffer-scroll::

    do[Enter] (to seize screen)
    Ctrl+A [Esc] (to switch to "Copy mode" with a scroll-back history)

Once you're in Copy Mode, you can use Page Up & Page Down. You can also use
Ctrl+B for back and Ctrl+F for forward. When you're done, hit the [Esc] key
again. When you want to release the screen session, it's still Ctrl+A, D
[Enter] to detach.

And finally, it can feel a little "out of control" to have a script running
insistently in the background with no way to stop.

The Unix/Linux-style type-in "terminal" interface that ships with Macs and can
be installed with Windows using CygWin or their new Windows 10 BASH shell is
your new portal into Wonderland. Jupyter Notebook gave you a taste of the power
of Python, but you're not really realizing it until you're running reports
during all that other delicious time when you're NOT sitting in front of a
browser hitting a button and waiting for something to finish on your local
machine.

****************************************
Making timestamps and caching pervasive
****************************************

You can't store everything locally, so don't try. You will run out of space,
and there's nothing worse than having to do file-maintenance on Cloud hardware
that's supposed to be sparing you from that nonsense. But neither can you write
anything that's going to fill your hard drive up forever with past data.
Hardware is hardware and resources are actually finite— or rather, they're as
finite as you're willing to pay for. So if we want to store the data long-term,
it's got to be off-server, probably using a service such as Amazon S3. Using a
"data bucket" NoSQL hash-table (call it what you will) is a good idea in
situations like this because "deconstructing" everything into rows & columns
for SQL-like RDBMS storage isn't worth it, and although field-stuffing into a
Text or XML field in an RDBMS would work, it feels a lot like shoving a round
peg into a square hole— why do it if a round hole is sitting right there?  This
is more a place-holder for me to incorporate probably a decorator-based cache
system that is back-ended by Amazon S3. That will solve a lot of ongoing server
maintenance issues.

########################################
First Scheduled Script
########################################

Okay, so the above sets out the framework for scheduling. We have:

- A daily reboot
- An every-10-minutes heartbeat
- Something beginning 1-minute after script runs

****************************************
A way to schedule external Python scripts
****************************************

So the idea now is to build-out from that 3rd point. We just just start putting
references to different external Python filename.py's there, and they'll just
run. But there's one more trick. I'm adding this function to mysched.py along
with importing the importlib library to do the trick::

    def do_main(name):
        mod = importlib.import_module(name)
        mod.main()

This way, if you follow the Python if __name__ == '__main__' convention, you
can use this to invoke the method (function) named "main" with it's standard
(non-parameterized) call by just putting it in the same folder as mysched.py
and referring to the file by name from within mysched.py like this::

    do_main(filename)

...and that's all you need to do to schedule something that uses that
convention. Conversely, if the code in the external file is of the directly
copy-pasted from Jupyter Notebook variety which is likely to NOT use a function
called main (or even functions at all), then you can use the alternative
version that just does it::

    def do_it(name):
        mod = importlib.import_module(name)

...invoked with the very straight forward::

    do_it(filename)

****************************************
Making the file
****************************************

You will be using .py files and not the .ipynb files of Jupyter Notebook for
scheduling. There are various ways to go about it, but I suggest just
copy-pasting your separate text-blocks from JN over to your text-editor or
whatever, and just re-build your script up from parts over server-side. The
reason for this is that it makes you think through your work again. The way you
work in Jupyter Notebook is going to be very different from the way you work on
a Linux scheduling system. Your considerations are about 100x more complex, and
so now is the time to start thinking about them. So make track.py in the same
repo directory::

    vim hello_world.py

Don't worry. I already put it in the repo for you. It is basically just a
template for the ASCII art that I like to do. I think I've gone overboard with
colors. I usually only use green for OK with other colors sprinkled in
sparingly to capture my attention (warnings & stuff). Thanking you for taking
the red pill gets an exception. But now that we've proven scheduling an
external script, it's time to add a SECOND external script and-get serious
about SEO::

    vim track.py

****************************************
There's no place like ~/pipulate
****************************************

The hardest part for me in trying to grab the reins and gaining control of all
the required parts of datamastering, is always staying centered. You always
have to know where things are relative to either root "/" or home "~/". Even
that is a Unix geek joke about symbolic links. Anyhoo, working directories
usually tend to end up relative to ~/ 'cause you don't edit much in root. And
that folder-name is likely going to be whatever your git repo. And if you're
cloning from me with::

    git clone git@github.com:miklevin/pipulate

...then you have a directory probably something like this::

    ~/pipulate

...which you're always going to want to be in, especially if the machine you're
working on is a cloud instance set up somewhere specifically for you
specifically for this purpose. Then, you can get rid of a lot of typing by
creating a file like this (given you're on Ubuntu / adjust to OS) as your
.bash_profile. These are invisible configuration files (because of the dot at
the beginning of their filename). .bash_profile is executed whenever your
username (in this case, the default EC2 Ubuntu's "ubuntu" user::

    source /home/ubuntu/py35/bin/activate /home/ubuntu/py35
    PATH="$HOME/:$PATH"
    clear
    python ~/hi.py
    cd /home/ubuntu/pipulate

This answers such pressing questions as:

- How do I always make sure I'm in the exact same Python virtualenv as the one
  I use for scheduling?
- How can I add little bash helper scripts to my repo and have them in my path
  so I can easily use them?
- How can I give myself a snazzy ASCII art login messing using Python and the
  Figlet library?
- How can I avoid typing cd pipulate every time I log into my scheduling
  server?

So now, whenever from your host machine you type::

    go

...you wil be logged automatically onto your cloud server and greeted with a
warm welcome that will impress your friends. What does hi.py look like you
ask?::

    from pyfiglet import figlet_format
    from colorama import Fore

    def out(print_me, color=Fore.GREEN, font='standard'):
        ascii_art = figlet_format(print_me, font=font)
        print('%s%s%s' % (color, ascii_art, Fore.WHITE))

    out('Welcome.')
    out("Get pipulating!", font='cybermedium', color=Fore.WHITE)

########################################
Getting over the hump
########################################

When getting started with any new investigation into data residing somewhere
that you're supposed to fetch, transform, and extract some insights from begins
with "where does the data come from?" and "Where do I put it?" questions. In
Google Sheets, you don't really have the option of warehousing all the raw data
pulls forever, unless you want your spreadsheets to get slower and slower, then
go corrupt. Instead, you have to either use services like Amazon S3, a large
local hard drive, or simply not warehouse as much data as you'd like.

****************************************
The Google Spreadsheet 100,000 cell limit
****************************************

Fortunately, you can do a lot in just the limited data-space of a single
spreadsheet, which supports (at last check) about 100,000 cells in any
Spreadsheet document before reaching a quota (and performance) limit. The 100K
cells can be broken up any way over rows & columns.

****************************************
Trim the fat
****************************************

Because every spreadsheet gives you an automatic 1000 rows and 26 columns, it's
easy to make the system use up 26,000 of those cells right away. This doesn't
really happen in practice, but there is ambiguity so as a matter of style and
preference, I like to delete all the rows and columns I'm not using. As in the
field of SEO, we just don't want to send mixed signals to Google.

To be continued...

########################################
To git clone or pip install?
########################################

If you "git clone", then you will get all the standard .ipynb example files in
a nice accessible place in ~/ (home) which you'll be able to reach with Jupyter
Notebook, but you can't make that your own home directory for a github repo
because you can't (easily) mix repos in the same folder. Yet, you're going to
want to immediately turn this location into your own repo. The answer is to::

    git clone git@github.com:miklevin/pipulate

...in one location in order to have access to the full repo and maybe
participate in Pipulate development. In another location, you make the folder
destined to become your own repo after you get my files, then delete out the
invisible .git folder inside and do a new "git init". So get started making the
myschedule folder::

    git clone git@github.com:miklevin/pipulate mysched
    cd mysched
    rm -rf .git
    rm -rf pipulate
    git init

From here, it's up to you how much you want to purge out from the original repo
files before you make you start adding files to your own git repo, but the
heart of the thing, the file that the Linux systemd daemon will point to in
your /etc/systemd/system/mysched.service file. If you pip installed Pipulate on
your system, none of the other files are really necessary. You may also wish to
do this clone-and-purge process on your local machine for the sake of keeping
your Jupyter Notebook work in a git repo as well. Remember the cloud server
you're working on is where you "promote" ad hoc Jupyter Notebook work to live
in a more persistent scheduled form, so you want to have very similar
environments on both. It's like forking, but none of this is really important
enough to fork. It's just your own scheduling instance of Pipulate.

########################################
I prefer to pip install... plus nbviewer.
########################################

If you're a purist about it and want to build it up from scratch for a fuller
understanding (than clone-and-purge can provide), then just make a new folder
directly from Jupyter Notebook and copy any raw source files you may need here
from github, or go through nbviewer for even easier saving of Jupyter
Notebook-ready .ipynb files. Just paste any templates you're interested in
from::

    https://github.com/miklevin/Pipulate

into::

    https://nbviewer.jupyter.org/

...and save the resulting .ipynb file to where your local copy of Jupyter
Notebook can reach it.

########################################
Reminders & To-Do's
########################################

Reminder to self: add logic to system to always address columns by Excel-style
letter-index::

    for i, col in enumerate(cols):
        letter = gs.cc(i+1)
        eval(tab)[col] = letter
        eval('%s2' % tab)[col] = '%s.%s' % (tab,letter)

Reminder to self: Pipulate Wisdom.

Much of the complexity is in the data-transform. Separate as much of the "raw
data" work as you can from the derivative output-data formats. Those can be
re-generated different ways with better and better insights revealed and
interactivity. But you may never be able to re-get that raw data. So focus!

########################################
Experimential: The Zen of Pipulate
########################################

- Everything you need has already been done many, many times.
- However, this does not spare you from SOME of the work.
- Processes resist automation until sufficient TLC is applied.
- And even then, it's all going to fall apart for 10 unexpected reasons.
- Your job then is to build with that sort of resilience in mind
- Even if it means scrapping-and-rebuilding quickly.

****************************************
Ideas for Tenants of the Pipulate System
****************************************

- Got a dataframe that was tough to get? Maybe it should be a .csv file.
- Got a .csv file on your drive blocking you? Was it generated today?
- It's better to pip install pipulate than git clone pipulate.
- Directories you create to pipulate out of shouldn't all be repos.
- Little secret-sauce pipulations belong in private Github gists.
