# ============================================
# Blood Bank Management System
# Backend: Flask + PostgreSQL (Render)
# File: app.py - With Access Control
# ============================================

from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
import psycopg2.extras
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "bloodbank_secret_key_2026"

DATABASE_URL   = os.environ.get("DATABASE_URL", "")
ADMIN_EMAIL    = "admin@bloodbank.com"
ADMIN_PASSWORD = "admin123"

# ============================================
# DATABASE
# ============================================

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    conn = get_db()
    cur  = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS donor (
        id SERIAL PRIMARY KEY, name TEXT NOT NULL, age INTEGER NOT NULL,
        gender TEXT NOT NULL, blood_group TEXT NOT NULL, mobile TEXT NOT NULL UNIQUE,
        address TEXT NOT NULL, email TEXT NOT NULL UNIQUE, password TEXT NOT NULL)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS doctor (
        id SERIAL PRIMARY KEY, name TEXT NOT NULL, age INTEGER NOT NULL,
        gender TEXT NOT NULL, blood_group TEXT NOT NULL, mobile TEXT NOT NULL UNIQUE,
        address TEXT NOT NULL, email TEXT NOT NULL UNIQUE, password TEXT NOT NULL)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS patient (
        id SERIAL PRIMARY KEY, name TEXT NOT NULL, age INTEGER NOT NULL,
        gender TEXT NOT NULL, blood_group TEXT NOT NULL, mobile TEXT NOT NULL UNIQUE,
        address TEXT NOT NULL, email TEXT NOT NULL UNIQUE, password TEXT NOT NULL)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS hospital (
        id SERIAL PRIMARY KEY, name TEXT NOT NULL, address TEXT NOT NULL,
        mobile TEXT NOT NULL, email TEXT NOT NULL UNIQUE)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS blood_bank (
        id SERIAL PRIMARY KEY, blood_group TEXT NOT NULL,
        available_units INTEGER NOT NULL DEFAULT 0,
        hospital_name TEXT NOT NULL, last_updated DATE DEFAULT CURRENT_DATE)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS donation_history (
        id SERIAL PRIMARY KEY, donor_id INTEGER REFERENCES donor(id) ON DELETE CASCADE,
        donor_name TEXT NOT NULL, blood_group TEXT NOT NULL, units INTEGER NOT NULL DEFAULT 1,
        donation_date DATE DEFAULT CURRENT_DATE, hospital_name TEXT NOT NULL,
        status TEXT DEFAULT 'Completed')''')

    cur.execute('''CREATE TABLE IF NOT EXISTS blood_request (
        id SERIAL PRIMARY KEY, patient_id INTEGER REFERENCES patient(id) ON DELETE CASCADE,
        patient_name TEXT NOT NULL, blood_group TEXT NOT NULL, units INTEGER NOT NULL DEFAULT 1,
        hospital_name TEXT NOT NULL, request_date DATE DEFAULT CURRENT_DATE,
        status TEXT DEFAULT 'Pending')''')

    cur.execute("SELECT COUNT(*) FROM hospital")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO hospital (name, address, mobile, email) VALUES (%s,%s,%s,%s)", [
            ('City Hospital',       '123 Main Street, City',  '9876543210', 'city@hospital.com'),
            ('Green Cross Hospital','456 Park Road, Town',    '9876543211', 'green@hospital.com'),
            ('Sunrise Medical',     '789 Lake View, Metro',   '9876543212', 'sunrise@hospital.com'),
        ])

    cur.execute("SELECT COUNT(*) FROM blood_bank")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO blood_bank (blood_group, available_units, hospital_name) VALUES (%s,%s,%s)", [
            ('A+',  15, 'City Hospital'),  ('A-',  8,  'City Hospital'),
            ('B+',  20, 'Green Cross Hospital'), ('B-', 5, 'Green Cross Hospital'),
            ('O+',  25, 'Sunrise Medical'), ('O-', 10, 'Sunrise Medical'),
            ('AB+', 12, 'City Hospital'),  ('AB-', 6,  'Green Cross Hospital'),
        ])

    conn.commit()
    conn.close()


# ============================================
# ACCESS CONTROL HELPERS
# ============================================

def is_admin():
    return session.get('user_role') == 'admin'

def is_logged_in():
    return 'user_name' in session

def can_edit(role, record_id):
    """Only admin or the owner can edit."""
    if is_admin():
        return True
    return session.get('user_role') == role and session.get('user_id') == record_id

def admin_required():
    """Redirect if not admin."""
    if not is_admin():
        return redirect(url_for('access_denied'))
    return None

def login_required():
    """Redirect if not logged in."""
    if not is_logged_in():
        return redirect(url_for('login'))
    return None


def check_duplicate(cursor, email, mobile, exclude_table=None, exclude_id=None):
    tables = ['donor', 'doctor', 'patient']
    for table in tables:
        if exclude_table == table and exclude_id:
            cursor.execute(f"SELECT id FROM {table} WHERE email=%s AND id!=%s", (email, exclude_id))
        else:
            cursor.execute(f"SELECT id FROM {table} WHERE email=%s", (email,))
        if cursor.fetchone():
            return "This email is already registered. Please use a different email."
        if exclude_table == table and exclude_id:
            cursor.execute(f"SELECT id FROM {table} WHERE mobile=%s AND id!=%s", (mobile, exclude_id))
        else:
            cursor.execute(f"SELECT id FROM {table} WHERE mobile=%s", (mobile,))
        if cursor.fetchone():
            return "This mobile number is already registered. Please use a different number."
    return None


def can_donate(donor_id):
    conn = get_db()
    cur  = conn.cursor()
    three_months_ago = datetime.now().date() - timedelta(days=90)
    cur.execute(
        "SELECT donation_date FROM donation_history WHERE donor_id=%s AND donation_date >= %s ORDER BY donation_date DESC LIMIT 1",
        (donor_id, three_months_ago)
    )
    last = cur.fetchone()
    conn.close()
    return last is None, last[0] if last else None


# ============================================
# ACCESS DENIED PAGE
# ============================================

@app.route('/access_denied')
def access_denied():
    return render_template('access_denied.html')


# ============================================
# HOME
# ============================================

@app.route('/')
def home():
    return render_template('home.html')


# ============================================
# REGISTER
# ============================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ""
    if request.method == 'POST':
        role        = request.form['role']
        name        = request.form['name'].strip()
        age         = request.form['age']
        gender      = request.form['gender']
        blood_group = request.form['blood_group']
        mobile      = request.form['mobile'].strip()
        address     = request.form['address'].strip()
        email       = request.form['email'].strip().lower()
        password    = request.form['password']
        confirm_pw  = request.form['confirm_password']

        if len(password) < 8:
            return render_template('register.html', message="Password must be at least 8 characters.")
        if password != confirm_pw:
            return render_template('register.html', message="Passwords do not match.")

        conn = get_db()
        cur  = conn.cursor()
        dup  = check_duplicate(cur, email, mobile)
        if dup:
            conn.close()
            return render_template('register.html', message=dup)

        try:
            cur.execute(
                f"INSERT INTO {role} (name,age,gender,blood_group,mobile,address,email,password) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (name, age, gender, blood_group, mobile, address, email, password)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('thankyou'))
        except Exception as e:
            conn.rollback()
            conn.close()
            return render_template('register.html', message=f"Registration failed: {str(e)}")

    return render_template('register.html', message=message)


# ============================================
# LOGIN
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ""
    if request.method == 'POST':
        role     = request.form['role']
        email    = request.form['email'].strip().lower()
        password = request.form['password']

        if role == 'admin':
            if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
                session['user_id']   = 0
                session['user_name'] = 'Admin'
                session['user_role'] = 'admin'
                return redirect(url_for('admin'))
            else:
                return render_template('login.html', message="Invalid admin credentials.")

        conn = get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(f"SELECT * FROM {role} WHERE email=%s AND password=%s", (email, password))
        user = cur.fetchone()
        conn.close()

        if user:
            session['user_id']   = user['id']
            session['user_name'] = user['name']
            session['user_role'] = role
            return redirect(url_for('dashboard'))
        else:
            message = "Invalid email or password. Please try again."

    return render_template('login.html', message=message)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# ============================================
# DASHBOARD
# ============================================

@app.route('/dashboard')
def dashboard():
    redirect_resp = login_required()
    if redirect_resp: return redirect_resp

    role    = session.get('user_role')
    user_id = session.get('user_id')

    if role == 'admin':
        return redirect(url_for('admin'))

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"SELECT * FROM {role} WHERE id=%s", (user_id,))
    user = cur.fetchone()

    donations  = []
    requests   = []
    eligible   = True
    next_date  = None

    if role == 'donor':
        cur.execute("SELECT * FROM donation_history WHERE donor_id=%s ORDER BY donation_date DESC", (user_id,))
        donations = cur.fetchall()
        eligible, last_date = can_donate(user_id)
        if not eligible:
            next_date = last_date + timedelta(days=90)

    if role == 'patient':
        cur.execute("SELECT * FROM blood_request WHERE patient_id=%s ORDER BY request_date DESC", (user_id,))
        requests = cur.fetchall()

    conn.close()
    return render_template('dashboard.html',
        user=user, role=role, donations=donations,
        requests=requests, eligible=eligible, next_date=next_date
    )


# ============================================
# DONATE
# ============================================

@app.route('/donate', methods=['GET', 'POST'])
def donate():
    redirect_resp = login_required()
    if redirect_resp: return redirect_resp
    if session.get('user_role') != 'donor':
        return redirect(url_for('access_denied'))

    donor_id         = session.get('user_id')
    eligible, last_d = can_donate(donor_id)

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM donor WHERE id=%s", (donor_id,))
    donor     = cur.fetchone()
    cur.execute("SELECT name FROM hospital")
    hospitals = cur.fetchall()
    message   = ""

    if not eligible:
        next_date = last_d + timedelta(days=90)
        conn.close()
        return render_template('donate.html', eligible=False, next_date=next_date, hospitals=[], donor=donor, message="")

    if request.method == 'POST':
        hospital = request.form['hospital_name']
        units    = int(request.form.get('units', 1))
        cur2     = conn.cursor()
        cur2.execute(
            "INSERT INTO donation_history (donor_id, donor_name, blood_group, units, hospital_name) VALUES (%s,%s,%s,%s,%s)",
            (donor_id, donor['name'], donor['blood_group'], units, hospital)
        )
        cur2.execute(
            "UPDATE blood_bank SET available_units = available_units + %s WHERE blood_group=%s AND hospital_name=%s",
            (units, donor['blood_group'], hospital)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))

    conn.close()
    return render_template('donate.html', eligible=True, donor=donor, hospitals=hospitals, message=message, next_date=None)


# ============================================
# BLOOD REQUEST
# ============================================

@app.route('/blood_request', methods=['GET', 'POST'])
def blood_request():
    redirect_resp = login_required()
    if redirect_resp: return redirect_resp
    if session.get('user_role') != 'patient':
        return redirect(url_for('access_denied'))

    patient_id = session.get('user_id')
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM patient WHERE id=%s", (patient_id,))
    patient   = cur.fetchone()
    cur.execute("SELECT name FROM hospital")
    hospitals = cur.fetchall()
    message   = ""

    if request.method == 'POST':
        hospital = request.form['hospital_name']
        units    = int(request.form.get('units', 1))
        bg       = patient['blood_group']
        cur2     = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur2.execute("SELECT available_units FROM blood_bank WHERE blood_group=%s AND hospital_name=%s", (bg, hospital))
        stock = cur2.fetchone()
        if not stock or stock['available_units'] < units:
            message = f"Sorry, not enough {bg} blood units available at {hospital}."
        else:
            cur3 = conn.cursor()
            cur3.execute(
                "INSERT INTO blood_request (patient_id, patient_name, blood_group, units, hospital_name) VALUES (%s,%s,%s,%s,%s)",
                (patient_id, patient['name'], bg, units, hospital)
            )
            cur3.execute(
                "UPDATE blood_bank SET available_units = available_units - %s WHERE blood_group=%s AND hospital_name=%s",
                (units, bg, hospital)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('dashboard'))

    conn.close()
    return render_template('blood_request.html', patient=patient, hospitals=hospitals, message=message)


# ============================================
# DONATION HISTORY
# ============================================

@app.route('/donation_history')
def donation_history():
    redirect_resp = login_required()
    if redirect_resp: return redirect_resp
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM donation_history ORDER BY donation_date DESC")
    history = cur.fetchall()
    conn.close()
    return render_template('donation_history.html', history=history)


# ============================================
# VIEW - PUBLIC
# ============================================

@app.route('/view_donor')
def view_donor():
    search = request.args.get('search', '').strip()
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if search:
        cur.execute("SELECT * FROM donor WHERE name ILIKE %s OR blood_group ILIKE %s OR email ILIKE %s ORDER BY id",
                    (f'%{search}%', f'%{search}%', f'%{search}%'))
    else:
        cur.execute("SELECT * FROM donor ORDER BY id")
    donors = cur.fetchall()
    conn.close()
    return render_template('view_donor.html', donors=donors, search=search)


@app.route('/view_doctor')
def view_doctor():
    search = request.args.get('search', '').strip()
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if search:
        cur.execute("SELECT * FROM doctor WHERE name ILIKE %s OR blood_group ILIKE %s OR email ILIKE %s ORDER BY id",
                    (f'%{search}%', f'%{search}%', f'%{search}%'))
    else:
        cur.execute("SELECT * FROM doctor ORDER BY id")
    doctors = cur.fetchall()
    conn.close()
    return render_template('view_doctor.html', doctors=doctors, search=search)


@app.route('/view_patient')
def view_patient():
    search = request.args.get('search', '').strip()
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if search:
        cur.execute("SELECT * FROM patient WHERE name ILIKE %s OR blood_group ILIKE %s OR email ILIKE %s ORDER BY id",
                    (f'%{search}%', f'%{search}%', f'%{search}%'))
    else:
        cur.execute("SELECT * FROM patient ORDER BY id")
    patients = cur.fetchall()
    conn.close()
    return render_template('view_patient.html', patients=patients, search=search)


# ============================================
# DELETE - ADMIN ONLY
# ============================================

@app.route('/delete_donor/<int:id>')
def delete_donor(id):
    if not is_admin():
        return redirect(url_for('access_denied'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM donor WHERE id=%s", (id,))
    conn.commit(); conn.close()
    return redirect(url_for('view_donor'))


@app.route('/delete_doctor/<int:id>')
def delete_doctor(id):
    if not is_admin():
        return redirect(url_for('access_denied'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM doctor WHERE id=%s", (id,))
    conn.commit(); conn.close()
    return redirect(url_for('view_doctor'))


@app.route('/delete_patient/<int:id>')
def delete_patient(id):
    if not is_admin():
        return redirect(url_for('access_denied'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM patient WHERE id=%s", (id,))
    conn.commit(); conn.close()
    return redirect(url_for('view_patient'))


# ============================================
# EDIT - OWNER OR ADMIN ONLY
# ============================================

@app.route('/edit_donor/<int:id>', methods=['GET', 'POST'])
def edit_donor(id):
    if not can_edit('donor', id):
        return redirect(url_for('access_denied'))
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method == 'POST':
        name=request.form['name'].strip(); age=request.form['age']
        gender=request.form['gender']; blood_group=request.form['blood_group']
        mobile=request.form['mobile'].strip(); address=request.form['address'].strip()
        email=request.form['email'].strip().lower(); password=request.form['password']
        if len(password) < 8:
            cur.execute("SELECT * FROM donor WHERE id=%s", (id,))
            return render_template('edit_donor.html', donor=cur.fetchone(), message="Password must be at least 8 characters.")
        dup = check_duplicate(cur, email, mobile, exclude_table='donor', exclude_id=id)
        if dup:
            cur.execute("SELECT * FROM donor WHERE id=%s", (id,))
            return render_template('edit_donor.html', donor=cur.fetchone(), message=dup)
        cur2 = conn.cursor()
        cur2.execute("UPDATE donor SET name=%s,age=%s,gender=%s,blood_group=%s,mobile=%s,address=%s,email=%s,password=%s WHERE id=%s",
                    (name,age,gender,blood_group,mobile,address,email,password,id))
        conn.commit(); conn.close()
        return redirect(url_for('view_donor'))
    cur.execute("SELECT * FROM donor WHERE id=%s", (id,))
    donor = cur.fetchone(); conn.close()
    return render_template('edit_donor.html', donor=donor, message="")


@app.route('/edit_doctor/<int:id>', methods=['GET', 'POST'])
def edit_doctor(id):
    if not can_edit('doctor', id):
        return redirect(url_for('access_denied'))
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method == 'POST':
        name=request.form['name'].strip(); age=request.form['age']
        gender=request.form['gender']; blood_group=request.form['blood_group']
        mobile=request.form['mobile'].strip(); address=request.form['address'].strip()
        email=request.form['email'].strip().lower(); password=request.form['password']
        if len(password) < 8:
            cur.execute("SELECT * FROM doctor WHERE id=%s", (id,))
            return render_template('edit_doctor.html', doctor=cur.fetchone(), message="Password must be at least 8 characters.")
        dup = check_duplicate(cur, email, mobile, exclude_table='doctor', exclude_id=id)
        if dup:
            cur.execute("SELECT * FROM doctor WHERE id=%s", (id,))
            return render_template('edit_doctor.html', doctor=cur.fetchone(), message=dup)
        cur2 = conn.cursor()
        cur2.execute("UPDATE doctor SET name=%s,age=%s,gender=%s,blood_group=%s,mobile=%s,address=%s,email=%s,password=%s WHERE id=%s",
                    (name,age,gender,blood_group,mobile,address,email,password,id))
        conn.commit(); conn.close()
        return redirect(url_for('view_doctor'))
    cur.execute("SELECT * FROM doctor WHERE id=%s", (id,))
    doctor = cur.fetchone(); conn.close()
    return render_template('edit_doctor.html', doctor=doctor, message="")


@app.route('/edit_patient/<int:id>', methods=['GET', 'POST'])
def edit_patient(id):
    if not can_edit('patient', id):
        return redirect(url_for('access_denied'))
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method == 'POST':
        name=request.form['name'].strip(); age=request.form['age']
        gender=request.form['gender']; blood_group=request.form['blood_group']
        mobile=request.form['mobile'].strip(); address=request.form['address'].strip()
        email=request.form['email'].strip().lower(); password=request.form['password']
        if len(password) < 8:
            cur.execute("SELECT * FROM patient WHERE id=%s", (id,))
            return render_template('edit_patient.html', patient=cur.fetchone(), message="Password must be at least 8 characters.")
        dup = check_duplicate(cur, email, mobile, exclude_table='patient', exclude_id=id)
        if dup:
            cur.execute("SELECT * FROM patient WHERE id=%s", (id,))
            return render_template('edit_patient.html', patient=cur.fetchone(), message=dup)
        cur2 = conn.cursor()
        cur2.execute("UPDATE patient SET name=%s,age=%s,gender=%s,blood_group=%s,mobile=%s,address=%s,email=%s,password=%s WHERE id=%s",
                    (name,age,gender,blood_group,mobile,address,email,password,id))
        conn.commit(); conn.close()
        return redirect(url_for('view_patient'))
    cur.execute("SELECT * FROM patient WHERE id=%s", (id,))
    patient = cur.fetchone(); conn.close()
    return render_template('edit_patient.html', patient=patient, message="")


# ============================================
# REPORT - PUBLIC
# ============================================

@app.route('/report')
def report():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM blood_bank ORDER BY hospital_name, blood_group")
    report_data = cur.fetchall()
    cur.execute("SELECT blood_group, SUM(available_units) as total FROM blood_bank GROUP BY blood_group ORDER BY blood_group")
    summary = cur.fetchall()
    conn.close()
    return render_template('report.html', report_data=report_data, summary=summary)


# ============================================
# ADMIN - ADMIN ONLY
# ============================================

@app.route('/admin')
def admin():
    if not is_admin():
        return redirect(url_for('access_denied'))
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT COUNT(*) as total FROM donor");   donors_count   = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM doctor");  doctors_count  = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM patient"); patients_count = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM donation_history"); donations_count = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM blood_request");   requests_count  = cur.fetchone()['total']
    cur.execute("SELECT * FROM donation_history ORDER BY donation_date DESC LIMIT 10")
    recent_donations = cur.fetchall()
    cur.execute("SELECT * FROM blood_request ORDER BY request_date DESC LIMIT 10")
    recent_requests  = cur.fetchall()
    cur.execute("SELECT blood_group, SUM(available_units) as total FROM blood_bank GROUP BY blood_group ORDER BY blood_group")
    blood_summary = cur.fetchall()
    conn.close()
    return render_template('admin.html',
        donors_count=donors_count, doctors_count=doctors_count,
        patients_count=patients_count, donations_count=donations_count,
        requests_count=requests_count, recent_donations=recent_donations,
        recent_requests=recent_requests, blood_summary=blood_summary
    )


@app.route('/admin/approve_request/<int:id>')
def approve_request(id):
    if not is_admin(): return redirect(url_for('access_denied'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE blood_request SET status='Approved' WHERE id=%s", (id,))
    conn.commit(); conn.close()
    return redirect(url_for('admin'))


@app.route('/admin/reject_request/<int:id>')
def reject_request(id):
    if not is_admin(): return redirect(url_for('access_denied'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE blood_request SET status='Rejected' WHERE id=%s", (id,))
    conn.commit(); conn.close()
    return redirect(url_for('admin'))


# ============================================
# THANK YOU
# ============================================

@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')


# ============================================
# RUN
# ============================================

if __name__ == '__main__':
    init_db()
    app.run(debug=False)

init_db()