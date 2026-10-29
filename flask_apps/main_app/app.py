import json
import os
import re
import secrets
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import MySQLdb
from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from urllib.parse import quote_plus, urlparse

import diy_payments
from diy_data import CATEGORIES, get_ideas

app = Flask(__name__)

# Load DB settings from a .env file next to this app.py (if python-dotenv is installed)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except ImportError:
    pass

# Sessions are signed with this key: anyone who knows it can forge a login.
# Set SECRET_KEY in .env for any real deployment; the fallback keeps local
# development working as before.
app.secret_key = os.environ.get('SECRET_KEY') or 'your_secret_key_here'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Database config
app.config['MYSQL_HOST'] = os.environ.get('DB_HOST', 'localhost')
app.config['MYSQL_PORT'] = int(os.environ.get('DB_PORT', 3306))
app.config['MYSQL_USER'] = os.environ.get('DB_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('DB_PASSWORD', '')
app.config['MYSQL_DB'] = os.environ.get('DB_NAME', 'waste2value_final')

mysql = MySQL(app)
bcrypt = Bcrypt(app)

app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/recycle')
def recycle():
    """Module 2 entry: pick a waste category to see its DIY ideas."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('recycle.html', categories=CATEGORIES)


@app.route('/recycle/ideas/<category>')
def recycle_ideas(category):
    """DIY ideas + YouTube tutorials for the chosen waste type."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    data = get_ideas(category)
    if not data:
        return redirect(url_for('recycle'))

    general_q = f"{data['label']} waste recycling DIY ideas"
    return render_template(
        'recycle_ideas.html',
        data=data,
        category=category,
        general_youtube="https://www.youtube.com/results?search_query=" + quote_plus(general_q),
    )


@app.route('/recycle/ideas/<category>/<int:idea_index>')
def recycle_idea_detail(category, idea_index):
    """Show the materials, safety guidance, and gallery for one DIY idea."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    data = get_ideas(category)
    if not data or idea_index >= len(data['ideas']):
        abort(404)

    return render_template(
        'diy_idea_detail.html',
        data=data,
        idea=data['ideas'][idea_index],
        category=category,
    )


# ---------------------------------------------------------------------
# DIY products marketplace: handmade / upcycled products.
# Separate from the waste-material marketplace (no listings, offers or
# pickups); products live in the `diy_products` table and their images in
# static/uploads/diy/.
# ---------------------------------------------------------------------
DIY_CATEGORIES = {
    'home-decor': 'Home Decor',
    'accessories': 'Accessories',
    'art': 'Art',
    'useful-recycled': 'Useful Recycled Products',
}
DIY_UPLOAD_SUBDIR = 'diy'
DIY_MAX_IMAGE_BYTES = 5 * 1024 * 1024
DIY_MAX_PRICE = Decimal('99999999.99')  # fits decimal(10,2)
# Plain ASCII digits, up to 8 before the point and 2 after ("250", "249.99", ".5").
# No sign, exponent, separators or non-ASCII digits, so nothing is ever rounded.
DIY_PRICE_PATTERN = re.compile(r'(?:[0-9]{1,8}(?:\.[0-9]{1,2})?|\.[0-9]{1,2})')
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], DIY_UPLOAD_SUBDIR), exist_ok=True)


def to_money(value):
    """Exact 2-decimal Decimal from a DB/stored amount (Decimal, int, str or float).

    Goes through str() so a float from any driver never leaks binary error
    (Decimal(349.99) would be 349.990000000000009...).
    """
    return Decimal(str(value)).quantize(Decimal('0.01'))


def parse_diy_price(raw, is_free):
    """Validate a product price exactly as submitted. Returns (Decimal, None) or (None, error).

    Never rounds, clamps or converts: a negative or malformed value is an
    error, not a free item. ₹0 is accepted only when the seller explicitly
    marked the item as free; paid items must cost more than ₹0. Use this for
    every product create/edit path.
    """
    raw = (raw or '').strip()
    if raw.startswith('-'):
        return None, "Price can't be negative."
    if is_free and raw == '':
        return Decimal('0.00'), None
    if raw == '':
        return None, "Enter a price, or tick “This is a free item”."
    if not DIY_PRICE_PATTERN.fullmatch(raw):
        return None, "Enter the price as a plain number such as 250 or 249.99 (digits only, at most 2 decimal places)."

    price = Decimal(raw).quantize(Decimal('0.01'))  # exact: the pattern allows at most 2 decimals
    if price > DIY_MAX_PRICE:
        return None, "Price is too high."
    if is_free and price != 0:
        return None, "A free item must have a price of 0. Untick “This is a free item” to sell it."
    if not is_free and price == 0:
        return None, "Paid items need a price above ₹0. To give it away, tick “This is a free item”."
    return price, None


def _diy_image_ext(file_storage):
    """Return a safe extension if the upload really is a PNG/JPEG/GIF/WEBP image, else None."""
    head = file_storage.stream.read(12)
    file_storage.stream.seek(0)
    if head.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if head.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if head[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return 'webp'
    return None


def _diy_validate(form, image_file):
    """Validate the 'Sell Your Creation' form. Returns (errors, price)."""
    errors = []
    price = None

    if not form['title']:
        errors.append("Please give your product a name.")
    elif len(form['title']) > 150:
        errors.append("Product name must be 150 characters or fewer.")

    if len(form['description']) > 2000:
        errors.append("Description must be 2000 characters or fewer.")

    if form['category'] not in DIY_CATEGORIES:
        errors.append("Please choose a category.")

    price, price_error = parse_diy_price(form['price'], form['is_free'] == 'yes')
    if price_error:
        errors.append(price_error)

    if not image_file or image_file.filename == '':
        errors.append("Please add a photo of your product.")
    else:
        image_file.stream.seek(0, os.SEEK_END)
        size = image_file.stream.tell()
        image_file.stream.seek(0)
        if size > DIY_MAX_IMAGE_BYTES:
            errors.append("Image must be 5 MB or smaller.")
        elif _diy_image_ext(image_file) is None:
            errors.append("Image must be a PNG, JPG, GIF or WEBP file.")

    return errors, price


@app.route('/diy-marketplace', methods=['GET', 'POST'])
def diy_marketplace():
    """Storefront for handmade / upcycled products, plus the 'Sell Your Creation' form."""
    errors = []
    form = {'title': '', 'description': '', 'price': '', 'category': '', 'is_free': ''}

    if request.method == 'POST':
        if 'user_id' not in session:
            return redirect(url_for('login'))

        # Reject oversized uploads before Flask parses the body.
        if request.content_length and request.content_length > DIY_MAX_IMAGE_BYTES + 64 * 1024:
            errors.append("Image must be 5 MB or smaller.")
        else:
            form = {key: request.form.get(key, '').strip() for key in form}
            image_file = request.files.get('image')
            errors, price = _diy_validate(form, image_file)

            if not errors:
                image_path = f"{DIY_UPLOAD_SUBDIR}/{uuid.uuid4().hex}.{_diy_image_ext(image_file)}"
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], *image_path.split('/'))
                image_file.save(full_path)
                try:
                    cur = mysql.connection.cursor()
                    cur.execute(
                        "INSERT INTO diy_products (seller_id, title, description, price, category, image_path) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (session['user_id'], form['title'], form['description'] or None,
                         price, form['category'], image_path)
                    )
                    mysql.connection.commit()
                    cur.close()
                except Exception:
                    # Don't leave an orphaned image behind if the insert fails.
                    if os.path.exists(full_path):
                        os.remove(full_path)
                    raise
                _diy_notice('added')
                return redirect(url_for('diy_marketplace') + '#shop')

    _diy_expire_stale_payments()
    selected_category = request.args.get('category', '')
    if selected_category not in DIY_CATEGORIES:
        selected_category = ''

    # Every product is listed, including sold ones (shown with a "Sold" label and
    # no Buy Now button) -- hiding them made sellers' products look "missing" after
    # a delivered order. Available pieces come first. Only invalid (negative-price)
    # rows are left out; checkout refuses them anyway.
    query = """
        SELECT p.id, p.title, p.description, p.price, p.category, p.image_path, u.name,
               p.seller_id, p.status
        FROM diy_products p
        JOIN users u ON u.id = p.seller_id
        WHERE p.price >= 0
    """
    params = ()
    if selected_category:
        query += " AND p.category = %s"
        params = (selected_category,)
    query += " ORDER BY (p.status = 'sold'), p.created_at DESC, p.id DESC"

    cur = mysql.connection.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()

    viewer_id = session.get('user_id')
    products = [
        {
            'id': r[0], 'title': r[1], 'description': r[2], 'price': to_money(r[3]),
            'category': r[4], 'category_label': DIY_CATEGORIES.get(r[4], r[4]),
            'image_url': url_for('static', filename='uploads/' + r[5]), 'seller': r[6],
            'status': r[8],
            'is_own': viewer_id is not None and r[7] == viewer_id,
            'is_free': to_money(r[3]) == 0,
        }
        for r in rows
    ]

    return render_template(
        'diy_marketplace.html',
        products=products,
        categories=DIY_CATEGORIES,
        selected_category=selected_category,
        form=form,
        errors=errors,
        added=request.method == 'GET' and (_diy_pop_notice() or {}).get('kind') == 'added',
        logged_in='user_id' in session,
        user_name=session.get('user_name'),
    ), (400 if errors else 200)


# ---------------------------------------------------------------------
# Request guards for the handmade shop (diy_* endpoints only, so the
# waste-marketplace pages behave exactly as before):
#   1. the logged-in user must still exist (an admin may have deleted them);
#      the navbar name is refreshed from the database;
#   2. every form POST needs the session CSRF token (same pattern as the admin app);
#   3. every form POST must come from a page rendered for the *current* user
#      ("acting_user"). Tabs in one browser share one login cookie, so after
#      logging into another account in tab B, a form left open in tab A would
#      otherwise silently act as the new account.
# ---------------------------------------------------------------------
DIY_GUARD_EXEMPT = {'diy_razorpay_webhook'}  # authenticated by Razorpay's signature instead


def diy_csrf_token():
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


app.jinja_env.globals['diy_csrf_token'] = diy_csrf_token


@app.before_request
def diy_request_guard():
    endpoint = request.endpoint or ''
    if not endpoint.startswith('diy_') or endpoint in DIY_GUARD_EXEMPT:
        return None

    if 'user_id' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT name FROM users WHERE id = %s", (session['user_id'],))
        row = cur.fetchone()
        cur.close()
        if row is None:
            session.clear()
            return redirect(url_for('login'))
        if session.get('user_name') != row[0]:
            session['user_name'] = row[0]

    # Logged-out POSTs change nothing: each view redirects them to login.
    if request.method != 'POST' or 'user_id' not in session:
        return None
    # Let the sell form reject oversized uploads without parsing the body.
    if endpoint == 'diy_marketplace' and request.content_length \
            and request.content_length > DIY_MAX_IMAGE_BYTES + 64 * 1024:
        return None

    expected = session.get('_csrf_token')
    sent = request.form.get('csrf_token', '')
    if not expected or not secrets.compare_digest(expected, sent):
        return "Your form session expired. Please go back, refresh the page and try again.", 400
    if request.form.get('acting_user', '') != str(session['user_id']):
        return render_template(
            'diy_message.html', title="You've switched accounts",
            message=f"This page was opened for a different account. You're now logged in as "
                    f"{session.get('user_name')} in this browser, so nothing was changed. "
                    "Reload the page to continue as this account. (Tabs in the same browser share one "
                    "login; use a private window or another browser profile to be logged in as two people.)",
        ), 409
    return None


@app.errorhandler(MySQLdb.Error)
def diy_database_error(err):
    """Friendly page for database failures in the shop; other pages behave as before."""
    if not (request.endpoint or '').startswith('diy_'):
        raise err
    app.logger.exception("Database error on %s", request.endpoint)
    try:
        mysql.connection.rollback()
    except Exception:
        pass
    return render_template(
        'diy_message.html', title="Something went wrong",
        message="The shop couldn't reach its database (or it is missing a required update). "
                "Nothing was charged or changed. Please try again in a moment.",
    ), 503


def _diy_notice(kind, order_number=None, **data):
    """One-time message shown on the next page (replaces ?placed=1 / ?updated= URL flags)."""
    session['diy_notice'] = dict(data, kind=kind, order=order_number)


def _diy_pop_notice(order_number=None):
    notice = session.pop('diy_notice', None)
    return notice if notice and notice.get('order') == order_number else None


# ---------------------------------------------------------------------
# DIY orders: Buy Now -> delivery details -> review -> place order.
# One item per order. Product ownership, availability and price always
# come from the database, never from the browser.
# ---------------------------------------------------------------------
PAYMENT_METHODS = {
    'cod': {'label': 'Cash on Delivery', 'group': 'Pay on delivery', 'online': False},
    'upi_gpay': {'label': 'Google Pay', 'group': 'UPI', 'online': True, 'rzp': 'upi'},
    'upi_phonepe': {'label': 'PhonePe', 'group': 'UPI', 'online': True, 'rzp': 'upi'},
    'upi_paytm': {'label': 'Paytm', 'group': 'UPI', 'online': True, 'rzp': 'upi'},
    'card': {'label': 'Debit / Credit Card', 'group': 'Card', 'online': True, 'rzp': 'card'},
    'netbanking': {'label': 'Net Banking', 'group': 'Net Banking', 'online': True, 'rzp': 'netbanking'},
}
ONLINE_METHODS = tuple(k for k, m in PAYMENT_METHODS.items() if m['online'])
PAYMENT_METHOD_LABELS = {key: m['label'] for key, m in PAYMENT_METHODS.items()}
PAYMENT_METHOD_LABELS['free'] = 'Free item (no payment)'
# Presentation-only stand-in for online payment while no gateway is configured.
# It never moves money and is never recorded as 'paid' (see diy_payments.simulation_enabled).
DEMO_METHOD = 'demo'
PAYMENT_METHOD_LABELS[DEMO_METHOD] = 'Pay Online (simulated)'
PAYMENT_REFERENCE_MAX = 100

PAYMENT_STATUS_LABELS = {
    'cod_pending': 'Cash due on delivery',
    'not_required': 'No payment needed',
    'not_charged': 'Not charged',
    'awaiting_payment': 'Awaiting online payment',
    'authorized': 'Payment authorised, waiting for Razorpay to capture it',
    'failed': 'Last payment attempt failed',
    'expired': 'Payment window expired (not charged)',
    'paid': 'Paid online (verified with Razorpay)',
    'refund_pending': 'Refund due (issue it from the Razorpay Dashboard)',
    'simulated': 'Simulated payment (demo only, no real money transferred)',
}

ORDER_STATUS_LABELS = {
    'pending_payment': 'Awaiting payment',
    'placed': 'Placed, awaiting seller',
    'confirmed': 'Confirmed by seller',
    'shipped': 'Shipped',
    'delivered': 'Delivered',
    'rejected': 'Rejected by seller',
    'cancelled': 'Cancelled',
}
ORDER_OPEN_STATUSES = ('pending_payment', 'placed', 'confirmed', 'shipped')

# action -> {current status: roles allowed}, plus the new status.
#   Seller manages fulfilment (confirm/reject, ship); only the buyer confirms receipt.
ORDER_ACTIONS = {
    'confirm': {'to': 'confirmed', 'from': {'placed': ('seller',)}},
    'reject': {'to': 'rejected', 'from': {'placed': ('seller',)}},
    'ship': {'to': 'shipped', 'from': {'confirmed': ('seller',)}},
    'deliver': {'to': 'delivered', 'from': {'shipped': ('buyer',)}},
    'cancel': {'to': 'cancelled', 'from': {'pending_payment': ('buyer',), 'placed': ('buyer',),
                                           'confirmed': ('buyer', 'seller')}},
}
# Timestamp column set when an order enters a status (fixed whitelist: safe to format into SQL).
STATUS_TIMESTAMP = {'confirmed': 'confirmed_at', 'shipped': 'shipped_at', 'delivered': 'delivered_at',
                    'rejected': 'closed_at', 'cancelled': 'closed_at'}
# Online orders can't move forward until Razorpay has verifiably captured the payment.
PAYMENT_REQUIRED_FOR = ('confirm', 'ship', 'deliver')
# What happens to the product when an order reaches these statuses.
PRODUCT_STATUS_AFTER = {'delivered': 'sold', 'rejected': 'available', 'cancelled': 'available'}
# Sellers only see orders that were really placed: COD/free, or online orders once paid.
SELLER_VISIBLE_SQL = ("(o.payment_method IN ('cod', 'free') OR o.paid_at IS NOT NULL "
                      "OR (o.payment_method = 'demo' AND o.payment_status = 'simulated'))")
# Unpaid online orders release the product after this long.
PAYMENT_WINDOW_MINUTES = 30
STALE_PAYMENT_SQL = f"created_at < NOW() - INTERVAL {PAYMENT_WINDOW_MINUTES} MINUTE"

INDIAN_STATES = (
    'Andaman and Nicobar Islands', 'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar',
    'Chandigarh', 'Chhattisgarh', 'Dadra and Nagar Haveli and Daman and Diu', 'Delhi', 'Goa',
    'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jammu and Kashmir', 'Jharkhand', 'Karnataka',
    'Kerala', 'Ladakh', 'Lakshadweep', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya',
    'Mizoram', 'Nagaland', 'Odisha', 'Puducherry', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
    'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
)
CHECKOUT_FIELDS = ('delivery_name', 'delivery_phone', 'address_line', 'locality', 'city',
                   'state', 'pincode', 'delivery_instructions', 'payment_method')
ORDER_NUMBER_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # no 0/O/1/I


def _diy_load_product(product_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.id, p.title, p.description, p.price, p.category, p.image_path,
               p.seller_id, p.status, u.name
        FROM diy_products p
        JOIN users u ON u.id = p.seller_id
        WHERE p.id = %s
    """, (product_id,))
    r = cur.fetchone()
    cur.close()
    if not r:
        return None
    return {
        'id': r[0], 'title': r[1], 'description': r[2], 'price': to_money(r[3]),
        'category_label': DIY_CATEGORIES.get(r[4], r[4]),
        'image_url': url_for('static', filename='uploads/' + r[5]),
        'seller_id': r[6], 'status': r[7], 'seller': r[8],
    }


