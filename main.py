from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    make_response
)
import mysql.connector
import numpy as np
import csv
from io import StringIO
from flask import Response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets
from datetime import datetime, timedelta
import random
from flask_mail import Mail, Message


app = Flask(
    __name__,
    template_folder="app/templates",
    static_folder="app/static"
)
import os
from dotenv import load_dotenv

load_dotenv()

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"
)

# =========================
# EMAIL / OTP CONFIGURATION
# =========================

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME")

mail = Mail(app)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False
)


# =========================
# SECURITY
# =========================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not session.get("admin_logged_in"):
            flash("Please login as admin first.", "error")
            return redirect(url_for("login"))

        response = make_response(f(*args, **kwargs))

        # Prevent browser from caching protected pages
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        return response

    return decorated_function


def main_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not session.get("admin_logged_in"):
            flash("Please login as admin first.", "error")
            return redirect(url_for("login"))

        if session.get("admin_role") != "main_admin":
            flash(
                "Access denied. Only Main Admin can access this page.",
                "error"
            )
            return redirect(url_for("admin"))

        response = make_response(f(*args, **kwargs))

        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        return response

    return decorated_function


def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not session.get("student_logged_in"):
            flash("Please login first.", "error")
            return redirect(url_for("student_login"))

        response = make_response(f(*args, **kwargs))

        # Prevent browser from caching protected pages
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        return response

    return decorated_function


# =========================
# MYSQL CONNECTION
# =========================

def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "college_management"),
        ssl_disabled=False
    )


# =========================
# MERGE SORT
# =========================

def merge_sort(data):

    if len(data) <= 1:
        return data

    middle = len(data) // 2

    left = merge_sort(data[:middle])
    right = merge_sort(data[middle:])

    return merge(left, right)


def merge(left, right):

    result = []

    i = 0
    j = 0

    while i < len(left) and j < len(right):

        # Higher registration count first
        if left[i][1] >= right[j][1]:

            result.append(left[i])
            i += 1

        else:

            result.append(right[j])
            j += 1

    while i < len(left):

        result.append(left[i])
        i += 1

    while j < len(right):

        result.append(right[j])
        j += 1

    return result 


# =========================
# HOME
# =========================

@app.route("/")
def home():

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        SELECT
            e.id,
            e.name,
            e.description,
            e.event_date,
            e.location,
            COUNT(r.id) AS registration_count
        FROM events e
        LEFT JOIN registrations r
            ON e.name = r.event
        GROUP BY
            e.id,
            e.name,
            e.description,
            e.event_date,
            e.location
        HAVING COUNT(r.id) > 0
        ORDER BY registration_count DESC, e.event_date ASC
        LIMIT 1
    """)

    trending_event = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "index.html",
        trending_event=trending_event
    )


# =========================
# EVENTS
# =========================

@app.route("/events")
def events():

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        SELECT e.id, e.name, e.description, e.event_date, e.location, a.username
        FROM events e
        LEFT JOIN admins a ON e.created_by = a.id
        ORDER BY e.event_date ASC
    """)

    events = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "events.html",
        events=events
    )


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    db = get_db_connection()
    cursor = db.cursor()

    # Get all events
    cursor.execute("SELECT * FROM events")
    events = cursor.fetchall()

    if request.method == "POST":

        name = request.form["name"]
        college_id = request.form["college_id"]
        email = request.form["email"]
        phone = request.form["phone"]
        event = request.form["event"]

        # Check duplicate registration
        cursor.execute("""
            SELECT * FROM registrations
            WHERE college_id = %s AND event = %s
        """, (college_id, event))

        existing = cursor.fetchone()

        if existing:

            cursor.close()
            db.close()

            flash("You are already registered for this event.", "error")

            return redirect(url_for("register"))

        # Insert new registration
        cursor.execute("""
            INSERT INTO registrations
            (name, college_id, email, phone, event)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            name,
            college_id,
            email,
            phone[:15],
            event
        ))

        db.commit()

        cursor.close()
        db.close()

        flash("Registration successful! <i class='fa-solid fa-calendar-check'></i>", "success")

        return redirect(url_for("register"))

    cursor.close()
    db.close()

    return render_template(
        "register.html",
        events=events
    )


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            SELECT id, username, password, role, status
            FROM admins
            WHERE username = %s
        """, (username,))

        admin_user = cursor.fetchone()

        cursor.close()
        db.close()

        if not admin_user:
            flash(
                "Invalid username or password.",
                "error"
            )
            return redirect(url_for("login"))

        admin_id = admin_user[0]
        admin_username = admin_user[1]
        stored_password = admin_user[2]
        admin_role = admin_user[3]
        admin_status = admin_user[4]

        if not check_password_hash(stored_password, password):
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))

        # Block inactive organizers
        if admin_role == "organizer" and admin_status == "inactive":
            flash(
                "Your organizer account is inactive. Please contact the Main Admin.",
                "error"
            )
            return redirect(url_for("login"))

        # Clear any previous admin session
        session.pop("admin_logged_in", None)
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        session.pop("admin_role", None)

        # Create new admin session
        session["admin_logged_in"] = True
        session["admin_id"] = admin_id
        session["admin_username"] = admin_username
        session["admin_role"] = admin_role

        if admin_role == "main_admin":
            flash(
                "Login successful! Welcome Main Admin 👋",
                "success"
            )
        else:
            flash(
                "Login successful! Welcome Organizer 👋",
                "success"
            )

        return redirect(url_for("admin"))

    return render_template("login.html")


# =========================
# ADMIN / ORGANIZER FORGOT PASSWORD
# =========================

@app.route("/admin-forgot-password", methods=["GET", "POST"])
def admin_forgot_password():

    if request.method == "POST":

        username = request.form["username"].strip()
        email = request.form["email"].strip()

        if not username or not email:
            flash("Please enter username and email.", "error")
            return redirect(url_for("admin_forgot_password"))

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            SELECT id, username, email
            FROM admins
            WHERE username = %s
            AND email = %s
        """, (username, email))

        admin = cursor.fetchone()

        if not admin:
            cursor.close()
            db.close()

            flash(
                "Username and email do not match our records.",
                "error"
            )

            return redirect(url_for("admin_forgot_password"))

        admin_id = admin[0]
        admin_email = admin[2]

        # Generate a secure 6-digit OTP
        otp = f"{secrets.randbelow(1000000):06d}"

        expires_at = datetime.now() + timedelta(minutes=10)

        # Invalidate previous OTPs
        cursor.execute("""
            DELETE FROM admin_password_otps
            WHERE admin_id = %s
            AND used = FALSE
        """, (admin_id,))

        # Store new OTP
        cursor.execute("""
            INSERT INTO admin_password_otps
            (admin_id, otp, expires_at)
            VALUES (%s, %s, %s)
        """, (
            admin_id,
            otp,
            expires_at
        ))

        db.commit()

        cursor.close()
        db.close()

        # Send OTP by email
        try:

            msg = Message(
                subject="RAIT Events Password Reset OTP",
                sender=app.config["MAIL_USERNAME"],
                recipients=[admin_email]
            )

            msg.body = f"""
