"""
Waste2Value - Module 4: Admin Dashboard.

A standalone Flask application (port 5001) that reads the Waste2Value
application data (users, listings, offers, pickups) and manages the
Module-4-owned entities (admins, recyclers, complaints).
"""
import os
import re
import secrets
from functools import wraps

import bcrypt
import click
import mysql.connector
from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   send_from_directory, session, url_for)
from werkzeug.security import safe_join

import db
from config import load_config

app = Flask(__name__)
app.config.update(load_config())
db.init_app(app)


# ======================================================================
# Constants
# ======================================================================

# Roles that exist in the main application's registration form.
ALLOWED_USER_ROLES = ("buyer", "seller")

# Listing statuses. 'available' is the application's own value (the only
# status the marketplace shows); the admin actions add 'removed'/'archived',
# which hide a listing without deleting it.
LISTING_AVAILABLE = "available"
LISTING_HIDDEN_STATUSES = ("removed", "archived")
LISTING_ACTIONS = {"remove": "removed", "archive": "archived", "restore": LISTING_AVAILABLE}

RECYCLER_PENDING, RECYCLER_VERIFIED, RECYCLER_REJECTED = "Pending", "Verified", "Rejected"
COMPLAINT_OPEN, COMPLAINT_RESOLVED, COMPLAINT_ARCHIVED = "Open", "Resolved", "Archived"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.@-]{3,50}$")
SEARCH_MAX_LEN = 100
PASSWORD_MIN_LEN = 8
PASSWORD_MAX_BYTES = 72  # bcrypt only uses the first 72 bytes


# ======================================================================
# Passwords
# ======================================================================

def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password, password_hash):
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# Compared against when a username does not exist, so a failed login takes the
# same time whether or not the admin account exists.
_DUMMY_HASH = hash_password(secrets.token_hex(16))


def password_error(password):
    if len(password) < PASSWORD_MIN_LEN:
        return f"Password must be at least {PASSWORD_MIN_LEN} characters."
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        return f"Password must be at most {PASSWORD_MAX_BYTES} bytes."
    return None


# ======================================================================
# CSRF protection, cache headers, template helpers
# ======================================================================

def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def csrf_protect():
    if request.method != "POST":
        return None
    expected = session.get("_csrf_token")
    sent = request.form.get("csrf_token", "")
    if not expected or not secrets.compare_digest(expected, sent):
        flash("Your form session expired. Please try again.", "error")
        return redirect(url_for("dashboard") if session.get("admin_id") else url_for("login"))
    return None


@app.after_request
def no_store(response):
    # Admin pages must not be served from the browser cache after logout.
    if request.endpoint != "static":
        response.headers["Cache-Control"] = "no-store"
    return response


@app.template_filter("datetime")
def format_datetime(value, fmt="%d %b %Y, %H:%M"):
    if not value:
        return "—"
    if isinstance(value, str):
        return value
    return value.strftime(fmt)


@app.template_filter("money")
def format_money(value):
    if value is None:
        return "—"
    return f"₹{value:,.2f}"


def search_term():
    return request.args.get("q", "").strip()[:SEARCH_MAX_LEN]


# ======================================================================
# Authentication / authorization
# ======================================================================