def _diy_purchase_block(product, buyer_id):
    """Why `buyer_id` can't buy `product` right now, or None if they can."""
    if product['seller_id'] == buyer_id:
        return "This is your own product, so you can't buy it."
    if product['status'] != 'available':
        return "Sorry, this piece is no longer available."
    if not (0 <= product['price'] <= DIY_MAX_PRICE):
        return "This piece has an invalid price, so it can't be bought right now."
    return None


def _diy_active_order_number(product_id, buyer_id):
    """The buyer's open order for this product, if any (e.g. after a double submit)."""
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT order_number FROM diy_orders WHERE product_id = %s AND buyer_id = %s "
        "AND status IN ('pending_payment', 'placed', 'confirmed', 'shipped') ORDER BY id DESC LIMIT 1",
        (product_id, buyer_id))
    r = cur.fetchone()
    cur.close()
    return r[0] if r else None


def _normalise_phone(raw):
    digits = re.sub(r'[\s\-().]', '', raw)
    if digits.startswith('+91'):
        digits = digits[3:]
    elif len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith('0'):
        digits = digits[1:]
    return digits if re.fullmatch(r'[6-9]\d{9}', digits) else None


def _is_person_name(value):
    return 2 <= len(value) <= 100 and all(ch.isalpha() or ch in " .'-" for ch in value) \
        and any(ch.isalpha() for ch in value)