Hello {username},

Your RAIT Events password reset OTP is:

{otp}

This OTP is valid for 10 minutes.

If you did not request a password reset, please ignore this email.

Regards,
RAIT Events Team
"""

            mail.send(msg)

        except Exception as e:

            # Remove OTP if email could not be sent
            db = get_db_connection()
            cursor = db.cursor()

            cursor.execute("""
                DELETE FROM admin_password_otps
                WHERE admin_id = %s
                AND otp = %s
            """, (admin_id, otp))

            db.commit()

            cursor.close()
            db.close()

            print("Email sending error:", e)

            flash(
                "Unable to send OTP email. Please try again later.",
                "error"
            )

            return redirect(url_for("admin_forgot_password"))

        # Store pending reset account in session
        session["admin_reset_id"] = admin_id

        flash(
            "OTP sent successfully to your registered email. <i class='fa-solid fa-envelope'></i>",
            "success"
        )

        return redirect(url_for("admin_verify_otp"))

    return render_template("admin_forgot_password.html")

@app.route("/admin-verify-otp", methods=["GET", "POST"])
def admin_verify_otp():

    admin_id = session.get("admin_reset_id")

    if not admin_id:
        flash(
            "Please start the password reset process again.",
            "error"
        )
        return redirect(url_for("admin_forgot_password"))

    if request.method == "POST":

        otp = request.form["otp"].strip()

        if not otp.isdigit() or len(otp) != 6:
            flash("Please enter a valid 6-digit OTP.", "error")
            return redirect(url_for("admin_verify_otp"))

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            SELECT id, otp, expires_at
            FROM admin_password_otps
            WHERE admin_id = %s
            AND used = FALSE
            ORDER BY created_at DESC
            LIMIT 1
        """, (admin_id,))

        otp_record = cursor.fetchone()

        if not otp_record:
            cursor.close()
            db.close()

            flash(
                "OTP not found or already used. Please request a new OTP.",
                "error"
            )

            return redirect(url_for("admin_forgot_password"))

        otp_id = otp_record[0]
        stored_otp = otp_record[1]
        expires_at = otp_record[2]

        if datetime.now() > expires_at:

            cursor.execute("""
                UPDATE admin_password_otps
                SET used = TRUE
                WHERE id = %s
            """, (otp_id,))

            db.commit()

            cursor.close()
            db.close()

            flash(
                "OTP has expired. Please request a new OTP.",
                "error"
            )

            return redirect(url_for("admin_forgot_password"))

        if otp != stored_otp:

            cursor.close()
            db.close()

            flash("Invalid OTP. Please try again.", "error")
            return redirect(url_for("admin_verify_otp"))

        # OTP is correct
        cursor.execute("""
            UPDATE admin_password_otps
            SET used = TRUE
            WHERE id = %s
        """, (otp_id,))

        db.commit()

        cursor.close()
        db.close()

        session["admin_otp_verified_id"] = admin_id
        session.pop("admin_reset_id", None)

        flash(
            "OTP verified successfully! <i class='fa-solid fa-lock'></i>",
            "success"
        )

        return redirect(url_for("admin_reset_password"))

    return render_template("admin_verify_otp.html")

@app.route("/admin-reset-password", methods=["GET", "POST"])
def admin_reset_password():

    admin_id = session.get("admin_otp_verified_id")

    if not admin_id:
        flash(
            "Please verify your OTP first.",
            "error"
        )
        return redirect(url_for("admin_forgot_password"))

    if request.method == "POST":

        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("admin_reset_password"))

        if len(new_password) < 6:
            flash(
                "Password must be at least 6 characters.",
                "error"
            )
            return redirect(url_for("admin_reset_password"))

        hashed_password = generate_password_hash(new_password)

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            UPDATE admins
            SET password = %s
            WHERE id = %s
        """, (
            hashed_password,
            admin_id
        ))

        db.commit()

        cursor.close()
        db.close()

        # Clear reset session
        session.pop("admin_otp_verified_id", None)

        flash(
            "Password reset successfully! You can now login. <i class='fa-solid fa-lock'></i>",
            "success"
        )

        return redirect(url_for("login"))

    return render_template("admin_reset_password.html")


# =========================
# ORGANIZER REGISTER
# =========================

@app.route("/organizer-register", methods=["GET", "POST"])
def organizer_register():

    if request.method == "POST":

        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if not username or not email or not password:
            flash("Please fill all fields.", "error")
            return redirect(url_for("organizer_register"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("organizer_register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return redirect(url_for("organizer_register"))

        db = get_db_connection()
        cursor = db.cursor()

        # Check whether username already exists as an admin/organizer
        cursor.execute("""
            SELECT id
            FROM admins
            WHERE username = %s
        """, (username,))

        existing_admin = cursor.fetchone()

        if existing_admin:
            cursor.close()
            db.close()

            flash(
                "Username already exists. Please choose another.",
                "error"
            )
            return redirect(url_for("organizer_register"))

        # Check whether a request with this username already exists
        cursor.execute("""
            SELECT id, status
            FROM organizer_requests
            WHERE username = %s
        """, (username,))

        existing_request = cursor.fetchone()

        if existing_request:

            cursor.close()
            db.close()

            if existing_request[1] == "pending":
                flash(
                    "Your organizer request is already pending approval. ⏳",
                    "error"
                )
            elif existing_request[1] == "rejected":
                flash(
                    "Your previous request was rejected. Please contact the Main Admin.",
                    "error"
                )
            else:
                flash(
                    "An organizer request already exists for this username.",
                    "error"
                )

            return redirect(url_for("organizer_register"))

        # Securely hash the password before storing the request
        hashed_password = generate_password_hash(password)

        # Create a PENDING organizer request
        cursor.execute("""
            INSERT INTO organizer_requests
            (username, email, password, status)
            VALUES (%s, %s, %s, 'pending')
        """, (
            username,
            email,
            hashed_password
        ))

        db.commit()

        cursor.close()
        db.close()

        flash(
            "Organizer request submitted successfully! ⏳ "
            "Please wait for Main Admin approval.",
            "success"
        )

        return redirect(url_for("login"))

    return render_template("organizer_register.html")

@app.route("/my-events")
@student_required
def my_events():

    if not session.get("student_logged_in"):
        flash("Please login first.", "error")
        return redirect(url_for("student_login"))

    college_id = session.get("student_college_id")

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        SELECT id, name, event, registration_date
        FROM registrations
        WHERE college_id = %s
        ORDER BY registration_date DESC
    """, (college_id,))

    registrations = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "my_events.html",
        registrations=registrations
    )

    