def safe_next_url(target):
    """Only allow redirects to a local path (prevents open redirects)."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return None


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        admin_id = session.get("admin_id")
        if admin_id is None:
            flash("Please log in to access the admin dashboard.", "error")
            if request.method == "GET":
                return redirect(url_for("login", next=request.full_path.rstrip("?")))
            return redirect(url_for("login"))

        admin = db.query_one("SELECT id, username FROM admins WHERE id = %s", (admin_id,))
        if admin is None:
            session.clear()
            flash("Your admin account is no longer available. Please log in again.", "error")
            return redirect(url_for("login"))

        g.admin = admin
        return view(*args, **kwargs)
    return wrapped


@app.route("/", methods=["GET", "POST"])
def login():
    if session.get("admin_id"):
        return redirect(url_for("dashboard"))

    next_url = safe_next_url(request.values.get("next"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Please enter both username and password.", "error")
            return render_template("login.html", username=username, next_url=next_url), 400

        admin = db.query_one(
            "SELECT id, username, password_hash FROM admins WHERE username = %s", (username,)
        )
        if admin is not None and check_password(password, admin["password_hash"]):
            session.clear()
            session.permanent = True
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            return redirect(next_url or url_for("dashboard"))

        if admin is None:
            check_password(password, _DUMMY_HASH)
        app.logger.warning("Failed admin login for %r from %s", username, request.remote_addr)
        flash("Invalid username or password.", "error")
        return render_template("login.html", username=username, next_url=next_url), 401

    return render_template("login.html", username="", next_url=next_url)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ======================================================================
# Dashboard
# ======================================================================

def optional_stats(sql):
    """
    Run an aggregate query and return its row as ints, or None when the table
    it needs does not exist in the connected database yet. The dashboard then
    shows "not available" instead of a made-up number.
    """
    try:
        row = db.query_one(sql)
    except mysql.connector.Error as err:
        if db.is_missing_schema_error(err):
            app.logger.warning("Dashboard statistic unavailable: %s", err)
            return None
        raise
    return {key: int(value or 0) for key, value in row.items()}


@app.route("/dashboard")
@admin_required
def dashboard():
    stats = {
        # Application data (Modules 1-3)
        "users": optional_stats(
            "SELECT COUNT(*) AS total, SUM(role = 'buyer') AS buyers, "
            "SUM(role = 'seller') AS sellers FROM users"
        ),
        "listings": optional_stats(
            "SELECT COUNT(*) AS total, SUM(status = 'available') AS available FROM listings"
        ),
        "offers": optional_stats(
            "SELECT COUNT(*) AS total, SUM(status = 'pending') AS pending, "
            "SUM(status = 'accepted') AS accepted FROM offers"
        ),
        "pickups": optional_stats(
            "SELECT COUNT(*) AS total, SUM(status = 'scheduled') AS scheduled FROM pickups"
        ),
        # Module 4 data
        "recyclers": optional_stats(
            "SELECT COUNT(*) AS total, SUM(status = 'Pending') AS pending FROM recyclers"
        ),
        "complaints": optional_stats(
            "SELECT COUNT(*) AS total, SUM(status = 'Open') AS open FROM complaints"
        ),
    }
    return render_template("dashboard.html", stats=stats)


# ======================================================================
# Users (application table, read + safe admin edits)
# ======================================================================

def validate_user_form(form, require_password, exclude_user_id=None):
    data = {
        "name": form.get("name", "").strip(),
        "email": form.get("email", "").strip(),
        "role": form.get("role", "").strip().lower(),
    }
    errors = {}

    if not data["name"]:
        errors["name"] = "Name is required."
    elif len(data["name"]) > 100:
        errors["name"] = "Name must be at most 100 characters."

    if not data["email"]:
        errors["email"] = "Email is required."
    elif len(data["email"]) > 100 or not EMAIL_RE.match(data["email"]):
        errors["email"] = "Enter a valid email address (max 100 characters)."

    if data["role"] not in ALLOWED_USER_ROLES:
        errors["role"] = "Role must be Buyer or Seller."

    password = ""
    if require_password:
        password = form.get("password", "")
        problem = password_error(password)
        if problem:
            errors["password"] = problem

    if "email" not in errors:
        existing = db.query_one("SELECT id FROM users WHERE email = %s", (data["email"],))
        if existing is not None and existing["id"] != exclude_user_id:
            errors["email"] = "A user with this email already exists."

    return data, password, errors


def get_user(user_id):
    return db.query_one(
        "SELECT id, name, email, role, created_at FROM users WHERE id = %s", (user_id,)
    )


@app.route("/users")
@admin_required
def users():
    q = search_term()
    sql = "SELECT id, name, email, role, created_at FROM users"
    params = ()
    if q:
        pattern = db.like_pattern(q)
        sql += " WHERE name LIKE %s OR email LIKE %s"
        params = (pattern, pattern)
    sql += " ORDER BY created_at DESC, id DESC"
    return render_template("users.html", users=db.query_all(sql, params), q=q)


@app.route("/add-user", methods=["GET", "POST"])
@admin_required
def add_user():
    if request.method == "POST":
        data, password, errors = validate_user_form(request.form, require_password=True)
        if errors:
            flash("Please correct the highlighted fields.", "error")
            return render_template("add_user.html", form=data, errors=errors, user=None), 400
        try:
            db.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
                (data["name"], data["email"], hash_password(password), data["role"]),
            )
        except mysql.connector.IntegrityError as err:
            if not db.is_duplicate_error(err):
                raise
            errors["email"] = "A user with this email already exists."
            flash("Please correct the highlighted fields.", "error")
            return render_template("add_user.html", form=data, errors=errors, user=None), 400

        flash(f"User '{data['name']}' was created.", "success")
        return redirect(url_for("users"))

    return render_template("add_user.html", form={"role": "buyer"}, errors={}, user=None)


@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = get_user(user_id)
    if user is None:
        flash(f"User #{user_id} was not found.", "error")
        return redirect(url_for("users"))

    if request.method == "POST":
        data, _, errors = validate_user_form(request.form, require_password=False,
                                             exclude_user_id=user_id)
        if errors:
            flash("Please correct the highlighted fields.", "error")
            return render_template("add_user.html", form=data, errors=errors, user=user), 400
        try:
            db.execute(
                "UPDATE users SET name = %s, email = %s, role = %s WHERE id = %s",
                (data["name"], data["email"], data["role"], user_id),
            )
        except mysql.connector.IntegrityError as err:
            if not db.is_duplicate_error(err):
                raise
            errors["email"] = "A user with this email already exists."
            flash("Please correct the highlighted fields.", "error")
            return render_template("add_user.html", form=data, errors=errors, user=user), 400

        flash(f"User #{user_id} was updated.", "success")
        return redirect(url_for("users"))

    return render_template("add_user.html", form=user, errors={}, user=user)


def count_or_zero(sql, params):
    """COUNT(*) helper that treats a not-yet-created table as having no rows."""
    try:
        row = db.query_one(sql, params)
    except mysql.connector.Error as err:
        if db.is_missing_schema_error(err):
            return 0
        raise
    return int(row["n"])


@app.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = get_user(user_id)
    if user is None:
        flash(f"User #{user_id} was not found.", "error")
        return redirect(url_for("users"))

    # Only users with no marketplace activity can be removed; anything else
    # would break listings/offers/complaints that reference them.
    related = {
        "listings": count_or_zero("SELECT COUNT(*) AS n FROM listings WHERE seller_id = %s", (user_id,)),
        "offers": count_or_zero("SELECT COUNT(*) AS n FROM offers WHERE buyer_id = %s", (user_id,)),
        "complaints": count_or_zero("SELECT COUNT(*) AS n FROM complaints WHERE user_id = %s", (user_id,)),
    }
    in_use = [f"{count} {name}" for name, count in related.items() if count]
    if in_use:
        flash(f"User '{user['name']}' cannot be deleted because they have "
              f"{', '.join(in_use)}. Their records must stay intact.", "error")
        return redirect(url_for("users"))

    try:
        db.execute("DELETE FROM users WHERE id = %s", (user_id,))
    except mysql.connector.IntegrityError as err:
        if not db.is_fk_error(err):
            raise
        flash(f"User '{user['name']}' is referenced by other records and cannot be deleted.", "error")
        return redirect(url_for("users"))

    flash(f"User '{user['name']}' was deleted.", "success")
    return redirect(url_for("users"))


# ======================================================================
# Listings (application table, read + status-only admin actions)
# ======================================================================

@app.route("/listings")
@admin_required
def listings():
    q = search_term()
    sql = (
        "SELECT l.id, l.title, l.category, l.price, l.item_condition, l.status, "
        "       l.created_at, l.seller_id, u.name AS seller_name "
        "FROM listings l LEFT JOIN users u ON u.id = l.seller_id"
    )
    params = ()
    if q:
        pattern = db.like_pattern(q)
        sql += (" WHERE l.title LIKE %s OR l.category LIKE %s OR l.status LIKE %s"
                " OR u.name LIKE %s")
        params = (pattern,) * 4
    sql += " ORDER BY l.created_at DESC, l.id DESC"
    return render_template("listings.html", listings=db.query_all(sql, params), q=q,
                           hidden_statuses=LISTING_HIDDEN_STATUSES)


@app.route("/listings/<int:listing_id>")
@admin_required
def view_listing(listing_id):
    listing = db.query_one(
        "SELECT l.*, u.name AS seller_name, u.email AS seller_email "
        "FROM listings l LEFT JOIN users u ON u.id = l.seller_id WHERE l.id = %s",
        (listing_id,),
    )
    if listing is None:
        flash(f"Listing #{listing_id} was not found.", "error")
        return redirect(url_for("listings"))

    try:
        offers = db.query_all(
            "SELECT o.id, o.offer_price, o.status, o.created_at, u.name AS buyer_name, "
            "       p.pickup_date, p.status AS pickup_status "
            "FROM offers o "
            "LEFT JOIN users u ON u.id = o.buyer_id "
            "LEFT JOIN pickups p ON p.offer_id = o.id "
            "WHERE o.listing_id = %s ORDER BY o.created_at DESC, o.id DESC",
            (listing_id,),
        )
    except mysql.connector.Error as err:
        if not db.is_missing_schema_error(err):
            raise
        offers = None

    image_path = listing["image_path"]
    image_url = url_for("listing_image", filename=image_path) if listing_image_file(image_path) else None

    return render_template("listing_view.html", listing=listing, offers=offers,
                           image_url=image_url, hidden_statuses=LISTING_HIDDEN_STATUSES)


# Module 2 accepts any uploaded file type, so only image types are ever served
# back (never e.g. .html or .svg, which could run script in the admin site).
LISTING_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def listing_image_file(filename):
    """Absolute path of an existing listing image in Module 2's uploads, or None."""
    if not filename or os.path.splitext(filename)[1].lower() not in LISTING_IMAGE_EXTENSIONS:
        return None
    path = safe_join(app.config["MAIN_UPLOAD_FOLDER"], filename)
    return path if path and os.path.isfile(path) else None


