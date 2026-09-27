"""
recycling_engine.py
--------------------
Backend "brain" for the AI Recycling Assistant & DIY Guide feature.

Responsibilities:
1. analyze_image_opencv()  -> a lightweight OpenCV-based heuristic that looks
   at an uploaded photo (colour, saturation, brightness, edge density) and
   guesses which waste category it most likely belongs to. This is a simple
   rule-based "computer vision" fallback -- it runs entirely on the server
   with no external model file needed.

   For real machine-learning-grade accuracy, the frontend (ai_assistant.html)
   also supports plugging in a model trained with Google's Teachable Machine
   (TensorFlow.js) that runs client-side in the browser. Whichever source
   provides a classification, it is routed through the same decision engine
   below.

2. get_diy_guide() / DIY_GUIDES -> the "decision engine": given a waste
   category, returns curated DIY reuse ideas, step-by-step instructions,
   safety tips and a suggested video search query.

3. youtube_search_url() -> builds a safe YouTube *search* link for the idea
   (we never hardcode a specific video id, since we can't verify a real
   video exists/stays up -- the search link always works).
"""

from urllib.parse import quote_plus

import numpy as np
import cv2

# Categories kept identical to the `category` values already used for
# marketplace listings, so detection results map 1:1 onto the site.
CATEGORIES = ["plastic", "paper", "glass", "metal", "e-waste", "clothes"]


# ---------------------------------------------------------------------------
# 1. OpenCV heuristic material detector
# ---------------------------------------------------------------------------
def analyze_image_opencv(image_bytes):
    """
    Very lightweight, dependency-free 'AI material detector'.

    Takes raw image bytes (from a Flask FileStorage.read()), decodes them
    with OpenCV, and scores each category using simple colour/texture cues.
    Returns: {"material": <best category>, "confidence": <0-100 float>,
              "scores": {category: score, ...}}

    NOTE: this is a heuristic, not a trained neural network. It is meant as
    an always-available fallback / second opinion alongside the optional
    Teachable Machine model on the frontend.
    """
    file_bytes = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Could not decode image")

    # Normalize size for consistent, fast analysis
    img = cv2.resize(img, (200, 200))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    hue, sat, val = cv2.split(hsv)
    mean_hue = float(np.mean(hue))
    mean_sat = float(np.mean(sat))
    mean_val = float(np.mean(val))
    std_val = float(np.std(val))  # brightness variation -> shiny/specular surfaces

    edges = cv2.Canny(gray, 60, 160)
    edge_density = float(np.count_nonzero(edges)) / edges.size  # 0-1, texture/complexity

    scores = {cat: 0.0 for cat in CATEGORIES}

    # Metal: fairly low colour saturation, but bright specular highlights
    # (big brightness swings) from reflective surfaces.
    scores["metal"] += max(0, 60 - mean_sat) * 0.6
    scores["metal"] += min(std_val, 80) * 0.8

    # Glass: low saturation, high overall brightness (clear/reflective),
    # relatively smooth (low edge density).
    scores["glass"] += max(0, 60 - mean_sat) * 0.5
    scores["glass"] += mean_val * 0.3
    scores["glass"] += max(0, 0.25 - edge_density) * 100

    # Plastic: usually the most saturated / colourful category (bright
    # packaging, bottles, toys).
    scores["plastic"] += mean_sat * 0.9

    # Paper/cardboard: warm tan/brown hues (~10-30 in OpenCV's 0-179 hue
    # range) with a visibly textured/fibrous surface.
    if 8 <= mean_hue <= 35:
        scores["paper"] += 40
    scores["paper"] += edge_density * 60
    scores["paper"] += max(0, 40 - mean_sat) * 0.3

    # E-waste: circuit boards are commonly green, casings often black/dark
    # with lots of small components -> high edge density + low brightness.
    if 40 <= mean_hue <= 90:
        scores["e-waste"] += 35
    scores["e-waste"] += max(0, 120 - mean_val) * 0.25
    scores["e-waste"] += edge_density * 70

    # Clothes/fabric: varied colour + high texture from weave/patterns.
    scores["clothes"] += edge_density * 50
    scores["clothes"] += min(mean_sat, 150) * 0.35

    best_category = max(scores, key=scores.get)
    total = sum(scores.values()) or 1.0
    confidence = round((scores[best_category] / total) * 100, 1)

    return {
        "material": best_category,
        "confidence": confidence,
        "scores": {k: round(v, 1) for k, v in scores.items()},
    }