# =========================
# PROFILE
# =========================

@app.route("/profile", methods=["GET", "POST"])
def profile():

    # =========================
    # CHECK LOGIN
    # =========================

    is_admin = session.get("admin_logged_in")
    is_student = session.get("student_logged_in")

    if not is_admin and not is_student:
        flash("Please login first.", "error")
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor()

    # =========================
    # ADMIN / ORGANIZER
    # =========================

    if is_admin:

        admin_id = session.get("admin_id")

        cursor.execute("""
            SELECT id, username, email, phone, role
            FROM admins
            WHERE id = %s
        """, (admin_id,))

        user = cursor.fetchone()

        if not user:
            cursor.close()
            db.close()
            session.clear()
            flash("Account not found.", "error")
            return redirect(url_for("login"))

        if request.method == "POST":

            email = request.form.get("email", "").strip()
            phone = request.form.get("phone", "").strip()

            if not email:
                cursor.close()
                db.close()
                flash("Email address is required.", "error")
                return redirect(url_for("profile"))

            # Check whether email belongs to another account
            cursor.execute("""
                SELECT id
                FROM admins
                WHERE email = %s
                AND id != %s
            """, (email, admin_id))

            existing_email = cursor.fetchone()

            if existing_email:
                cursor.close()
                db.close()
                flash(
                    "This email address is already used by another account.",
                    "error"
                )
                return redirect(url_for("profile"))

            # Update profile
            cursor.execute("""
                UPDATE admins
                SET email = %s,
                    phone = %s
                WHERE id = %s
            """, (
                email,
                phone,
                admin_id
            ))

            db.commit()

            cursor.close()
            db.close()

            flash(
                "Profile updated successfully! <i class='fa-solid fa-circle-check'></i>",
                "success"
            )

            return redirect(url_for("profile"))

        cursor.close()
        db.close()

        return render_template(
            "profile.html",
            user=user,
            user_type="admin"
        )

    # =========================
    # STUDENT
    # =========================

    student_id = session.get("student_id")

    cursor.execute("""
        SELECT id, name, college_id, email, phone
        FROM students
        WHERE id = %s
    """, (student_id,))

    user = cursor.fetchone()

    if not user:
        cursor.close()
        db.close()
        session.clear()
        flash("Student account not found.", "error")
        return redirect(url_for("student_login"))

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()

        if not email:
            cursor.close()
            db.close()
            flash("Email address is required.", "error")
            return redirect(url_for("profile"))

        # Check whether email belongs to another student
        cursor.execute("""
            SELECT id
            FROM students
            WHERE email = %s
            AND id != %s
        """, (email, student_id))

        existing_email = cursor.fetchone()

        if existing_email:
            cursor.close()
            db.close()
            flash(
                "This email address is already used by another student.",
                "error"
            )
            return redirect(url_for("profile"))

        # Update profile
        cursor.execute("""
            UPDATE students
            SET email = %s,
                phone = %s
            WHERE id = %s
        """, (
            email,
            phone,
            student_id
        ))

        db.commit()

        cursor.close()
        db.close()

        flash(
            "Profile updated successfully! <i class='fa-solid fa-circle-check'></i>",
            "success"
        )

        return redirect(url_for("profile"))

    cursor.close()
    db.close()

    return render_template(
        "profile.html",
        user=user,
        user_type="student"
    )

