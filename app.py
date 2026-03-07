# ============================================
# Blood Bank Management System
# Backend: Flask + SQLite
# File: app.py
# ============================================

from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "bloodbank_secret_key"

DB_NAME = "blood_bank.db"

# ============================================
# DATABASE SETUP
# ============================================

def get_db():
    """Create a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # allows column access by name
    return conn


def init_db():
    """Initialize the database and create tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()

    # Donor Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS donor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    # Doctor Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    # Patient Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patient (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    # Hospital Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hospital (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            mobile TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )
    ''')

    # Blood Bank Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blood_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blood_group TEXT NOT NULL,
            available_units INTEGER NOT NULL DEFAULT 0,
            hospital_name TEXT NOT NULL,
            last_updated TEXT DEFAULT (DATE('now'))
        )
    ''')

    # Insert sample hospital data if table is empty
    cursor.execute("SELECT COUNT(*) FROM hospital")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO hospital (name, address, mobile, email) VALUES (?, ?, ?, ?)", [
            ('City Hospital', '123 Main Street, City', '9876543210', 'city@hospital.com'),
            ('Green Cross Hospital', '456 Park Road, Town', '9876543211', 'green@hospital.com'),
            ('Sunrise Medical Center', '789 Lake View, Metro', '9876543212', 'sunrise@hospital.com'),
        ])

    # Insert sample blood bank data if table is empty
    cursor.execute("SELECT COUNT(*) FROM blood_bank")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO blood_bank (blood_group, available_units, hospital_name) VALUES (?, ?, ?)", [
            ('A+', 15, 'City Hospital'),
            ('A-', 8,  'City Hospital'),
            ('B+', 20, 'Green Cross Hospital'),
            ('B-', 5,  'Green Cross Hospital'),
            ('O+', 25, 'Sunrise Medical Center'),
            ('O-', 10, 'Sunrise Medical Center'),
            ('AB+', 12, 'City Hospital'),
            ('AB-', 6,  'Green Cross Hospital'),
        ])

    conn.commit()
    conn.close()


# ============================================
# HOME ROUTE
# ============================================

@app.route('/')
def home():
    return render_template('home.html')


# ============================================
# REGISTER ROUTES
# ============================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ""
    if request.method == 'POST':
        role = request.form['role']
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        blood_group = request.form['blood_group']
        mobile = request.form['mobile']
        address = request.form['address']
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()

        try:
            if role == 'donor':
                cursor.execute(
                    "INSERT INTO donor (name, age, gender, blood_group, mobile, address, email, password) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (name, age, gender, blood_group, mobile, address, email, password)
                )
            elif role == 'doctor':
                cursor.execute(
                    "INSERT INTO doctor (name, age, gender, blood_group, mobile, address, email, password) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (name, age, gender, blood_group, mobile, address, email, password)
                )
            elif role == 'patient':
                cursor.execute(
                    "INSERT INTO patient (name, age, gender, blood_group, mobile, address, email, password) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (name, age, gender, blood_group, mobile, address, email, password)
                )
            conn.commit()
            conn.close()
            return redirect(url_for('thankyou'))
        except sqlite3.IntegrityError:
            message = "Error: Email already registered. Please use a different email."
            conn.close()

    return render_template('register.html', message=message)


# ============================================
# LOGIN ROUTES
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ""
    if request.method == 'POST':
        role = request.form['role']
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()

        if role == 'donor':
            cursor.execute("SELECT * FROM donor WHERE email=? AND password=?", (email, password))
        elif role == 'doctor':
            cursor.execute("SELECT * FROM doctor WHERE email=? AND password=?", (email, password))
        elif role == 'patient':
            cursor.execute("SELECT * FROM patient WHERE email=? AND password=?", (email, password))

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
# VIEW ROUTES
# ============================================

@app.route('/view_donor')
def view_donor():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM donor")
    donors = cursor.fetchall()
    conn.close()
    return render_template('view_donor.html', donors=donors)


@app.route('/view_doctor')
def view_doctor():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doctor")
    doctors = cursor.fetchall()
    conn.close()
    return render_template('view_doctor.html', doctors=doctors)


@app.route('/view_patient')
def view_patient():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patient")
    patients = cursor.fetchall()
    conn.close()
    return render_template('view_patient.html', patients=patients)


# ============================================
# DELETE ROUTES
# ============================================

@app.route('/delete_donor/<int:id>')
def delete_donor(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM donor WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_donor'))


@app.route('/delete_doctor/<int:id>')
def delete_doctor(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM doctor WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_doctor'))


@app.route('/delete_patient/<int:id>')
def delete_patient(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM patient WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_patient'))


# ============================================
# EDIT ROUTES - DONOR
# ============================================

@app.route('/edit_donor/<int:id>', methods=['GET', 'POST'])
def edit_donor(id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        blood_group = request.form['blood_group']
        mobile = request.form['mobile']
        address = request.form['address']
        email = request.form['email']
        password = request.form['password']

        cursor.execute('''
            UPDATE donor SET name=?, age=?, gender=?, blood_group=?, mobile=?, address=?, email=?, password=?
            WHERE id=?
        ''', (name, age, gender, blood_group, mobile, address, email, password, id))
        conn.commit()
        conn.close()
        return redirect(url_for('view_donor'))

    cursor.execute("SELECT * FROM donor WHERE id=?", (id,))
    donor = cursor.fetchone()
    conn.close()
    return render_template('edit_donor.html', donor=donor)


# ============================================
# EDIT ROUTES - DOCTOR
# ============================================

@app.route('/edit_doctor/<int:id>', methods=['GET', 'POST'])
def edit_doctor(id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        blood_group = request.form['blood_group']
        mobile = request.form['mobile']
        address = request.form['address']
        email = request.form['email']
        password = request.form['password']

        cursor.execute('''
            UPDATE doctor SET name=?, age=?, gender=?, blood_group=?, mobile=?, address=?, email=?, password=?
            WHERE id=?
        ''', (name, age, gender, blood_group, mobile, address, email, password, id))
        conn.commit()
        conn.close()
        return redirect(url_for('view_doctor'))

    cursor.execute("SELECT * FROM doctor WHERE id=?", (id,))
    doctor = cursor.fetchone()
    conn.close()
    return render_template('edit_doctor.html', doctor=doctor)


# ============================================
# EDIT ROUTES - PATIENT
# ============================================

@app.route('/edit_patient/<int:id>', methods=['GET', 'POST'])
def edit_patient(id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        blood_group = request.form['blood_group']
        mobile = request.form['mobile']
        address = request.form['address']
        email = request.form['email']
        password = request.form['password']

        cursor.execute('''
            UPDATE patient SET name=?, age=?, gender=?, blood_group=?, mobile=?, address=?, email=?, password=?
            WHERE id=?
        ''', (name, age, gender, blood_group, mobile, address, email, password, id))
        conn.commit()
        conn.close()
        return redirect(url_for('view_patient'))

    cursor.execute("SELECT * FROM patient WHERE id=?", (id,))
    patient = cursor.fetchone()
    conn.close()
    return render_template('edit_patient.html', patient=patient)


# ============================================
# REPORT ROUTE
# ============================================

@app.route('/report')
def report():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blood_bank ORDER BY hospital_name, blood_group")
    report_data = cursor.fetchall()
    conn.close()
    return render_template('report.html', report_data=report_data)


# ============================================
# THANK YOU ROUTE
# ============================================

@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')


# ============================================
# RUN APP
# ============================================

if __name__ == '__main__':
    init_db()
    app.run(debug=False)

init_db()