# ---------------------------------------------------------------------------
# 2. Decision engine: DIY ideas, steps & safety tips per category
# ---------------------------------------------------------------------------
DIY_GUIDES = {
    "plastic": {
        "display_name": "Plastic",
        "icon": "♻️",
        "general_safety": [
            "Rinse and dry the item before working with it.",
            "Use scissors/cutters away from your body; ask an adult to help with cutting if you're a minor.",
            "Sand or tape any sharp cut edges before handling.",
        ],
        "ideas": [
            {
                "title": "Self-Watering Bottle Planter",
                "difficulty": "Easy",
                "time": "15 mins",
                "materials_needed": [
                    "1 plastic bottle (1–2 L)",
                    "Scissors or a cutter",
                    "A strip of cotton rope or old cloth (~20 cm)",
                    "Potting soil",
                    "A small seedling or seeds",
                ],
                "steps": [
                    "Wash and dry the bottle, and peel off the label.",
                    "Mark a line about one-third of the way down from the neck, then cut the bottle in half.",
                    "Poke a small hole in the cap and thread the rope/cloth strip through it — this becomes the water wick.",
                    "Turn the top half upside down (neck facing down) and rest it inside the bottom half.",
                    "Fill the top half with soil and your plant; fill the bottom half with water so the wick can draw it up over time.",
                ],
                "safety_tips": [
                    "Cut on a stable surface, keeping fingers away from the blade path.",
                    "Round off or tape the cut rim so it isn't sharp.",
                ],
                "video_query": "DIY self watering planter from plastic bottle",
            },
            {
                "title": "Plastic Bottle Bird Feeder",
                "difficulty": "Easy",
                "time": "20 mins",
                "materials_needed": [
                    "1 plastic bottle",
                    "2 wooden spoons or sticks",
                    "String",
                    "Birdseed",
                ],
                "steps": [
                    "Clean the bottle thoroughly and remove the label.",
                    "About a third up from the base, cut two small X-shaped slits on opposite sides for the spoon handles.",
                    "Just above each slit, cut a small hole so seed can trickle onto the spoon.",
                    "Push the spoon handles through the X-slits so the spoon bowls sit outside as little perches/trays.",
                    "Poke two holes near the neck, thread string through to hang it, then fill with birdseed via the neck.",
                ],
                "safety_tips": [
                    "Use blunt-tipped scissors and have an adult help pierce the holes.",
                    "Hang the feeder somewhere it won't fall on anyone below.",
                ],
                "video_query": "DIY plastic bottle bird feeder tutorial",
            },
        ],
    },
    "paper": {
        "display_name": "Paper / Cardboard",
        "icon": "📦",
        "general_safety": [
            "Keep blenders/mixers unplugged before cleaning them out.",
            "Work over a tray or basin — pulping paper is messy.",
            "Let all glue/paste-based crafts dry in a ventilated area.",
        ],
        "ideas": [
            {
                "title": "Handmade Recycled Paper Sheets",
                "difficulty": "Medium",
                "time": "1–2 hrs (+ drying overnight)",
                "materials_needed": [
                    "Waste paper or newspaper",
                    "Water",
                    "A blender (for pulping)",
                    "A frame with mesh/screen (an old photo frame + net works)",
                    "A basin and a cloth or sponge",
                ],
                "steps": [
                    "Tear the paper into small pieces and soak in water for a few hours.",
                    "Blend the soaked paper with plenty of water into a smooth pulp.",
                    "Pour the pulp into a basin of water, dip the screen frame in, and lift it flat to catch an even layer of pulp.",
                    "Press the wet sheet with a cloth or sponge to squeeze out excess water.",
                    "Carefully flip the sheet onto a dry cloth and let it air-dry for 24 hours, then peel it off.",
                ],
                "safety_tips": [
                    "An adult should operate the blender.",
                    "Don't put fingers near the screen mesh edges — trim any sharp wire ends first.",
                ],
                "video_query": "how to make recycled paper at home DIY",
            },
            {
                "title": "Paper Mâché Storage Bowl",
                "difficulty": "Medium",
                "time": "2 days (mostly drying time)",
                "materials_needed": [
                    "Newspaper, torn into strips",
                    "Flour + water paste (or diluted white glue)",
                    "A balloon",
                    "Paint (optional)",
                ],
                "steps": [
                    "Blow up the balloon to your desired bowl size.",
                    "Dip newspaper strips in the paste and layer them over half the balloon, 3–4 layers thick.",
                    "Let it dry fully for 24–48 hours in a ventilated spot.",
                    "Pop the balloon and trim the rim neatly with scissors.",
                    "Paint and decorate once completely dry.",
                ],
                "safety_tips": [
                    "Work in a well-ventilated room, especially if using glue-based paste.",
                    "Wash hands after handling the paste; keep away from eyes.",
                ],
                "video_query": "paper mache bowl DIY tutorial",
            },
        ],
    },
    "glass": {
        "display_name": "Glass",
        "icon": "🍾",
        "general_safety": [
            "Inspect jars/bottles for cracks or chips before reusing — discard anything damaged.",
            "Wear gloves when cleaning glass, especially if a piece has broken.",
            "Prefer battery LED tealights over open flame inside glass crafts.",
        ],
        "ideas": [
            {
                "title": "Glass Jar Herb Garden",
                "difficulty": "Easy",
                "time": "20 mins",
                "materials_needed": [
                    "A clean glass jar",
                    "Small stones or pebbles (for drainage)",
                    "Potting soil",
                    "A small herb seedling or seeds",
                    "Twine or paint (optional decoration)",
                ],
                "steps": [
                    "Wash the jar in warm soapy water and remove the label completely.",
                    "Add a layer of small stones at the bottom for drainage.",
                    "Add potting soil on top of the stones.",
                    "Plant your herb seedling or seeds and water lightly.",
                    "Decorate the outside with twine or paint, then place on a sunny windowsill.",
                ],
                "safety_tips": [
                    "Check the jar's rim for chips before use — a chipped rim can cut fingers.",
                    "If soil residue makes the jar slippery, dry your hands before handling it.",
                ],
                "video_query": "glass jar herb garden DIY indoor",
            },
            {
                "title": "Glass Bottle Lantern",
                "difficulty": "Easy",
                "time": "15 mins",
                "materials_needed": [
                    "A clean glass bottle",
                    "Twine or string",
                    "1 battery-powered LED tealight",
                ],
                "steps": [
                    "Wash and fully dry the bottle, removing any label.",
                    "Wrap twine around the neck for a decorative touch (optional).",
                    "Drop the LED tealight in through the neck.",
                    "Place it on a table or windowsill as ambient lighting.",
                ],
                "safety_tips": [
                    "Never place a real lit candle inside a glass bottle unattended — use LED lights instead.",
                    "Handle the bottle by the body, not the neck, to avoid it slipping.",
                ],
                "video_query": "DIY glass bottle lantern LED",
            },
        ],
    },
    "metal": {
        "display_name": "Metal",
        "icon": "🔩",
        "general_safety": [
            "Cut/cutting edges of cans and metal sheets can be razor sharp — sand or tape them.",
            "Wear gloves and safety glasses when drilling, hammering or piercing metal.",
            "Have an adult supervise any drilling for children.",
        ],
        "ideas": [
            {
                "title": "Tin Can Pen & Pencil Holder",
                "difficulty": "Easy",
                "time": "20 mins",
                "materials_needed": [
                    "A clean, empty tin can (lid fully removed)",
                    "Sandpaper",
                    "Paint or decorative paper",
                    "Twine (optional)",
                ],
                "steps": [
                    "Remove the label and wash the can thoroughly.",
                    "Run sandpaper around the rim to smooth any rough edge.",
                    "Prime and paint the outside, or wrap it in decorative paper.",
                    "Add twine or trim for extra decoration, then let it dry.",
                    "Use it on your desk to hold pens, pencils, or brushes.",
                ],
                "safety_tips": [
                    "Sand the rim before handling with bare hands — freshly cut lids are sharp.",
                    "Wear gloves while sanding if the edge still feels rough.",
                ],
                "video_query": "tin can pencil holder DIY craft",
            },
            {
                "title": "Aluminum Can Wind Chime",
                "difficulty": "Medium",
                "time": "45 mins",
                "materials_needed": [
                    "3–4 clean aluminum cans",
                    "A drill or hammer + nail",
                    "String or fishing line",
                    "A wooden dowel or hanger",
                ],
                "steps": [
                    "Wash and dry all the cans thoroughly.",
                    "With an adult's help, make a small hole near the closed end of each can using a drill or a hammer and nail.",
                    "Thread string through each hole and tie it securely.",
                    "Tie the cans at varying heights along a horizontal dowel.",
                    "Hang it outdoors somewhere it will catch a breeze.",
                ],
                "safety_tips": [
                    "Wear safety glasses when piercing metal — small metal shavings can fly.",
                    "Keep fingers clear of the drill bit/nail point at all times.",
                ],
                "video_query": "aluminum can wind chime DIY tutorial",
            },
        ],
    },
    "e-waste": {
        "display_name": "E-Waste",
        "icon": "💻",
        "general_safety": [
            "Never open batteries, capacitors, or CRT/old monitor components yourself — they can be toxic or hold a dangerous charge.",
            "Always disconnect a device from power before taking it apart.",
            "Anything with a working battery, screen, or motor should go to a certified e-waste collection point — only DIY with the exterior casing/keys.",
            "Wear gloves and wash your hands after handling old electronics; avoid inhaling dust from aged components.",
        ],
        "ideas": [
            {
                "title": "Keyboard Keycap Fridge Magnets",
                "difficulty": "Easy",
                "time": "20 mins",
                "materials_needed": [
                    "Keycaps from an old, unplugged keyboard",
                    "Small round magnets",
                    "Strong craft glue",
                ],
                "steps": [
                    "Make sure the keyboard has been unplugged/disconnected and is no longer in use.",
                    "Gently pop off the keycaps you want using a flat tool.",
                    "Clean each keycap with a damp cloth and let dry.",
                    "Glue a small magnet to the back of each cap and let it cure for 24 hours.",
                    "Use them on your fridge, whiteboard, or locker.",
                ],
                "safety_tips": [
                    "Work in a ventilated area if the glue has strong fumes.",
                    "Keep small magnets and keycaps away from young children — swallowing hazard.",
                ],
                "video_query": "keyboard keycap magnets DIY craft",
            },
            {
                "title": "Circuit Board Wall Art / Coasters",
                "difficulty": "Medium",
                "time": "30–45 mins",
                "materials_needed": [
                    "A cleaned, non-functional circuit board (batteries/capacitors already removed by a certified handler if it came from a powered device)",
                    "A shallow photo frame or clear resin",
                    "Felt pads (if making a coaster)",
                ],
                "steps": [
                    "Confirm the board has no battery, capacitor, or power source still attached — if unsure, take it to a certified e-waste recycler instead of DIY-ing it.",
                    "Wipe the board clean of dust and let it fully dry.",
                    "Mount it inside a shallow frame, or coat it in resin in a well-ventilated outdoor space.",
                    "Once fully cured, add felt pads underneath if it will be used as a coaster or trivet.",
                    "Display it as tech-inspired décor.",
                ],
                "safety_tips": [
                    "Do not attempt this with a board you haven't verified is fully de-powered.",
                    "Wear gloves and a dust mask while cleaning old boards.",
                    "Resin fumes can be strong — always cure resin in a ventilated area, away from children and pets.",
                ],
                "video_query": "circuit board coaster resin art tutorial",
            },
        ],
    },
    "clothes": {
        "display_name": "Clothes / Fabric",
        "icon": "👕",
        "general_safety": [
            "Wash old clothing before reworking it.",
            "Cut on a stable, flat surface, keeping fingers clear of the blade.",
            "Use a thimble when hand-sewing to avoid needle pricks; keep pins away from small children.",
        ],
        "ideas": [
            {
                "title": "No-Sew T-Shirt Tote Bag",
                "difficulty": "Easy",
                "time": "20 mins",
                "materials_needed": [
                    "1 old t-shirt",
                    "Scissors",
                    "Ruler or chalk (optional, for straight cuts)",
                ],
                "steps": [
                    "Turn the t-shirt inside out and lay it flat.",
                    "Cut off the sleeves and cut a wider neckline to form the bag's top opening.",
                    "Along the bottom hem, cut fringe strips about 1 inch wide and 3 inches long.",
                    "Tie each front fringe strip to the matching back strip using a double knot, working all the way across.",
                    "Turn the bag right-side out — it's ready to use.",
                ],
                "safety_tips": [
                    "Cut on a table, not in your lap, to keep fingers safe.",
                    "Adult supervision recommended for children using scissors.",
                ],
                "video_query": "no sew t shirt tote bag DIY",
            },
            {
                "title": "Braided Fabric Scrap Rug/Coaster",
                "difficulty": "Medium",
                "time": "1–2 hrs",
                "materials_needed": [
                    "Long strips cut from old clothing",
                    "Scissors",
                    "Needle and thread (optional, for stitching layers)",
                ],
                "steps": [
                    "Cut old clothing into long strips, about 2 inches wide.",
                    "Tie three strips together at one end and braid them tightly.",
                    "Coil the finished braid into a tight spiral, starting from the center.",
                    "Hand-stitch the coils together as you go to hold the shape.",
                    "Tuck in and stitch down the final end to finish.",
                ],
                "safety_tips": [
                    "Use a thimble while hand-sewing to protect your fingertips.",
                    "Store needles/pins in a labeled box away from young children.",
                ],
                "video_query": "braided fabric scrap rug DIY tutorial",
            },
        ],
    },
}


def get_diy_guide(material):
    """Return the DIY guide dict for a given material key, or None if unknown."""
    return DIY_GUIDES.get(material)


def youtube_search_url(query):
    """Build a safe YouTube search link (never a hardcoded/possibly-dead video id)."""
    return f"https://www.youtube.com/results?search_query={quote_plus(query)}"