def _diy_validate_checkout(form, price):
    """Validate delivery + payment details. Returns (errors, cleaned values)."""
    errors = []
    clean = dict(form)

    if not _is_person_name(form['delivery_name']):
        errors.append("Enter the full name of the person receiving the order (letters only).")

    phone = _normalise_phone(form['delivery_phone'])
    if phone is None:
        errors.append("Enter a valid 10-digit Indian mobile number.")
    else:
        clean['delivery_phone'] = phone

    if not 5 <= len(form['address_line']) <= 255:
        errors.append("Enter your house number and street (5 to 255 characters).")
    if not 2 <= len(form['locality']) <= 120:
        errors.append("Enter your area or locality.")
    if not (2 <= len(form['city']) <= 80 and _is_person_name(form['city'])):
        errors.append("Enter a valid city name.")
    if form['state'] not in INDIAN_STATES:
        errors.append("Choose your state or union territory.")
    if not re.fullmatch(r'[1-9]\d{5}', form['pincode']):
        errors.append("Enter a valid 6-digit PIN code.")
    if len(form['delivery_instructions']) > 300:
        errors.append("Delivery instructions must be 300 characters or fewer.")

    if price == 0:
        clean['payment_method'] = 'free'
    else:
        method = PAYMENT_METHODS.get(form['payment_method'])
        if form['payment_method'] == DEMO_METHOD:
            if not diy_payments.simulation_enabled():
                errors.append("Demo payments are switched off on this site. Please choose another payment method.")
        elif method is None:
            errors.append("Choose a payment method.")
        elif method['online'] and not diy_payments.is_configured():
            errors.append(f"{method['label']} isn't available: {diy_payments.unavailable_reason()} "
                          "Please choose Cash on Delivery.")
        elif method['online'] and price < diy_payments.MIN_AMOUNT:
            errors.append("Online payments need an order of at least ₹1. Please choose Cash on Delivery.")

    return errors, clean


def _new_order_number():
    suffix = ''.join(secrets.choice(ORDER_NUMBER_ALPHABET) for _ in range(6))
    return f"RM{date.today():%y%m%d}-{suffix}"


def _diy_place_order(product_id, buyer_id, details, expected_price):
    """Create the order in one transaction.

    Returns ('ok', order_number), ('unavailable', None), ('price_changed', None)
    or ('gateway_error', message).
    The conditional UPDATE is the concurrency guard: only one request can move a
    product from 'available' to 'reserved', so two buyers (or a double click)
    can never both get an order for the same piece, and the seller can never
    reserve their own product. For online payments the Razorpay order is
    created inside the same transaction, from the database price; if Razorpay
    can't be reached everything is rolled back and the product stays available.
    """
    conn = mysql.connection
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE diy_products SET status = 'reserved' "
            "WHERE id = %s AND status = 'available' AND seller_id <> %s",
            (product_id, buyer_id))
        if cur.rowcount != 1:
            conn.rollback()
            return 'unavailable', None

        cur.execute("SELECT title, price, seller_id FROM diy_products WHERE id = %s", (product_id,))
        title, price, seller_id = cur.fetchone()
        price = to_money(price)
        if not (0 <= price <= DIY_MAX_PRICE):
            # Legacy/hand-edited bad price: never sell it (rollback un-reserves it).
            conn.rollback()
            return 'unavailable', None
        if price != expected_price:
            conn.rollback()
            return 'price_changed', None

        method = details['payment_method']
        if price == 0:
            payment_method, payment_status, status, provider = 'free', 'not_required', 'placed', None
        elif method == 'cod':
            payment_method, payment_status, status, provider = 'cod', 'cod_pending', 'placed', None
        elif method == DEMO_METHOD and diy_payments.simulation_enabled():
            payment_method, payment_status, status, provider = DEMO_METHOD, 'awaiting_payment', 'pending_payment', 'simulation'
        elif method in ONLINE_METHODS and diy_payments.is_configured() and price >= diy_payments.MIN_AMOUNT:
            payment_method, payment_status, status, provider = method, 'awaiting_payment', 'pending_payment', 'razorpay'
        else:
            conn.rollback()
            return 'gateway_error', (diy_payments.unavailable_reason()
                                     or "That payment method can't be used for this order.")

        for attempt in range(5):
            order_number = _new_order_number()
            try:
                cur.execute("""
                    INSERT INTO diy_orders
                        (order_number, product_id, buyer_id, seller_id, product_title,
                         unit_price, quantity, total_amount, delivery_name, delivery_phone,
                         address_line, locality, city, state, pincode, delivery_instructions,
                         payment_method, payment_status, status, payment_provider)
                    VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (order_number, product_id, buyer_id, seller_id, title, price, price,
                      details['delivery_name'], details['delivery_phone'], details['address_line'],
                      details['locality'], details['city'], details['state'], details['pincode'],
                      details['delivery_instructions'] or None, payment_method, payment_status,
                      status, provider))
                break
            except MySQLdb.IntegrityError as err:
                # 1062 = duplicate key: retry only on an order-number collision.
                if err.args[0] == 1062 and 'order_number' in str(err) and attempt < 4:
                    continue
                raise

        if provider == 'razorpay':
            try:
                rzp_order_id = diy_payments.create_order(price, order_number, {'order_number': order_number})
            except diy_payments.GatewayUnavailable as err:
                conn.rollback()
                return 'gateway_error', str(err)
            cur.execute("UPDATE diy_orders SET provider_order_id = %s WHERE order_number = %s",
                        (rzp_order_id, order_number))

        conn.commit()
        return 'ok', order_number
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


@app.route('/diy-marketplace/checkout/<int:product_id>', methods=['GET', 'POST'])
def diy_checkout(product_id):
    """Buy Now: delivery details -> review -> place order (one item)."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    buyer_id = session['user_id']

    _diy_expire_stale_payments(product_id)
    product = _diy_load_product(product_id)
    if product is None:
        abort(404)

    blocked = _diy_purchase_block(product, buyer_id)
    if blocked:
        existing = _diy_active_order_number(product_id, buyer_id)
        if existing:
            return redirect(url_for('diy_order_detail', order_number=existing))
        status = 403 if product['seller_id'] == buyer_id else 409
        return render_template('diy_checkout.html', product=product, blocked=blocked), status

    step, errors, notice, http_status = 'details', [], None, 200
    form = {key: '' for key in CHECKOUT_FIELDS}
    form['delivery_name'] = session.get('user_name', '')
    form['payment_method'] = 'free' if product['price'] == 0 else 'cod'

    if request.method == 'POST':
        form = {key: request.form.get(key, '').strip() for key in CHECKOUT_FIELDS}
        action = request.form.get('action', 'review')
        errors, clean = _diy_validate_checkout(form, product['price'])

        if action == 'edit' or errors:
            step = 'details'
            http_status = 400 if errors else 200
        elif action == 'review':
            step, form = 'review', clean
        elif action == 'place' and request.form.get('confirm') != 'yes':
            step, form, http_status = 'review', clean, 400
            errors = ["Please tick the box to confirm your order details."]
        elif action == 'place':
            try:
                expected_price = Decimal(request.form.get('expected_price', '')).quantize(Decimal('0.01'))
            except (InvalidOperation, ValueError):
                expected_price = None
            result, detail = _diy_place_order(product_id, buyer_id, clean, expected_price) \
                if expected_price is not None else ('price_changed', None)

            if result == 'ok':
                if clean['payment_method'] == DEMO_METHOD:
                    return redirect(url_for('diy_payment_simulation', order_number=detail))
                if clean['payment_method'] in ONLINE_METHODS:
                    return redirect(url_for('diy_payment_page', order_number=detail))
                _diy_notice('placed', detail)
                return redirect(url_for('diy_order_detail', order_number=detail))
            product = _diy_load_product(product_id)
            if result == 'gateway_error':
                step, form, http_status = 'review', clean, 503
                errors = [f"{detail} Your order was not placed and you weren't charged. "
                          "You can try again or choose Cash on Delivery."]
            elif result == 'price_changed' and _diy_purchase_block(product, buyer_id) is None:
                step, form, http_status = 'review', clean, 409
                notice = "The price of this piece changed. Please review the new total before placing your order."
            else:
                existing = _diy_active_order_number(product_id, buyer_id)
                if existing:
                    return redirect(url_for('diy_order_detail', order_number=existing))
                return render_template(
                    'diy_checkout.html', product=product,
                    blocked=_diy_purchase_block(product, buyer_id) or "Sorry, this piece is no longer available."
                ), 409
        else:
            abort(400)

    return render_template(
        'diy_checkout.html',
        product=product, step=step, form=form, errors=errors, notice=notice,
        states=INDIAN_STATES, payment_methods=PAYMENT_METHODS,
        online_available=diy_payments.is_configured(),
        online_reason=diy_payments.unavailable_reason(),
        online_test_mode=diy_payments.is_test_mode(),
        simulation_enabled=diy_payments.simulation_enabled(),
        payment_labels=PAYMENT_METHOD_LABELS,
    ), http_status


ORDER_COLUMNS = """
    o.id, o.order_number, o.product_id, o.buyer_id, o.seller_id, o.product_title,
    o.unit_price, o.quantity, o.total_amount, o.delivery_name, o.delivery_phone,
    o.address_line, o.locality, o.city, o.state, o.pincode, o.delivery_instructions,
    o.payment_method, o.payment_status, o.status, o.created_at, o.updated_at,
    b.name, s.name, p.image_path,
    o.confirmed_at, o.shipped_at, o.delivered_at, o.closed_at,
    o.courier_name, o.tracking_number, o.tracking_url,
    o.payment_provider, o.provider_order_id, o.paid_at
"""
ORDER_JOINS = """
    FROM diy_orders o
    JOIN users b ON b.id = o.buyer_id
    JOIN users s ON s.id = o.seller_id
    JOIN diy_products p ON p.id = o.product_id
"""
ORDER_KEYS = ('id', 'order_number', 'product_id', 'buyer_id', 'seller_id', 'product_title',
              'unit_price', 'quantity', 'total_amount', 'delivery_name', 'delivery_phone',
              'address_line', 'locality', 'city', 'state', 'pincode', 'delivery_instructions',
              'payment_method', 'payment_status', 'status', 'created_at', 'updated_at',
              'buyer_name', 'seller_name', 'image_path',
              'confirmed_at', 'shipped_at', 'delivered_at', 'closed_at',
              'courier_name', 'tracking_number', 'tracking_url',
              'payment_provider', 'provider_order_id', 'paid_at')


def _fmt_dt(value):
    if value is None:
        return None
    return value.strftime('%d %b %Y, %I:%M %p') if hasattr(value, 'strftime') else str(value)


def _order_from_row(r):
    o = dict(zip(ORDER_KEYS, r))
    o['unit_price'] = to_money(o['unit_price'])
    o['total_amount'] = to_money(o['total_amount'])
    o['image_url'] = url_for('static', filename='uploads/' + o['image_path'])
    o['status_label'] = ORDER_STATUS_LABELS.get(o['status'], o['status'])
    o['payment_method_label'] = PAYMENT_METHOD_LABELS.get(o['payment_method'], o['payment_method'])
    o['payment_status_label'] = PAYMENT_STATUS_LABELS.get(o['payment_status'], o['payment_status'])
    o['is_free'] = o['payment_method'] == 'free'
    o['is_online'] = o['payment_method'] in ONLINE_METHODS
    o['is_demo'] = o['payment_method'] == DEMO_METHOD
    for key in ('created_at', 'confirmed_at', 'shipped_at', 'delivered_at', 'closed_at', 'paid_at'):
        o[key.replace('_at', '_label')] = _fmt_dt(o[key])
    return o


def _order_role(order, user_id):
    if order['buyer_id'] == user_id:
        return 'buyer'
    if order['seller_id'] == user_id:
        return 'seller'
    return None


def _payment_settled(order):
    """May the order move forward? COD/free: yes. Real online methods: only after a
    verified Razorpay capture ('paid'). Demo orders: after the simulated step
    ('simulated'), which is never treated as paid."""
    if order['payment_method'] in ('cod', 'free'):
        return True
    if order['payment_method'] == DEMO_METHOD:
        return order['payment_status'] == 'simulated'
    return order['payment_status'] == 'paid'


def _seller_can_see(order):
    if order['payment_method'] in ('cod', 'free'):
        return True
    if order['payment_method'] == DEMO_METHOD:
        return order['payment_status'] == 'simulated'
    return order['paid_at'] is not None


def _allowed_actions(order, role):
    actions = []
    for action, rule in ORDER_ACTIONS.items():
        if role not in rule['from'].get(order['status'], ()):
            continue
        if action in PAYMENT_REQUIRED_FOR and not _payment_settled(order):
            continue
        actions.append(action)
    return actions


def _payment_status_after_close(payment_status):
    """Payment status when an order is rejected/cancelled. Money taken online is never 'forgotten'."""
    return {'cod_pending': 'not_charged', 'awaiting_payment': 'not_charged', 'failed': 'not_charged',
            'paid': 'refund_pending', 'authorized': 'refund_pending'}.get(payment_status, payment_status)


def _validate_shipment(form):
    """Optional courier details typed by the seller. Returns (errors, values)."""
    courier = form.get('courier_name', '').strip()
    number = form.get('tracking_number', '').strip()
    link = form.get('tracking_url', '').strip()
    errors = []
    if len(courier) > 100:
        errors.append("Courier name must be 100 characters or fewer.")
    if number and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 ./-]{0,99}', number):
        errors.append("Tracking number can only contain letters, digits, spaces, dots, dashes and slashes.")
    if link:
        parsed = urlparse(link)
        if len(link) > 500 or parsed.scheme not in ('http', 'https') or not parsed.netloc or ' ' in link:
            errors.append("Tracking link must be a full web address starting with https:// or http://.")
    return errors, {'courier_name': courier or None, 'tracking_number': number or None, 'tracking_url': link or None}