@app.route("/listing-images/<path:filename>")
@admin_required
def listing_image(filename):
    if listing_image_file(filename) is None:
        abort(404)
    response = send_from_directory(app.config["MAIN_UPLOAD_FOLDER"], filename)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.route("/listings/<int:listing_id>/<action>", methods=["POST"])
@admin_required
def listing_action(listing_id, action):
    new_status = LISTING_ACTIONS.get(action)
    if new_status is None:
        abort(404)

    listing = db.query_one("SELECT id, title, status FROM listings WHERE id = %s", (listing_id,))
    if listing is None:
        flash(f"Listing #{listing_id} was not found.", "error")
        return redirect(url_for("listings"))

    if request.form.get("return_to") == "view":
        back = url_for("view_listing", listing_id=listing_id)
    else:
        back = url_for("listings")

    # 'restore' only applies to hidden listings; remove/archive only to visible ones.
    is_hidden = listing["status"] in LISTING_HIDDEN_STATUSES
    if (action == "restore") != is_hidden:
        flash(f"Listing '{listing['title']}' is currently '{listing['status']}', "
              f"so it cannot be {new_status if action != 'restore' else 'restored'}.", "error")
        return redirect(back)

    # Status change only: the listing, its offers and pickups are never deleted.
    db.execute("UPDATE listings SET status = %s WHERE id = %s", (new_status, listing_id))
    flash(f"Listing '{listing['title']}' is now '{new_status}'.", "success")
    return redirect(back)