@app.route("/admin")
@admin_required
def admin():

    if not session.get("admin_logged_in"):
        flash("Please login as admin first.", "error")
        return redirect(url_for("login"))

    admin_id = session.get("admin_id")
    admin_role = session.get("admin_role")

    db = get_db_connection()
    cursor = db.cursor()

    # =========================
    # MAIN ADMIN
    # =========================

    if admin_role == "main_admin":

        cursor.execute("SELECT COUNT(*) FROM registrations")
        total_registrations = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM events")
        total_events = cursor.fetchone()[0]

        cursor.execute("""
            SELECT e.id, e.name, COUNT(r.id)
            FROM events e
            LEFT JOIN registrations r
                ON e.name = r.event
            GROUP BY e.id, e.name
        """)

        event_stats = cursor.fetchall()

        cursor.execute("""
            SELECT
                e.id,
                e.name,
                e.description,
                e.event_date,
                e.location,
                COUNT(r.id) AS registration_count
            FROM events e
            LEFT JOIN registrations r
                ON e.name = r.event
            GROUP BY
                e.id,
                e.name,
                e.description,
                e.event_date,
                e.location
            ORDER BY e.event_date ASC
        """)

        events = cursor.fetchall()

    # =========================
    # EVENT ORGANIZER
    # =========================

    elif admin_role == "organizer":

        cursor.execute("""
            SELECT COUNT(*)
            FROM registrations r
            JOIN events e
                ON e.name = r.event
            WHERE e.created_by = %s
        """, (admin_id,))

        total_registrations = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM events
            WHERE created_by = %s
        """, (admin_id,))

        total_events = cursor.fetchone()[0]

        cursor.execute("""
            SELECT
                e.id,
                e.name,
                COUNT(r.id)
            FROM events e
            LEFT JOIN registrations r
                ON e.name = r.event
            WHERE e.created_by = %s
            GROUP BY e.id, e.name
        """, (admin_id,))

        event_stats = cursor.fetchall()

        cursor.execute("""
            SELECT
                e.id,
                e.name,
                e.description,
                e.event_date,
                e.location,
                COUNT(r.id) AS registration_count
            FROM events e
            LEFT JOIN registrations r
                ON e.name = r.event
            WHERE e.created_by = %s
            GROUP BY
                e.id,
                e.name,
                e.description,
                e.event_date,
                e.location
            ORDER BY e.event_date ASC
        """, (admin_id,))

        events = cursor.fetchall()

    else:

        cursor.close()
        db.close()

        flash("Invalid admin role.", "error")
        return redirect(url_for("login"))

    # =========================
    # COMMON ANALYTICS
    # =========================

    events_with_registrations = sum(
        1 for event in events
        if event[5] > 0
    )

    events_without_registrations = sum(
        1 for event in events
        if event[5] == 0
    )

    if event_stats:

        popular_event = max(
            event_stats,
            key=lambda x: x[2]
        )[1]

    else:

        popular_event = "None"

    cursor.close()
    db.close()

    return render_template(
        "admin_dashboard.html",
        total_registrations=total_registrations,
        total_events=total_events,
        popular_event=popular_event,
        event_stats=event_stats,
        events=events,
        events_with_registrations=events_with_registrations,
        events_without_registrations=events_without_registrations,
        admin_role=admin_role
    )


@app.route("/admin/organizers")
@main_admin_required
def manage_organizers():

    if not session.get("admin_logged_in"):
        flash("Please login as admin first.", "error")
        return redirect(url_for("login"))

    # Only Main Admin can manage organizers
    if session.get("admin_role") != "main_admin":
        flash("Access denied. Only Main Admin can manage organizers.", "error")
        return redirect(url_for("admin"))

    db = get_db_connection()
    cursor = db.cursor()

    # Get all organizer requests
    cursor.execute("""
        SELECT id, username, status, requested_at
        FROM organizer_requests
        ORDER BY requested_at DESC
    """)

    requests = cursor.fetchall()

    # Get all current organizers
    cursor.execute("""
        SELECT id, username, role, status
        FROM admins
        WHERE role = 'organizer'
        ORDER BY username ASC
    """)

    organizers = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "manage_organizers.html",
        requests=requests,
        organizers=organizers
    )


@app.route("/admin/organizers/toggle-status/<int:organizer_id>")
@main_admin_required
def toggle_organizer_status(organizer_id):

    # Check admin login
    if not session.get("admin_logged_in"):
        flash("Please login as admin first.", "error")
        return redirect(url_for("login"))

    # Only Main Admin can change organizer status
    if session.get("admin_role") != "main_admin":
        flash(
            "Access denied. Only Main Admin can change organizer status.",
            "error"
        )
        return redirect(url_for("admin"))

    db = get_db_connection()
    cursor = db.cursor()

    # Get current organizer status
    cursor.execute("""
        SELECT username, status
        FROM admins
        WHERE id = %s
        AND role = 'organizer'
    """, (organizer_id,))

    organizer = cursor.fetchone()

    if not organizer:
        cursor.close()
        db.close()

        flash("Organizer not found.", "error")
        return redirect(url_for("manage_organizers"))

    username = organizer[0]
    current_status = organizer[1]

    # Toggle status
    if current_status == "active":
        new_status = "inactive"
    else:
        new_status = "active"

    cursor.execute("""
        UPDATE admins
        SET status = %s
        WHERE id = %s
        AND role = 'organizer'
    """, (new_status, organizer_id))

    db.commit()

    cursor.close()
    db.close()

    if new_status == "active":
        flash(
            f"Organizer '{username}' activated successfully. 🟢",
            "success"
        )
    else:
        flash(
            f"Organizer '{username}' deactivated successfully. 🔴",
            "success"
        )

    return redirect(url_for("manage_organizers"))


@app.route("/admin/organizers/delete/<int:organizer_id>")
@main_admin_required
def delete_organizer(organizer_id):

    if not session.get("admin_logged_in"):
        flash("Please login as admin first.", "error")
        return redirect(url_for("login"))

    if session.get("admin_role") != "main_admin":
        flash(
            "Access denied. Only Main Admin can delete organizers.",
            "error"
        )
        return redirect(url_for("admin"))

    db = get_db_connection()
    cursor = db.cursor()

    # Find organizer first
    cursor.execute("""
        SELECT username
        FROM admins
        WHERE id = %s
        AND role = 'organizer'
    """, (organizer_id,))

    organizer = cursor.fetchone()

    if not organizer:
        cursor.close()
        db.close()

        flash("Organizer not found.", "error")
        return redirect(url_for("manage_organizers"))

    username = organizer[0]

    # Delete organizer
    cursor.execute("""
        DELETE FROM admins
        WHERE id = %s
        AND role = 'organizer'
    """, (organizer_id,))

    db.commit()

    cursor.close()
    db.close()

    flash(
        f"Organizer '{username}' deleted successfully. 🗑️",
        "success"
    )

    return redirect(url_for("manage_organizers"))


@app.route("/admin/registrations")
@admin_required
def admin_registrations():

    if not session.get("admin_logged_in"):
        flash("Please login as admin first.", "error")
        return redirect(url_for("login"))

    admin_id = session.get("admin_id")
    admin_role = session.get("admin_role")

    db = get_db_connection()
    cursor = db.cursor()

    if admin_role == "main_admin":

        # Main Admin sees ALL registrations
        cursor.execute("""
            SELECT
                r.id,
                r.name,
                r.college_id,
                r.email,
                r.phone,
                r.event,
                r.registration_date
            FROM registrations r
            ORDER BY r.registration_date DESC
        """)

        registrations = cursor.fetchall()

        # All events for filter
        cursor.execute("""
            SELECT id, name
            FROM events
            ORDER BY name ASC
        """)

        events = cursor.fetchall()

    elif admin_role == "organizer":

        # Organizer sees only registrations
        # belonging to their own events
        cursor.execute("""
            SELECT
                r.id,
                r.name,
                r.college_id,
                r.email,
                r.phone,
                r.event,
                r.registration_date
            FROM registrations r
            JOIN events e
                ON e.name = r.event
            WHERE e.created_by = %s
            ORDER BY r.registration_date DESC
        """, (admin_id,))

        registrations = cursor.fetchall()

        # Only organizer's events for filter
        cursor.execute("""
            SELECT id, name
            FROM events
            WHERE created_by = %s
            ORDER BY name ASC
        """, (admin_id,))

        events = cursor.fetchall()

    else:

        cursor.close()
        db.close()

        flash("Invalid admin role.", "error")
        return redirect(url_for("login"))

    events_with_registrations = len(set(
        registration[5]
        for registration in registrations
    ))

    cursor.close()
    db.close()

    return render_template(
        "admin_registrations.html",
        registrations=registrations,
        events=events,
        events_with_registrations=events_with_registrations
    )


@app.route("/admin/export-registrations")
@admin_required
def export_registrations():

    db = get_db_connection()
    cursor = db.cursor()

    # ==========================================
    # MAIN ADMIN → EXPORT ALL REGISTRATIONS
    # ==========================================

    if session.get("admin_role") == "main_admin":

        cursor.execute("""
            SELECT
                r.id,
                r.name,
                r.college_id,
                r.email,
                r.phone,
                r.event,
                r.registration_date
            FROM registrations r
            ORDER BY r.registration_date DESC
        """)

    # ==========================================
    # ORGANIZER → EXPORT ONLY THEIR EVENTS
    # ==========================================

    elif session.get("admin_role") == "organizer":

        logged_in_admin_id = session.get("admin_id")

        cursor.execute("""
            SELECT
                r.id,
                r.name,
                r.college_id,
                r.email,
                r.phone,
                r.event,
                r.registration_date
            FROM registrations r
            INNER JOIN events e
                ON r.event = e.name
            WHERE e.created_by = %s
            ORDER BY r.registration_date DESC
        """, (logged_in_admin_id,))

    # ==========================================
    # INVALID ROLE
    # ==========================================

    else:

        cursor.close()
        db.close()

        flash(
            "Access denied.",
            "error"
        )

        return redirect(url_for("login"))

    registrations = cursor.fetchall()

    cursor.close()
    db.close()

    # ==========================================
    # CREATE CSV
    # ==========================================

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Student Name",
        "College ID",
        "Email",
        "Phone",
        "Event",
        "Registration Date"
    ])

    for registration in registrations:
        writer.writerow(registration)

    response = Response(
        output.getvalue(),
        mimetype="text/csv"
    )

    response.headers["Content-Disposition"] = (
        "attachment; filename=campus_events_registrations.csv"
    )

    # Prevent caching of exported registration data
    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@app.route("/admin/delete-registration/<int:registration_id>")
@admin_required
def admin_delete_registration(registration_id):

    db = get_db_connection()
    cursor = db.cursor()

    # Find the registration and its event owner
    cursor.execute("""
        SELECT
            r.name,
            r.event,
            e.created_by
        FROM registrations r
        LEFT JOIN events e
            ON r.event = e.name
        WHERE r.id = %s
    """, (registration_id,))

    registration = cursor.fetchone()

    # Registration doesn't exist
    if not registration:

        cursor.close()
        db.close()

        flash(
            "Registration not found.",
            "error"
        )

        return redirect(url_for("admin_registrations"))

    student_name = registration[0]
    event_name = registration[1]
    event_created_by = registration[2]

    # ==========================================
    # AUTHORIZATION CHECK
    # ==========================================

    # Main Admin can delete any registration
    if session.get("admin_role") == "main_admin":
        pass

    # Organizer can delete only registrations
    # belonging to their own events
    elif session.get("admin_role") == "organizer":

        logged_in_admin_id = session.get("admin_id")

        if event_created_by != logged_in_admin_id:

            cursor.close()
            db.close()

            flash(
                "Access denied. You can only delete registrations from your own events.",
                "error"
            )

            return redirect(url_for("admin_registrations"))

    # Invalid role
    else:

        cursor.close()
        db.close()

        flash(
            "Access denied.",
            "error"
        )

        return redirect(url_for("admin_registrations"))

    # ==========================================
    # DELETE REGISTRATION
    # ==========================================

    cursor.execute("""
        DELETE FROM registrations
        WHERE id = %s
    """, (registration_id,))

    db.commit()

    cursor.close()
    db.close()

    flash(
        f"Registration of {student_name} for {event_name} removed successfully! 🗑️",
        "success"
    )

    return redirect(url_for("admin_registrations"))


# =========================
# ADD EVENT
# =========================

@app.route("/add-event", methods=["GET", "POST"])
@admin_required
def add_event():

    if not session.get("admin_logged_in"):
        flash("Please login as admin first.", "error")
        return redirect(url_for("login"))

    admin_id = session.get("admin_id")

    if request.method == "POST":

        name = request.form["name"].strip()
        description = request.form["description"].strip()
        event_date = request.form["event_date"]
        location = request.form["location"].strip()

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO events
            (name, description, event_date, location, created_by)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            name,
            description,
            event_date,
            location,
            admin_id
        ))

        db.commit()

        cursor.close()
        db.close()

        flash(
            f"Event '{name}' created successfully! <i class='fa-solid fa-calendar-check'></i>",
            "success"
        )

        return redirect(url_for("admin"))

    return render_template("add_event.html")

@app.route("/edit-event/<int:event_id>", methods=["GET", "POST"])
@admin_required
def edit_event(event_id):

    if not session.get("admin_logged_in"):
        flash("Please login as admin first.", "error")
        return redirect(url_for("login"))

    admin_id = session.get("admin_id")
    admin_role = session.get("admin_role")

    db = get_db_connection()
    cursor = db.cursor()

    # Check event ownership
    if admin_role == "main_admin":

        cursor.execute("""
            SELECT id, name, description, event_date, location, created_by
            FROM events
            WHERE id = %s
        """, (event_id,))

    elif admin_role == "organizer":

        cursor.execute("""
            SELECT id, name, description, event_date, location, created_by
            FROM events
            WHERE id = %s
            AND created_by = %s
        """, (event_id, admin_id))

    else:
        cursor.close()
        db.close()
        flash("Invalid admin role.", "error")
        return redirect(url_for("login"))

    event = cursor.fetchone()

    # Event doesn't exist OR organizer doesn't own it
    if not event:

        cursor.close()
        db.close()

        flash(
            "You do not have permission to edit this event.",
            "error"
        )

        return redirect(url_for("admin"))

    if request.method == "POST":

        name = request.form["name"].strip()
        description = request.form["description"].strip()
        event_date = request.form["event_date"]
        location = request.form["location"].strip()

        cursor.execute("""
            UPDATE events
            SET name = %s,
                description = %s,
                event_date = %s,
                location = %s
            WHERE id = %s
        """, (
            name,
            description,
            event_date,
            location,
            event_id
        ))

        db.commit()

        cursor.close()
        db.close()

        flash(
            f"Event '{name}' updated successfully! ✏️",
            "success"
        )

        return redirect(url_for("admin"))

    cursor.close()
    db.close()

    return render_template(
        "edit_event.html",
        event=event
    )


@app.route("/delete-event/<int:event_id>")
@admin_required
def delete_event(event_id):

    db = get_db_connection()
    cursor = db.cursor()

    # Get event details
    cursor.execute(
        """
        SELECT id, name, created_by
        FROM events
        WHERE id = %s
        """,
        (event_id,)
    )

    event = cursor.fetchone()

    # Event doesn't exist
    if not event:

        cursor.close()
        db.close()

        flash(
            "Event not found.",
            "error"
        )

        return redirect(url_for("admin"))

    event_id_db = event[0]
    event_name = event[1]
    event_created_by = event[2]

    # ==========================================
    # AUTHORIZATION CHECK
    # ==========================================

    # Main Admin can delete any event
    if session.get("admin_role") == "main_admin":
        pass

    # Organizer can delete only events created by them
    elif session.get("admin_role") == "organizer":

        logged_in_admin_id = session.get("admin_id")

        if event_created_by != logged_in_admin_id:

            cursor.close()
            db.close()

            flash(
                "Access denied. You can only delete your own events.",
                "error"
            )

            return redirect(url_for("admin"))

    # Invalid role
    else:

        cursor.close()
        db.close()

        flash(
            "Access denied.",
            "error"
        )

        return redirect(url_for("admin"))

    # ==========================================
    # DELETE REGISTRATIONS
    # ==========================================

    cursor.execute(
        "DELETE FROM registrations WHERE event = %s",
        (event_name,)
    )

    # ==========================================
    # DELETE EVENT
    # ==========================================

    cursor.execute(
        """
        DELETE FROM events
        WHERE id = %s
        """,
        (event_id_db,)
    )

    db.commit()

    cursor.close()
    db.close()

    flash(
        f"'{event_name}' deleted successfully! 🗑️",
        "success"
    )

    return redirect(url_for("admin"))


@app.route("/analysis")
@admin_required
def analysis():

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        SELECT event, COUNT(*)
        FROM registrations
        GROUP BY event
    """)

    data = cursor.fetchall()

    cursor.close()
    db.close()

    if not data:
        return "No registration data available."

    event_names = [row[0] for row in data]

    registration_counts = [row[1] for row in data]

    counts = np.array(registration_counts)

    total = np.sum(counts)

    average = np.mean(counts)

    maximum = np.max(counts)

    minimum = np.min(counts)

    max_index = np.argmax(counts)

    min_index = np.argmin(counts)

    most_popular = event_names[max_index]

    least_popular = event_names[min_index]

    # Sort events from highest to lowest
    event_stats = []

    for i in range(len(event_names)):

        event_stats.append(
            (event_names[i], int(counts[i]))
        )

    event_stats = merge_sort(event_stats)

    return render_template(
        "analysis.html",
        total=int(total),
        average=round(float(average), 2),
        maximum=int(maximum),
        minimum=int(minimum),
        most_popular=most_popular,
        least_popular=least_popular,
        event_stats=event_stats
    )