# ---------------------------------------------------------------- payments
def _lock_order(cur, where_sql, params):
    cur.execute(
        "SELECT id, order_number, buyer_id, seller_id, status, product_id, payment_method, "
        "payment_status, provider_order_id, total_amount, paid_at "
        f"FROM diy_orders WHERE {where_sql} FOR UPDATE", params)
    r = cur.fetchone()
    if r is None:
        return None
    keys = ('id', 'order_number', 'buyer_id', 'seller_id', 'status', 'product_id', 'payment_method',
            'payment_status', 'provider_order_id', 'total_amount', 'paid_at')
    order = dict(zip(keys, r))
    order['total_amount'] = to_money(order['total_amount'])
    return order


def _apply_capture(cur, order, payment_id):
    """Record a verified Razorpay capture. Idempotent: repeats change nothing.

    Returns 'paid' (order moves to placed), 'late' (order was already closed, so
    the money must be refunded) or 'noop'.
    """
    if order['status'] == 'pending_payment':
        cur.execute(
            "UPDATE diy_orders SET status = 'placed', payment_status = 'paid', provider_payment_id = %s, "
            "paid_at = CURRENT_TIMESTAMP WHERE id = %s AND status = 'pending_payment'",
            (payment_id, order['id']))
        return 'paid' if cur.rowcount == 1 else 'noop'
    if order['status'] in ('cancelled', 'rejected') and order['paid_at'] is None:
        cur.execute(
            "UPDATE diy_orders SET payment_status = 'refund_pending', provider_payment_id = %s, "
            "paid_at = CURRENT_TIMESTAMP WHERE id = %s AND paid_at IS NULL",
            (payment_id, order['id']))
        return 'late' if cur.rowcount == 1 else 'noop'
    return 'noop'


def _apply_gateway_state(cur, order, state, payment_id):
    if state == 'captured':
        return _apply_capture(cur, order, payment_id)
    if state in ('authorized', 'failed') and order['status'] == 'pending_payment' \
            and order['payment_status'] in ('awaiting_payment', 'failed', 'authorized'):
        cur.execute("UPDATE diy_orders SET payment_status = %s WHERE id = %s AND status = 'pending_payment'",
                    (state, order['id']))
    return state


def _close_unpaid_order(order_number, payment_status_if_closed, buyer_id=None):
    """Cancel an online order that never got paid and release the product.

    Asks Razorpay first, so a payment that did go through is recorded instead of
    lost. Returns 'closed', 'paid', 'authorized', 'unknown' (Razorpay unreachable:
    left as is) or 'noop'.
    """
    conn = mysql.connection
    cur = conn.cursor()
    try:
        order = _lock_order(cur, "order_number = %s", (order_number,))
        if order is None or order['status'] != 'pending_payment' \
                or (buyer_id is not None and order['buyer_id'] != buyer_id):
            conn.rollback()
            return 'noop'
        if order['provider_order_id'] and diy_payments.is_configured():
            try:
                state, payment_id = diy_payments.captured_payment(order['provider_order_id'], order['total_amount'])
            except diy_payments.GatewayUnavailable:
                conn.rollback()
                return 'unknown'
            if state in ('captured', 'authorized'):
                result = _apply_gateway_state(cur, order, state, payment_id)
                conn.commit()
                return 'paid' if result == 'paid' else state
        cur.execute(
            "UPDATE diy_orders SET status = 'cancelled', payment_status = %s, closed_at = CURRENT_TIMESTAMP "
            "WHERE id = %s AND status = 'pending_payment'", (payment_status_if_closed, order['id']))
        if cur.rowcount == 1:
            cur.execute("UPDATE diy_products SET status = 'available' WHERE id = %s AND status = 'reserved'",
                        (order['product_id'],))
        conn.commit()
        return 'closed'
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def _diy_expire_stale_payments(product_id=None):
    """Release products held by online orders left unpaid for PAYMENT_WINDOW_MINUTES."""
    cur = mysql.connection.cursor()
    sql = f"SELECT order_number FROM diy_orders WHERE status = 'pending_payment' AND {STALE_PAYMENT_SQL}"
    params = ()
    if product_id is not None:
        sql += " AND product_id = %s"
        params = (product_id,)
    cur.execute(sql, params)
    stale = [r[0] for r in cur.fetchall()]
    cur.close()
    for order_number in stale:
        _close_unpaid_order(order_number, 'expired')


