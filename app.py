# ============================================
# Blood Bank Management System
# Backend: Flask + PostgreSQL (Render)
# File: app.py
# ============================================

from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
import psycopg2.extras
import os

app = Flask(__name__)
app.secret_key = "bloodbank_secret_key"

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS donor (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            mobile TEXT NOT NULL,
            address TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctor (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            mobile TEXT NOT NULL,
            address TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patient (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            mobile TEXT NOT NULL,
            address TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hospital (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            mobile TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blood_bank (
            id SERIAL PRIMARY KEY,
            blood_group TEXT NOT NULL,
            available_units INTEGER NOT NULL DEFAULT 0,
            hospital_name TEXT NOT NULL,
            last_updated DATE DEFAULT CURRENT_DATE
        )
    ''')

    cursor.execute("SELECT COUNT(*) FROM hospital")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO hospital (name, address, mobile, email) VALUES (%s, %s, %s, %s)", [
            ('City Hospital', '123 Main Street, City', '9876543210', 'city@hospital.com'),
            ('Green Cross Hospital', '456 Park Road, Town', '9876543211', 'green@hospital.com'),
            ('Sunrise Medical Center', '789 Lake View, Metro', '9876543212', 'sunrise@hospital.com'),
        ])

    cursor.execute("SELECT COUNT(*) FROM blood_bank")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO blood_bank (blood_group, available_units, hospital_name) VALUES (%s, %s, %s)", [
            ('A+',  15, 'City Hospital'),
            ('A-',  8,  'City Hospital'),
            ('B+',  20, 'Green Cross Hospital'),
            ('B-',  5,  'Green Cross Hospital'),
            ('O+',  25, 'Sunrise Medical Center'),
            ('O-',  10, 'Sunrise Medical Center'),
            ('AB+', 12, 'City Hospital'),
            ('AB-', 6,  'Green Cross Hospital'),
        ])

    conn.commit()
    conn.close()


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
    form_data = {}

    if request.method == 'POST':
        form_data = request.form.to_dict()
        role       = request.form['role']
        name       = request.form['name'].strip()
        age        = request.form['age'].strip()
        gender     = request.form['gender']
        blood_group= request.form['blood_group']
        mobile     = request.form['mobile'].strip()
        address    = request.form['address'].strip()
        email      = request.form['email'].strip().lower()
        password   = request.form['password']

        # Password length validation
        if len(password) < 8:
            message = "Password must be at least 8 characters long."
            return render_template('register.html', message=message, form_data=form_data)

        conn = get_db()
        cursor = conn.cursor()

        # Check if email already exists in any table
        cursor.execute("SELECT email FROM donor WHERE email=%s", (email,))
        if cursor.fetchone():
            conn.close()
            message = "This email is already registered as a Donor."
            return render_template('register.html', message=message, form_data=form_data)

        cursor.execute("SELECT email FROM doctor WHERE email=%s", (email,))
        if cursor.fetchone():
            conn.close()
            message = "This email is already registered as a Doctor."
            return render_template('register.html', message=message, form_data=form_data)

        cursor.execute("SELECT email FROM patient WHERE email=%s", (email,))
        if cursor.fetchone():
            conn.close()
            message = "This email is already registered as a Patient."
            return render_template('register.html', message=message, form_data=form_data)

        try:
            if role == 'donor':
                cursor.execute(
                    "INSERT INTO donor (name, age, gender, blood_group, mobile, address, email, password) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (name, age, gender, blood_group, mobile, address, email, password)
                )
            elif role == 'doctor':
                cursor.execute(
                    "INSERT INTO doctor (name, age, gender, blood_group, mobile, address, email, password) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (name, age, gender, blood_group, mobile, address, email, password)
                )
            elif role == 'patient':
                cursor.execute(
                    "INSERT INTO patient (name, age, gender, blood_group, mobile, address, email, password) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (name, age, gender, blood_group, mobile, address, email, password)
                )
            conn.commit()
            conn.close()
            return redirect(url_for('thankyou'))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            conn.close()
            message = "This email is already registered. Please use a different email."

    return render_template('register.html', message=message, form_data=form_data)


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

        conn   = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if role == 'donor':
            cursor.execute("SELECT * FROM donor WHERE email=%s AND password=%s", (email, password))
        elif role == 'doctor':
            cursor.execute("SELECT * FROM doctor WHERE email=%s AND password=%s", (email, password))
        elif role == 'patient':
            cursor.execute("SELECT * FROM patient WHERE email=%s AND password=%s", (email, password))

        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_name'] = user['name']
            session['user_role'] = role
            return redirect(url_for('home'))
        else:
            message = "Invalid email or password. Please try again."

    return render_template('login.html', message=message)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# ============================================
# VIEW
# ============================================

@app.route('/view_donor')
def view_donor():
    conn   = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM donor ORDER BY id")
    donors = cursor.fetchall()
    conn.close()
    return render_template('view_donor.html', donors=donors)


@app.route('/view_doctor')
def view_doctor():
    conn   = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM doctor ORDER BY id")
    doctors = cursor.fetchall()
    conn.close()
    return render_template('view_doctor.html', doctors=doctors)


@app.route('/view_patient')
def view_patient():
    conn   = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM patient ORDER BY id")
    patients = cursor.fetchall()
    conn.close()
    return render_template('view_patient.html', patients=patients)


# ============================================
# DELETE
# ============================================

@app.route('/delete_donor/<int:id>')
def delete_donor(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM donor WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_donor'))


@app.route('/delete_doctor/<int:id>')
def delete_doctor(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM doctor WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_doctor'))


@app.route('/delete_patient/<int:id>')
def delete_patient(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM patient WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_patient'))


# ============================================
# EDIT - DONOR
# ============================================

@app.route('/edit_donor/<int:id>', methods=['GET', 'POST'])
def edit_donor(id):
    conn   = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    message = ""

    if request.method == 'POST':
        name        = request.form['name'].strip()
        age         = request.form['age'].strip()
        gender      = request.form['gender']
        blood_group = request.form['blood_group']
        mobile      = request.form['mobile'].strip()
        address     = request.form['address'].strip()
        email       = request.form['email'].strip().lower()
        password    = request.form['password']

        if len(password) < 8:
            message = "Password must be at least 8 characters long."
            cursor.execute("SELECT * FROM donor WHERE id=%s", (id,))
            donor = cursor.fetchone()
            conn.close()
            return render_template('edit_donor.html', donor=donor, message=message)

        cursor.execute('''
            UPDATE donor SET name=%s, age=%s, gender=%s, blood_group=%s,
            mobile=%s, address=%s, email=%s, password=%s WHERE id=%s
        ''', (name, age, gender, blood_group, mobile, address, email, password, id))
        conn.commit()
        conn.close()
        return redirect(url_for('view_donor'))

    cursor.execute("SELECT * FROM donor WHERE id=%s", (id,))
    donor = cursor.fetchone()
    conn.close()
    return render_template('edit_donor.html', donor=donor, message=message)


# ============================================
# EDIT - DOCTOR
# ============================================

@app.route('/edit_doctor/<int:id>', methods=['GET', 'POST'])
def edit_doctor(id):
    conn   = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    message = ""

    if request.method == 'POST':
        name        = request.form['name'].strip()
        age         = request.form['age'].strip()
        gender      = request.form['gender']
        blood_group = request.form['blood_group']
        mobile      = request.form['mobile'].strip()
        address     = request.form['address'].strip()
        email       = request.form['email'].strip().lower()
        password    = request.form['password']

        if len(password) < 8:
            message = "Password must be at least 8 characters long."
            cursor.execute("SELECT * FROM doctor WHERE id=%s", (id,))
            doctor = cursor.fetchone()
            conn.close()
            return render_template('edit_doctor.html', doctor=doctor, message=message)

        cursor.execute('''
            UPDATE doctor SET name=%s, age=%s, gender=%s, blood_group=%s,
            mobile=%s, address=%s, email=%s, password=%s WHERE id=%s
        ''', (name, age, gender, blood_group, mobile, address, email, password, id))
        conn.commit()
        conn.close()
        return redirect(url_for('view_doctor'))

    cursor.execute("SELECT * FROM doctor WHERE id=%s", (id,))
    doctor = cursor.fetchone()
    conn.close()
    return render_template('edit_doctor.html', doctor=doctor, message=message)


# ============================================
# EDIT - PATIENT
# ============================================

@app.route('/edit_patient/<int:id>', methods=['GET', 'POST'])
def edit_patient(id):
    conn   = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    message = ""

    if request.method == 'POST':
        name        = request.form['name'].strip()
        age         = request.form['age'].strip()
        gender      = request.form['gender']
        blood_group = request.form['blood_group']
        mobile      = request.form['mobile'].strip()
        address     = request.form['address'].strip()
        email       = request.form['email'].strip().lower()
        password    = request.form['password']

        if len(password) < 8:
            message = "Password must be at least 8 characters long."
            cursor.execute("SELECT * FROM patient WHERE id=%s", (id,))
            patient = cursor.fetchone()
            conn.close()
            return render_template('edit_patient.html', patient=patient, message=message)

        cursor.execute('''
            UPDATE patient SET name=%s, age=%s, gender=%s, blood_group=%s,
            mobile=%s, address=%s, email=%s, password=%s WHERE id=%s
        ''', (name, age, gender, blood_group, mobile, address, email, password, id))
        conn.commit()
        conn.close()
        return redirect(url_for('view_patient'))

    cursor.execute("SELECT * FROM patient WHERE id=%s", (id,))
    patient = cursor.fetchone()
    conn.close()
    return render_template('edit_patient.html', patient=patient, message=message)


# ============================================
# REPORT
# ============================================

@app.route('/report')
def report():
    conn   = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM blood_bank ORDER BY hospital_name, blood_group")
    report_data = cursor.fetchall()

    # Summary: total units per blood group
    cursor.execute("SELECT blood_group, SUM(available_units) as total FROM blood_bank GROUP BY blood_group ORDER BY blood_group")
    summary = cursor.fetchall()
    conn.close()
    return render_template('report.html', report_data=report_data, summary=summary)


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
