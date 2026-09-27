import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename

from recycling_engine import CATEGORIES, analyze_image_opencv, get_diy_guide, youtube_search_url

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # needed for sessions

# Load DB settings from a .env file next to this app.py (if python-dotenv is installed)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except ImportError:
    pass

# Database config
app.config['MYSQL_HOST'] = os.environ.get('DB_HOST', 'localhost')
app.config['MYSQL_PORT'] = int(os.environ.get('DB_PORT', 3306))
app.config['MYSQL_USER'] = os.environ.get('DB_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('DB_PASSWORD', '')
app.config['MYSQL_DB'] = os.environ.get('DB_NAME', 'waste2value')

mysql = MySQL(app)
bcrypt = Bcrypt(app)

app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')


@app.route('/')
def home():
    return "Hello, Waste2Value!"


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            (name, email, hashed_password, role)
        )
        mysql.connection.commit()
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

    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        description = request.form['description']
        price = request.form['price']
        item_condition = request.form['item_condition']
        seller_id = session['user_id']

        image_file = request.files.get('image')
        image_path = None
        if image_file and image_file.filename != '':
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = filename

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO listings (seller_id, title, category, description, price, item_condition, image_path) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (seller_id, title, category, description, price, item_condition, image_path)
        )
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('marketplace'))

    return render_template('new_listing.html')


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

    offer_price = request.form['offer_price']
    buyer_id = session['user_id']

    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO offers (listing_id, buyer_id, offer_price) VALUES (%s, %s, %s)",
        (listing_id, buyer_id, offer_price)
    )
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('listing_detail', listing_id=listing_id, offer_sent=1))


@app.route('/offers')
def offers():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    offer_type = request.args.get('type', 'received')
    user_id = session['user_id']

    cur = mysql.connection.cursor()

    if offer_type == 'received':
        # Offers made on listings that THIS user is selling
        cur.execute("""
            SELECT listings.title, users.name, offers.offer_price, offers.status, offers.id,
                   pickups.id, pickups.pickup_date
            FROM offers
            JOIN listings ON offers.listing_id = listings.id
            JOIN users ON offers.buyer_id = users.id
            LEFT JOIN pickups ON pickups.offer_id = offers.id
            WHERE listings.seller_id = %s
            ORDER BY offers.created_at DESC
        """, (user_id,))
    else:
        # Offers THIS user has sent as a buyer
        cur.execute("""
            SELECT listings.title, users.name, offers.offer_price, offers.status, offers.id,
                   pickups.id, pickups.pickup_date
            FROM offers
            JOIN listings ON offers.listing_id = listings.id
            JOIN users ON listings.seller_id = users.id
            LEFT JOIN pickups ON pickups.offer_id = offers.id
            WHERE offers.buyer_id = %s
            ORDER BY offers.created_at DESC
        """, (user_id,))

    offers_list = cur.fetchall()
    cur.close()

    return render_template('offers.html', offers=offers_list, offer_type=offer_type)


@app.route('/offer/respond/<int:offer_id>', methods=['POST'])
def offer_respond(offer_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    action = request.form['action']  # 'accepted' or 'rejected'

    cur = mysql.connection.cursor()
    cur.execute("UPDATE offers SET status = %s WHERE id = %s", (action, offer_id))
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('offers', type='received'))


@app.route('/pickup/schedule/<int:offer_id>', methods=['GET', 'POST'])
def schedule_pickup(offer_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        address = request.form['address']
        pickup_date = request.form['pickup_date']

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO pickups (offer_id, address, pickup_date) VALUES (%s, %s, %s)",
            (offer_id, address, pickup_date)
        )
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('offers', type='received'))

    return render_template('schedule_pickup.html', offer_id=offer_id)


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


@app.route('/ai-assistant', methods=['GET'])
def ai_assistant():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('ai_assistant.html', categories=CATEGORIES, result=None, error=None)


@app.route('/ai-assistant/analyze', methods=['POST'])
def ai_assistant_analyze():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Priority for the decision engine:
    #   1. Manual category override (user picked from the dropdown)
    #   2. Teachable Machine result (client-side AI model, if configured)
    #   3. OpenCV heuristic analysis of the uploaded photo (server-side fallback)
    manual_material = request.form.get('manual_material') or None
    tm_material = request.form.get('tm_material') or None
    tm_confidence = request.form.get('tm_confidence') or None

    image_file = request.files.get('image')
    cv_result = None
    saved_image_path = None

    if image_file and image_file.filename != '':
        filename = secure_filename(image_file.filename)
        image_bytes = image_file.read()

        try:
            cv_result = analyze_image_opencv(image_bytes)
        except Exception:
            cv_result = None

        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(save_path, 'wb') as f:
            f.write(image_bytes)
        saved_image_path = filename

    if manual_material and manual_material in CATEGORIES:
        final_material = manual_material
        source = 'Manual selection'
        confidence = None
    elif tm_material and tm_material in CATEGORIES:
        final_material = tm_material
        source = 'Teachable Machine (AI model)'
        confidence = tm_confidence
    elif cv_result:
        final_material = cv_result['material']
        source = 'OpenCV heuristic analysis'
        confidence = cv_result['confidence']
    else:
        return render_template(
            'ai_assistant.html',
            categories=CATEGORIES,
            result=None,
            error="Please upload a photo or choose a category to analyze."
        )

    guide = get_diy_guide(final_material)
    ideas = []
    for idea in guide['ideas']:
        idea = dict(idea)
        idea['video_url'] = youtube_search_url(idea['video_query'])
        ideas.append(idea)

    result = {
        'material': final_material,
        'display_name': guide['display_name'],
        'icon': guide['icon'],
        'source': source,
        'confidence': confidence,
        'general_safety': guide['general_safety'],
        'ideas': ideas,
        'image_path': saved_image_path,
        'cv_scores': cv_result['scores'] if cv_result else None,
    }

    return render_template('ai_assistant.html', categories=CATEGORIES, result=result, error=None)


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
    # Only allow deleting your own listing
    cur.execute("DELETE FROM listings WHERE id = %s AND seller_id = %s", (listing_id, session['user_id']))
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('my_listings'))


if __name__ == '__main__':
    app.run(debug=True)