def _diy_require_buyer_order(order_number):
    """Load an order for its buyer, or 404 (same response for missing or someone else's)."""
    cur = mysql.connection.cursor()
    cur.execute(f"SELECT {ORDER_COLUMNS} {ORDER_JOINS} WHERE o.order_number = %s", (order_number,))
    row = cur.fetchone()
    cur.close()
    order = _order_from_row(row) if row else None
    if order is None or order['buyer_id'] != session['user_id']:
        abort(404)
    return order


@app.route('/diy-marketplace/orders/<order_number>/pay')
def diy_payment_page(order_number):
    """Razorpay hosted Checkout for an order awaiting online payment (buyer only)."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    order = _diy_require_buyer_order(order_number)
    if order['status'] != 'pending_payment' or not order['provider_order_id']:
        return redirect(url_for('diy_order_detail', order_number=order_number))
    return render_template(
        'diy_pay.html', order=order,
        available=diy_payments.is_configured(), reason=diy_payments.unavailable_reason(),
        key_id=diy_payments.key_id(), test_mode=diy_payments.is_test_mode(),
        amount_paise=diy_payments.to_paise(order['total_amount']), currency=diy_payments.CURRENCY,
        rzp_method=PAYMENT_METHODS.get(order['payment_method'], {}).get('rzp'),
        window_minutes=PAYMENT_WINDOW_MINUTES,
    )


@app.route('/diy-marketplace/orders/<order_number>/pay/verify', methods=['POST'])
def diy_payment_verify(order_number):
    """Checkout success handler. The browser's word is never enough: the signature is
    checked with the key secret AND Razorpay is asked directly whether the right
    amount was captured before the order is marked paid."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    rzp_order_id = request.form.get('razorpay_order_id', '')
    rzp_payment_id = request.form.get('razorpay_payment_id', '')
    signature = request.form.get('razorpay_signature', '')

    conn = mysql.connection
    cur = conn.cursor()
    try:
        order = _lock_order(cur, "order_number = %s", (order_number,))
        if order is None or order['buyer_id'] != session['user_id']:
            conn.rollback()
            abort(404)
        if order['payment_status'] == 'paid':
            conn.rollback()
            _diy_notice('paid', order_number)
            return redirect(url_for('diy_order_detail', order_number=order_number))
        if not order['provider_order_id'] or rzp_order_id != order['provider_order_id'] \
                or not diy_payments.verify_checkout_signature(rzp_order_id, rzp_payment_id, signature):
            conn.rollback()
            _diy_notice('error', order_number, message="We couldn't verify that payment, so the order "
                        "was not marked as paid. If money left your account, use “Check payment status”.")
            return redirect(url_for('diy_order_detail', order_number=order_number))
        try:
            state, payment_id = diy_payments.captured_payment(rzp_order_id, order['total_amount'])
        except diy_payments.GatewayUnavailable:
            conn.rollback()
            _diy_notice('error', order_number, message="Razorpay couldn't be reached to confirm the payment. "
                        "Use “Check payment status” in a moment.")
            return redirect(url_for('diy_order_detail', order_number=order_number))
        result = _apply_gateway_state(cur, order, state, payment_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()

    if result == 'paid':
        _diy_notice('paid', order_number)
    elif result == 'late':
        _diy_notice('error', order_number, message="Your payment arrived after this order had closed. "
                    "It is marked for a refund.")
    elif result == 'authorized':
        _diy_notice('error', order_number, message="Your payment is authorised but Razorpay hasn't captured it yet. "
                    "The order will move forward once it is captured.")
    else:
        _diy_notice('error', order_number, message="Razorpay hasn't confirmed this payment yet, so the order "
                    "isn't marked as paid. Use “Check payment status” in a moment.")
    return redirect(url_for('diy_order_detail', order_number=order_number))


@app.route('/diy-marketplace/orders/<order_number>/pay/refresh', methods=['POST'])
def diy_payment_refresh(order_number):
    """Ask Razorpay directly for this order's payment state (works without webhooks)."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = mysql.connection
    cur = conn.cursor()
    try:
        order = _lock_order(cur, "order_number = %s", (order_number,))
        if order is None or order['buyer_id'] != session['user_id']:
            conn.rollback()
            abort(404)
        if not order['provider_order_id'] or order['payment_status'] == 'paid':
            conn.rollback()
            return redirect(url_for('diy_order_detail', order_number=order_number))
        try:
            state, payment_id = diy_payments.captured_payment(order['provider_order_id'], order['total_amount'])
        except diy_payments.GatewayUnavailable as err:
            conn.rollback()
            _diy_notice('error', order_number, message=str(err))
            return redirect(url_for('diy_order_detail', order_number=order_number))
        result = _apply_gateway_state(cur, order, state, payment_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
    if result == 'paid':
        _diy_notice('paid', order_number)
    else:
        _diy_notice('info', order_number, message={
            'none': "No payment has been made for this order yet.",
            'failed': "The last payment attempt failed. You can try again.",
            'authorized': "Payment authorised; waiting for Razorpay to capture it.",
            'late': "Your payment arrived after this order had closed. It is marked for a refund.",
        }.get(result, "Payment status is unchanged."))
    return redirect(url_for('diy_order_detail', order_number=order_number))


@app.route('/diy-marketplace/orders/<order_number>/simulate', methods=['GET', 'POST'])
def diy_payment_simulation(order_number):
    """Demo Payment (simulation only), for presentations while no gateway is configured.

    No money moves and no provider is contacted. A simulated success records
    payment_status='simulated' -- never 'paid', never paid_at or a provider id --
    so it can't be mistaken for (or upgraded into) a verified payment. It only
    lets the demo order continue through the normal seller workflow.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    order = _diy_require_buyer_order(order_number)
    if order['payment_method'] != DEMO_METHOD or order['status'] != 'pending_payment':
        return redirect(url_for('diy_order_detail', order_number=order_number))
    if not diy_payments.simulation_enabled():
        return render_template(
            'diy_message.html', title="Demo payments are switched off",
            message="This site no longer offers simulated payments. Cancel this order from the order page "
                    "and choose another payment method."), 409

    if request.method == 'POST':
        outcome = request.form.get('outcome')
        if outcome not in ('success', 'failure'):
            abort(400)
        # "Pay Online" presentation flow: any non-empty payment reference is accepted.
        # It is only echoed back on the confirmation (there is no column for it and
        # nothing verifies it), so it is never evidence of a genuine payment.
        reference = request.form.get('payment_reference', '').strip()
        if outcome == 'success' and not 0 < len(reference) <= PAYMENT_REFERENCE_MAX:
            return render_template(
                'diy_simulate.html', order=order, simulated_failure=False, reference=reference,
                reference_error=("Enter a payment reference." if not reference else
                                 f"Payment reference must be {PAYMENT_REFERENCE_MAX} characters or fewer."),
            ), 400
        new_status, new_payment = ('placed', 'simulated') if outcome == 'success' else ('pending_payment', 'failed')
        conn = mysql.connection
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE diy_orders SET status = %s, payment_status = %s "
                "WHERE order_number = %s AND buyer_id = %s AND payment_method = %s "
                "AND status = 'pending_payment' AND payment_status IN ('awaiting_payment', 'failed')",
                (new_status, new_payment, order_number, session['user_id'], DEMO_METHOD))
            changed = cur.rowcount == 1
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
        if outcome == 'success' and changed:
            _diy_notice('simulated', order_number, reference=reference)
            return redirect(url_for('diy_order_detail', order_number=order_number))
        if outcome == 'failure' and changed:
            order = _diy_require_buyer_order(order_number)
            return render_template('diy_simulate.html', order=order, simulated_failure=True)
        return redirect(url_for('diy_order_detail', order_number=order_number))

    return render_template('diy_simulate.html', order=order, simulated_failure=False)


@app.route('/diy-marketplace/payments/razorpay/webhook', methods=['POST'])
def diy_razorpay_webhook():
    """Signed Razorpay events. Idempotent: redelivered events change nothing twice."""
    if not (diy_payments.is_configured() and diy_payments.webhook_secret()):
        return "webhook not configured", 503
    raw = request.get_data(as_text=True)
    if not diy_payments.verify_webhook(raw, request.headers.get('X-Razorpay-Signature', '')):
        return "invalid signature", 400
    try:
        event = json.loads(raw)
        entity = event['payload']['payment']['entity']
        name = event['event']
    except (ValueError, KeyError, TypeError):
        return "ignored", 200

    conn = mysql.connection
    cur = conn.cursor()
    try:
        order = _lock_order(cur, "provider_order_id = %s", (entity.get('order_id') or '',))
        if order is None:
            conn.rollback()
            return "ignored", 200
        right_amount = (entity.get('amount') == diy_payments.to_paise(order['total_amount'])
                        and entity.get('currency') == diy_payments.CURRENCY)
        if name in ('payment.captured', 'order.paid') and entity.get('status') == 'captured' and right_amount:
            _apply_capture(cur, order, entity.get('id'))
        elif name == 'payment.authorized' and right_amount:
            _apply_gateway_state(cur, order, 'authorized', entity.get('id'))
        elif name == 'payment.failed':
            _apply_gateway_state(cur, order, 'failed', None)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
    return "ok", 200


