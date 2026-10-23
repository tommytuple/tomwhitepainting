#!/usr/bin/env python3
"""Build the themed paint colour pages under /paint-colours/.

Every colour on these pages is a real paint. The hex, LRV, undertone and
colour family all come from the paint colour API at build time and get
written into static HTML, so the pages are readable by search engines and
by anything that doesn't run JavaScript. The explorer itself stays a live
tool; these pages are the part that can be indexed and quoted.

    python3 build_colour_pages.py && python3 build_sitemap.py

Colours are pinned by id rather than by name so a rename upstream can't
quietly swap a swatch underneath the words written about it.
"""

import html
import json
import pathlib
import shutil
import subprocess
import tempfile
import urllib.request

API = "https://paint-colour-db.fly.dev/v1"
SITE = "https://tomwhitepainter.co.uk"
ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "paint-colours"


# --------------------------------------------------------------------------
# The themes. "note" is what I'd tell someone standing in the room with a
# brush in my hand: where the colour works, and where it doesn't.
# --------------------------------------------------------------------------

THEMES = {
    "sexy": {
        "slug": "sexy",
        "h1": "Sexy Paint Colours: Deep, Dramatic Shades That Actually Work",
        "title": "Sexy Paint Colours &ndash; 12 Deep, Dramatic Shades | Tom White",
        "desc": "Twelve genuinely dramatic paint colours, with light reflectance values and honest advice on which rooms they suit, from a decorator of 30 years.",
        "lede": [
            "Every list of &ldquo;sexy&rdquo; paint colours I have ever read is a "
            "mood board. Here is the decorator&rsquo;s version: twelve colours I would "
            "actually put on a wall, with the numbers that tell you whether they will "
            "work in your room.",
            "The number that matters is the light reflectance value, the LRV. It runs "
            "from 0 for black to 100 for white, and it tells you how much light the "
            "colour throws back into the room. Everything on this page sits under 15. "
            "That is the point of them &mdash; and it is also the thing people get "
            "caught out by.",
        ],
        "advice_h2": "Before you commit to a dark colour",
        "advice": [
            "A dark colour eats light. In a north-facing room with one small window "
            "it will read as flat and grey for most of the day. In a room with a "
            "decent window, or one you mainly use after dark, the same colour comes "
            "alive. Dark colours are for evening rooms: bedrooms, dining rooms, "
            "snugs, downstairs loos.",
            "Finish does more work than the colour does. A dead flat matt swallows "
            "light and makes the colour look deeper and softer. An eggshell or a "
            "satin bounces light off the surface and makes the same colour look "
            "harder and glossier. If you want drama rather than severity, go matt.",
            "Dark colours show every defect in the plaster, because the sheen "
            "difference over a filled patch is far more visible than it is under "
            "white. Budget for the preparation, not just the paint.",
            "Two coats will almost never do it over a light wall. Deep reds and "
            "inky blues routinely want three, sometimes four, and a tinted primer "
            "underneath saves you a coat of expensive topcoat.",
        ],
        "colours": [
            (675715, "Near enough black until the light catches it, then it is "
                     "unmistakably blue. At an LRV of 1 this is about as dark as "
                     "paint gets. Glorious on joinery in a room that already has "
                     "good light."),
            (675709, "A proper deep cherry with real warmth in it. Reds this "
                     "saturated are the hardest colours to apply evenly &mdash; "
                     "use a tinted undercoat and keep a wet edge."),
            (647681, "Softer and dustier than the name suggests, which is why it "
                     "works in a bedroom where a brighter red would be exhausting. "
                     "One of the most forgiving dark reds there is."),
            (647602, "An aubergine with a pink undertone that stops it going cold. "
                     "Beautiful by candlelight, muddy under a cool LED &mdash; worth "
                     "changing the bulbs before you judge it."),
            (647639, "The dark blue everyone reaches for, and for good reason. Deep "
                     "enough to feel dramatic, blue enough never to read as black. "
                     "Excellent in a dining room."),
            (675757, "Darker and greener than Hague Blue, and a touch more severe. "
                     "This is a colour for a room with a fire in it."),
            (647703, "Reads as near-black in low light and as a deep forest green "
                     "when the sun gets to it. The most useful dark colour on this "
                     "list because it changes all day."),
            (647670, "A black with purple in it rather than blue, which keeps it "
                     "warm. The right black for woodwork in a Victorian house."),
            (647832, "A muted plum-brown that behaves more like a deep neutral than "
                     "a colour. Easier to live with than a true purple."),
            (647925, "A loud, confident red that needs somewhere to be loud. A "
                     "front door, a hallway, a single chimney breast &mdash; not a "
                     "whole bedroom unless you are very sure."),
            (675851, "Almost black, with the warmth of chocolate underneath. "
                     "Exceptional on panelling and on the inside of a bookcase."),
            (647748, "A cool charcoal with blue in it. The safe entry point to dark "
                     "walls if the rest of this page frightens you."),
        ],
        "faq": [
            ("Do dark paint colours make a room look smaller?",
             "Not in the way people mean. A dark colour hides where the wall ends, "
             "so the corners of the room stop announcing themselves and the space "
             "reads as deeper, not smaller. What dark colours genuinely do is make "
             "a room darker, which is only a problem if you needed the light."),
            ("How many coats of a dark colour will I need?",
             "Over an existing light wall, expect three. Deep reds and strong "
             "blues sometimes want four. A grey or tinted primer close to the "
             "final colour will usually save you a full topcoat, which pays for "
             "itself on designer paint."),
            ("What finish is best for a dark colour?",
             "A flat or dead matt emulsion on walls, because it absorbs light and "
             "keeps the colour soft. Use eggshell on woodwork, where you need the "
             "durability. Avoid silk on a dark wall entirely &mdash; it will show "
             "every roller mark."),
            ("Which rooms suit dark paint colours?",
             "Rooms you use in the evening, and rooms that already have decent "
             "natural light. Bedrooms, dining rooms, snugs and downstairs "
             "cloakrooms are the usual wins. A dark north-facing kitchen you use "
             "at eight in the morning is the usual regret."),
        ],
    },

    "earthy": {
        "slug": "earthy",
        "h1": "Earthy Paint Colours: Clay, Ochre, Olive and Warm Stone",
        "title": "Earthy Paint Colours &ndash; Clay, Ochre &amp; Olive Tones | Tom White",
        "desc": "Warm earth tone paint colours with light reflectance values and practical advice on undertones, from a Brighton decorator of 30 years.",
        "lede": [
            "Earthy colours are the ones that look like something: clay, ochre, "
            "olive, dust, stone. They are pigments people have been putting on "
            "walls for several thousand years, which is roughly why they are so "
            "easy to live with.",
            "What makes them work is the undertone &mdash; the yellow, the red or "
            "the green sitting underneath the colour you think you are looking at. "
            "Get two earthy colours with fighting undertones next to each other "
            "and the whole scheme goes slightly sour. Every colour below lists its "
            "undertone so you can keep them talking to each other.",
        ],
        "advice_h2": "Making earth tones work together",
        "advice": [
            "Pick one undertone and stay with it. A yellow-undertone stone next to "
            "a red-undertone clay will read as dirty rather than warm. The "
            "undertone is listed on every colour here; matching it is most of the "
            "job.",
            "Earth tones want warm light. Under a 2700K bulb they glow; under a "
            "cool 4000K one they go grey and flat. If you have cool LEDs "
            "throughout, change those before you change the paint.",
            "They are forgiving on imperfect walls, which makes them a genuinely "
            "good choice for an old house. The slight irregularity of lime plaster "
            "or a hundred-year-old wall reads as texture rather than as a defect.",
            "Mid-LRV earth tones &mdash; the 25 to 50 range &mdash; are the most "
            "useful colours in decorating. Dark enough to have character, light "
            "enough to use across a whole room without the place closing in.",
        ],
        "colours": [
            (647645, "The classic ochre. Properly yellow without going anywhere "
                     "near acid, and it makes a north-facing room feel as though "
                     "the sun is out when it isn't."),
            (647684, "A terracotta softened with grey, which is what stops it "
                     "looking like a flowerpot. Very good in a hallway."),
            (613227, "A stronger, redder terracotta than Red Earth. Use it on one "
                     "wall or in a small room rather than everywhere."),
            (675889, "A deep brick red with brown in it. Traditional on the outside "
                     "of a building and increasingly good inside on joinery."),
            (647661, "The most useful muddy neutral there is &mdash; a brown-grey "
                     "with a yellow undertone that behaves itself next to almost "
                     "anything."),
            (647603, "Deeper and browner than Mouse's Back, same easy temperament. "
                     "Handsome on a panelled wall."),
            (647711, "A grey-green that reads as olive in good light and as stone "
                     "in bad. One of the few greens that works in a room with no "
                     "garden to look at."),
            (675833, "A real olive, dark and dusty. Superb on exterior joinery and "
                     "on a kitchen island."),
            (675708, "A warm greyish brown with a yellow undertone. Reads as a "
                     "dark neutral rather than as a colour, which is useful."),
            (647704, "An antique yellow with plenty of warmth. Lighter and gentler "
                     "than India Yellow if that one is too much."),
            (675750, "Exactly what it says: a soft sandy clay. Mid-LRV and almost "
                     "impossible to get wrong across a whole room."),
            (675887, "A pale warm stone, the colour of the building material. A "
                     "better alternative to magnolia than most things sold as one."),
            (651933, "A soft warm off-white with a yellow undertone. Earthborn's "
                     "clay paints are breathable, which matters on an old solid "
                     "wall that needs to let moisture out."),
        ],
        "faq": [
            ("What are earth tone paint colours?",
             "Colours drawn from natural pigments &mdash; ochres, clays, umbers, "
             "olives and warm stones. In practical terms they are colours with a "
             "warm yellow, red or brown undertone and relatively low saturation, "
             "which is why they sit comfortably in a room rather than shouting."),
            ("Are earthy colours warm or cool?",
             "Almost always warm, though olives and some stones sit close to "
             "neutral. Every colour on this page lists its measured warmth and its "
             "undertone, so you can tell the genuinely warm ones from the ones "
             "that will go grey on a north wall."),
            ("Which earthy colour works best in a north-facing room?",
             "One with a yellow or red undertone and an LRV above about 35. India "
             "Yellow, Sudbury Yellow and Clay all push warmth back into a cold "
             "room. Avoid the grey-greens in a north-facing space unless you want "
             "the room to feel cool."),
            ("Do earth tones work in a modern house?",
             "Yes, and arguably better than in a period one, because a modern "
             "room with flat plaster and large windows needs the warmth. The thing "
             "to avoid is pairing them with cool grey flooring, which fights the "
             "undertone."),
        ],
    },

    "brighton": {
        "slug": "brighton",
        "h1": "Brighton Paint Colours: Regency Stucco, Beach Hut Pastels and Sea Greens",
        "title": "Brighton Paint Colours &ndash; Regency, Seaside &amp; Sea Green | Tom White",
        "desc": "The colours Brighton and Hove houses are actually painted: Regency stucco creams, beach hut pastels and sea greens, from a decorator working here 30 years.",
        "lede": [
            "I have been painting houses in Brighton and Hove for thirty years, and "
            "the city has a palette whether it means to or not. Regency cream on the "
            "stucco, washed-out pastels along the seafront, and a particular grey-"
            "green that turns up on every other front door between Kemptown and "
            "Hove.",
            "These are real paints with their light reflectance values and "
            "undertones, chosen for how they behave in this specific light. The sea "
            "throws a great deal of bright, slightly cool light at the front of a "
            "building here, and colours that look right inland can look bleached "
            "out by eleven in the morning.",
        ],
        "advice_h2": "Painting a house by the sea",
        "advice": [
            "Salt air is the whole problem. Exterior paint on a seafront building "
            "has a materially shorter life than the same paint two miles inland, "
            "and the south and west elevations go first. Expect to repaint exposed "
            "elevations more often than the back of the house.",
            "On Regency and Victorian stucco, use a breathable masonry paint. "
            "Those walls are solid, with no cavity and usually no damp proof "
            "course, and they rely on being able to dry outwards. A plastic film "
            "paint traps moisture behind it and the render blows off in sheets a "
            "few winters later.",
            "Strong colours fade faster here. The light off the water is harsh and "
            "south-facing fronts take a beating &mdash; which is part of why the "
            "traditional seafront palette is pale. The pastels are not just a "
            "style choice, they weather better.",
            "If you are in a conservation area &mdash; and a great deal of central "
            "Brighton and Hove is &mdash; check with the council before you change "
            "an exterior colour. Listed buildings have tighter rules again.",
        ],
        "colours": [
            (647664, "The Regency stucco colour. A warm off-white that reads as "
                     "cream on a terrace front without ever looking yellow."),
            (675876, "A cooler, cleaner version of the same idea. Good where the "
                     "neighbouring houses are already warm and you want to sit "
                     "slightly apart from them."),
            (647673, "A soft greige that does very well on seafront render. High "
                     "enough LRV to stay bright, grey enough not to glare."),
            (647615, "A cool grey with a yellow undertone that keeps it from going "
                     "blue. The standard-issue Brighton flat interior, and it has "
                     "earned it."),
            (647623, "A grey-green with blue in it. If there is one Brighton "
                     "colour, this is it &mdash; on front doors, on shopfronts, on "
                     "garden gates all over Hove."),
            (647637, "Softer and greener than Dix Blue. Lovely on a kitchen in a "
                     "flat that looks at the sea."),
            (675739, "A pale sea green with real depth. Handsome on exterior "
                     "joinery against a cream front."),
            (647699, "A proper mid blue with grey in it, closer to the Channel than "
                     "to the Mediterranean. Excellent on a front door."),
            (647656, "A clear, pale, slightly chalky blue &mdash; the beach hut "
                     "colour. Looks right on a balcony or a bit of seafront "
                     "ironwork."),
            (675725, "A gentle blue-green that works where Lulworth Blue would be "
                     "too sweet. Good in a bathroom."),
            (647671, "A very pale green-grey. On a north-facing wall it reads as "
                     "white with something going on in it."),
            (647599, "A pale blue-grey with a cool undertone, which suits a bright "
                     "south-facing seafront room that already has too much warmth "
                     "coming in off the water."),
            (647653, "Despite the name, a grey-green rather than a blue. A "
                     "Georgian colour that sits very comfortably on Brighton "
                     "joinery."),
            (675703, "A soft, dusty aquamarine. The most seaside colour here "
                     "without tipping into novelty."),
        ],
        "faq": [
            ("What colour are Brighton's Regency houses painted?",
             "The stucco fronts of the Regency terraces in Brighton and Hove are "
             "traditionally a warm off-white or pale cream, meant to imitate Bath "
             "stone. Farrow &amp; Ball New White and Little Greene Slaked Lime are "
             "both close to the traditional colour in a modern breathable masonry "
             "paint."),
            ("What paint should I use on a house by the sea?",
             "A breathable masonry paint on solid walls, and a high quality "
             "exterior eggshell on joinery. Salt air and driving rain shorten the "
             "life of exterior coatings noticeably on the seafront, and a "
             "non-breathable paint on old solid render will trap moisture and blow "
             "the surface off."),
            ("Can I paint my house any colour in Brighton?",
             "Not everywhere. Much of central Brighton and Hove sits in a "
             "conservation area, and many seafront terraces are listed, which "
             "restricts exterior colour changes. Check with Brighton &amp; Hove "
             "City Council before changing an exterior colour on a period "
             "building."),
            ("How often does a seafront house need repainting?",
             "More often than an inland one, and the exposed elevations go first. "
             "The south and west faces of a seafront building take the salt and "
             "the weather, and will usually want attention well before the "
             "sheltered sides do."),
        ],
    },
}


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------

