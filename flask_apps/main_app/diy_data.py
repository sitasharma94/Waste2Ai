"""DIY recycling ideas per waste category: (title, emoji, materials, steps)."""

import os
import re

ITEMS_DIR = os.path.join(os.path.dirname(__file__), "static", "items")


def _normalize_text(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


_PURPOSES = {
    "Bottle Planter": "a small growing space for seedlings, herbs, or flowers",
    "Bird Feeder": "a refillable place for garden birds to feed",
    "Pen Stand": "a tidy holder for pens, pencils, and desk supplies",
    "Piggy Bank": "a simple container for saving coins",
    "Hanging Lamp Shade": "a decorative shade for a cool-running LED light",
    "Vertical Garden": "a space-saving row of planters for a wall or balcony",
    "Bottle Cap Wall Art": "colorful wall decor made from sorted bottle caps",
    "Storage Organizer": "small compartments for everyday supplies",
    "Watering Can": "a lightweight container for watering small plants",
    "Toy Car": "a simple rolling toy made from a bottle and reused caps",
    "Self-Watering Pot": "a planter that draws water through a wick from its reservoir",
    "Flower Vase": "a decorative holder for fresh or dried flowers",
    "Funnel": "a handy aid for pouring liquids or dry ingredients",
    "Carry-Bag Dispenser": "a dispenser for clean reusable bags",
    "Mini Greenhouse": "a cover that helps protect young seedlings",
    "Paper Bags": "a woven newspaper-tube bag for lightweight, dry items",
    "Paper Bead Jewellery": "lightweight beads for a necklace or bracelet",
    "Pencil Holder": "a desk holder made from paper tubes rolled by hand",
    "Recycled Notebook": "a notebook made with reused paper and a sturdy cover",
    "Handmade Paper": "fresh sheets of paper from recycled scraps",
    "Paper Basket": "a woven basket for lightweight household items",
    "Wall Hanging": "a lightweight decoration for a wall or window",
    "Gift Boxes": "a reusable box sized for a small present",
    "Photo Frame": "a personalized frame for a favorite photograph",
    "Seed Paper": "plantable paper that carries seeds for later sowing",
    "Paper Lantern": "a woven paper-tube lantern for a battery-powered LED tea light",
    "Bookmarks": "a simple marker to save your place in a book",
    "Paper Flowers": "colorful handmade flowers for a vase or display",
    "Papier-Mache Bowl": "a decorative bowl for lightweight items",
    "Magazine Coasters": "sealed coasters for cold drinks",
    "Candle Holder": "a stable jar display for a candle or LED candle",
    "Painted Vase": "a glass bottle transformed into a decorative vase",
    "Bottle Lamp": "a soft accent lamp made with battery-powered fairy lights",
    "Herb Jar Garden": "a small indoor growing spot for herbs",
    "Storage Jars": "labeled jars that make pantry items easy to identify",
    "Wind Chime": "a hanging garden decoration that moves in the breeze",
    "Terrarium": "a compact display garden for suitable small plants",
    "Soap Dispenser": "a refillable dispenser for liquid soap",
    "Mosaic Art": "a decorative board covered with small mosaic pieces",
    "Drinking Glass from Bottle": "a drinking glass made with specialist glass-cutting tools",
    "Fairy Light Jar": "a gentle decorative light using battery-powered LEDs",
    "Garden Bottle Edging": "a row of bottles that defines a garden bed",
    "Hanging Bottle Planter": "a suspended planter for a suitable plant cutting",
    "Jar Piggy Bank": "a clear coin saver that is easy to decorate",
    "Snow Globe": "a sealed display jar with a floating glitter effect",
    "Tin Can Planter": "a sturdy planter for a small indoor or outdoor plant",
    "Lantern": "a patterned outdoor lantern for an LED tea light",
    "Desk Organizer": "compartments for sorting desk supplies",
    "Pen Holder": "a decorated holder that keeps pens upright",
    "Spice Rack": "a magnetic arrangement for small spice tins",
    "Wall Clock": "a working clock made with a metal lid and clock kit",
    "Key Hooks": "a wall-mounted place to hang keys",
    "Jewellery Stand": "a display stand for lightweight jewellery",
    "Phone Stand": "a stable angled rest for a phone",
    "Wall Clock from Old Disc": "a lightweight clock that reuses an old disc",
    "Cable Organizer": "a tidy way to coil and label charging cables",
    "Mini Planter": "a small planter made from a cleaned computer mouse shell",
    "Desk Lamp": "a compact lamp assembled from a tested low-voltage LED kit",
    "Keyboard Art Frame": "a framed design made from reused keyboard keys",
    "Pen Stand from Old Charger": "a desk holder made from an emptied adapter casing",
    "Speaker Box": "a compact speaker enclosure for compatible parts",
    "Jewellery from Circuit Boards": "decorative jewellery pieces made from prepared circuit-board material",
    "Drawer Organizer": "compartments that sort small items in a drawer",
    "CD Coasters": "lightweight coasters with a protective backing",
    "CD Mosaic Mirror": "a reflective mosaic border for a mirror or display board",
    "Cable Bracelet": "a braided bracelet made from clean, flexible cable covering",
    "Mobile Charging Dock": "a holder that keeps a phone steady while charging",
    "Mini Fan": "a small fan project using a low-voltage motor kit",
    "Tote Bag": "a reusable carry bag for lightweight shopping",
    "Cushion Cover": "a washable cover made to fit a cushion insert",
    "Rag Rug": "a braided rug made from washable fabric strips",
    "Hair Scrunchies": "soft hair ties made from fabric offcuts",
    "Denim Pouch": "a small zip pouch made from sturdy denim",
    "Patchwork Quilt": "a warm quilt top assembled from fabric squares",
    "Pet Toy": "a simple fabric toy for supervised play",
    "Plant Hanger": "a braided holder for a lightweight plant pot",
    "Doormat": "a textured mat made from fabric strips secured to mesh",
    "Reusable Cleaning Cloths": "washable cloths cut from clean cotton garments",
    "Hanging Planter": "a suspended planter made from a reused metal can",
    "Cutlery Caddy": "a carryable holder for clean cutlery",
    "Candle Holder": "a metal container for a candle project",
    "Garden Markers": "durable labels that identify plants in a garden",
    "Coin Bank": "a decorated container for collecting coins",
    "Bunting Flags": "reusable fabric flags for a celebration display",
    "Jeans Apron": "a sturdy apron with pockets made from old jeans",
    "Pot Holder": "a padded square for handling warm cookware",
    "Produce Bag": "a lightweight reusable bag for produce",
    "Headband": "a soft braided headband made from a T-shirt",
}


def _step_guidance(step):
    """Keep each project instruction as one distinct numbered step."""
    text = step.strip().rstrip(".")
    lower = text.lower()
    replacements = {
        "heat nail and poke holes in cap": "Mark the cap, then ask an adult to make small holes with a hand punch; never heat a nail over a flame",
        "score the bottle": "Use a pre-cut bottle section, or have an experienced adult cut it with a purpose-made bottle cutter and the manufacturer's safety instructions",
        "separate with hot/cold water": "Do not use hot-and-cold water to crack glass; use only the bottle cutter manufacturer's method or use pre-cut glass",
        "sand the edge smooth": "Have an adult finish the cut edge with the cutter's recommended glass-finishing method; do not use the glass if any edge is sharp",
        "smooth bottle edges": "Use only professionally edge-finished glass pieces; do not handle broken or sharp glass",
    }
    text = replacements.get(lower, text)
    return [text + "."]

def _i(t, e, m, s):
    materials = m.split(", ")
    purpose = _PURPOSES.get(t, "a useful item made from clean, reusable materials")
    if t == "Candle Holder" and materials[0].lower().startswith("glass"):
        purpose = "a stable jar display for a candle or LED candle"
    elif t == "Candle Holder":
        purpose = "a metal-can holder for an LED candle"
    elif t == "Wind Chime" and materials[0].lower().startswith("glass"):
        purpose = "a hanging garden decoration made from glass bottle necks"
    elif t == "Wind Chime":
        purpose = "a hanging decoration made from reused metal pieces"
    elif t == "Bird Feeder" and materials[0].lower().startswith("tin"):
        purpose = "a simple metal-can feeder for dry birdseed"
    elif t == "Pen Holder" and materials[0].lower().startswith("tin"):
        purpose = "a decorated tin-can holder that keeps pens upright"
    description = (
        f"This project gives {materials[0].lower()} a second life by turning it into {purpose}. "
        "You will prepare the reused material, assemble the parts, and finish the item so it is ready to use or display. "
        "Before starting, choose clean, sturdy pieces and check them for cracks, leaks, or damage. Lay out the listed supplies "
        "and follow the numbered steps in order. Let glue or paint dry completely, then check that the finished project is stable "
        "and suited to its intended use. You can adjust colors and decoration to match your space."
    )
    if t in {
        "Phone Stand", "Wall Clock from Old Disc", "Cable Organizer", "Mini Planter", "Desk Lamp",
        "Keyboard Art Frame", "Pen Stand from Old Charger", "Speaker Box", "Jewellery from Circuit Boards",
        "Drawer Organizer", "CD Coasters", "CD Mosaic Mirror", "Cable Bracelet", "Mobile Charging Dock", "Mini Fan",
    }:
        description += (
            " Keep electronic parts disconnected from power. Do not open batteries or mains-powered equipment; "
            "get help from a qualified adult and recycle unsafe parts through an e-waste collection point."
        )
    # Break each broad instruction into smaller numbered actions for readability.
    steps = [substep for step in s.split(" | ") for substep in _step_guidance(step)]
    return {"title": t, "emoji": e, "materials": materials, "description": description, "steps": steps}
CATEGORIES = {
 "plastic": ("Plastic", "🧴", [
  _i("Bottle Planter","🌱","Plastic bottle, scissors, soil, seeds","Cut bottle in half | Poke drainage holes in base | Fill with soil and plant seeds"),
  _i("Bird Feeder","🐦","Plastic bottle, 2 wooden spoons, string, birdseed","Cut two small openings | Slide spoons through as perches | Fill with seed and hang"),
  _i("Pen Stand","✏️","Plastic bottle, scissors, paint, glue","Cut bottle to desired height | Smooth the edge | Paint and decorate"),
  _i("Piggy Bank","🐷","Plastic bottle, cutter, paint, bottle caps","Cut a coin slot | Paint it as an animal | Add caps as feet"),
  _i("Hanging Lamp Shade","💡","Plastic bottles, scissors, cord, bulb holder","Cut bottle bottoms into petals | Join in layers | Fit around the bulb holder"),
  _i("Vertical Garden","🪴","Plastic bottles, rope, soil, small plants","Cut a side opening in each bottle | Tie bottles in a vertical row | Fill with soil and plant"),
  _i("Bottle Cap Wall Art","🎨","Bottle caps, glue, cardboard, paint","Sketch a design on cardboard | Sort caps by colour | Glue caps in place"),
  _i("Storage Organizer","🗃️","Plastic containers, glue, paper, paint","Clean containers | Stack and glue together | Cover with paper or paint"),
  _i("Watering Can","🚿","Plastic bottle, cap","Heat nail and poke holes in cap | Fill bottle with water | Screw cap on and sprinkle"),
  _i("Toy Car","🚗","Plastic bottle, 4 caps, straws, skewers","Make axle holes in bottle | Thread skewers through straws | Attach caps as wheels"),
  _i("Self-Watering Pot","💧","Plastic bottle, cotton cord, soil, plant","Cut bottle in two | Thread cord through the cap | Invert top into water-filled base"),
  _i("Flower Vase","💐","Plastic bottle, paint, twine","Cut off the top | Wrap with twine or paint | Add water and flowers"),
 ]),
 "paper": ("Paper", "📄", [
  _i("Paper Bags","🛍️","Newspaper, glue, scissors, thin skewer or dowel, cardboard base, ruler, pencil, string or paper for handles","Cut newspaper into long strips | Roll strips diagonally around a skewer and glue the tips to make tubes | Weave tubes into a flat rectangular base | Bend the base tubes upward and weave more tubes around them to form the sides | Fold and glue the ends over the top rim to reinforce it | Attach paper-tube or string handles securely and let the bag dry"),
  _i("Paper Bead Jewellery","📿","Magazine pages, glue, thread, skewer","Cut long triangles | Roll around skewer and glue | Thread beads into necklace"),
  _i("Pencil Holder","✏️","Newspaper or magazine paper, glue, skewer or thin dowel, sturdy cardboard base","Cut paper into long strips | Roll each strip tightly around a skewer and glue the tip | Make several tubes and trim them to different heights | Arrange tubes upright on a cardboard base and mark positions | Glue tubes to the base and each other, then let dry"),
  _i("Recycled Notebook","📓","Used paper, cardboard, thread, needle","Cut sheets to size | Stack with cardboard cover | Stitch the spine"),
  _i("Handmade Paper","🗞️","Scrap paper, water, blender, mesh frame","Soak and blend paper into pulp | Spread on mesh | Press and dry"),
  _i("Paper Basket","🧺","Newspaper, glue, paint","Roll sheets into tight tubes | Weave into a base and sides | Seal with glue and paint"),
  _i("Wall Hanging","🖼️","Magazines, glue, thread","Roll pages into spirals | Arrange on thread | Hang as decor"),
  _i("Gift Boxes","🎁","Cardboard, paper, glue, ribbon","Cut and fold box template | Glue seams | Decorate"),
  _i("Photo Frame","📷","Cardboard, newspaper, glue, paint","Cut a frame from cardboard | Cover in rolled paper strips | Paint and add a stand"),
  _i("Seed Paper","🌼","Scrap paper, seeds, water, blender","Make paper pulp | Mix in seeds | Press flat and dry; plant later"),
 ]),
 "glass": ("Glass", "🍶", [
  _i("Candle Holder","🕯️","Glass jar, sand or beads, battery-powered LED candle","Clean jar | Add sand or beads | Place the LED candle inside"),
  _i("Painted Vase","🏺","Glass bottle, glass paint, brush","Clean and dry bottle | Apply base coat | Add patterns and let cure"),
  _i("Bottle Lamp","💡","Glass bottle, fairy lights","Clean bottle | Feed light string inside | Leave battery pack at the neck"),
  _i("Herb Jar Garden","🌿","Glass jars, pebbles, soil, herb seeds","Layer pebbles at bottom | Add soil | Sow herbs and keep sunny"),
  _i("Storage Jars","🫙","Glass jars, labels, marker","Wash jars | Dry fully | Label for spices or grains"),
  _i("Wind Chime","🎐","Glass bottle necks, string, wooden stick","Smooth bottle edges | Tie them at varying lengths | Hang from stick"),
  _i("Terrarium","🌵","Large jar, pebbles, soil, succulents","Add pebble drainage | Add soil | Plant succulents and decorate"),
  _i("Soap Dispenser","🧼","Glass bottle, pump nozzle","Clean bottle | Fit pump top | Fill with liquid soap"),
  _i("Mosaic Art","🧩","Broken glass pieces (safely handled), glue, board","Wear gloves and sand edges | Sketch design | Glue pieces down and grout"),
  _i("Drinking Glass from Bottle","🥂","Professionally pre-cut bottle glass, bottle cutter, glass-edge finishing pads","Use only glass pre-cut by an experienced adult with a purpose-made cutter | Have the rim professionally finished and check carefully for sharp spots | Do not use it for drinking unless the glass is food-safe and the rim is fully smooth"),
 ]),
 "metal": ("Metal", "🥫", [
  _i("Tin Can Planter","🪴","Tin can, paint, nail, hammer","Smooth sharp edges | Punch drainage holes | Paint and plant"),
  _i("Lantern","🏮","Tin can, nail, hammer, battery-powered LED tea light","Fill can with ice and freeze | Hammer a pattern of holes | Add the LED tea light and attach the wire handle"),
  _i("Desk Organizer","🗂️","Several tin cans, glue, paint, board","Clean cans | Glue onto a base board | Paint and decorate"),
  _i("Wind Chime","🎐","Metal cans or spoons, string","Punch holes in cans | Tie varying lengths | Hang from a ring"),
  _i("Pen Holder","✏️","Tin can, fabric or paper, glue","Remove label and sand edges | Wrap in fabric | Glue and trim"),
  _i("Spice Rack","🧂","Small tins, magnets, board","Clean tins | Glue magnets on back | Mount on a metal board"),
  _i("Bird Feeder","🐦","Tin can, wire, birdseed","Cut an opening | Add a perch | Hang with wire"),
  _i("Wall Clock","🕰️","Metal lid, clock kit, paint","Drill centre hole | Paint numbers | Fit clock mechanism"),
  _i("Key Hooks","🔑","Old forks or spoons, wood plank","Bend utensil handles | Mount on plank | Screw to wall"),
  _i("Jewellery Stand","💍","Aluminium cans, wire, paint","Cut shapes from can | Bend to form branches | Paint and display"),
 ]),
 "e-waste": ("E-Waste", "🔌", [
  _i("Phone Stand","📱","Old keyboard keys or cardboard, glue","Choose sturdy base | Glue support at angle | Test with phone"),
  _i("Wall Clock from Old Disc","🕰️","Old CD/DVD, clock kit","Drill centre hole | Mark numbers | Fit mechanism"),
  _i("Cable Organizer","🔌","Old cables, bottle caps or clips","Coil cables | Secure with clips | Label each"),
  _i("Mini Planter","🪴","Old mouse or casing, soil, succulent","Open casing | Add drainage and soil | Plant succulent"),
  _i("Desk Lamp","💡","Old LED parts, battery box, wire","Salvage working LEDs | Wire to battery pack | Mount in housing"),
  _i("Keyboard Art Frame","⌨️","Old keyboard keys, frame, glue","Remove keys | Arrange a picture or word | Glue inside frame"),
  _i("Pen Stand from Old Charger","✏️","Old adapter casing, paint","Remove internals safely | Clean casing | Paint and use"),
  _i("Speaker Box","🔊","Old speakers, cardboard box, amp module","Test speaker | Mount in box | Connect small amp"),
  _i("Jewellery from Circuit Boards","💎","Old circuit board, jewellery findings","Cut board shapes (wear mask) | Seal with resin | Add findings"),
  _i("Drawer Organizer","🗄️","Old laptop casing, glue","Remove electronics | Cut dividers | Glue together"),
 ]),
 "clothes": ("Clothes", "👕", [
  _i("Tote Bag","👜","Old T-shirt, scissors, needle or machine","Cut off sleeves and neck | Sew bottom closed | Use as bag"),
  _i("Cushion Cover","🛋️","Old jeans or shirt, needle, thread","Cut two squares | Sew three sides | Insert cushion and close"),
  _i("Rag Rug","🧶","Old fabric strips, rope or net","Cut strips | Braid together | Coil and stitch into a rug"),
  _i("Hair Scrunchies","🎀","Fabric scraps, elastic, needle","Cut rectangle | Sew into a tube | Thread elastic and close"),
  _i("Denim Pouch","👖","Old jeans, zipper, thread","Cut pocket section | Sew in zipper | Finish edges"),
  _i("Patchwork Quilt","🧵","Old shirts, thread, batting","Cut equal squares | Stitch into rows | Layer with batting and backing"),
  _i("Pet Toy","🐶","Old socks or fabric, filling","Cut and braid strips | Knot ends | Stuff into sock if desired"),
  _i("Plant Hanger","🪴","Old T-shirt, scissors","Cut into long strips | Braid | Knot into a pot hanger"),
  _i("Doormat","🚪","Old towels or T-shirts, mesh","Cut strips | Knot onto mesh | Trim ends"),
  _i("Reusable Cleaning Cloths","🧽","Old cotton shirts, scissors","Cut into squares | Hem edges | Wash and reuse"),
 ]),
}


# ---- extra ideas so every category has 15 ----
CATEGORIES["plastic"][2].extend([
  _i("Funnel","🥤","Plastic bottle, scissors","Cut bottle just below the neck | Smooth the cut edge | Flip it over and use as a funnel"),
  _i("Carry-Bag Dispenser","🛍️","Plastic bottle, scissors, old plastic bags","Cut off top and bottom | Stuff bags inside | Pull bags out through the neck"),
  _i("Mini Greenhouse","🌿","Clear plastic bottle, soil, seeds","Cut bottle in half | Plant seeds in the base | Cover with the top to trap warmth"),
])
CATEGORIES["paper"][2].extend([
  _i("Paper Lantern","🏮","Newspaper, glue, scissors, thin skewer or dowel, cardboard strips, ruler, pencil, battery-powered LED tea light","Cut newspaper into strips | Roll strips diagonally around a skewer and glue the tips to make tubes | Make cardboard rings for the top and bottom | Attach upright paper tubes between the rings to form a frame | Weave more paper tubes around the upright supports | Fold and glue the tube ends to finish the rim | Add a string loop and place the lantern over a battery-powered LED tea light"),
  _i("Bookmarks","🔖","Old magazine pages, scissors, glue, string","Cut long strips | Fold and glue double layer | Add a string tassel"),
  _i("Paper Flowers","🌸","Coloured paper, wire, glue","Cut petal shapes | Layer and glue petals | Attach to a wire stem"),
  _i("Papier-Mache Bowl","🥣","Newspaper, flour paste, balloon","Tear paper into strips | Paste layers over a balloon | Dry, pop balloon and paint"),
  _i("Magazine Coasters","☕","Magazine pages, glue, cardboard","Roll pages into tight coils | Glue coils into a circle | Seal with varnish or clear glue"),
])
CATEGORIES["glass"][2].extend([
  _i("Fairy Light Jar","✨","Glass jar, fairy lights","Clean the jar | Coil battery lights inside | Close lid for a night lamp"),
  _i("Garden Bottle Edging","🌷","Glass bottles, soil, spade","Dig a shallow trench | Bury bottles neck-down | Pack soil around them"),
  _i("Hanging Bottle Planter","🪴","Glass bottle, rope, water, cutting","Tie rope securely around the neck | Fill with water | Add a plant cutting and hang"),
  _i("Jar Piggy Bank","🐷","Glass jar, metal lid, cutter, paint","Cut a coin slot in the lid | Paint the lid | Screw on and start saving"),
  _i("Snow Globe","❄️","Glass jar, glitter, small figurine, glue","Glue figurine inside the lid | Fill jar with water and glitter | Seal lid tightly and flip"),
])
CATEGORIES["metal"][2].extend([
  _i("Hanging Planter","🪴","Tin can, rope, paint, nail","Punch holes near the rim | Thread rope through | Plant and hang"),
  _i("Cutlery Caddy","🍴","Large tin can, paint, handle","Smooth edges | Paint the outside | Fix a handle and fill with cutlery"),
  _i("Candle Holder","🕯️","Small tin can, wax, wick","Clean the can | Fix wick in centre | Pour melted wax and let set"),
  _i("Garden Markers","🏷️","Old spoons, permanent marker","Wash spoons | Write plant names on the bowl | Push handles into soil"),
  _i("Coin Bank","🪙","Tin can, paper, scissors, tape","Cover can with paper | Cut a slot in a plastic lid | Fit lid and decorate"),
])
CATEGORIES["e-waste"][2].extend([
  _i("CD Coasters","💿","Old CDs, cork sheet, glue","Cut cork to circle size | Glue to CD back | Press and let dry"),
  _i("CD Mosaic Mirror","🪞","Old CDs, scissors, glue, wooden board","Cut CDs into small pieces | Glue onto board | Frame with a border"),
  _i("Cable Bracelet","📿","Old thin cables, thread, clasp","Strip a short length | Braid cables together | Attach clasp"),
  _i("Mobile Charging Dock","🔋","Old small box, cable, glue","Cut a slot for the phone | Route charger cable through | Glue it in place"),
  _i("Mini Fan","🌀","Old small motor, battery box, plastic blade","Fix blade on motor shaft | Wire motor to battery | Mount on a stand"),
])
CATEGORIES["clothes"][2].extend([
  _i("Bunting Flags","🚩","Fabric scraps, string, scissors","Cut triangles | Fold over string | Stitch or glue to hold"),
  _i("Jeans Apron","🧑‍🍳","Old jeans, thread, needle","Cut off legs and open seams | Shape the top | Add waist ties from leg fabric"),
  _i("Pot Holder","♨️","Old cotton shirt, thread, needle","Cut and layer squares | Stitch around edges | Add a hanging loop"),
  _i("Produce Bag","🥬","Old T-shirt, needle, thread","Cut the sleeves and neck | Stitch the bottom closed | Use for fruit and veg"),
  _i("Headband","👒","Old T-shirt, scissors","Cut three long strips | Braid together | Tie into a loop"),
])

# Curated, actionable instructions for every idea. Keep these steps specific to
# the project; the short legacy action strings above are retained as fallbacks.
_STEP_OVERRIDES = {
    "plastic": {
        "Bottle Planter": ["Wash and dry a clean bottle; remove its label.", "Mark a cut line and ask an adult to cut the bottle to the desired height.", "Ask an adult to make several drainage holes in the base with a hand punch.", "Add potting soil and seeds or a small plant, then water lightly."],
        "Bird Feeder": ["Wash and dry the bottle, then mark two openings on opposite sides near the lower half.", "With adult help, cut openings large enough for the spoon bowls; smooth or cover the edges.", "Push the spoons through so each bowl sits under an opening and catches seed.", "Make a hanging hole near the top, add string, fill with birdseed, and hang securely."],
        "Pen Stand": ["Wash and dry the bottle and remove its label.", "Mark the stand height and have an adult cut the bottle on the line.", "Cover the cut edge with edge trim or sand it smooth under adult supervision.", "Paint and decorate the outside; let it dry fully before adding pens."],
        "Piggy Bank": ["Wash and dry the bottle and choose which side will face up.", "Mark a coin slot on the side; have an adult cut it with a craft knife, then cover its edges.", "Paint the bottle and let the paint dry completely.", "Glue clean bottle caps on as feet and let the glue set before using."],
        "Hanging Lamp Shade": ["Use clean, dry bottle bottoms with no cracks; ask an adult to cut them into petal shapes.", "Smooth or cover every cut edge before handling the pieces.", "Arrange the petals in layers and join them with ties or suitable craft fasteners.", "Hang the shade around a cool-running LED fitting, keeping plastic clear of the bulb and wiring."],
        "Vertical Garden": ["Wash bottles and mark a large planting opening on each side.", "Have an adult cut the openings and make drainage holes; cover sharp edges.", "Make two aligned rope holes near each end of every bottle.", "Thread rope through the holes, knot beneath each bottle, then hang from a secure rail.", "Add soil and small plants, leaving space for watering and drainage."],
        "Bottle Cap Wall Art": ["Wash and dry the caps and backing board.", "Sketch the design and sort caps by color before gluing.", "Glue caps flat to the board, keeping them inside its edges.", "Let the adhesive cure fully, then attach a secure hanger to the board."],
        "Storage Organizer": ["Wash and dry containers, removing labels and checking for cracks.", "Arrange them on a sturdy base so the openings remain accessible.", "Glue containers together and to the base using adhesive suitable for their plastic.", "Let the adhesive cure, then use the compartments for lightweight supplies."],
        "Watering Can": ["Wash a bottle and mark several small holes across its cap.", "Ask an adult to make the holes with a hand punch; do not heat a nail.", "Fill the bottle with water and screw the pierced cap on tightly.", "Test the flow over a sink, then use it to water plants."],
        "Toy Car": ["Wash and dry the bottle; choose four matching caps for wheels.", "Mark two straight axle positions on opposite sides of the bottle.", "Ask an adult to make aligned axle holes; slide straws through and skewers through the straws.", "Attach caps to the skewer ends, keeping them clear of the bottle so they can turn.", "Trim exposed skewer points safely and test the car on a flat surface."],
        "Self-Watering Pot": ["Wash a bottle and ask an adult to cut it into a top and bottom section.", "Thread cotton cord through a hole in the cap and tie a knot so it cannot slip through.", "Fill the lower section with water; place the inverted top so the cord reaches the water.", "Add soil and a small plant to the top section, keeping the cap above the water line.", "Check the water level regularly and keep the planter on a drip tray."],
        "Flower Vase": ["Wash and dry a bottle and remove its label.", "If shortening it, ask an adult to cut it and cover the cut edge with trim.", "Paint the outside or wrap it with twine, securing the ends with glue.", "Let the finish dry fully, then add water and flowers; check for leaks first."],
        "Funnel": ["Wash and dry a plastic bottle.", "Mark a cut line below the shoulder and ask an adult to cut the bottle there.", "Cover or smooth the cut edge so it cannot scratch hands.", "Turn the neck downward and use it to guide dry or cool liquids into a container."],
        "Carry-Bag Dispenser": ["Wash and dry a large bottle and remove its cap.", "Mark the top and bottom openings; have an adult cut them and cover the edges.", "Make a small mounting hole near the top if needed and secure the bottle to a wall or cabinet.", "Fold clean, dry bags loosely and load them through the top; pull them out through the neck."],
        "Mini Greenhouse": ["Wash a clear bottle and remove its label.", "Have an adult cut it in half and cover the cut edges.", "Plant seeds in damp potting mix in a small pot or seed tray.", "Place the bottle top over the pot, leaving the cap off for airflow.", "Keep it in bright indirect light, ventilate if condensation builds, and remove the cover as seedlings grow."],
    },
    "paper": {
        "Paper Bags": ["Cut newspaper into long strips of equal width.", "Place a skewer at one corner of a strip and roll the paper diagonally around it; glue the final corner and slide out the skewer to make a tube.", "Make at least 12 tubes. Flatten several tubes and lay them side by side; weave crosswise tubes over and under them to form a firm rectangular base sized for the bag.", "Bend the base tubes upward at the edges to form upright supports. Weave new tubes around them, alternating over and under each support to build the sides evenly.", "When the bag is the desired height, fold the upright ends over the top row and glue them down to make a firm rim.", "Make handles from twisted paper tubes or string, attach them through reinforced points on opposite sides, and let all glue dry fully.", "Use the finished bag for lightweight, dry items only; it is not suitable for heavy or wet items."],
        "Paper Bead Jewellery": ["Cut magazine pages into long triangles, keeping the strips similar in size.", "Place the wide end of a strip on a skewer and roll it evenly toward the pointed end.", "Add a small amount of glue to the tip and press it down; slide the bead off the skewer.", "Make enough beads for the design and seal them with clear craft sealer.", "After they dry, thread them onto cord and tie or clasp the ends."],
        "Pencil Holder": ["Cut newspaper or magazine pages into long, even strips.", "Place a skewer at one corner of a strip and roll the paper diagonally around it, keeping the roll tight.", "Glue the final corner down, slide out the skewer, and repeat to make enough tubes.", "Trim the tubes to different heights and arrange them upright on the cardboard base.", "Mark the positions, then glue the tubes to the base and to one another; let the glue dry fully."],
        "Recycled Notebook": ["Trim reused paper and two cardboard cover pieces to the same size.", "Stack the pages between the covers and clamp the stack along one edge.", "Mark evenly spaced holes along the spine and make them with an awl on a protected surface.", "Sew through the holes with sturdy thread, then tie the ends securely inside."],
        "Handmade Paper": ["Tear scrap paper into small pieces and soak them in water until soft.", "Blend the soaked paper with water in short pulses to make pulp; keep hands clear of the blades.", "Dip the mesh frame into a basin of pulp and lift it level so fibers form an even sheet.", "Press water out with a sponge, turn the sheet onto absorbent cloth, and lift away the mesh.", "Let the sheet dry flat before peeling it from the cloth."],
        "Paper Basket": ["Roll newspaper diagonally around a skewer and glue the tips to make paper tubes.", "Lay tubes side by side for the base and weave another tube over and under them.", "Continue weaving, bending the base tubes upward to form the sides.", "Join new tubes with glue as needed and keep rows close and even.", "Fold or glue the ends inside, then seal and paint after the basket is dry."],
        "Wall Hanging": ["Cut magazine pages into strips and roll them tightly around a skewer; glue each end.", "Flatten or shape the rolls consistently, then arrange them into a design.", "Thread cord through the pieces or glue them to a backing; let glue dry fully.", "Attach the design to a dowel or hanging ring and secure a hanging cord."],
        "Gift Boxes": ["Measure and draw a box net with a base, four sides, and glue tabs on cardboard.", "Cut around the outside and score the fold lines without cutting through the cardboard.", "Fold the sides upward and glue the tabs inside the neighboring sides.", "Hold the corners until secure, then decorate after the glue dries."],
        "Photo Frame": ["Measure the photograph and mark a cardboard frame with an opening slightly smaller than the photo.", "Cut out the outer shape and inner opening; ask an adult to handle any craft knife.", "Glue rolled newspaper strips around the frame and let them dry.", "Paint or seal the frame, add a cardboard backing and stand, then fit the photo."],
        "Seed Paper": ["Tear scrap paper into small pieces and soak until soft.", "Blend the paper with water into pulp, then stir in seeds by hand; do not blend the seeds.", "Spread a thin, even layer of pulp over mesh and press out excess water with a sponge.", "Dry the sheet flat and completely before cutting it into cards.", "To plant, cover a piece lightly with soil and keep it moist."],
        "Paper Lantern": ["Cut newspaper into long strips about 4–5 cm wide; keep the strips as even as possible.", "Place a skewer at one corner of a strip and roll the paper diagonally around it, keeping the tube tight. Glue the last corner and slide out the skewer.", "Repeat until you have enough tubes for the frame and weaving. If a tube is too short, glue the narrow end of another tube inside it to extend it.", "Cut two equal cardboard strips, bend each into a ring, and glue the overlapping ends. Check that the rings are the same size and let them dry.", "Stand several paper tubes evenly around the lower ring, with their ends extending past it. Glue them in place, then attach the upper ring to their other ends to make upright supports.", "Starting near the bottom, weave a new tube in front of one support and behind the next. Continue around the frame, pushing each row gently against the previous row.", "When a weaving tube runs short, insert the narrow end of another tube into it and add a dab of glue. Keep weaving until the sides are the desired height.", "Fold the upright supports over the top ring, tuck or glue their ends inside the rim, and let the whole lantern dry completely.", "Tie a string loop to the top frame if you want to hang it. Place a battery-powered LED tea light underneath or inside with ventilation; never use a candle or hot bulb."],
        "Bookmarks": ["Cut two matching strips of magazine paper or lightweight card.", "Glue the strips together with the printed sides outward and press flat until dry.", "Trim the corners and punch a hole near one end, away from the edge.", "Thread string through the hole and knot it securely."],
        "Paper Flowers": ["Cut several petals of the same size from colored paper.", "Layer the petals, offsetting each row, and glue only at the center.", "Wrap a paper center around the end of a craft wire; secure it with floral tape.", "Attach the flower head to the stem and let the glue dry before arranging."],
        "Papier-Mache Bowl": ["Cover the work area and place an inflated balloon in a stable bowl.", "Tear newspaper into strips and prepare flour paste until smooth.", "Dip strips in paste, wipe off excess, and layer them over the balloon, leaving the opening clear.", "Add several layers, allowing them to dry between layers, then dry completely.", "Ask an adult to pop and remove the balloon; trim the rim and paint the bowl. Use for dry, lightweight items only."],
        "Magazine Coasters": ["Fold magazine pages into narrow strips and roll each strip tightly into a coil.", "Glue the end of each coil and press it flat so it holds its shape.", "Arrange coils tightly together in a circle and glue their sides together.", "Seal both faces with waterproof sealer and let them cure fully before use with cold drinks."],
    },
    "glass": {
        "Candle Holder": ["Wash and dry a sound glass jar; check it for chips or cracks.", "Add a shallow layer of sand or beads to steady the candle.", "Place a battery-powered LED candle upright in the center.", "Keep the jar on a stable, heat-safe surface and use it as decoration; do not use a real flame."],
        "Painted Vase": ["Wash the bottle, remove its label, and dry it completely.", "Wipe the outside with rubbing alcohol if the paint instructions recommend it.", "Apply glass paint in thin coats, allowing each coat to dry as directed.", "Cure the paint according to its label before adding water or flowers."],
        "Bottle Lamp": ["Wash and dry the bottle and make sure its opening has no chips.", "Test the battery-powered fairy lights before placing them inside.", "Feed the lights gently into the bottle, keeping the battery pack outside and accessible.", "Switch on the lights and place the bottle upright; do not use mains wiring or a hot bulb."],
        "Herb Jar Garden": ["Wash jars and add a thin layer of pebbles for drainage space.", "Fill each jar partway with potting mix suitable for the selected herb.", "Sow seeds at the depth shown on their packet and cover lightly with soil.", "Mist gently and place in bright light; avoid waterlogging the jars."],
        "Storage Jars": ["Wash jars and lids with warm soapy water, then dry them completely.", "Check each jar for cracks and discard damaged ones.", "Write the contents and date on labels and attach them to the jars.", "Store only suitable dry goods in clean, food-safe jars."],
        "Wind Chime": ["Use only professionally cut and edge-finished glass pieces; do not use broken bottle glass.", "Attach each piece to a separate length of strong cord using pre-made holes or secure loops.", "Tie the cords at different lengths to a wooden stick or ring and balance the pieces.", "Hang the chime securely where pieces can move without striking people or windows."],
        "Terrarium": ["Choose a clean jar and small plants suited to a humid terrarium.", "Add pebbles, then a thin layer of activated charcoal and potting mix.", "Plant the greenery with space between leaves and avoid compacting the roots.", "Mist lightly and place in bright indirect light; vent the jar if excess condensation forms."],
        "Soap Dispenser": ["Wash and dry a sturdy bottle and check that its neck fits the pump.", "Fit a washer to the pump if supplied, then screw the pump onto the bottle.", "Fill with liquid soap, leaving room at the top, and tighten the pump.", "Test over a sink for leaks and clean spills before placing it on a counter."],
        "Mosaic Art": ["Use pre-cut, edge-finished mosaic tiles; do not handle broken glass.", "Wear eye protection and gloves, then arrange the tiles on a stable board before gluing.", "Glue tiles in place with tile adhesive, leaving small gaps between them.", "After the adhesive cures, apply grout, wipe the surface clean, and let it dry as directed."],
        "Drinking Glass from Bottle": ["Use only a bottle section cut by an experienced adult with a purpose-made bottle cutter.", "Have the rim finished with the cutter maker's recommended glass-finishing method; wear eye protection and gloves.", "Check the entire rim carefully; reject the piece if it has chips, cracks, or any sharp area.", "Use for drinking only if the glass and finish are food-safe; otherwise use it as a display vase."],
        "Fairy Light Jar": ["Wash and dry a sound jar and remove its label.", "Check that the battery lights work and that the battery compartment stays outside the jar.", "Arrange the light string loosely inside without pinching or bending the wire sharply.", "Close the lid loosely if the lights need ventilation, and switch them off when unattended."],
        "Garden Bottle Edging": ["Choose intact bottles and wash them; do not use chipped or cracked glass.", "Mark a shallow trench along the garden bed and ask an adult to dig it.", "Place bottles neck-down with their bases level and close together.", "Pack soil firmly around the bottles, leaving them stable and away from walkways."],
        "Hanging Bottle Planter": ["Use a purpose-made bottle planter with professionally finished edges; do not cut a glass bottle at home.", "Secure a rated hanging cradle or rope net around the planter, not just around a narrow neck.", "Add a small plant in a nursery pot or a suitable liner with drainage.", "Hang from a secure hook rated for the wet planter's weight and check it regularly."],
        "Jar Piggy Bank": ["Wash and dry a sound jar and lid; check the lid has no sharp rust.", "Use a lid with a pre-cut coin slot, or ask an adult to make one with a suitable tool.", "Cover the slot edges with a smooth, firmly attached trim so coins cannot catch fingers.", "Decorate the outside, let it dry, then screw on the lid and place the jar on a stable shelf."],
        "Snow Globe": ["Glue a waterproof figurine to the inside of a clean lid and let it cure fully.", "Fill the jar most of the way with clean water and a small pinch of glitter.", "Apply waterproof sealant to the lid threads if appropriate, then screw the lid on tightly.", "Turn it over above a sink and check for leaks before displaying; keep away from small children."],
    },
    "metal": {
        "Tin Can Planter": ["Wash the can and remove its label; discard cans with rust or sharp dents.", "Ask an adult to smooth the rim and punch several drainage holes in the base.", "Paint the outside and let it dry fully; keep paint away from the inside rim.", "Add potting soil and a small plant, then place the can on a drip tray."],
        "Lantern": ["Wash a can, remove its label, fill it with water, and freeze it solid to support the sides.", "Mark a simple pattern and have an adult punch the holes with a hammer and nail while the can is frozen.", "Let the ice melt, empty the can, and check that no sharp metal burrs remain.", "Attach a wire handle through two adult-made holes and use only a battery-powered LED tea light."],
        "Desk Organizer": ["Wash cans and remove labels; have an adult smooth or cover every rim.", "Arrange the cans on a sturdy board with openings facing up and mark their positions.", "Glue cans to the board with adhesive suitable for metal and let it cure fully.", "Paint and decorate the outside, then use for lightweight desk supplies."],
        "Wind Chime": ["Use clean metal pieces with no sharp edges; ask an adult to smooth them if needed.", "Have an adult make hanging holes away from the edges.", "Tie each piece to a ring at a different length and knot the cords securely.", "Hang the chime from a strong hook and test its balance close to the ground."],
        "Pen Holder": ["Wash the can and remove its label; have an adult smooth or cover the rim.", "Measure fabric or paper to wrap around the can, leaving the rim unobstructed.", "Apply craft glue to the outside and wrap the covering smoothly around it.", "Trim and glue the seam, then let it dry fully before adding pens."],
        "Spice Rack": ["Wash and dry small tins and label each one.", "Attach magnets to the backs with adhesive rated for the tin's loaded weight.", "Let the adhesive cure, then test each tin on a low metal surface with a small amount inside.", "Mount a metal board securely and place the tins on it; keep food in food-safe containers."],
        "Bird Feeder": ["Use a clean can and mark a wide opening; have an adult cut and smooth the metal edges.", "Fit a wooden perch below the opening using adult-made holes or a secure fastener.", "Attach a wire hanger through secure holes and tug-test it before filling.", "Add dry birdseed and hang the feeder where cats cannot reach it."],
        "Wall Clock": ["Use a clean, flat lid with no sharp burrs; ask an adult to drill the center hole to the kit's specified size.", "Mark the positions for the numbers and paint or attach them evenly.", "Fit the clock movement through the center hole and tighten its retaining nut by hand.", "Attach the hands in the kit's order, add a battery, and check that the hands move freely."],
        "Key Hooks": ["Clean the utensils and select ones with no cracks or sharp points.", "Have an adult bend the handles into hooks using pliers and eye protection.", "Arrange hooks on a wood plank and mark pilot holes.", "Screw the hooks to the plank, then anchor the plank securely to a wall."],
        "Jewellery Stand": ["Wash the cans and choose pieces without rust; have an adult cut shapes and smooth every edge.", "Bend the prepared strips into branches with pliers, keeping cut edges turned inward.", "Attach the branches to a stable base with wire or screws and check that they cannot wobble.", "Paint the stand and let it cure fully before hanging lightweight jewellery."],
        "Hanging Planter": ["Wash a sound can and have an adult smooth the rim and punch drainage holes in the base.", "Paint the outside and let it dry fully.", "Make two opposite holes near the rim and thread rope through them, knotting securely.", "Add soil and a small plant, then hang from a secure hook rated for its wet weight."],
        "Cutlery Caddy": ["Wash a large can and have an adult smooth or cover its rim.", "Paint the outside and allow it to dry completely.", "Attach a handle using two adult-made holes and bolts with washers, or a secure metal-rated fastener.", "Pull-test the handle, then use the caddy for clean, dry cutlery."],
        "Candle Holder": ["Use a clean, sound can and have an adult smooth or cover the rim.", "Secure a wick tab in the center of the can and keep the wick upright.", "Melt candle wax in a proper double boiler with adult supervision; never heat wax directly over a flame.", "Pour carefully, let the wax cool and set fully, then trim the wick; place the candle on a heat-safe surface."],
        "Garden Markers": ["Wash the spoons and remove any loose rust.", "Write plant names on the spoon bowls with a weather-resistant marker.", "Let the ink dry, then apply a suitable clear outdoor sealer if desired.", "Push the handles gently into soil without striking or bending them."],
        "Coin Bank": ["Wash and dry a can and a plastic lid that fits securely; have an adult smooth any metal rim.", "Cut a coin slot in the plastic lid with adult help and smooth its edges.", "Cover the can with paper and tape or glue, keeping the lid fit clear.", "Fit the lid and decorate the can; remove the lid to retrieve coins."],
    },
    "e-waste": {
        "Phone Stand": ["Choose clean keyboard keys or sturdy cardboard and make a stable base.", "Cut cardboard supports to form a backward-leaning rest; ask an adult to handle any craft knife.", "Glue the support to the base and let it cure fully.", "Add non-slip pads and test with the phone before using it."],
        "Wall Clock from Old Disc": ["Clean the disc and check it for cracks.", "Use a clock kit designed for a thin disc; ask an adult to make or enlarge the center hole to the kit size.", "Fit and tighten the movement according to its instructions, then attach the hands in order.", "Add a battery and test that the hands clear the disc and each other."],
        "Cable Organizer": ["Unplug and inspect cables; do not use any with exposed wires, fraying, or damaged plugs.", "Coil each cable loosely in a loop, avoiding tight bends.", "Secure the loop with reusable ties or clips, not adhesive around the cable itself.", "Label each coil and store it dry, away from heat."],
        "Mini Planter": ["Use an empty, disconnected mouse shell only; do not open equipment with batteries or sealed components.", "Clean the shell and line it with a waterproof liner that does not block drainage.", "Add potting mix and a small plant suited to the container's size.", "Water lightly over a tray and check that water cannot reach electrical contacts."],
        "Desk Lamp": ["Use a ready-made low-voltage LED kit and battery holder; do not salvage mains-powered wiring or open batteries.", "Assemble the LED, switch, and battery holder exactly as the kit instructions show, with power disconnected.", "Insulate exposed low-voltage connections and mount the parts in a stable housing with ventilation.", "Insert batteries, test the switch, and stop if wires heat up or the light flickers."],
        "Keyboard Art Frame": ["Disconnect the keyboard and remove only its loose keycaps; do not open its electronics.", "Clean and dry the keycaps.", "Arrange them on a backing board to make a word or pattern and take a reference photo.", "Glue each keycap to the board, let it cure, then fit the board into a frame."],
        "Pen Stand from Old Charger": ["Use an empty, unplugged adapter casing supplied already opened by a qualified adult; never open a mains adapter yourself.", "Check that no circuit board, capacitor, or metal prong remains, and discard the casing if unsure.", "Wash or wipe the casing and dry it fully; cover sharp edges with suitable trim.", "Paint the outside, let it cure, and use it only for lightweight pens."],
        "Speaker Box": ["Use a small speaker and amplifier module that are compatible and undamaged; keep everything disconnected from power.", "Measure the speaker and mark a snug opening in a sturdy box.", "Ask an adult to cut the opening, mount the speaker, and secure any amplifier module without pinching wires.", "Connect only according to the module diagram and its rated low-voltage supply, then test at low volume."],
        "Jewellery from Circuit Boards": ["Use only clean, depopulated, pre-cut circuit-board pieces from a reputable craft or e-waste supplier; do not dismantle or cut electronic waste at home.", "Check each piece for loose components or sharp edges and set unsafe pieces aside for proper e-waste recycling.", "Seal the safe pieces with a suitable clear coating in a ventilated area and let it cure fully.", "Attach jewellery findings using existing holes or secure loops; do not drill or sand the board."],
        "Drawer Organizer": ["Use a clean, empty computer casing with all electronics and batteries already removed by a qualified person.", "Measure the drawer and mark divider lengths on safe, flat casing pieces.", "Ask an adult to cut the pieces and cover any sharp edges.", "Fit the dividers in the drawer and add non-slip liner; do not force the drawer closed."],
        "CD Coasters": ["Clean the CDs and check for cracks or sharp splinters; discard damaged discs.", "Trace each disc on cork sheet and cut the cork slightly inside the outline.", "Glue cork to the printed side of each disc, keeping the reflective side facing down on a table.", "Press flat until dry, then seal the cork with a waterproof coating and let it cure."],
        "CD Mosaic Mirror": ["Use intact CDs or pre-cut, smooth mosaic pieces; do not cut discs with household scissors.", "Arrange pieces around a mirror on a stable backing board, leaving small gaps.", "Glue pieces with suitable mosaic adhesive and let it cure.", "Apply grout with gloves, wipe the surface clean, and let the mosaic dry before hanging securely."],
        "Cable Bracelet": ["Use only clean, flexible, non-electrical cable covering with all conductors removed; do not strip unknown cables.", "Measure around the wrist and cut strands longer than needed.", "Braid the strands evenly, keeping the bracelet loose enough to remove comfortably.", "Attach a clasp with jump rings and pliers, then check that all ends are covered and secure."],
        "Mobile Charging Dock": ["Choose a sturdy, clean box large enough for the phone and charger plug.", "Mark a phone slot and a separate cable opening; ask an adult to cut them and smooth the edges.", "Route the cable through the opening without sharp bends and secure it with a clip.", "Add non-slip pads, place the phone in the slot, and check that the box does not block ventilation."],
        "Mini Fan": ["Use a low-voltage motor kit with a purpose-made guarded blade; do not reuse cracked plastic blades.", "Attach the blade to the motor shaft while the battery holder is disconnected.", "Wire the motor, switch, and battery holder according to the kit diagram and insulate connections.", "Mount the motor firmly behind the guard, then test briefly at low voltage with fingers clear."],
    },
    "clothes": {
        "Tote Bag": ["Wash and dry a sturdy T-shirt, then turn it inside out.", "Cut off the sleeves and neckline to make handles and an open top.", "Pin the bottom edge and sew a straight seam; reinforce it with a second seam.", "Turn the shirt right-side out and check the seams before carrying light items."],
        "Cushion Cover": ["Wash and dry the fabric, then measure the cushion insert.", "Cut two pieces with seam allowance on every side.", "Place the pieces right sides together, pin them, and sew three sides plus most of the fourth.", "Turn right side out, insert the cushion, then sew the opening closed or add a closure."],
        "Rag Rug": ["Wash, dry, and cut fabric into strips of similar width.", "Tie or sew strip ends together and braid three strips, adding new strips as needed.", "Coil the braid flat, stitching each row to the previous row as you go.", "Secure the final end underneath and add non-slip backing before placing the rug."],
        "Hair Scrunchies": ["Cut a fabric rectangle and elastic to the desired size.", "Fold the fabric lengthwise with right sides together and sew the long edge into a tube.", "Turn the tube right side out and thread elastic through it with a safety pin.", "Sew the elastic ends together, tuck one fabric end inside the other, and stitch the opening closed."],
        "Denim Pouch": ["Wash and dry denim, then cut two matching pouch panels.", "Pin one zipper edge to the top edge of each panel, right sides together, and stitch it in place.", "Open the zipper partway, place panels right sides together, and sew around the remaining edges.", "Trim bulky corners, turn through the zipper opening, and check that the zipper moves freely."],
        "Patchwork Quilt": ["Wash and dry the fabric, then cut equal squares with consistent seam allowance.", "Arrange the squares in rows and sew them together, pressing each seam flat.", "Join the rows to make the quilt top and trim it square.", "Layer backing, batting, and quilt top; pin from the center outward and stitch through all layers.", "Bind the edges and check that no pins remain."],
        "Pet Toy": ["Use clean, sturdy fabric and pet-safe stuffing; remove buttons, zippers, and small parts.", "Cut two matching shapes and place them right sides together.", "Sew around the edge, leaving a small opening, then turn the toy right side out.", "Add a small amount of stuffing and sew the opening shut with strong, close stitches.", "Check for loose seams before supervised play and replace the toy if it tears."],
        "Plant Hanger": ["Cut clean T-shirt fabric into several long strips and stretch them gently into cords.", "Gather the strips and tie a strong knot to form the base.", "Divide the strips into groups and knot neighboring groups at equal heights around the pot.", "Repeat the knots to form a net, then gather and tie the ends above the pot.", "Test the hanger close to the floor with the empty pot before hanging it from a secure hook."],
        "Doormat": ["Wash and dry fabric, then cut it into strips of equal length.", "Lay non-slip mesh flat and knot each strip through adjacent mesh openings.", "Work row by row, keeping the knots tight and the fabric evenly spread.", "Trim loose ends and check that no mesh edges or knots can catch toes."],
        "Reusable Cleaning Cloths": ["Wash and dry clean cotton garments before cutting.", "Mark equal squares and cut with fabric scissors.", "Fold each raw edge under and hem with a sewing machine or needle and thread; skip hemming if the fabric does not fray.", "Wash the cloths before first use and launder them after use."],
        "Bunting Flags": ["Wash and dry fabric scraps, then cut matching triangles with a safe seam or fold allowance.", "Fold the top edge of each triangle over string or bias tape.", "Pin each flag in place with even gaps and sew or glue the folded edge securely.", "Tie loops at both ends and hang the bunting away from heat and walkways."],
        "Jeans Apron": ["Wash and dry old jeans, then remove a leg seam with a seam ripper.", "Lay the opened leg flat and cut an apron shape, keeping a sturdy section for the body.", "Hem or bind the raw edges and add a pocket from a remaining denim piece.", "Make waist ties from denim strips, sew them securely, and tug-test before wearing."],
        "Pot Holder": ["Cut two fabric squares and heat-resistant batting to the same size.", "Layer fabric, batting, and fabric, then pin the layers together.", "Quilt through all layers with parallel lines or a grid, keeping stitches close.", "Bind the edges and sew in a hanging loop; use only materials rated for heat."],
        "Produce Bag": ["Wash and dry a sturdy T-shirt and turn it inside out.", "Cut off the sleeves and neckline, keeping the hem as the bag opening if suitable.", "Pin and sew the bottom closed with a reinforced seam.", "Turn right side out and check seams; use for clean produce and wash regularly."],
        "Headband": ["Cut three equal-length strips from a clean T-shirt and stretch them gently into cords.", "Tie the strips together at one end and braid them evenly.", "Measure the braid around the head with a comfortable fit and trim to length.", "Overlap the ends, sew them securely into a loop, and cover the join with a small fabric wrap."],
    },
}

_SIMPLE_PROJECTS = {
    ("plastic", "Bottle Cap Wall Art"), ("plastic", "Watering Can"), ("plastic", "Flower Vase"),
    ("paper", "Bookmarks"), ("paper", "Paper Flowers"),
    ("glass", "Painted Vase"), ("glass", "Storage Jars"), ("glass", "Fairy Light Jar"),
    ("metal", "Garden Markers"), ("e-waste", "Cable Organizer"), ("e-waste", "CD Coasters"),
    ("clothes", "Reusable Cleaning Cloths"), ("clothes", "Produce Bag"), ("clothes", "Headband"),
}

_STEP_SETUP = {
    "plastic": ["Wash and dry the plastic item, remove its label, and check it for cracks.", "Gather the supplies and mark any planned cuts or holes before assembling."],
    "paper": ["Clear a clean, dry work surface and flatten the paper before starting.", "Gather the supplies and measure or sketch the project size before cutting or folding."],
    "glass": ["Inspect each glass item for chips or cracks and set damaged pieces aside for recycling.", "Stabilize the glass on a non-slip surface and wear eye protection when handling it."],
    "metal": ["Inspect the metal for rust, dents, or sharp edges; do not use unsafe pieces.", "Mark planned cuts or holes first, and have an adult handle metal cutting or punching."],
    "e-waste": ["Use only clean, disconnected parts; do not open mains-powered equipment or sealed batteries.", "Inspect pieces for exposed wires, sharp edges, or damage and set unsafe parts aside for proper recycling."],
    "clothes": ["Wash and dry the fabric, then remove any buttons or damaged sections not needed for the design.", "Measure and mark the pattern before cutting, and gather the thread and tools."],
}

_STEP_FINISH = {
    "plastic": "Check the finished item for loose parts, sharp edges, or leaks before using it.",
    "paper": "Let all glue dry fully, then check that the joins hold and the project keeps its shape.",
    "glass": "Check for chips, cracks, loose parts, or leaks before displaying or using the project.",
    "metal": "Check that the edges are covered, the fasteners are secure, and the project sits steadily.",
    "e-waste": "Check that all edges and attached parts are secure, then let adhesives or sealant cure fully.",
    "clothes": "Trim loose threads and tug-test the seams before using the finished item.",
}

for category_key, (_, _, category_ideas) in CATEGORIES.items():
    for project in category_ideas:
        steps = list(_STEP_OVERRIDES[category_key][project["title"]])
        target_count = 6 if (category_key, project["title"]) in _SIMPLE_PROJECTS else 7
        prep_count = 0
        while len(steps) < target_count:
            if prep_count < len(_STEP_SETUP[category_key]):
                steps.insert(prep_count, _STEP_SETUP[category_key][prep_count])
                prep_count += 1
            else:
                steps.append(_STEP_FINISH[category_key])
        project["steps"] = steps


_MATERIAL_ADDITIONS = {
    "plastic": {
        "Bottle Planter": ["marker", "hand punch for drainage holes", "small drip tray"],
        "Bird Feeder": ["scissors", "marker"],
        "Pen Stand": ["ruler", "paintbrush", "fine sandpaper"],
        "Piggy Bank": ["marker", "paintbrush", "fine sandpaper"],
        "Hanging Lamp Shade": ["marker", "ruler", "low-heat LED bulb", "lamp cord and fitting"],
        "Vertical Garden": ["marker", "scissors", "wall hooks or a secure hanging rail"],
        "Bottle Cap Wall Art": ["pencil", "ruler", "protective backing board"],
        "Storage Organizer": ["scissors", "ruler", "sturdy base board"],
        "Watering Can": ["marker", "hand punch or awl for the cap holes"],
        "Toy Car": ["ruler", "marker", "scissors", "strong craft glue", "fine sandpaper for axle ends"],
        "Self-Watering Pot": ["marker", "scissors", "small pebbles", "drip tray"],
        "Flower Vase": ["scissors", "paintbrush", "strong craft glue"],
        "Funnel": ["marker", "fine sandpaper"],
        "Carry-Bag Dispenser": ["marker", "fine sandpaper", "wall hook or mounting tape"],
        "Mini Greenhouse": ["marker", "scissors", "clear tape", "seedling tray"],
    },
    "paper": {
        "Paper Bags": ["ruler", "pencil", "thin skewer or dowel", "sturdy cardboard base"],
        "Paper Bead Jewellery": ["scissors", "clear craft sealer"],
        "Pencil Holder": ["sturdy cardboard base", "ruler", "scissors"],
        "Recycled Notebook": ["ruler", "pencil", "paper clips or binder clips", "awl"],
        "Handmade Paper": ["large basin", "sponge", "absorbent cloth or towel"],
        "Paper Basket": ["scissors", "ruler", "bowl or other form to shape the basket"],
        "Wall Hanging": ["scissors", "wooden dowel or sturdy hanging ring"],
        "Gift Boxes": ["ruler", "pencil", "scissors"],
        "Photo Frame": ["ruler", "scissors", "backing card or stand"],
        "Seed Paper": ["mesh screen", "large basin", "sponge", "absorbent cloth or towel"],
        "Paper Lantern": ["scissors", "thin skewer or dowel", "cardboard strips for rings", "ruler", "pencil"],
        "Bookmarks": ["ruler", "hole punch"],
        "Paper Flowers": ["scissors", "floral tape"],
        "Papier-Mache Bowl": ["water", "mixing bowl", "brush"],
        "Magazine Coasters": ["scissors", "clear waterproof sealer"],
    },
    "glass": {
        "Candle Holder": [],
        "Painted Vase": ["masking tape", "palette or disposable plate"],
        "Bottle Lamp": ["batteries for the fairy lights"],
        "Herb Jar Garden": ["mesh pieces", "spoon", "small spray bottle"],
        "Storage Jars": ["matching lids"],
        "Wind Chime": ["pre-cut, professionally edge-finished glass pieces", "protective gloves", "safety glasses", "beads", "hanging hook"],
        "Terrarium": ["activated charcoal", "moss", "spoon", "small spray bottle"],
        "Soap Dispenser": ["liquid soap", "pump that fits the bottle neck", "rubber washer or seal"],
        "Mosaic Art": ["tile nippers", "grout", "grout sponge", "protective gloves", "safety glasses"],
        "Drinking Glass from Bottle": ["cut-resistant gloves", "safety glasses", "glass-edge finishing pads"],
        "Fairy Light Jar": ["batteries for the fairy lights"],
        "Garden Bottle Edging": ["garden gloves", "spade"],
        "Hanging Bottle Planter": ["plant cutting", "purpose-made bottle cutter", "protective gloves", "safety glasses", "secure hanging hook"],
        "Jar Piggy Bank": ["marker", "paintbrush", "metal snips or a suitable lid punch", "protective gloves"],
        "Snow Globe": ["water", "glycerin", "waterproof glue", "small funnel"],
    },
    "metal": {
        "Tin Can Planter": ["garden gloves", "marker", "paintbrush", "small plant", "potting soil"],
        "Lantern": ["wire for the handle", "garden gloves", "marker"],
        "Desk Organizer": ["ruler", "paintbrush", "fine sandpaper"],
        "Wind Chime": ["metal ring", "beads", "pliers", "protective gloves", "safety glasses"],
        "Pen Holder": ["scissors", "paintbrush", "fine sandpaper"],
        "Spice Rack": ["strong adhesive for magnets", "labels", "marker"],
        "Bird Feeder": ["marker", "tin snips", "metal file", "protective gloves", "safety glasses"],
        "Wall Clock": ["battery", "marker", "hand drill", "drill bit sized for the clock kit", "screwdriver"],
        "Key Hooks": ["pliers", "screws", "drill", "screwdriver"],
        "Jewellery Stand": ["tin snips", "pliers", "fine sandpaper", "sturdy base", "protective gloves", "safety glasses"],
        "Hanging Planter": ["marker", "paintbrush", "small plant", "potting soil", "secure hanging hook"],
        "Cutlery Caddy": ["drill", "screw and washer for the handle", "paintbrush", "fine sandpaper"],
        "Candle Holder": ["wick tab", "double boiler or wax-melting pot", "thermometer", "heatproof work surface"],
        "Garden Markers": ["pliers", "metal-safe permanent marker"],
        "Coin Bank": ["plastic lid", "marker", "strong glue"],
    },
    "e-waste": {
        "Phone Stand": ["ruler", "pencil", "scissors or craft knife", "non-slip pads"],
        "Wall Clock from Old Disc": ["battery", "hand drill", "drill bit sized for the clock kit", "screwdriver"],
        "Cable Organizer": ["reusable hook-and-loop cable ties", "labels", "scissors"],
        "Mini Planter": ["waterproof liner", "potting soil", "small plant"],
        "Desk Lamp": ["low-voltage LED kit", "on/off switch", "insulating tape", "small screwdriver"],
        "Keyboard Art Frame": ["backing board", "tweezers", "small pliers"],
        "Pen Stand from Old Charger": ["small screwdriver", "fine sandpaper", "paintbrush"],
        "Speaker Box": ["speaker wire", "power source compatible with the amplifier", "screws", "protective grille fabric"],
        "Jewellery from Circuit Boards": ["flush cutters", "fine sandpaper", "protective gloves", "safety glasses", "clear sealant"],
        "Drawer Organizer": ["ruler", "pencil", "dividers", "non-slip drawer liner", "craft knife"],
        "CD Coasters": ["scissors", "waterproof clear sealer"],
        "CD Mosaic Mirror": ["small mirror", "mosaic nippers", "tile adhesive", "grout", "sponge", "protective gloves", "safety glasses"],
        "Cable Bracelet": ["scissors", "pliers", "jump rings"],
        "Mobile Charging Dock": ["ruler", "pencil", "craft knife", "non-slip pads"],
        "Mini Fan": ["low-voltage motor kit", "battery holder", "on/off switch", "insulated wire", "protective blade guard", "small screwdriver"],
    },
    "clothes": {
        "Tote Bag": ["ruler", "fabric pins", "matching thread"],
        "Cushion Cover": ["cushion insert", "ruler", "fabric pins", "zipper or buttons"],
        "Rag Rug": ["scissors", "non-slip rug backing", "needle and strong thread"],
        "Hair Scrunchies": ["fabric pins", "safety pin for threading elastic", "matching thread"],
        "Denim Pouch": ["scissors", "fabric pins", "sewing needle or sewing machine"],
        "Patchwork Quilt": ["backing fabric", "ruler", "fabric pins", "scissors or rotary cutter", "sewing machine or needle"],
        "Pet Toy": ["scissors", "needle and strong thread", "pet-safe stuffing"],
        "Plant Hanger": ["plant pot", "secure ceiling or wall hook", "scissors"],
        "Doormat": ["scissors", "non-slip mat backing"],
        "Reusable Cleaning Cloths": ["sewing needle and thread or sewing machine, if hemming edges"],
        "Bunting Flags": ["ruler", "pencil", "needle and thread or fabric glue"],
        "Jeans Apron": ["scissors", "fabric pins", "seam ripper", "sewing machine or strong needle and thread"],
        "Pot Holder": ["heat-resistant batting", "fabric backing", "fabric pins", "scissors", "hanging loop"],
        "Produce Bag": ["scissors", "fabric pins", "matching thread"],
        "Headband": ["ruler", "fabric glue or needle and thread"],
    },
}

for category_key, (_, _, category_ideas) in CATEGORIES.items():
    additions_by_title = _MATERIAL_ADDITIONS.get(category_key, {})
    for project in category_ideas:
        existing = {material.casefold() for material in project["materials"]}
        for material in additions_by_title.get(project["title"], []):
            if material.casefold() not in existing:
                project["materials"].append(material)
                existing.add(material.casefold())


# Final lists for projects whose safety-reviewed steps require different
# supplies from the original short idea entries.
_MATERIAL_CORRECTIONS = {
    ("plastic", "Hanging Lamp Shade"): ["Clean plastic bottles", "Scissors", "Adult help for cutting", "Protective gloves", "Edge trim or fine sandpaper", "Cable ties or craft fasteners", "Preassembled cool-running LED lamp fitting"],
    ("plastic", "Piggy Bank"): ["Plastic bottle", "Four clean bottle caps", "Paint", "Strong craft glue", "Marker", "Adult help and craft knife for the coin slot", "Protective gloves", "Fine sandpaper"],
    ("paper", "Paper Lantern"): ["Newspaper", "Glue", "Scissors", "Thin skewer or dowel", "Cardboard strips for the rings", "Ruler", "Pencil", "String for hanging loop", "Battery-powered LED tea light"],
    ("glass", "Wind Chime"): ["Pre-drilled, professionally cut and edge-finished glass chime pieces", "Strong cord", "Wooden stick or metal ring", "Protective gloves", "Safety glasses", "Secure hanging hook"],
    ("glass", "Mosaic Art"): ["Pre-cut, edge-finished mosaic tiles", "Tile adhesive", "Grout", "Backing board", "Grout sponge", "Protective gloves", "Safety glasses"],
    ("glass", "Drinking Glass from Bottle"): ["Professionally cut and edge-finished food-safe glass bottle section", "Cut-resistant gloves", "Safety glasses"],
    ("glass", "Hanging Bottle Planter"): ["Purpose-made pre-cut glass bottle planter", "Rated rope cradle or planter hanger", "Waterproof liner or nursery pot", "Small plant", "Secure hanging hook"],
    ("glass", "Jar Piggy Bank"): ["Glass jar", "Pre-slotted metal lid", "Smooth slot-edge trim", "Waterproof sealant for lid threads", "Paint", "Paintbrush", "Marker"],
    ("metal", "Bird Feeder"): ["Clean tin can", "Wire", "Wooden dowel perch", "Birdseed", "Tin snips for adult use", "Metal file", "Protective gloves", "Safety glasses"],
    ("metal", "Hanging Planter"): ["Tin can", "Rope", "Paint", "Nail and hammer or hand punch for adult-made holes", "Marker", "Paintbrush", "Potting soil", "Small plant", "Secure hanging hook"],
    ("e-waste", "Desk Lamp"): ["Ready-made low-voltage LED kit", "Battery holder", "On/off switch", "Insulated wire", "Stable lamp housing", "Small screwdriver", "Insulating tape"],
    ("e-waste", "Pen Stand from Old Charger"): ["Empty adapter casing opened by a qualified adult", "Edge trim", "Paint", "Paintbrush"],
    ("e-waste", "Speaker Box"): ["Compatible low-voltage speaker", "Sturdy box", "Compatible amplifier module", "Speaker wire", "Power source rated for the amplifier", "Screws", "Protective grille fabric", "Small screwdriver", "Adult help and a suitable tool for cutting the speaker opening"],
    ("e-waste", "Jewellery from Circuit Boards"): ["Clean, depopulated, pre-cut circuit-board pieces", "Jewellery findings", "Clear sealant", "Disposable gloves for sealant"],
    ("e-waste", "CD Mosaic Mirror"): ["Pre-cut reflective CD mosaic pieces", "Small mirror", "Wooden backing board", "Tile adhesive", "Grout", "Sponge", "Protective gloves", "Safety glasses"],
    ("e-waste", "Cable Bracelet"): ["Clean, non-electrical cable covering with conductors already removed", "Thread", "Clasp", "Jump rings", "Pliers", "Scissors"],
    ("e-waste", "Mini Fan"): ["Low-voltage motor kit", "Battery holder", "On/off switch", "Insulated wire", "Purpose-made guarded fan blade", "Stable stand", "Small screwdriver"],
}

for category_key, (_, _, category_ideas) in CATEGORIES.items():
    for project in category_ideas:
        corrected_materials = _MATERIAL_CORRECTIONS.get((category_key, project["title"]))
        if corrected_materials:
            project["materials"] = corrected_materials


# ---- pictures (category-specific folders in static/items) ----
def _is_numbered_gallery_photo(filename):
    stem = _normalize_text(os.path.splitext(filename)[0])
    return re.search(r"\s*[234]$", stem) is not None


def _picture(cat, idea):
    target_title = _normalize_text(idea["title"])
    folder_map = {
        "plastic": "Plastic",
        "paper": "Paper",
        "glass": "Glass",
        "metal": "Metal",
        "e-waste": "E-Waste",
        "clothes": "Clothes",
    }

    folder_name = folder_map.get(cat, "")
    directory = os.path.join(ITEMS_DIR, folder_name)
    if os.path.isdir(directory):
        best_match = None
        best_score = -1

        for filename in sorted(os.listdir(directory)):
            if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".svg")):
                continue
            if _is_numbered_gallery_photo(filename):
                continue

            base_name = _normalize_text(os.path.splitext(filename)[0])
            score = 0

            if base_name == target_title:
                score = 100
            elif target_title in base_name:
                score = 80
            elif base_name in target_title:
                score = 70
            else:
                title_tokens = set(target_title.split())
                file_tokens = set(base_name.split())
                score = len(title_tokens & file_tokens) * 20

            if score > best_score:
                best_score = score
                best_match = os.path.join("items", folder_name, filename).replace("\\", "/")

        if best_score >= 20:
            return best_match

    # fallback to first image in category folder
    if os.path.isdir(directory):
        files = sorted(
            f for f in os.listdir(directory)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".svg"))
            and not _is_numbered_gallery_photo(f)
        )
        if files:
            return os.path.join("items", folder_name, files[0]).replace("\\", "/")

    fallback = {
        "plastic": "items/plastic_bottle.svg",
        "paper": "items/newspaper.svg",
        "glass": "items/glass_bottle.svg",
        "metal": "items/tin_can.svg",
        "e-waste": "items/circuit_board.svg",
        "clothes": "items/tshirt.svg",
    }
    return fallback.get(cat, "items/plastic_bottle.svg")