@app.route("/search", methods=["GET", "POST"])
@admin_required
def search():

    # 🔒 Only admin can use student search
    if not session.get("admin_logged_in"):
        flash(
            "Access denied. Student search is available only to admin.",
            "error"
        )
        return redirect(url_for("student_dashboard"))

    registrations = []
    searched = False

    if request.method == "POST":

        searched = True

        college_id = request.form["college_id"].strip()

    elif request.args.get("college_id"):

        searched = True

        college_id = request.args.get("college_id").strip()

    if searched:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM registrations")

        students = cursor.fetchall()

        cursor.close()
        db.close()

        # --------------------------------
        # SORT BY COLLEGE ID
        # --------------------------------

        students = sorted(
            students,
            key=lambda x: x[2]
        )

        # --------------------------------
        # BINARY SEARCH
        # --------------------------------

        low = 0
        high = len(students) - 1
        found_index = -1

        while low <= high:

            middle = (low + high) // 2

            current_id = students[middle][2]

            if current_id == college_id:

                found_index = middle
                break

            elif current_id < college_id:

                low = middle + 1

            else:

                high = middle - 1

        # --------------------------------
        # GET ALL REGISTRATIONS
        # --------------------------------

        if found_index != -1:

            # Go backwards to find first matching record
            start = found_index

            while start > 0 and students[start - 1][2] == college_id:
                start -= 1

            # Go forward and collect all matching records
            index = start

            while index < len(students) and students[index][2] == college_id:

                registrations.append(students[index])

                index += 1

    # --------------------------------
    # NUMPY: REGISTRATION COUNT
    # --------------------------------

    registration_count = len(registrations)

    count_array = np.array([registration_count])

    total_registrations = np.sum(count_array)

    return render_template(
        "search.html",
        registrations=registrations,
        searched=searched,
        total_registrations=int(total_registrations)
    )