def fetch(path):
    with urllib.request.urlopen(f"{API}{path}", timeout=30) as r:
        return json.load(r)


def colour(cid):
    return fetch(f"/colours/{cid}")["colour"]


def equivalents(cid, limit=3):
    """The closest colour from a handful of other makes, so someone who likes
    a Farrow & Ball colour can find the trade equivalent."""
    try:
        eqs = fetch(f"/colours/{cid}/equivalents")["equivalents"]
    except Exception:
        return []
    eqs = [e for e in eqs if e.get("delta_e", 99) < 3]
    eqs.sort(key=lambda e: e["delta_e"])
    return eqs[:limit]


# --------------------------------------------------------------------------
# Social cards
# --------------------------------------------------------------------------

def social_card(hexes, dest, cols=4, rows=2):
    """A 1200x630 card made of the page's own colours.

    Needs ImageMagick. It is only the Open Graph preview, so if magick isn't
    installed the page still builds and keeps whatever card is already there.
    """
    if shutil.which("magick") is None:
        print(f"    (no imagemagick, keeping {dest.name})")
        return

    w, h = 1200 // cols, 630 // rows
    picks = [hexes[i % len(hexes)] for i in range(cols * rows)]

    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        chips = []
        for i, hx in enumerate(picks):
            chip = tmp / f"{i:02d}.png"
            subprocess.run(["magick", "-size", f"{w}x{h}", f"xc:{hx}", str(chip)],
                           check=True)
            chips.append(str(chip))

        strips = []
        for r in range(rows):
            strip = tmp / f"row{r}.png"
            subprocess.run(["magick", *chips[r * cols:(r + 1) * cols],
                            "+append", str(strip)], check=True)
            strips.append(str(strip))

        subprocess.run(["magick", *strips, "-append",
                        "-quality", "88", "-strip", str(dest)], check=True)
    print(f"    card: {dest.name}")


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def e(s):
    return html.escape(str(s), quote=True)


