
-- 1. Donor Table
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
);

-- 2. Doctor Table
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
);

-- 3. Patient Table
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
);

-- 4. Hospital Table
CREATE TABLE IF NOT EXISTS hospital (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    mobile TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);

-- 5. Blood Bank Table
CREATE TABLE IF NOT EXISTS blood_bank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blood_group TEXT NOT NULL,
    available_units INTEGER NOT NULL DEFAULT 0,
    hospital_name TEXT NOT NULL,
    last_updated TEXT DEFAULT (DATE('now'))
);

-- ============================================
-- Sample Data for Blood Bank Report
-- ============================================

INSERT INTO hospital (name, address, mobile, email) VALUES
('City Hospital', '123 Main Street, City', '9876543210', 'city@hospital.com'),
('Green Cross Hospital', '456 Park Road, Town', '9876543211', 'green@hospital.com'),
('Sunrise Medical Center', '789 Lake View, Metro', '9876543212', 'sunrise@hospital.com');

INSERT INTO blood_bank (blood_group, available_units, hospital_name) VALUES
('A+', 15, 'City Hospital'),
('A-', 8,  'City Hospital'),
('B+', 20, 'Green Cross Hospital'),
('B-', 5,  'Green Cross Hospital'),
('O+', 25, 'Sunrise Medical Center'),
('O-', 10, 'Sunrise Medical Center'),
('AB+', 12, 'City Hospital'),
('AB-', 6,  'Green Cross Hospital');