# ======================================================================
# Recyclers (Module 4 table)
# ======================================================================

def get_recycler(recycler_id):
    return db.query_one(
        "SELECT id, recycler_name, company, location, status FROM recyclers WHERE id = %s",
        (recycler_id,),
    )


@app.route("/recyclers")
@admin_required
def recyclers():
    q = search_term()
    sql = "SELECT id, recycler_name, company, location, status FROM recyclers"
    params = ()
    if q:
        pattern = db.like_pattern(q)
        sql += (" WHERE recycler_name LIKE %s OR company LIKE %s OR location LIKE %s"
                " OR status LIKE %s")
        params = (pattern,) * 4
    sql += " ORDER BY id DESC"
    return render_template("recyclers.html", recyclers=db.query_all(sql, params), q=q)


@app.route("/recyclers/add", methods=["GET", "POST"])
@admin_required
def add_recycler():
    if request.method == "POST":
        data = {
            "recycler_name": request.form.get("recycler_name", "").strip(),
            "company": request.form.get("company", "").strip(),
            "location": request.form.get("location", "").strip(),
        }
        errors = {}
        if not data["recycler_name"]:
            errors["recycler_name"] = "Recycler name is required."
        elif len(data["recycler_name"]) > 100:
            errors["recycler_name"] = "Recycler name must be at most 100 characters."
        if len(data["company"]) > 150:
            errors["company"] = "Company must be at most 150 characters."
        if len(data["location"]) > 100:
            errors["location"] = "Location must be at most 100 characters."

        if errors:
            flash("Please correct the highlighted fields.", "error")
            return render_template("add_recycler.html", form=data, errors=errors), 400

        db.execute(
            "INSERT INTO recyclers (recycler_name, company, location, status) "
            "VALUES (%s, %s, %s, %s)",
            (data["recycler_name"], data["company"] or None, data["location"] or None,
             RECYCLER_PENDING),
        )
        flash(f"Recycler '{data['recycler_name']}' was added and is pending approval.", "success")
        return redirect(url_for("recyclers"))

    return render_template("add_recycler.html", form={}, errors={})