def swatch_card(c, note, eqs):
    label = e(c["label"])
    make = e(c["make"]["name"])
    hexv = c["hex"]
    fg = "#ffffff" if c["text_colour"] == "white" else "#000000"

    eq_html = ""
    if eqs:
        items = "".join(
            f"<li>{e(x['colour']['make']['name'])} "
            f"<strong>{e(x['colour']['label'])}</strong> "
            f"<small>(&Delta;E {x['delta_e']:.1f})</small></li>"
            for x in eqs
        )
        eq_html = (
            "\n                        <details>\n"
            "                            <summary>Closest match from other makes</summary>\n"
            f"                            <ul class=\"swatch-equivalents\">{items}</ul>\n"
            "                        </details>"
        )

    buy = ""
    if c.get("brewers_url"):
        buy = (f'\n                        <p class="swatch-buy">'
               f'<a href="{e(c["brewers_url"])}" rel="nofollow noopener" '
               f'target="_blank">Look it up at Brewers</a></p>')

    return f"""                <article class="swatch">
                    <div class="swatch-chip" style="background: {hexv}; color: {fg}">
                        <span>{hexv}</span>
                    </div>
                    <div class="swatch-body">
                        <h3>{label}</h3>
                        <p class="swatch-make">{make}</p>
                        <p class="swatch-note">{note}</p>
                        <dl class="swatch-data">
                            <div><dt>Light reflectance</dt><dd>{c['lrv']}</dd></div>
                            <div><dt>Undertone</dt><dd>{e(c['undertone'] or 'none')}</dd></div>
                            <div><dt>Colour family</dt><dd>{e(c['family'])}</dd></div>
                            <div><dt>Temperature</dt><dd>{e(c['temperature'])}</dd></div>
                            <div><dt>Hex</dt><dd><code>{hexv}</code></dd></div>
                            <div><dt>RGB</dt><dd>{c['rgb']['r']}, {c['rgb']['g']}, {c['rgb']['b']}</dd></div>
                        </dl>{eq_html}{buy}
                    </div>
                </article>"""


