# ============================================
# Blood Bank Management System
# Backend: Flask + PostgreSQL
# Full Real-Life Version
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
# BLOOD COMPATIBILITY CHART
# ============================================

BLOOD_COMPATIBILITY = {
    'A+':  ['A+', 'A-', 'O+', 'O-'],
    'A-':  ['A-', 'O-'],
    'B+':  ['B+', 'B-', 'O+', 'O-'],
    'B-':  ['B-', 'O-'],
    'AB+': ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'],
    'AB-': ['A-', 'B-', 'O-', 'AB-'],
    'O+':  ['O+', 'O-'],
    'O-':  ['O-'],
}

LOW_STOCK_THRESHOLD = 5

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
        gender TEXT NOT NULL, blood_group TEXT NOT NULL,
        mobile TEXT NOT NULL UNIQUE, address TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE, password TEXT NOT NULL)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS doctor (
        id SERIAL PRIMARY KEY, name TEXT NOT NULL, age INTEGER NOT NULL,
        gender TEXT NOT NULL, blood_group TEXT NOT NULL,
        mobile TEXT NOT NULL UNIQUE, address TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE, password TEXT NOT NULL)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS patient (
        id SERIAL PRIMARY KEY, name TEXT NOT NULL, age INTEGER NOT NULL,
        gender TEXT NOT NULL, blood_group TEXT NOT NULL,
        mobile TEXT NOT NULL UNIQUE, address TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE, password TEXT NOT NULL)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS hospital (
        id SERIAL PRIMARY KEY, name TEXT NOT NULL,
        address TEXT NOT NULL, mobile TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS blood_bank (
        id SERIAL PRIMARY KEY, blood_group TEXT NOT NULL,
        available_units INTEGER NOT NULL DEFAULT 0,
        hospital_name TEXT NOT NULL,
        last_updated DATE DEFAULT CURRENT_DATE)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS donation_history (
        id SERIAL PRIMARY KEY,
        donor_id INTEGER REFERENCES donor(id) ON DELETE CASCADE,
        donor_name TEXT NOT NULL, blood_group TEXT NOT NULL,
        units INTEGER NOT NULL DEFAULT 1,
        donation_date DATE DEFAULT CURRENT_DATE,
        hospital_name TEXT NOT NULL,
        status TEXT DEFAULT 'Completed')''')

    cur.execute('''CREATE TABLE IF NOT EXISTS blood_request (
        id SERIAL PRIMARY KEY,
        patient_id INTEGER REFERENCES patient(id) ON DELETE CASCADE,
        patient_name TEXT NOT NULL, blood_group TEXT NOT NULL,
        units INTEGER NOT NULL DEFAULT 1,
        hospital_name TEXT NOT NULL,
        urgency TEXT DEFAULT 'Normal',
        reason TEXT,
        request_date DATE DEFAULT CURRENT_DATE,
        required_date DATE,
        doctor_status TEXT DEFAULT 'Pending',
        admin_status TEXT DEFAULT 'Pending',
        doctor_id INTEGER,
        doctor_note TEXT,
        admin_note TEXT)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS appointment (
        id SERIAL PRIMARY KEY,
        donor_id INTEGER REFERENCES donor(id) ON DELETE CASCADE,
        donor_name TEXT NOT NULL, blood_group TEXT NOT NULL,
        hospital_name TEXT NOT NULL,
        appointment_date DATE NOT NULL,
        appointment_time TEXT NOT NULL,
        status TEXT DEFAULT 'Scheduled',
        note TEXT)''')

    # Sample hospital data
    cur.execute("SELECT COUNT(*) FROM hospital")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO hospital (name, address, mobile, email) VALUES (%s,%s,%s,%s)", [
            ('City Hospital',        '123 Main Street, City', '9876543210', 'city@hospital.com'),
            ('Green Cross Hospital', '456 Park Road, Town',   '9876543211', 'green@hospital.com'),
            ('Sunrise Medical',      '789 Lake View, Metro',  '9876543212', 'sunrise@hospital.com'),
        ])

    # Sample blood bank data
    cur.execute("SELECT COUNT(*) FROM blood_bank")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO blood_bank (blood_group, available_units, hospital_name) VALUES (%s,%s,%s)", [
            ('A+',  15, 'City Hospital'),   ('A-',  8,  'City Hospital'),
            ('B+',  20, 'Green Cross Hospital'), ('B-', 3, 'Green Cross Hospital'),
            ('O+',  25, 'Sunrise Medical'), ('O-',  4,  'Sunrise Medical'),
            ('AB+', 12, 'City Hospital'),   ('AB-', 2,  'Green Cross Hospital'),
        ])

    conn.commit()
    conn.close()


# ============================================
# HELPERS
# ============================================

def is_admin():
    return session.get('user_role') == 'admin'

def is_doctor():
    return session.get('user_role') == 'doctor'

def is_logged_in():
    return 'user_name' in session

def login_required():
    if not is_logged_in():
        return redirect(url_for('login'))
    return None

def admin_required():
    if not is_admin():
        return redirect(url_for('access_denied'))
    return None

def admin_or_doctor_required():
    if not (is_admin() or is_doctor()):
        return redirect(url_for('access_denied'))
    return None

def can_edit(role, record_id):
    if is_admin():
        return True
    return session.get('user_role') == role and session.get('user_id') == record_id

def check_duplicate(cursor, email, mobile, exclude_table=None, exclude_id=None):
    for table in ['donor', 'doctor', 'patient']:
        if exclude_table == table and exclude_id:
            cursor.execute(f"SELECT id FROM {table} WHERE email=%s AND id!=%s", (email, exclude_id))
        else:
            cursor.execute(f"SELECT id FROM {table} WHERE email=%s", (email,))
        if cursor.fetchone():
            return "This email is already registered."
        if exclude_table == table and exclude_id:
            cursor.execute(f"SELECT id FROM {table} WHERE mobile=%s AND id!=%s", (mobile, exclude_id))
        else:
            cursor.execute(f"SELECT id FROM {table} WHERE mobile=%s", (mobile,))
        if cursor.fetchone():
            return "This mobile number is already registered."
    return None

def can_donate_check(donor_id):
    conn = get_db()
    cur  = conn.cursor()
    three_months_ago = datetime.now().date() - timedelta(days=90)
    cur.execute(
        "SELECT donation_date FROM donation_history WHERE donor_id=%s AND donation_date>=%s ORDER BY donation_date DESC LIMIT 1",
        (donor_id, three_months_ago)
    )
    last = cur.fetchone()
    conn.close()
    return last is None, last[0] if last else None

def get_pending_count():
    """Get count of pending blood requests for navbar badge."""
    if not is_logged_in():
        return 0
    try:
        conn = get_db()
        cur  = conn.cursor()
        if is_admin():
            cur.execute("SELECT COUNT(*) FROM blood_request WHERE doctor_status='Approved' AND admin_status='Pending'")
        elif is_doctor():
            cur.execute("SELECT COUNT(*) FROM blood_request WHERE doctor_status='Pending'")
        else:
            cur.execute("SELECT COUNT(*) FROM blood_request WHERE patient_id=%s AND doctor_status='Pending'",
                       (session.get('user_id'),))
        count = cur.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def get_low_stock():
    """Get list of blood groups with low stock."""
    try:
        conn = get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT blood_group, hospital_name, available_units FROM blood_bank WHERE available_units < %s ORDER BY available_units",
                   (LOW_STOCK_THRESHOLD,))
        low = cur.fetchall()
        conn.close()
        return low
    except:
        return []

# Make helpers available in all templates
@app.context_processor
def inject_globals():
    return {
        'pending_count': get_pending_count(),
        'low_stock': get_low_stock(),
        'is_admin': is_admin(),
        'is_doctor': is_doctor(),
        'is_logged_in': is_logged_in(),
    }


# ============================================
# ACCESS DENIED
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
        age         = int(request.form['age'])
        gender      = request.form['gender']
        blood_group = request.form['blood_group']
        mobile      = request.form['mobile'].strip()
        address     = request.form['address'].strip()
        email       = request.form['email'].strip().lower()
        password    = request.form['password']
        confirm_pw  = request.form['confirm_password']

        # Validations
        if len(password) < 8:
            return render_template('register.html', message="Password must be at least 8 characters.")
        if password != confirm_pw:
            return render_template('register.html', message="Passwords do not match.")
        if role == 'donor' and age < 18:
            return render_template('register.html', message="Donors must be at least 18 years old.")
        if role == 'donor' and age > 65:
            return render_template('register.html', message="Donors must be 65 years old or younger.")
        if len(mobile) != 10 or not mobile.isdigit():
            return render_template('register.html', message="Mobile number must be exactly 10 digits.")

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
    r = login_required()
    if r: return r
    role    = session.get('user_role')
    user_id = session.get('user_id')
    if role == 'admin':
        return redirect(url_for('admin'))

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"SELECT * FROM {role} WHERE id=%s", (user_id,))
    user = cur.fetchone()

    donations = []; requests = []; appointments = []
    eligible = True; next_date = None

    if role == 'donor':
        cur.execute("SELECT * FROM donation_history WHERE donor_id=%s ORDER BY donation_date DESC", (user_id,))
        donations = cur.fetchall()
        eligible, last_date = can_donate_check(user_id)
        if not eligible:
            next_date = last_date + timedelta(days=90)
        cur.execute("SELECT * FROM appointment WHERE donor_id=%s ORDER BY appointment_date DESC", (user_id,))
        appointments = cur.fetchall()

    if role == 'patient':
        cur.execute("SELECT * FROM blood_request WHERE patient_id=%s ORDER BY request_date DESC", (user_id,))
        requests = cur.fetchall()

    if role == 'doctor':
        cur.execute("SELECT * FROM blood_request WHERE doctor_status='Pending' ORDER BY request_date DESC")
        requests = cur.fetchall()

    conn.close()
    return render_template('dashboard.html',
        user=user, role=role, donations=donations,
        requests=requests, appointments=appointments,
        eligible=eligible, next_date=next_date
    )


# ============================================
# DONATE
# ============================================

@app.route('/donate', methods=['GET', 'POST'])
def donate():
    r = login_required()
    if r: return r
    if session.get('user_role') != 'donor':
        return redirect(url_for('access_denied'))

    donor_id         = session.get('user_id')
    eligible, last_d = can_donate_check(donor_id)

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM donor WHERE id=%s", (donor_id,))
    donor = cur.fetchone()
    cur.execute("SELECT name FROM hospital")
    hospitals = cur.fetchall()
    message = ""

    if not eligible:
        next_date = last_d + timedelta(days=90)
        conn.close()
        return render_template('donate.html', eligible=False,
            next_date=next_date, hospitals=[], donor=donor, message="")

    # Eligibility checks
    if donor['age'] < 18 or donor['age'] > 65:
        conn.close()
        return render_template('donate.html', eligible=False,
            next_date=None, hospitals=[], donor=donor,
            message="Age must be between 18 and 65 to donate blood.")

    if request.method == 'POST':
        hospital = request.form['hospital_name']
        units    = int(request.form.get('units', 1))
        cur2     = conn.cursor()
        cur2.execute(
            "INSERT INTO donation_history (donor_id,donor_name,blood_group,units,hospital_name) VALUES (%s,%s,%s,%s,%s)",
            (donor_id, donor['name'], donor['blood_group'], units, hospital)
        )
        cur2.execute(
            "UPDATE blood_bank SET available_units=available_units+%s, last_updated=CURRENT_DATE WHERE blood_group=%s AND hospital_name=%s",
            (units, donor['blood_group'], hospital)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('certificate', donor_id=donor_id))

    conn.close()
    return render_template('donate.html', eligible=True,
        donor=donor, hospitals=hospitals, message=message, next_date=None)


# ============================================
# CERTIFICATE
# ============================================

@app.route('/certificate/<int:donor_id>')
def certificate(donor_id):
    r = login_required()
    if r: return r
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM donor WHERE id=%s", (donor_id,))
    donor = cur.fetchone()
    cur.execute("SELECT * FROM donation_history WHERE donor_id=%s ORDER BY donation_date DESC LIMIT 1", (donor_id,))
    donation = cur.fetchone()
    conn.close()
    return render_template('certificate.html', donor=donor, donation=donation)


# ============================================
# APPOINTMENT
# ============================================

@app.route('/appointment', methods=['GET', 'POST'])
def appointment():
    r = login_required()
    if r: return r
    if session.get('user_role') != 'donor':
        return redirect(url_for('access_denied'))

    donor_id = session.get('user_id')
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM donor WHERE id=%s", (donor_id,))
    donor = cur.fetchone()
    cur.execute("SELECT name FROM hospital")
    hospitals = cur.fetchall()
    message = ""

    if request.method == 'POST':
        hospital = request.form['hospital_name']
        app_date = request.form['appointment_date']
        app_time = request.form['appointment_time']
        note     = request.form.get('note', '')

        # Cannot book in past
        if app_date < str(datetime.now().date()):
            message = "Appointment date cannot be in the past."
        else:
            cur2 = conn.cursor()
            cur2.execute(
                "INSERT INTO appointment (donor_id,donor_name,blood_group,hospital_name,appointment_date,appointment_time,note) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (donor_id, donor['name'], donor['blood_group'], hospital, app_date, app_time, note)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('dashboard'))

    conn.close()
    return render_template('appointment.html',
        donor=donor, hospitals=hospitals, message=message)


# ============================================
# MANAGE APPOINTMENTS - ADMIN/DOCTOR
# ============================================

@app.route('/manage_appointments')
def manage_appointments():
    r = admin_or_doctor_required()
    if r: return r
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM appointment ORDER BY appointment_date DESC")
    appointments = cur.fetchall()
    conn.close()
    return render_template('manage_appointments.html', appointments=appointments)


@app.route('/update_appointment/<int:id>/<string:status>')
def update_appointment(id, status):
    r = admin_or_doctor_required()
    if r: return r
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE appointment SET status=%s WHERE id=%s", (status, id))
    conn.commit(); conn.close()
    return redirect(url_for('manage_appointments'))


# ============================================
# BLOOD REQUEST - PATIENT
# ============================================

@app.route('/blood_request', methods=['GET', 'POST'])
def blood_request():
    r = login_required()
    if r: return r
    if session.get('user_role') != 'patient':
        return redirect(url_for('access_denied'))

    patient_id = session.get('user_id')
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM patient WHERE id=%s", (patient_id,))
    patient = cur.fetchone()
    cur.execute("SELECT name FROM hospital")
    hospitals = cur.fetchall()
    compatible = BLOOD_COMPATIBILITY.get(patient['blood_group'], [])
    message = ""

    if request.method == 'POST':
        hospital      = request.form['hospital_name']
        units         = int(request.form.get('units', 1))
        urgency       = request.form['urgency']
        reason        = request.form.get('reason', '').strip()
        required_date = request.form.get('required_date', None)

        cur2 = conn.cursor()
        cur2.execute(
            "INSERT INTO blood_request (patient_id,patient_name,blood_group,units,hospital_name,urgency,reason,required_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (patient_id, patient['name'], patient['blood_group'], units, hospital, urgency, reason, required_date or None)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))

    conn.close()
    return render_template('blood_request.html',
        patient=patient, hospitals=hospitals,
        compatible=compatible, message=message)


# ============================================
# MANAGE REQUESTS - DOCTOR
# ============================================

@app.route('/manage_requests')
def manage_requests():
    r = admin_or_doctor_required()
    if r: return r
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if is_admin():
        cur.execute("SELECT * FROM blood_request WHERE doctor_status='Approved' ORDER BY request_date DESC")
    else:
        cur.execute("SELECT * FROM blood_request WHERE doctor_status='Pending' ORDER BY request_date DESC")
    requests = cur.fetchall()
    conn.close()
    return render_template('manage_requests.html', requests=requests)


@app.route('/doctor_action/<int:id>/<string:action>', methods=['POST'])
def doctor_action(id, action):
    if not is_doctor() and not is_admin():
        return redirect(url_for('access_denied'))
    note = request.form.get('note', '')
    status = 'Approved' if action == 'approve' else 'Rejected'
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE blood_request SET doctor_status=%s, doctor_id=%s, doctor_note=%s WHERE id=%s",
               (status, session.get('user_id'), note, id))
    conn.commit(); conn.close()
    return redirect(url_for('manage_requests'))


@app.route('/admin_action/<int:id>/<string:action>', methods=['POST'])
def admin_action(id, action):
    if not is_admin():
        return redirect(url_for('access_denied'))
    note = request.form.get('note', '')
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if action == 'approve':
        cur.execute("SELECT * FROM blood_request WHERE id=%s", (id,))
        req = cur.fetchone()
        # Check stock
        cur2 = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur2.execute("SELECT available_units FROM blood_bank WHERE blood_group=%s AND hospital_name=%s",
                    (req['blood_group'], req['hospital_name']))
        stock = cur2.fetchone()
        if not stock or stock['available_units'] < req['units']:
            conn.close()
            return redirect(url_for('admin'))
        cur3 = conn.cursor()
        cur3.execute("UPDATE blood_request SET admin_status='Approved', admin_note=%s WHERE id=%s", (note, id))
        cur3.execute("UPDATE blood_bank SET available_units=available_units-%s WHERE blood_group=%s AND hospital_name=%s",
                    (req['units'], req['blood_group'], req['hospital_name']))
    else:
        cur4 = conn.cursor()
        cur4.execute("UPDATE blood_request SET admin_status='Rejected', admin_note=%s WHERE id=%s", (note, id))

    conn.commit(); conn.close()
    return redirect(url_for('admin'))


# ============================================
# SEARCH DONORS BY BLOOD GROUP
# ============================================

@app.route('/search_donors')
def search_donors():
    blood_group = request.args.get('blood_group', '').strip()
    donors = []
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if blood_group:
        compatible = BLOOD_COMPATIBILITY.get(blood_group, [blood_group])
        placeholders = ','.join(['%s'] * len(compatible))
        cur.execute(f"SELECT id,name,blood_group,mobile,address FROM donor WHERE blood_group IN ({placeholders}) ORDER BY blood_group",
                   compatible)
        donors = cur.fetchall()
    conn.close()
    return render_template('search_donors.html',
        donors=donors, blood_group=blood_group,
        blood_groups=['A+','A-','B+','B-','O+','O-','AB+','AB-'])


# ============================================
# DONATION HISTORY
# ============================================

@app.route('/donation_history')
def donation_history():
    r = login_required()
    if r: return r
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM donation_history ORDER BY donation_date DESC")
    history = cur.fetchall()
    conn.close()
    return render_template('donation_history.html', history=history)


# ============================================
# VIEW - RESTRICTED
# ============================================

@app.route('/view_donor')
def view_donor():
    r = admin_or_doctor_required()
    if r: return r
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
    r = admin_required()
    if r: return r
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
    r = admin_or_doctor_required()
    if r: return r
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
    if not is_admin(): return redirect(url_for('access_denied'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM donor WHERE id=%s", (id,))
    conn.commit(); conn.close()
    return redirect(url_for('view_donor'))

@app.route('/delete_doctor/<int:id>')
def delete_doctor(id):
    if not is_admin(): return redirect(url_for('access_denied'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM doctor WHERE id=%s", (id,))
    conn.commit(); conn.close()
    return redirect(url_for('view_doctor'))

@app.route('/delete_patient/<int:id>')
def delete_patient(id):
    if not is_admin(): return redirect(url_for('access_denied'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM patient WHERE id=%s", (id,))
    conn.commit(); conn.close()
    return redirect(url_for('view_patient'))


# ============================================
# EDIT - OWNER OR ADMIN ONLY
# ============================================

@app.route('/edit_donor/<int:id>', methods=['GET', 'POST'])
def edit_donor(id):
    if not can_edit('donor', id): return redirect(url_for('access_denied'))
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
        dup = check_duplicate(cur, email, mobile, 'donor', id)
        if dup:
            cur.execute("SELECT * FROM donor WHERE id=%s", (id,))
            return render_template('edit_donor.html', donor=cur.fetchone(), message=dup)
        cur2 = conn.cursor()
        cur2.execute("UPDATE donor SET name=%s,age=%s,gender=%s,blood_group=%s,mobile=%s,address=%s,email=%s,password=%s WHERE id=%s",
                    (name,age,gender,blood_group,mobile,address,email,password,id))
        conn.commit(); conn.close()
        return redirect(url_for('dashboard') if not is_admin() else url_for('view_donor'))
    cur.execute("SELECT * FROM donor WHERE id=%s", (id,))
    donor = cur.fetchone(); conn.close()
    return render_template('edit_donor.html', donor=donor, message="")


@app.route('/edit_doctor/<int:id>', methods=['GET', 'POST'])
def edit_doctor(id):
    if not can_edit('doctor', id): return redirect(url_for('access_denied'))
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
        dup = check_duplicate(cur, email, mobile, 'doctor', id)
        if dup:
            cur.execute("SELECT * FROM doctor WHERE id=%s", (id,))
            return render_template('edit_doctor.html', doctor=cur.fetchone(), message=dup)
        cur2 = conn.cursor()
        cur2.execute("UPDATE doctor SET name=%s,age=%s,gender=%s,blood_group=%s,mobile=%s,address=%s,email=%s,password=%s WHERE id=%s",
                    (name,age,gender,blood_group,mobile,address,email,password,id))
        conn.commit(); conn.close()
        return redirect(url_for('dashboard') if not is_admin() else url_for('view_doctor'))
    cur.execute("SELECT * FROM doctor WHERE id=%s", (id,))
    doctor = cur.fetchone(); conn.close()
    return render_template('edit_doctor.html', doctor=doctor, message="")


@app.route('/edit_patient/<int:id>', methods=['GET', 'POST'])
def edit_patient(id):
    if not can_edit('patient', id): return redirect(url_for('access_denied'))
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
        dup = check_duplicate(cur, email, mobile, 'patient', id)
        if dup:
            cur.execute("SELECT * FROM patient WHERE id=%s", (id,))
            return render_template('edit_patient.html', patient=cur.fetchone(), message=dup)
        cur2 = conn.cursor()
        cur2.execute("UPDATE patient SET name=%s,age=%s,gender=%s,blood_group=%s,mobile=%s,address=%s,email=%s,password=%s WHERE id=%s",
                    (name,age,gender,blood_group,mobile,address,email,password,id))
        conn.commit(); conn.close()
        return redirect(url_for('dashboard') if not is_admin() else url_for('view_patient'))
    cur.execute("SELECT * FROM patient WHERE id=%s", (id,))
    patient = cur.fetchone(); conn.close()
    return render_template('edit_patient.html', patient=patient, message="")


# ============================================
# REPORT
# ============================================

@app.route('/report')
def report():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM blood_bank ORDER BY hospital_name, blood_group")
    report_data = cur.fetchall()
    cur.execute("SELECT blood_group, SUM(available_units) as total FROM blood_bank GROUP BY blood_group ORDER BY blood_group")
    summary = cur.fetchall()
    cur.execute("SELECT hospital_name, SUM(available_units) as total FROM blood_bank GROUP BY hospital_name ORDER BY hospital_name")
    hospital_summary = cur.fetchall()
    conn.close()
    return render_template('report.html',
        report_data=report_data, summary=summary,
        hospital_summary=hospital_summary,
        low_threshold=LOW_STOCK_THRESHOLD)


# ============================================
# ADMIN
# ============================================

@app.route('/admin')
def admin():
    if not is_admin(): return redirect(url_for('access_denied'))
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT COUNT(*) as total FROM donor");         donors_count    = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM doctor");        doctors_count   = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM patient");       patients_count  = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM donation_history"); donations_count = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM blood_request"); requests_count  = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM appointment");   appt_count      = cur.fetchone()['total']
    cur.execute("SELECT * FROM donation_history ORDER BY donation_date DESC LIMIT 10")
    recent_donations = cur.fetchall()
    cur.execute("SELECT * FROM blood_request WHERE doctor_status='Approved' AND admin_status='Pending' ORDER BY request_date DESC")
    pending_requests = cur.fetchall()
    cur.execute("SELECT * FROM blood_request ORDER BY request_date DESC LIMIT 10")
    all_requests = cur.fetchall()
    cur.execute("SELECT blood_group, SUM(available_units) as total FROM blood_bank GROUP BY blood_group ORDER BY blood_group")
    blood_summary = cur.fetchall()
    cur.execute("SELECT * FROM blood_bank WHERE available_units < %s ORDER BY available_units", (LOW_STOCK_THRESHOLD,))
    low_stock_list = cur.fetchall()
    conn.close()
    return render_template('admin.html',
        donors_count=donors_count, doctors_count=doctors_count,
        patients_count=patients_count, donations_count=donations_count,
        requests_count=requests_count, appt_count=appt_count,
        recent_donations=recent_donations, pending_requests=pending_requests,
        all_requests=all_requests, blood_summary=blood_summary,
        low_stock_list=low_stock_list)


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