@app.route("/recyclers/<int:recycler_id>")
@admin_required
def view_recycler(recycler_id):
    recycler = get_recycler(recycler_id)
    if recycler is None:
        flash(f"Recycler #{recycler_id} was not found.", "error")
        return redirect(url_for("recyclers"))
    return render_template("recycler_view.html", recycler=recycler)


def set_recycler_status(recycler_id, new_status, verb):
    recycler = get_recycler(recycler_id)
    if recycler is None:
        flash(f"Recycler #{recycler_id} was not found.", "error")
    elif recycler["status"] == new_status:
        flash(f"Recycler '{recycler['recycler_name']}' is already {new_status.lower()}.", "info")
    else:
        db.execute("UPDATE recyclers SET status = %s WHERE id = %s", (new_status, recycler_id))
        flash(f"Recycler '{recycler['recycler_name']}' was {verb}.", "success")
    return redirect(url_for("recyclers"))


@app.route("/recyclers/<int:recycler_id>/approve", methods=["POST"])
@admin_required
def approve_recycler(recycler_id):
    return set_recycler_status(recycler_id, RECYCLER_VERIFIED, "approved")


@app.route("/recyclers/<int:recycler_id>/reject", methods=["POST"])
@admin_required
def reject_recycler(recycler_id):
    return set_recycler_status(recycler_id, RECYCLER_REJECTED, "rejected")


@app.route("/recyclers/<int:recycler_id>/remove", methods=["POST"])
@admin_required
def remove_recycler(recycler_id):
    # Recyclers are owned by Module 4 and nothing references them, so a
    # physical delete is safe here.
    recycler = get_recycler(recycler_id)
    if recycler is None:
        flash(f"Recycler #{recycler_id} was not found.", "error")
    else:
        db.execute("DELETE FROM recyclers WHERE id = %s", (recycler_id,))
        flash(f"Recycler '{recycler['recycler_name']}' was removed.", "success")
    return redirect(url_for("recyclers"))


# ======================================================================
# Complaints (Module 4 table, linked to users.id)
# ======================================================================

COMPLAINT_SELECT = (
    "SELECT c.id, c.user_id, c.subject, c.description, c.status, c.created_at, "
    "       u.name AS user_name, u.email AS user_email, u.role AS user_role "
    "FROM complaints c LEFT JOIN users u ON u.id = c.user_id"
)


@app.route("/complaints")
@admin_required
def complaints():
    q = search_term()
    sql = COMPLAINT_SELECT
    params = ()
    if q:
        pattern = db.like_pattern(q)
        sql += (" WHERE c.subject LIKE %s OR c.description LIKE %s OR c.status LIKE %s"
                " OR u.name LIKE %s OR u.email LIKE %s")
        params = (pattern,) * 5
    sql += " ORDER BY c.created_at DESC, c.id DESC"
    return render_template("complaints.html", complaints=db.query_all(sql, params), q=q)


@app.route("/complaints/<int:complaint_id>")
@admin_required
def view_complaint(complaint_id):
    complaint = db.query_one(COMPLAINT_SELECT + " WHERE c.id = %s", (complaint_id,))
    if complaint is None:
        flash(f"Complaint #{complaint_id} was not found.", "error")
        return redirect(url_for("complaints"))
    return render_template("complaint_view.html", complaint=complaint)