NAV = """                <nav>
                    <input
                        type="checkbox"
                        id="my-nav"
                        class="navbar-toggle"
                        hidden
                    />

                    <label for="my-nav" class="navbar-burger">&#9776;</label>
                    <ul class="navbar-menu">
                        <li><a href="{up}index.html">Home</a></li>
                        <li><a href="{up}explore-paint-colours/">Paint Colours</a></li>
                        <li><a href="{up}paint-colours/">Colour Guides</a></li>
                        <li><a href="{up}testimonials.html">Testimonials</a></li>
                        <li><a href="{up}about.html">About Me</a></li>
                        <li><a href="{up}contact.html">Contact</a></li>
                    </ul>
                </nav>"""


def page_shell(*, canonical, title, desc, og_img, body, schema, up):
    url = SITE + canonical
    plain_title = html.unescape(title).split(" | ")[0]
    plain_desc = html.unescape(desc)
    return f"""<!doctype html>
<html style="scroll-behavior: smooth" lang="en" data-theme="light">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>
            {title}
        </title>
        <meta name="description" content="{desc}" />
        <link rel="canonical" href="{url}" />

        <meta property="og:type" content="article" />
        <meta property="og:site_name" content="Tom White, Painter &amp; Decorator" />
        <meta property="og:locale" content="en_GB" />
        <meta property="og:url" content="{url}" />
        <meta property="og:title" content="{e(plain_title)}" />
        <meta property="og:description" content="{e(plain_desc)}" />
        <meta property="og:image" content="{SITE}{og_img}" />
        <meta property="og:image:width" content="1200" />
        <meta property="og:image:height" content="630" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="{e(plain_title)}" />
        <meta name="twitter:description" content="{e(plain_desc)}" />
        <meta name="twitter:image" content="{SITE}{og_img}" />

{schema}
        <link
            rel="stylesheet"
            href="https://unpkg.com/@digicreon/mucss/dist/mu.azure.css"
        />
        <link rel="stylesheet" href="{up}style.css" />
    </head>
    <body class="container wide" style="margin-top: 2rem">
        <section>
            <picture>
                <source
                    media="(max-width: 768px)"
                    srcset="{up}photos/mobile/tomwhite_logo.webp"
                    type="image/webp"
                />
                <img src="{up}photos/tomwhite_logo.webp" alt="Tom White Logo" />
            </picture>
        </section>

        <main>
            <article>
{NAV.format(up=up)}
            </article>

{body}
        </main>
    </body>
</html>
"""


