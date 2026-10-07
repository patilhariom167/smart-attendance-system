from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, time
import pytz
import pandas as pd
import io
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

# PostgreSQL & SQLite Compatibility Configuration
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///attendance.db'

db = SQLAlchemy(app)

# IST Timezone Definition
IST = pytz.timezone('Asia/Kolkata')

def get_current_ist_time():
    """Returns current date and time in Indian Standard Time (IST)"""
    return datetime.now(IST)

# 1. Employee Model
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='Employee')
    fingerprint_id = db.Column(db.Integer, unique=True, nullable=True)
    basic_salary = db.Column(db.Float, nullable=False, default=15000.0)
    shift = db.Column(db.String(50), nullable=False, default='Shift 1 (9 AM)')
    branch = db.Column(db.String(100), nullable=False, default='Head Office')
    advance_salary = db.Column(db.Float, nullable=False, default=0.0)
    bonus = db.Column(db.Float, nullable=False, default=0.0)

# 2. Attendance Model
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    in_time = db.Column(db.String(20), nullable=True)
    out_time = db.Column(db.String(20), nullable=True)
    working_hours = db.Column(db.Float, nullable=True, default=0.0)
    late_minutes = db.Column(db.Integer, default=0)       
    overtime_hours = db.Column(db.Float, default=0.0)     
    status = db.Column(db.String(20), nullable=False, default='Present')
    
    # Relationship to access employee details directly
    employee = db.relationship('Employee', backref=db.backref('attendances', lazy=True))

# 3. Leave Model
class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    start_date = db.Column(db.String(20), nullable=False)
    end_date = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.String(250), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')

# 4. Holiday Model
class Holiday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)

# Database Tables & Default Admin Creation
with app.app_context():
    db.create_all()
    admin_exists = Employee.query.filter_by(email='admin@gmail.com').first()
    if not admin_exists:
        default_admin = Employee(
            name='Admin User',
            email='admin@gmail.com',
            password='123',
            role='Admin',
            basic_salary=25000.0,
            shift='Shift 1 (9 AM)',
            branch='Head Office'
        )
        db.session.add(default_admin)
        db.session.commit()

# Login Route
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = Employee.query.filter_by(email=email).first()
        
        if user and user.password == password:
            session['user_id'] = user.id
            session['role'] = user.role
            session['user_name'] = user.name
            if user.role == 'Admin':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('employee_dashboard'))
        else:
            return 'Invalid Email or Password! <a href="/">Go Back</a>'
            
    return render_template('login.html')

# Admin Dashboard Route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    all_employees = Employee.query.all()
    return render_template('dashboard.html', employees=all_employees)

# Add Employee Route
@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'Employee')
        fingerprint_id = request.form.get('fingerprint_id')
        basic_salary = request.form.get('basic_salary', 15000.0)
        shift = request.form.get('shift', 'Shift 1 (9 AM)')
        branch = request.form.get('branch', 'Head Office')
        
        existing = Employee.query.filter_by(email=email).first()
        if existing:
            return "Email already registered! <a href='/dashboard'>Go Back</a>"
            
        new_emp = Employee(
            name=name,
            email=email,
            password=password,
            role=role,
            fingerprint_id=int(fingerprint_id) if fingerprint_id else None,
            basic_salary=float(basic_salary) if basic_salary else 15000.0,
            shift=shift,
            branch=branch
        )
        db.session.addS