@app.route("/cancel-registration/<int:registration_id>")
@student_required
def cancel_registration(registration_id):

    if not session.get("student_logged_in"):
        flash("Please login first.", "error")
        return redirect(url_for("student_login"))

    college_id = session.get("student_college_id")

    db = get_db_connection()
    cursor = db.cursor()

    # Make sure this registration belongs to the logged-in student
    cursor.execute("""
        SELECT event
        FROM registrations
        WHERE id = %s
        AND college_id = %s
    """, (registration_id, college_id))

    registration = cursor.fetchone()

    if not registration:

        cursor.close()
        db.close()

        flash(
            "Registration not found.",
            "error"
        )

        return redirect(url_for("my_events"))

    event_name = registration[0]

    # Delete registration
    cursor.execute("""
        DELETE FROM registrations
        WHERE id = %s
        AND college_id = %s
    """, (registration_id, college_id))

    db.commit()

    cursor.close()
    db.close()

    flash(
        f"Registration for {event_name} cancelled successfully.",
        "success"
    )

    return redirect(url_for("my_events"))


@app.route("/logout")
def logout():

    session.clear()

    response = redirect(url_for("login"))

    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    flash(
        "You have been logged out successfully.",
        "success"
    )

    return response


@app.route("/student-login", methods=["GET", "POST"])
def student_login():

    next_page = request.args.get("next")

    if request.method == "POST":

        next_page = request.form.get("next")

        college_id = request.form["college_id"].strip()
        password = request.form["password"]

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT id, name, college_id, password_hash
            FROM students
            WHERE college_id = %s
            """,
            (college_id,)
        )

        student = cursor.fetchone()

        cursor.close()
        db.close()

        # College ID doesn't exist
        if not student:

            flash(
                "College ID not found. Please create an account.",
                "error"
            )

            return redirect(
                url_for(
                    "student_login",
                    next=next_page
                )
            )

        # Check password
        if not student[3] or not check_password_hash(
            student[3],
            password
        ):

            flash(
                "Incorrect password. Please try again.",
                "error"
            )

            return redirect(
                url_for(
                    "student_login",
                    next=next_page
                )
            )

        # Login successful
        session["student_logged_in"] = True
        session["student_id"] = student[0]
        session["student_name"] = student[1]
        session["student_college_id"] = student[2]

        flash(
            f"Welcome back, {student[1]}! <i class='fa-solid fa-graduation-cap'></i>",
            "success"
        )

        # Return to event registration if applicable
        if next_page and next_page != "None":
            return redirect(next_page)

        return redirect(
            url_for("student_dashboard")
        )

    return render_template(
        "student_login.html",
        next_page=next_page
    )


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        college_id = request.form["college_id"].strip()
        email = request.form["email"].strip()

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT id, name, email
            FROM students
            WHERE college_id = %s
            AND email = %s
            """,
            (college_id, email)
        )

        student = cursor.fetchone()

        if not student:

            cursor.close()
            db.close()

            flash(
                "College ID and email do not match.",
                "error"
            )

            return redirect(
                url_for("forgot_password")
            )

        student_id = student[0]

        # Generate a secure random token
        reset_token = secrets.token_urlsafe(48)

        # Token valid for 15 minutes
        expires_at = datetime.now() + timedelta(minutes=15)

        # Remove previous unused tokens for this student
        cursor.execute(
            """
            DELETE FROM password_reset_tokens
            WHERE student_id = %s
            AND used = FALSE
            """,
            (student_id,)
        )

        # Store new token
        cursor.execute(
            """
            INSERT INTO password_reset_tokens
            (
                student_id,
                token,
                expires_at
            )
            VALUES (%s, %s, %s)
            """,
            (
                student_id,
                reset_token,
                expires_at
            )
        )

        db.commit()

        cursor.close()
        db.close()

        # Send student to secure reset page
        return redirect(
            url_for(
                "reset_password",
                token=reset_token
            )
        )

    return render_template("forgot_password.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    token = request.args.get("token", "").strip()

    if not token:

        flash(
            "Invalid or missing password reset link.",
            "error"
        )

        return redirect(
            url_for("forgot_password")
        )

    db = get_db_connection()
    cursor = db.cursor()

    # Check token
    cursor.execute(
        """
        SELECT
            id,
            student_id,
            expires_at,
            used
        FROM password_reset_tokens
        WHERE token = %s
        """,
        (token,)
    )

    reset_record = cursor.fetchone()

    if not reset_record:

        cursor.close()
        db.close()

        flash(
            "Invalid password reset link.",
            "error"
        )

        return redirect(
            url_for("forgot_password")
        )

    reset_id = reset_record[0]
    student_id = reset_record[1]
    expires_at = reset_record[2]
    used = reset_record[3]

    # Token already used
    if used:

        cursor.close()
        db.close()

        flash(
            "This password reset link has already been used.",
            "error"
        )

        return redirect(
            url_for("forgot_password")
        )

    # Token expired
    if datetime.now() > expires_at:

        cursor.close()
        db.close()

        flash(
            "This password reset link has expired. Please request a new one.",
            "error"
        )

        return redirect(
            url_for("forgot_password")
        )

    # ==========================================
    # UPDATE PASSWORD
    # ==========================================

    if request.method == "POST":

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:

            cursor.close()
            db.close()

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for(
                    "reset_password",
                    token=token
                )
            )

        if len(password) < 6:

            cursor.close()
            db.close()

            flash(
                "Password must be at least 6 characters long.",
                "error"
            )

            return redirect(
                url_for(
                    "reset_password",
                    token=token
                )
            )

        password_hash = generate_password_hash(password)

        # Update student password
        cursor.execute(
            """
            UPDATE students
            SET password_hash = %s
            WHERE id = %s
            """,
            (
                password_hash,
                student_id
            )
        )

        # Mark token as used
        cursor.execute(
            """
            UPDATE password_reset_tokens
            SET used = TRUE
            WHERE id = %s
            """,
            (reset_id,)
        )

        db.commit()

        cursor.close()
        db.close()

        flash(
            "Password updated successfully! <i class='fa-solid fa-lock'></i> Please login.",
            "success"
        )

        return redirect(
            url_for("student_login")
        )

    cursor.close()
    db.close()

    return render_template(
        "reset_password.html",
        token=token
    )