def ld(obj):
    return ('        <script type="application/ld+json">\n'
            + json.dumps(obj, indent=2, ensure_ascii=False)
            + "\n        </script>")


def build_theme(key, t):
    up = "../../"
    canonical = f"/paint-colours/{t['slug']}/"
    print(f"  {t['slug']}: fetching {len(t['colours'])} colours…")

    rows = []
    records = []
    for cid, note in t["colours"]:
        c = colour(cid)
        records.append(c)
        rows.append(swatch_card(c, note, equivalents(cid)))

    lede = "\n".join(f"                <p>{p}</p>" for p in t["lede"])
    advice = "\n".join(f"                <p>{p}</p>" for p in t["advice"])

    faq_html = "\n".join(
        f"""                <details class="faq">
                    <summary><h3>{q}</h3></summary>
                    <p>{a}</p>
                </details>"""
        for q, a in t["faq"]
    )

    others = " &middot; ".join(
        f'<a href="../{o["slug"]}/">{html.unescape(o["h1"]).split(":")[0]}</a>'
        for k, o in THEMES.items() if k != key
    )

    body = f"""            <article class="card-primary" style="margin-bottom: 3rem">
                <header><h1>{t['h1']}</h1></header>
{lede}

                <p class="colour-caveat">
                    Every colour below is a real paint, and the light reflectance
                    values and undertones are measured rather than guessed. They are
                    still screen versions of paint though, so order a sample pot and
                    look at it on your own wall, in your own light, before you buy
                    ten litres of anything.
                </p>

                <h2>{t['advice_h2']}</h2>
{advice}

                <h2>The colours</h2>
                <div class="swatch-grid">
{chr(10).join(rows)}
                </div>

                <h2>Common questions</h2>
{faq_html}

                <h2>Find your own</h2>
                <p>
                    This page is a shortlist. If you want to work through the whole
                    range &mdash; every colour from Dulux, Farrow &amp; Ball, Little
                    Greene, Crown, Johnstone&rsquo;s and the rest, filtered by tone,
                    warmth and light reflectance &mdash; use the
                    <a href="{up}explore-paint-colours/">paint colour explorer</a>.
                    You can match any colour you already have to the closest real
                    paints, and see what it looks like next to the colours that go
                    with it.
                </p>
                <p class="theme-links">Other shortlists: {others}</p>

                <h2>Want someone to paint it?</h2>
                <p>
                    I am a painter and decorator in Brighton &amp; Hove, interior and
                    exterior, private and commercial. If you have picked a colour and
                    want it put on properly &mdash; or you want a second opinion
                    before you commit &mdash;
                    <a href="{up}contact.html">get in touch</a>.
                </p>
            </article>"""

    schema = "\n\n".join([
        ld({
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": html.unescape(t["h1"]),
            "description": html.unescape(t["desc"]),
            "image": f"{SITE}/photos/og-{t['slug']}.jpg",
            "author": {"@type": "Person", "name": "Tom White"},
            "publisher": {"@id": f"{SITE}/#business"},
            "mainEntityOfPage": SITE + canonical,
        }),
        ld({
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": html.unescape(t["h1"]),
            "numberOfItems": len(records),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "item": {
                        "@type": "Product",
                        "name": f"{c['make']['name']} {c['label']}",
                        "category": "Paint",
                        "color": c["hex"],
                        "brand": {"@type": "Brand", "name": c["make"]["name"]},
                    },
                }
                for i, c in enumerate(records)
            ],
        }),
        ld({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": html.unescape(q),
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": html.unescape(a),
                    },
                }
                for q, a in t["faq"]
            ],
        }),
        ld({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home",
                 "item": f"{SITE}/"},
                {"@type": "ListItem", "position": 2, "name": "Paint Colours",
                 "item": f"{SITE}/paint-colours/"},
                {"@type": "ListItem", "position": 3,
                 "name": html.unescape(t["h1"]).split(":")[0],
                 "item": SITE + canonical},
            ],
        }),
    ])

    out = OUT / t["slug"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page_shell(
        canonical=canonical, title=t["title"], desc=t["desc"],
        og_img=f"/photos/og-{t['slug']}.jpg", body=body, schema=schema, up=up,
    ))

    print(f"  {t['slug']}: wrote {out / 'index.html'}")
    social_card([c["hex"] for c in records], ROOT / "photos" / f"og-{t['slug']}.jpg")
    return records