# ---------------------------------------------------------------- order pages
@app.route('/diy-marketplace/orders')
def diy_orders():
    """My Orders: purchases (as buyer) and incoming orders (as seller)."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    _diy_expire_stale_payments()
    view = 'sales' if request.args.get('view') == 'sales' else 'purchases'

    cur = mysql.connection.cursor()
    if view == 'sales':
        cur.execute(f"SELECT {ORDER_COLUMNS} {ORDER_JOINS} WHERE o.seller_id = %s AND {SELLER_VISIBLE_SQL} "
                    "ORDER BY o.created_at DESC, o.id DESC", (user_id,))
    else:
        cur.execute(f"SELECT {ORDER_COLUMNS} {ORDER_JOINS} WHERE o.buyer_id = %s "
                    "ORDER BY o.created_at DESC, o.id DESC", (user_id,))
    orders = [_order_from_row(r) for r in cur.fetchall()]
    cur.execute(f"SELECT COUNT(*) FROM diy_orders o WHERE o.seller_id = %s AND o.status = 'placed' "
                f"AND {SELLER_VISIBLE_SQL}", (user_id,))
    awaiting = cur.fetchone()[0]
    cur.close()

    return render_template('diy_orders.html', orders=orders, view=view, awaiting=awaiting)


ACTION_DONE_MESSAGES = {
    'confirm': "Order confirmed. The buyer can now see that it is confirmed.",
    'reject': "Order declined. The piece is back in the shop.",
    'ship': "Marked as shipped. The buyer can now see the shipment details.",
    'deliver': "Thanks for confirming you received it. The order is complete.",
    'cancel': "Order cancelled.",
}


@app.route('/diy-marketplace/orders/<order_number>')
def diy_order_detail(order_number):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute(f"SELECT {ORDER_COLUMNS} {ORDER_JOINS} WHERE o.order_number = %s", (order_number,))
    row = cur.fetchone()
    cur.close()

    order = _order_from_row(row) if row else None
    role = _order_role(order, session['user_id']) if order else None
    if role is None or (role == 'seller' and not _seller_can_see(order)):
        abort(404)  # same response whether the order is missing or someone else's

    # Messages come from a one-time session notice, and are shown only if they
    # still agree with the order's real status in the database.
    notice = _diy_pop_notice(order_number)
    message = None
    if notice:
        kind = notice['kind']
        if kind == 'placed' and role == 'buyer' and order['status'] == 'placed':
            message = ('success', 'placed')
        elif kind == 'updated' and ORDER_ACTIONS.get(notice.get('action'), {}).get('to') == order['status']:
            message = ('success', ACTION_DONE_MESSAGES[notice['action']])
        elif kind == 'paid' and role == 'buyer' and order['payment_status'] == 'paid':
            message = ('success', 'paid')
        elif kind == 'simulated' and role == 'buyer' and order['payment_status'] == 'simulated' \
                and order['status'] == 'placed':
            message = ('success', 'simulated', notice.get('reference'))
        elif kind in ('error', 'info'):
            message = (kind, notice.get('message', "That change isn't allowed for this order in its current state. "
                                                   "Nothing was changed."))

    # Once an order is closed without delivery, the seller no longer needs the
    # buyer's address and phone number.
    show_address = role == 'buyer' or order['status'] not in ('rejected', 'cancelled')

    return render_template(
        'diy_order_detail.html',
        order=order, role=role, actions=_allowed_actions(order, role), show_address=show_address,
        message=message, payment_settled=_payment_settled(order),
        online_available=diy_payments.is_configured(),
    )


@app.route('/diy-marketplace/orders/<order_number>/status', methods=['POST'])
def diy_order_update(order_number):
    """Move an order along: placed -> confirmed -> shipped -> delivered (or rejected/cancelled).

    Every change is checked against the order's current status in the database
    (locked for the transaction) and the logged-in user's role on that order.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    action = request.form.get('action', '')
    rule = ORDER_ACTIONS.get(action)

    shipment = {}
    if action == 'ship':
        ship_errors, shipment = _validate_shipment(request.form)
        if ship_errors:
            _diy_notice('error', order_number, message=' '.join(ship_errors) + " Nothing was changed.")
            return redirect(url_for('diy_order_detail', order_number=order_number))

    conn = mysql.connection
    cur = conn.cursor()
    try:
        order = _lock_order(cur, "order_number = %s", (order_number,))
        role = _order_role(order, user_id) if order else None
        if role is None or (role == 'seller' and not _seller_can_see(order)):
            conn.rollback()
            abort(404)

        allowed = rule is not None and role in rule['from'].get(order['status'], ())
        if allowed and action in PAYMENT_REQUIRED_FOR and not _payment_settled(order):
            allowed = False
        if not allowed:
            conn.rollback()
            _diy_notice('error', order_number)
            return redirect(url_for('diy_order_detail', order_number=order_number))

        if order['status'] == 'pending_payment':
            # Only the buyer can get here (cancel). Check Razorpay first so a
            # payment that did go through isn't lost.
            conn.rollback()
            result = _close_unpaid_order(order_number, 'not_charged', buyer_id=user_id)
            if result == 'closed':
                _diy_notice('updated', order_number, action='cancel')
            elif result == 'paid':
                _diy_notice('error', order_number, message="Your payment had already gone through, so the order "
                            "was placed instead of cancelled. You can still cancel it below.")
            else:
                _diy_notice('error', order_number, message="We couldn't confirm the payment state with Razorpay, "
                            "so the order wasn't cancelled. Please try again shortly.")
            return redirect(url_for('diy_order_detail', order_number=order_number))

        new_status = rule['to']
        payment_status = order['payment_status']
        if new_status in ('rejected', 'cancelled'):
            payment_status = _payment_status_after_close(payment_status)

        ts_col = STATUS_TIMESTAMP[new_status]
        cur.execute(
            f"UPDATE diy_orders SET status = %s, payment_status = %s, {ts_col} = CURRENT_TIMESTAMP, "
            "courier_name = COALESCE(%s, courier_name), tracking_number = COALESCE(%s, tracking_number), "
            "tracking_url = COALESCE(%s, tracking_url) "
            "WHERE id = %s AND status = %s",
            (new_status, payment_status, shipment.get('courier_name'), shipment.get('tracking_number'),
             shipment.get('tracking_url'), order['id'], order['status']))
        if cur.rowcount != 1:
            conn.rollback()
            _diy_notice('error', order_number)
            return redirect(url_for('diy_order_detail', order_number=order_number))

        if new_status in PRODUCT_STATUS_AFTER:
            cur.execute("UPDATE diy_products SET status = %s WHERE id = %s AND status = 'reserved'",
                        (PRODUCT_STATUS_AFTER[new_status], order['product_id']))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()

    _diy_notice('updated', order_number, action=action)
    return redirect(url_for('diy_order_detail', order_number=order_number))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', '')

        # Ordinary accounts only: the role is a profile label (any user can buy and
        # sell); administrators live in the separate admin app's `admins` table.
        if not name or len(name) > 100 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email) \
                or len(email) > 100 or len(password) < 6 or role not in ('buyer', 'seller'):
            return render_template('register.html', error="Please fill in every field: a name, a valid email "
                                   "and a password of at least 6 characters."), 400

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
                (name, email, hashed_password, role)
            )
            mysql.connection.commit()
        except MySQLdb.IntegrityError as err:
            mysql.connection.rollback()
            if err.args[0] != 1062:  # 1062 = duplicate email (UNIQUE KEY `email`)
                raise
            return render_template('register.html', error="An account with this email already exists. "
                                   "Please log in instead."), 409
        finally:
            cur.close()

        return '''
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            * { margin:0; padding:0; box-sizing:border-box; font-family:'Segoe UI', Arial, sans-serif; }
            body {
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                background: linear-gradient(135deg, #56ab2f, #a8e063);
            }
            .box {
                background: white;
                padding: 40px;
                border-radius: 16px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                text-align: center;
                max-width: 380px;
            }
            .icon { font-size: 50px; margin-bottom: 10px; }
            h2 { color: #2e7d32; margin-bottom: 10px; }
            p { color: #666; margin-bottom: 20px; font-size: 14px; }
            a {
                display: inline-block;
                padding: 12px 24px;
                background: linear-gradient(135deg, #56ab2f, #2e7d32);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                margin: 5px;
            }
        </style>
        </head>
        <body>
            <div class="box">
                <div class="icon">✅</div>
                <h2>Registration Successful!</h2>
                <p>Your Waste2Value account has been created.</p>
                <a href="/login">Login Now</a>
                <a href="/register">Register Another</a>
            </div>
        </body>
        </html>
        '''

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.check_password_hash(user[3], password):
            # Start a fresh session: nothing from a previously logged-in account
            # (CSRF token, pending messages) carries over to this one.
            session.clear()
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_role'] = user[4]
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid email or password")

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user_name=session['user_name'], user_role=session['user_role'])


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/listing/new', methods=['GET', 'POST'])
def new_listing():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    errors = []
    form = {
        'title': '',
        'category': '',
        'description': '',
        'price': '',
        'item_condition': 'Used',
    }

    if request.method == 'POST':
        form = {
            'title': request.form.get('title', '').strip(),
            'category': request.form.get('category', '').strip(),
            'description': request.form.get('description', '').strip(),
            'price': request.form.get('price', '').strip(),
            'item_condition': request.form.get('item_condition', '').strip(),
        }

        # Validate price on the server; HTML constraints can be bypassed.
        try:
            if not form['price']:
                raise InvalidOperation
            listing_price = Decimal(form['price'])
            if not listing_price.is_finite() or listing_price < 0:
                errors.append("Price cannot be negative.")
            elif listing_price > Decimal('99999999.99'):
                errors.append("Price is too high.")
            elif listing_price.as_tuple().exponent < -2:
                errors.append("Enter a price with no more than 2 decimal places.")
        except (InvalidOperation, ValueError):
            listing_price = None
            if not errors:
                errors.append("Enter a valid price, for example 250 or 249.99.")

        if not form['title']:
            errors.append("Please enter a listing title.")
        if not form['category']:
            errors.append("Please choose a category.")
        if not form['description']:
            errors.append("Please enter a description.")

        allowed_conditions = {'Used', 'Damaged'}
        if form['item_condition'] not in allowed_conditions:
            errors.append("Choose Used or Damaged for the item condition.")

        image_file = request.files.get('image')
        image_path = None
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            if not filename:
                errors.append("Please choose a valid image filename.")
            else:
                extension = os.path.splitext(filename)[1].lower()
                if extension not in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}:
                    errors.append("Upload an image in PNG, JPG, JPEG, GIF, or WEBP format.")
                else:
                    # Unique names prevent a later upload from replacing an existing image.
                    image_path = f"{uuid.uuid4().hex}{extension}"

        if not errors:
            if image_file and image_file.filename and image_path:
                image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_path))

            cur = mysql.connection.cursor()
            try:
                cur.execute(
                    "INSERT INTO listings "
                    "(seller_id, title, category, description, price, item_condition, image_path) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        session['user_id'],
                        form['title'],
                        form['category'],
                        form['description'],
                        listing_price,
                        form['item_condition'],
                        image_path,
                    )
                )
                mysql.connection.commit()
            except Exception:
                mysql.connection.rollback()
                if image_path:
                    saved_image = os.path.join(app.config['UPLOAD_FOLDER'], image_path)
                    if os.path.exists(saved_image):
                        os.remove(saved_image)
                raise
            finally:
                cur.close()

            return redirect(url_for('marketplace'))

        return render_template('new_listing.html', errors=errors, form=form), 400

    return render_template('new_listing.html', errors=errors, form=form)