@app.route("/student-register", methods=["GET", "POST"])
def student_register():

    next_page = request.args.get("next")

    if request.method == "POST":

        next_page = request.form.get("next")

        name = request.form["name"].strip()
        college_id = request.form["college_id"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Check password confirmation
        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for(
                    "student_register",
                    next=next_page
                )
            )

        # Minimum password length
        if len(password) < 6:

            flash(
                "Password must be at least 6 characters long.",
                "error"
            )

            return redirect(
                url_for(
                    "student_register",
                    next=next_page
                )
            )

        db = get_db_connection()
        cursor = db.cursor()

        # Check if College ID already exists
        cursor.execute(
            """
            SELECT id
            FROM students
            WHERE college_id = %s
            """,
            (college_id,)
        )

        existing_student = cursor.fetchone()

        if existing_student:

            cursor.close()
            db.close()

            flash(
                "This College ID is already registered. Please login.",
                "error"
            )

            return redirect(
                url_for(
                    "student_login",
                    next=next_page
                )
            )

        # Hash password
        password_hash = generate_password_hash(password)

        # Create student account
        cursor.execute(
            """
            INSERT INTO students
            (name, college_id, email, phone, password_hash)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                name,
                college_id,
                email,
                phone,
                password_hash
            )
        )

        db.commit()

        student_id = cursor.lastrowid

        # Login newly created student
        session["student_logged_in"] = True
        session["student_id"] = student_id
        session["student_name"] = name
        session["student_college_id"] = college_id

        flash(
            f"Account created successfully! Welcome {name}! <i class='fa-solid fa-calendar-check'></i>",
            "success"
        )

        # If student came from event registration
        if next_page and next_page != "None":

            if next_page.startswith("/register/"):

                try:

                    event_id = int(
                        next_page.split("/")[-1]
                    )

                    # Get event
                    cursor.execute(
                        """
                        SELECT id, name
                        FROM events
                        WHERE id = %s
                        """,
                        (event_id,)
                    )

                    event = cursor.fetchone()

                    if event:

                        event_name = event[1]

                        # Register student for event
                        cursor.execute(
                            """
                            INSERT INTO registrations
                            (name, college_id, email, phone, event)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (
                                name,
                                college_id,
                                email,
                                phone,
                                event_name
                            )
                        )

                        db.commit()

                        flash(
                            f"Successfully registered for {event_name}! <i class='fa-solid fa-calendar-check'></i>",
                            "success"
                        )

                        cursor.close()
                        db.close()

                        return redirect(
                            url_for("my_events")
                        )

                except (ValueError, IndexError):
                    pass

        cursor.close()
        db.close()

        return redirect(
            url_for("student_dashboard")
        )

    return render_template(
        "student_register.html",
        next_page=next_page
    )


@app.route("/student-dashboard")
@student_required
def student_dashboard():

    if not session.get("student_logged_in"):

        flash(
            "Please login first.",
            "error"
        )

        return redirect(url_for("student_login"))

    college_id = session.get("student_college_id")

    return render_template(
        "student_dashboard.html",
        college_id=college_id
    )


@app.route("/student-logout")
def student_logout():

    session.clear()

    response = redirect(url_for("student_login"))

    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    flash(
        "You have been logged out successfully. 👋",
        "success"
    )

    return response