def build_hub(all_records):
    up = "../"
    cards = []
    for key, t in THEMES.items():
        recs = all_records[key]
        strip = "".join(
            f'<span style="background:{c["hex"]}"></span>' for c in recs[:10]
        )
        name = html.unescape(t["h1"]).split(":")[0]
        blurb = html.unescape(t["desc"]).split(",")[0]
        cards.append(f"""                <article class="theme-card">
                    <a href="{t['slug']}/">
                        <span class="theme-strip">{strip}</span>
                        <h2>{e(name)}</h2>
                    </a>
                    <p>{e(blurb)}. {len(recs)} colours.</p>
                </article>""")

    body = f"""            <article class="card-primary" style="margin-bottom: 3rem">
                <header><h1>Paint Colour Guides</h1></header>
                <p>
                    Shortlists of real paint colours, picked by someone who has spent
                    thirty years putting them on walls. Every colour comes with its
                    measured light reflectance value and undertone, and honest advice
                    about the rooms it suits.
                </p>

                <div class="theme-grid">
{chr(10).join(cards)}
                </div>

                <h2>Or browse the lot</h2>
                <p>
                    These pages are shortlists. The
                    <a href="{up}explore-paint-colours/">paint colour explorer</a>
                    holds every colour from Dulux, Farrow &amp; Ball, Little Greene,
                    Crown, Johnstone&rsquo;s and more, and will match any colour you
                    give it to the closest real paints you can buy.
                </p>
            </article>"""

    schema = ld({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Paint Colour Guides",
        "url": f"{SITE}/paint-colours/",
        "publisher": {"@id": f"{SITE}/#business"},
        "hasPart": [
            {"@type": "Article",
             "name": html.unescape(t["h1"]),
             "url": f"{SITE}/paint-colours/{t['slug']}/"}
            for t in THEMES.values()
        ],
    })

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page_shell(
        canonical="/paint-colours/",
        title="Paint Colour Guides &ndash; Shortlists by a Decorator | Tom White",
        desc="Shortlists of real paint colours with light reflectance values, undertones and advice on the rooms they suit, from a Brighton decorator of 30 years.",
        og_img="/photos/og-paint-colours.jpg", body=body, schema=schema, up=up,
    ))
    print(f"  hub: wrote {OUT / 'index.html'}")


def main():
    print("building themed colour pages")
    all_records = {}
    for key, t in THEMES.items():
        all_records[key] = build_theme(key, t)
    build_hub(all_records)
    print("done — now run: python3 build_sitemap.py")


if __name__ == "__main__":
    main()