def set_complaint_status(complaint_id, new_status, allowed_from, verb):
    complaint = db.query_one("SELECT id, subject, status FROM complaints WHERE id = %s",
                             (complaint_id,))
    if complaint is None:
        flash(f"Complaint #{complaint_id} was not found.", "error")
    elif complaint["status"] not in allowed_from:
        flash(f"Complaint #{complaint_id} is '{complaint['status']}' and cannot be {verb}.", "error")
    else:
        db.execute("UPDATE complaints SET status = %s WHERE id = %s", (new_status, complaint_id))
        flash(f"Complaint #{complaint_id} was {verb}.", "success")
    if request.form.get("return_to") == "view":
        return redirect(url_for("view_complaint", complaint_id=complaint_id))
    return redirect(url_for("complaints"))


@app.route("/complaints/<int:complaint_id>/resolve", methods=["POST"])
@admin_required
def resolve_complaint(complaint_id):
    return set_complaint_status(complaint_id, COMPLAINT_RESOLVED, (COMPLAINT_OPEN,), "resolved")


@app.route("/complaints/<int:complaint_id>/archive", methods=["POST"])
@admin_required
def archive_complaint(complaint_id):
    return set_complaint_status(complaint_id, COMPLAINT_ARCHIVED,
                                (COMPLAINT_OPEN, COMPLAINT_RESOLVED), "archived")


# ======================================================================
# Diagnostics
# ======================================================================

@app.route("/db-test")
@admin_required
def db_test():
    report = db.check_schema()
    ok = all(t["exists"] and not t["missing_columns"] for t in report.values())
    return {"connected": True, "database": app.config["DB_NAME"], "schema_ok": ok, "tables": report}


# ======================================================================
# Error handling
# ======================================================================

@app.errorhandler(mysql.connector.Error)
def handle_db_error(err):
    app.logger.exception("Database error: %s", err)
    if db.is_missing_schema_error(err):
        message = ("A required database table or column is missing. Make sure Module 4 is "
                   "connected to the Waste2Value application database and that "
                   "database.sql has been applied.")
    else:
        message = ("The database is currently unavailable or rejected the request. "
                   "Please check the database configuration and try again.")
    return render_template("error.html", title="Database error", message=message), 500


@app.errorhandler(404)
def not_found(err):
    return render_template("error.html", title="Page not found",
                           message="The page you requested does not exist."), 404


@app.errorhandler(405)
def method_not_allowed(err):
    return render_template("error.html", title="Action not allowed",
                           message="This action cannot be performed this way."), 405


# ======================================================================
# CLI: admin accounts (no public admin registration exists)
# ======================================================================

@app.cli.command("create-admin")
@click.option("--username", prompt=True, help="Admin username (3-50 characters).")
@click.password_option(help="Admin password (min 8 characters).")
def create_admin_command(username, password):
    """Create an Admin Dashboard account."""
    username = username.strip()
    if not USERNAME_RE.match(username):
        raise click.ClickException(
            "Username must be 3-50 characters: letters, digits, '.', '_', '-' or '@'.")
    problem = password_error(password)
    if problem:
        raise click.ClickException(problem)
    try:
        db.execute("INSERT INTO admins (username, password_hash) VALUES (%s, %s)",
                   (username, hash_password(password)))
    except mysql.connector.IntegrityError as err:
        if db.is_duplicate_error(err):
            raise click.ClickException(f"An admin named '{username}' already exists.")
        raise
    click.echo(f"Admin '{username}' created.")


@app.cli.command("check-schema")
def check_schema_command():
    """Report whether the connected database has every table/column Module 4 needs."""
    report = db.check_schema()
    for table, info in report.items():
        if not info["exists"]:
            status = "MISSING TABLE"
        elif info["missing_columns"]:
            status = "missing columns: " + ", ".join(info["missing_columns"])
        else:
            status = "ok"
        click.echo(f"{table:<12} {status}")


if __name__ == "__main__":
    app.run(host=app.config["ADMIN_HOST"], port=app.config["ADMIN_PORT"],
            debug=app.config["ADMIN_DEBUG"])