@app.route("/register/<int:event_id>")
@student_required
def register_event(event_id):

    # Check student login
    if not session.get("student_logged_in"):
        flash("Please login to register for this event.", "error")
        return redirect(
            url_for(
                "student_login",
                next=url_for("register_event", event_id=event_id)
            )
        )

    college_id = session.get("student_college_id")

    db = get_db_connection()
    cursor = db.cursor()

    # Get student details
    cursor.execute("""
        SELECT name, college_id, email, phone
        FROM students
        WHERE college_id = %s
    """, (college_id,))

    student = cursor.fetchone()

    # Get event details
    cursor.execute("""
        SELECT id, name
        FROM events
        WHERE id = %s
    """, (event_id,))

    event = cursor.fetchone()

    if not student:
        cursor.close()
        db.close()

        flash("Student not found.", "error")
        return redirect(url_for("student_login"))

    if not event:
        cursor.close()
        db.close()

        flash("Event not found.", "error")
        return redirect(url_for("events"))

    event_name = event[1]

    # Check duplicate registration
    cursor.execute("""
        SELECT id
        FROM registrations
        WHERE college_id = %s
        AND event = %s
    """, (college_id, event_name))

    already_registered = cursor.fetchone()

    if already_registered:

        cursor.close()
        db.close()

        flash(
            f"You are already registered for {event_name}.",
            "error"
        )

        return redirect(url_for("events"))

    # Register student
    cursor.execute("""
        INSERT INTO registrations
        (name, college_id, email, phone, event)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        student[0] or "Unknown",
        student[1] or "Unknown",
        student[2] or "No Email",
        (student[3] or "No Phone")[:15],
        event_name
    ))

    db.commit()

    cursor.close()
    db.close()

    # =========================
    # SEND REGISTRATION EMAIL
    # =========================
    if student[2]:
        try:
            msg = Message(
                subject=f"RAIT Events Registration Confirmation - {event_name}",
                recipients=[student[2]]
            )

            msg.body = f"""
Hello {student[0]},

Your registration for the following RAIT Events event has been confirmed successfully! <i class='fa-solid fa-calendar-check'></i>

Event: {event_name}

You are now officially registered for this event.

Please keep this email for your records.

Regards,
RAIT Events
"""

            mail.send(msg)

        except Exception as e:
            print("Registration email error:", e)

    flash(
        f"Successfully registered for {event_name}! <i class='fa-solid fa-calendar-check'></i>",
        "success"
    )

    return redirect(url_for("my_events"))


@app.route("/admin/organizers/approve/<int:request_id>")
@main_admin_required
def approve_organizer(request_id):

    if not session.get("admin_logged_in"):
        flash("Please login as admin first.", "error")
        return redirect(url_for("login"))

    if session.get("admin_role") != "main_admin":
        flash("Access denied. Only Main Admin can approve organizers.", "error")
        return redirect(url_for("admin"))

    db = get_db_connection()
    cursor = db.cursor()

    # Get the pending request
    cursor.execute("""
        SELECT id, username, email, password, status
        FROM organizer_requests
        WHERE id = %s
    """, (request_id,))

    organizer_request = cursor.fetchone()

    if not organizer_request:
        cursor.close()
        db.close()
        flash("Organizer request not found.", "error")
        return redirect(url_for("manage_organizers"))

    request_id_db = organizer_request[0]
    username = organizer_request[1]
    request_email = organizer_request[2]
    hashed_password = organizer_request[3]
    status = organizer_request[4]

    if status != "pending":
        cursor.close()
        db.close()
        flash("This organizer request has already been processed.", "error")
        return redirect(url_for("manage_organizers"))

    if not request_email:
        cursor.close()
        db.close()
        flash(
            "This organizer request has no email address. "
            "Ask the organizer to submit a new request with an email.",
            "error"
        )
        return redirect(url_for("manage_organizers"))

    # Double-check username doesn't already exist
    cursor.execute("""
        SELECT id
        FROM admins
        WHERE username = %s
    """, (username,))

    existing_admin = cursor.fetchone()

    if existing_admin:
        cursor.close()
        db.close()
        flash("This username already exists as an admin.", "error")
        return redirect(url_for("manage_organizers"))

    # Create the organizer account
    cursor.execute("""
        INSERT INTO admins
        (username, email, password, role)
        VALUES (%s, %s, %s, 'organizer')
    """, (
        username,
        request_email,
        hashed_password
    ))

    # Mark request as approved
    cursor.execute("""
        UPDATE organizer_requests
        SET status = 'approved'
        WHERE id = %s
    """, (request_id_db,))

    db.commit()

    cursor.close()
    db.close()

    flash(
        f"Organizer '{username}' approved successfully! <i class='fa-solid fa-circle-check'></i>",
        "success"
    )

    return redirect(url_for("manage_organizers"))


@app.route("/admin/organizers/reject/<int:request_id>")
@main_admin_required
def reject_organizer(request_id):

    if not session.get("admin_logged_in"):
        flash("Please login as admin first.", "error")
        return redirect(url_for("login"))

    if session.get("admin_role") != "main_admin":
        flash("Access denied. Only Main Admin can reject organizers.", "error")
        return redirect(url_for("admin"))

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        SELECT username, status
        FROM organizer_requests
        WHERE id = %s
    """, (request_id,))

    organizer_request = cursor.fetchone()

    if not organizer_request:
        cursor.close()
        db.close()
        flash("Organizer request not found.", "error")
        return redirect(url_for("manage_organizers"))

    username = organizer_request[0]
    status = organizer_request[1]

    if status != "pending":
        cursor.close()
        db.close()
        flash("This organizer request has already been processed.", "error")
        return redirect(url_for("manage_organizers"))

    cursor.execute("""
        UPDATE organizer_requests
        SET status = 'rejected'
        WHERE id = %s
    """, (request_id,))

    db.commit()

    cursor.close()
    db.close()

    flash(
        f"Organizer '{username}' rejected. <i class='fa-solid fa-circle-xmark'></i>",
        "success"
    )

    return redirect(url_for("manage_organizers"))


# =========================
# GLOBAL EVENT SEARCH
# =========================

@app.route("/event-search")
def event_search():

    search_query = request.args.get("q", "").strip()

    db = get_db_connection()
    cursor = db.cursor()

    if search_query:

        cursor.execute("""
            SELECT
                e.id,
                e.name,
                e.description,
                e.event_date,
                e.location,
                a.username
            FROM events e
            LEFT JOIN admins a
                ON e.created_by = a.id
            WHERE
                e.name LIKE %s
                OR a.username LIKE %s
            ORDER BY e.event_date ASC
        """, (
            "%" + search_query + "%",
            "%" + search_query + "%"
        ))

    else:

        cursor.execute("""
            SELECT
                e.id,
                e.name,
                e.description,
                e.event_date,
                e.location,
                a.username
            FROM events e
            LEFT JOIN admins a
                ON e.created_by = a.id
            ORDER BY e.event_date ASC
        """)

    search_results = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "event_search.html",
        search_query=search_query,
        search_results=search_results
    )



@app.route("/admin/students")
def manage_students():
    if "admin_logged_in" not in session:
        return redirect(url_for("login"))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    cursor.execute("SELECT id, name, college_id, email, phone FROM students ORDER BY id DESC")
    students = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    return render_template("admin_students.html", students=students)

@app.route("/admin/students/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    if "admin_logged_in" not in session:
        return redirect(url_for("login"))
        
    if session.get("admin_role") != "main_admin":
        flash("Unauthorized. Only Main Admins can delete student accounts.", "error")
        return redirect(url_for("manage_students"))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
    db.commit()
    
    cursor.close()
    db.close()
    
    flash("Student account permanently deleted.", "success")
    return redirect(url_for("manage_students"))


if __name__ == "__main__":
    app.run(debug=True)