def _gallery_images(cat, idea):
    """Find the optional project photos whose filenames end in 2, 3, or 4."""
    folder_map = {
        "plastic": "Plastic",
        "paper": "Paper",
        "glass": "Glass",
        "metal": "Metal",
        "e-waste": "E-Waste",
        "clothes": "Clothes",
    }
    folder_name = folder_map.get(cat, "")
    directory = os.path.join(ITEMS_DIR, folder_name)
    target = _normalize_text(idea["title"])
    # Keep filename variants explicit. Token-overlap matching is unsafe here:
    # projects such as "CD Coasters" and "CD Mosaic Mirror" share the token CD.
    aliases = {
        ("e-waste", "cd coasters"): {"cs coasters"},  # existing filename typo
    }
    accepted_bases = {target, *aliases.get((cat, target), set())}
    found = {}
    if not os.path.isdir(directory):
        return [None, None, None]

    for filename in sorted(os.listdir(directory)):
        if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        stem = _normalize_text(os.path.splitext(filename)[0])
        match = re.search(r"\s*([234])$", stem)
        if not match:
            continue
        number = int(match.group(1))
        base = stem[:match.start()].strip()
        if base in accepted_bases:
            score = 100 if base == target else 90
        else:
            continue
        if number not in found or score > found[number][0]:
            found[number] = (score, os.path.join("items", folder_name, filename).replace("\\", "/"))

    return [found.get(number, (0, None))[1] for number in (2, 3, 4)]


from urllib.parse import quote_plus


def get_ideas(category):
    c = CATEGORIES.get(category)
    if not c:
        return None
    for idea in c[2]:
        idea["image"] = _picture(category, idea)
        idea["gallery_images"] = [idea["image"], *_gallery_images(category, idea)]
        idea["youtube"] = "https://www.youtube.com/results?search_query=" + quote_plus(f"{idea['title']} {c[0]} DIY")
    return {"label": c[0], "icon": c[1], "ideas": c[2]}