@app.route('/marketplace')
def marketplace():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    search_query = request.args.get('search', '')
    selected_category = request.args.get('category', '')

    cur = mysql.connection.cursor()

    query = "SELECT * FROM listings WHERE status = 'available'"
    params = []

    if search_query:
        query += " AND title LIKE %s"
        params.append(f"%{search_query}%")

    if selected_category:
        query += " AND category = %s"
        params.append(selected_category)

    query += " ORDER BY created_at DESC"

    cur.execute(query, tuple(params))
    listings = cur.fetchall()
    cur.close()

    return render_template(
        'marketplace.html',
        listings=listings,
        search_query=search_query,
        selected_category=selected_category,
        user_name=session.get('user_name')
    )


@app.route('/listing/<int:listing_id>')
def listing_detail(listing_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM listings WHERE id = %s", (listing_id,))
    listing = cur.fetchone()
    cur.close()

    if not listing:
        return "Listing not found", 404

    offer_sent = request.args.get('offer_sent')

    return render_template(
        'listing_detail.html',
        listing=listing,
        session_user_id=session['user_id'],
        offer_sent=offer_sent
    )


@app.route('/offer/new/<int:listing_id>', methods=['POST'])
def new_offer(listing_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    buyer_id = session['user_id']
    offer_price = request.form.get('offer_price', '').strip()
    connection = mysql.connection
    cur = connection.cursor()
    try:
        # Lock the listing so creating an offer and accepting one cannot race.
        connection.begin()
        cur.execute(
            "SELECT seller_id, status FROM listings WHERE id = %s FOR UPDATE",
            (listing_id,),
        )
        listing = cur.fetchone()
        if not listing:
            abort(404)
        if listing[0] == buyer_id:
            abort(403)
        if str(listing[1] or '').lower() != 'available':
            connection.rollback()
            flash("This listing is no longer available for offers.", "warning")
            return redirect(url_for('listing_detail', listing_id=listing_id))

        cur.execute(
            "SELECT id FROM offers WHERE listing_id = %s AND status = 'accepted' FOR UPDATE",
            (listing_id,),
        )
        if cur.fetchall():
            connection.rollback()
            flash("An offer has already been accepted for this listing.", "warning")
            return redirect(url_for('listing_detail', listing_id=listing_id))

        cur.execute(
            "INSERT INTO offers (listing_id, buyer_id, offer_price) VALUES (%s, %s, %s)",
            (listing_id, buyer_id, offer_price),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cur.close()

    return redirect(url_for('listing_detail', listing_id=listing_id, offer_sent=1))


def _pickup_date_info(value, today=None):
    """Format a stored pickup date without changing even malformed legacy values."""
    if value is None or not str(value).strip():
        return {"display": None, "state": "missing", "warning": None}

    today = today or date.today()
    raw_value = str(value).strip()
    try:
        if isinstance(value, datetime):
            parsed = value.date()
        elif isinstance(value, date):
            parsed = value
        else:
            # DATE columns normally return a date object; accepting the first
            # ten characters also lets us display legacy datetime strings.
            parsed = date.fromisoformat(raw_value[:10])
    except (TypeError, ValueError):
        return {
            "display": raw_value,
            "state": "invalid",
            "warning": "The stored pickup date could not be read. Please verify this record.",
        }

    display = parsed.strftime("%d %b %Y")
    if parsed < today:
        return {
            "display": display,
            "state": "past",
            "warning": "This scheduled date has passed. Confirm whether the pickup occurred; the stored record was left unchanged.",
        }
    return {"display": display, "state": "upcoming", "warning": None}


def _build_offer_sections(rows, offer_type, today=None):
    """Split offer rows into one active arrangement, actionable pending, and history."""
    views = []
    for row in rows:
        (offer_id, listing_id, title, other_name, offer_price, status,
         listing_status, pickup_id, pickup_address, pickup_date,
         pickup_status, offer_created_at, pickup_created_at) = row
        date_info = _pickup_date_info(pickup_date, today=today)
        views.append({
            "offer_id": offer_id,
            "listing_id": listing_id,
            "title": title,
            "other_name": other_name,
            "offer_price": offer_price,
            "status": str(status or "pending").strip().lower(),
            "listing_status": str(listing_status or "").strip().lower(),
            "pickup_id": pickup_id,
            "pickup_address": pickup_address,
            "pickup_date_display": date_info["display"],
            "pickup_date_state": date_info["state"],
            "pickup_date_warning": date_info["warning"],
            "pickup_status": str(pickup_status or "").strip().lower(),
            "offer_created_at": offer_created_at,
            "pickup_created_at": pickup_created_at,
            "history_reason": None,
            "can_respond": False,
        })

    accepted_by_listing = {}
    for offer in views:
        if offer["status"] == "accepted":
            accepted_by_listing.setdefault(offer["listing_id"], []).append(offer)

    terminal_pickup_statuses = {
        "complete", "completed", "delivered", "cancelled", "canceled", "closed",
    }
    active_ids = set()
    for listing_id, accepted in accepted_by_listing.items():
        candidates = [offer for offer in accepted if (
            offer["pickup_status"] not in terminal_pickup_statuses
            and (offer["pickup_id"] or offer["listing_status"] == "available")
        )]
        if candidates:
            active = max(candidates, key=lambda offer: (
                bool(offer["pickup_id"]),
                {"upcoming": 3, "invalid": 2, "missing": 1, "past": 0}.get(
                    offer["pickup_date_state"], 0
                ),
                str(offer["pickup_created_at"] or offer["offer_created_at"] or ""),
                str(offer["offer_id"]),
            ))
            active_ids.add(active["offer_id"])

    active_arrangements = []
    pending_offers = []
    history_offers = []
    for offer in views:
        status = offer["status"]
        has_accepted = bool(accepted_by_listing.get(offer["listing_id"]))
        if status == "accepted" and offer["offer_id"] in active_ids:
            offer["is_active_arrangement"] = True
            active_arrangements.append(offer)
        elif status == "pending" and offer["listing_status"] == "available" and not has_accepted:
            offer["can_respond"] = offer_type == "received"
            pending_offers.append(offer)
        else:
            if status == "pending":
                if has_accepted:
                    offer["history_reason"] = "Not actionable because an offer is already accepted for this listing."
                else:
                    offer["history_reason"] = "Not actionable because this listing is no longer available."
            elif status == "accepted":
                if offer["offer_id"] in active_ids:
                    offer["history_reason"] = "Another accepted offer is shown as the active arrangement."
                elif offer["pickup_date_state"] == "past":
                    offer["history_reason"] = "The scheduled pickup date has passed; verify the outcome."
                elif offer["pickup_status"] in terminal_pickup_statuses:
                    offer["history_reason"] = f"Pickup status: {offer['pickup_status']}."
                else:
                    offer["history_reason"] = "This accepted offer is no longer the active arrangement."
            elif status == "rejected":
                offer["history_reason"] = "Offer declined."
            else:
                offer["history_reason"] = f"Stored offer status: {status or 'unknown'}."
            history_offers.append(offer)

    return {
        "active_arrangements": active_arrangements,
        "pending_offers": pending_offers,
        "history_offers": history_offers,
    }


@app.route('/offers')
def offers():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    offer_type = request.args.get('type', 'received')
    if offer_type not in {'received', 'sent'}:
        offer_type = 'received'
    user_id = session['user_id']

    cur = mysql.connection.cursor()
    latest_pickup_join = """
        LEFT JOIN pickups ON pickups.id = (
            SELECT latest.id FROM pickups AS latest
            WHERE latest.offer_id = offers.id
            ORDER BY latest.created_at DESC, latest.id DESC
            LIMIT 1
        )
    """
    columns = """
        SELECT offers.id, offers.listing_id, listings.title, users.name,
               offers.offer_price, offers.status, listings.status,
               pickups.id, pickups.address, CAST(pickups.pickup_date AS CHAR), pickups.status,
               offers.created_at, pickups.created_at
        FROM offers
        JOIN listings ON offers.listing_id = listings.id
    """
    try:
        if offer_type == 'received':
            cur.execute(columns
                        + " JOIN users ON offers.buyer_id = users.id "
                        + latest_pickup_join
                        + " WHERE listings.seller_id = %s ORDER BY offers.created_at DESC, offers.id DESC",
                        (user_id,))
        else:
            cur.execute(columns
                        + " JOIN users ON listings.seller_id = users.id "
                        + latest_pickup_join
                        + " WHERE offers.buyer_id = %s ORDER BY offers.created_at DESC, offers.id DESC",
                        (user_id,))
        rows = cur.fetchall()
    finally:
        cur.close()

    sections = _build_offer_sections(rows, offer_type)
    return render_template('offers.html', offer_type=offer_type, **sections)


@app.route('/offer/respond/<int:offer_id>', methods=['POST'])
def offer_respond(offer_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if str(session.get('user_role', '')).lower() != 'seller':
        abort(403)
    action = request.form.get('action', '').strip().lower()
    if action not in {'accepted', 'rejected'}:
        abort(400)

    connection = mysql.connection
    cur = connection.cursor()
    try:
        # The listing row is the shared lock for offer submission and acceptance.
        cur.execute("SELECT listing_id FROM offers WHERE id = %s", (offer_id,))
        offer_ref = cur.fetchone()
        if not offer_ref:
            abort(404)
        listing_id = offer_ref[0]

        connection.begin()
        cur.execute("SELECT seller_id, status FROM listings WHERE id = %s FOR UPDATE", (listing_id,))
        listing = cur.fetchone()
        if not listing:
            abort(404)
        if listing[0] != session['user_id']:
            abort(403)
        if str(listing[1] or '').lower() != 'available':
            connection.rollback()
            flash("This listing is no longer available, so its offers cannot be changed.", "warning")
            return redirect(url_for('offers', type='received'))

        cur.execute(
            "SELECT buyer_id, status FROM offers WHERE id = %s AND listing_id = %s FOR UPDATE",
            (offer_id, listing_id),
        )
        offer = cur.fetchone()
        if not offer:
            abort(404)
        if offer[0] == session['user_id']:
            abort(403)
        if str(offer[1] or '').lower() != 'pending':
            connection.rollback()
            flash("Only pending offers can be changed.", "warning")
            return redirect(url_for('offers', type='received'))

        cur.execute(
            "SELECT id FROM offers WHERE listing_id = %s AND status = 'accepted' FOR UPDATE",
            (listing_id,),
        )
        accepted = cur.fetchall()
        if accepted:
            connection.rollback()
            flash("An offer is already accepted for this listing. Other pending offers are closed.", "warning")
            return redirect(url_for('offers', type='received'))

        cur.execute(
            "UPDATE offers SET status = %s WHERE id = %s AND listing_id = %s AND status = 'pending'",
            (action, offer_id, listing_id),
        )
        if cur.rowcount != 1:
            connection.rollback()
            flash("This offer changed before your response was saved. Refresh the page and try again.", "warning")
            return redirect(url_for('offers', type='received'))

        if action == 'accepted':
            # Keep every offer row, closing only pending competitors with the
            # project's existing 'rejected' status value.
            cur.execute(
                "UPDATE offers SET status = 'rejected' "
                "WHERE listing_id = %s AND id <> %s AND status = 'pending'",
                (listing_id, offer_id),
            )
            flash("Offer accepted. Other pending offers for this listing were moved to history.", "success")
        else:
            flash("Offer declined. It remains available in Offer History.", "success")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cur.close()

    return redirect(url_for('offers', type='received'))


@app.route('/pickup/schedule/<int:offer_id>', methods=['GET', 'POST'])
def schedule_pickup(offer_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if str(session.get('user_role', '')).lower() != 'seller':
        abort(403)

    connection = mysql.connection
    cur = connection.cursor()
    try:
        cur.execute("SELECT listing_id FROM offers WHERE id = %s", (offer_id,))
        offer_ref = cur.fetchone()
        if not offer_ref:
            abort(404)
        listing_id = offer_ref[0]

        connection.begin()
        cur.execute("SELECT seller_id, status FROM listings WHERE id = %s FOR UPDATE", (listing_id,))
        listing = cur.fetchone()
        if not listing:
            abort(404)
        if listing[0] != session['user_id']:
            abort(403)
        if str(listing[1] or '').lower() != 'available':
            connection.rollback()
            flash("Pickup cannot be scheduled because this listing is no longer available.", "warning")
            return redirect(url_for('offers', type='received'))

        cur.execute(
            "SELECT buyer_id, status FROM offers WHERE id = %s AND listing_id = %s FOR UPDATE",
            (offer_id, listing_id),
        )
        offer = cur.fetchone()
        if not offer:
            abort(404)
        if offer[0] == session['user_id']:
            abort(403)
        if str(offer[1] or '').lower() != 'accepted':
            connection.rollback()
            flash("Only an accepted offer can have a pickup scheduled.", "warning")
            return redirect(url_for('offers', type='received'))

        cur.execute(
            "SELECT id FROM offers WHERE listing_id = %s AND status = 'accepted' FOR UPDATE",
            (listing_id,),
        )
        accepted_ids = [row[0] for row in cur.fetchall()]
        if any(accepted_id != offer_id for accepted_id in accepted_ids):
            connection.rollback()
            flash("More than one accepted offer exists for this listing. Review the offer history before scheduling.", "warning")
            return redirect(url_for('offers', type='received'))

        cur.execute(
            "SELECT id FROM pickups WHERE offer_id = %s ORDER BY created_at DESC, id DESC LIMIT 1 FOR UPDATE",
            (offer_id,),
        )
        if cur.fetchone():
            connection.rollback()
            flash("A pickup is already recorded for this offer. Its details are shown in the active arrangement.", "info")
            return redirect(url_for('offers', type='received'))

        errors = []
        form = {"address": "", "pickup_date": ""}
        if request.method == 'POST':
            form = {
                "address": request.form.get('address', '').strip(),
                "pickup_date": request.form.get('pickup_date', '').strip(),
            }
            pickup_date = None
            if not form["address"]:
                errors.append("Enter a pickup address.")
            elif len(form["address"]) > 255:
                errors.append("The pickup address must be 255 characters or fewer.")

            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", form["pickup_date"]):
                    raise ValueError
                pickup_date = date.fromisoformat(form["pickup_date"])
                if pickup_date < date.today():
                    errors.append("Choose today or a future pickup date.")
            except ValueError:
                errors.append("Enter a valid pickup date.")

            if errors:
                connection.rollback()
                return render_template(
                    'schedule_pickup.html', offer_id=offer_id, errors=errors,
                    form=form, min_pickup_date=date.today().isoformat(),
                ), 400

            cur.execute(
                "INSERT INTO pickups (offer_id, address, pickup_date) VALUES (%s, %s, %s)",
                (offer_id, form["address"], pickup_date),
            )
            connection.commit()
            flash("Pickup scheduled successfully.", "success")
            return redirect(url_for('offers', type='received'))

        connection.rollback()
        return render_template(
            'schedule_pickup.html', offer_id=offer_id, errors=errors,
            form=form, min_pickup_date=date.today().isoformat(),
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        cur.close()


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form.get('password')

        if password:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            cur.execute(
                "UPDATE users SET name=%s, email=%s, password_hash=%s WHERE id=%s",
                (name, email, hashed_password, user_id)
            )
        else:
            cur.execute(
                "UPDATE users SET name=%s, email=%s WHERE id=%s",
                (name, email, user_id)
            )
        mysql.connection.commit()

        # Update session so navbar/dashboard reflect the new name
        session['user_name'] = name

        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        return render_template('profile.html', user=user, updated=True)

    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    return render_template('profile.html', user=user, updated=False)


@app.route('/my-listings')
def my_listings():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM listings WHERE seller_id = %s ORDER BY created_at DESC", (session['user_id'],))
    listings = cur.fetchall()
    cur.close()

    return render_template('my_listings.html', listings=listings)


@app.route('/listing/delete/<int:listing_id>', methods=['POST'])
def delete_listing(listing_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # Listings that already have offers can't be deleted (offers reference them)
    cur.execute("""
        SELECT COUNT(*) FROM offers o
        JOIN listings l ON o.listing_id = l.id
        WHERE l.id = %s AND l.seller_id = %s
    """, (listing_id, session['user_id']))
    if cur.fetchone()[0] > 0:
        cur.execute("SELECT * FROM listings WHERE seller_id = %s ORDER BY created_at DESC", (session['user_id'],))
        listings = cur.fetchall()
        cur.close()
        return render_template(
            'my_listings.html',
            listings=listings,
            error="This listing cannot be deleted because it has existing offers."
        )

    # Only allow deleting your own listing
    cur.execute("DELETE FROM listings WHERE id = %s AND seller_id = %s", (listing_id, session['user_id']))
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('my_listings'))


if __name__ == '__main__':
    app.run(debug=True)
