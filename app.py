from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'

db = SQLAlchemy(app)

# 1. Employee Model (Updated with Basic Salary)
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='Employee')
    fingerprint_id = db.Column(db.Integer, unique=True, nullable=True)
    basic_salary = db.Column(db.Float, nullable=False, default=15000.0)

# 2. Attendance Model (Punch In / Out & Hours)
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    in_time = db.Column(db.String(20), nullable=True)
    out_time = db.Column(db.String(20), nullable=True)
    working_hours = db.Column(db.Float, nullable=True, default=0.0)
    status = db.Column(db.String(20), nullable=False, default='Present')

# 3. Leave Model (Leave Request & Approval)
class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    start_date = db.Column(db.String(20), nullable=False)
    end_date = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.String(250), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')

# Login Route (Updated with Employee redirection)
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
        
        existing = Employee.query.filter_by(email=email).first()
        if existing:
            return "Email already registered! <a href='/dashboard'>Go Back</a>"
            
        new_emp = Employee(
            name=name,
            email=email,
            password=password,
            role=role,
            fingerprint_id=int(fingerprint_id) if fingerprint_id else None,
            basic_salary=float(basic_salary) if basic_salary else 15000.0
        )
        db.session.add(new_emp)
        db.session.commit()
        return redirect(url_for('dashboard'))
        
    return render_template('add_employee.html')

# --- PHASE 2: EMPLOYEE PORTAL & PUNCH IN / OUT ---

# Employee Dashboard Route (Updated with Leaves)
@app.route('/employee_dashboard')
def employee_dashboard():
    if 'user_id' not in session or session.get('role') != 'Employee':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    emp_id = session['user_id']
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    # Aajchi attendance check kara
    today_attendance = Attendance.query.filter_by(employee_id=emp_id, date=today_date).first()
    
    # Tyachya sagle leave requests fetch kara
    emp_leaves = Leave.query.filter_by(employee_id=emp_id).all()
    
    return render_template('employee_dashboard.html', attendance=today_attendance, leaves=emp_leaves)

# Punch In Route
@app.route('/punch_in', methods=['POST'])
def punch_in():
    if 'user_id' not in session or session.get('role') != 'Employee':
        return redirect(url_for('login'))
        
    emp_id = session['user_id']
    today_date = datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.now().strftime('%H:%M:%S')
    
    existing = Attendance.query.filter_by(employee_id=emp_id, date=today_date).first()
    if not existing:
        new_attendance = Attendance(
            employee_id=emp_id,
            date=today_date,
            in_time=current_time,
            status='Present'
        )
        db.session.add(new_attendance)
        db.session.commit()
        
    return redirect(url_for('employee_dashboard'))

# Punch Out Route
@app.route('/punch_out', methods=['POST'])
def punch_out():
    if 'user_id' not in session or session.get('role') != 'Employee':
        return redirect(url_for('login'))
        
    emp_id = session['user_id']
    today_date = datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.now().strftime('%H:%M:%S')
    
    attendance = Attendance.query.filter_by(employee_id=emp_id, date=today_date).first()
    if attendance and not attendance.out_time:
        attendance.out_time = current_time
        
        # Working hours calculate karne
        fmt = '%H:%M:%S'
        t1 = datetime.strptime(attendance.in_time, fmt)
        t2 = datetime.strptime(current_time, fmt)
        diff = t2 - t1
        hours = round(diff.total_seconds() / 3600, 2)
        attendance.working_hours = hours
        
        db.session.commit()
        
    return redirect(url_for('employee_dashboard'))


# --- PHASE 3: LEAVE MANAGEMENT SYSTEM ---

# Employee: Apply for Leave Route
@app.route('/apply_leave', methods=['GET', 'POST'])
def apply_leave():
    if 'user_id' not in session or session.get('role') != 'Employee':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        reason = request.form.get('reason')
        
        new_leave = Leave(
            employee_id=session['user_id'],
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            status='Pending'
        )
        db.session.add(new_leave)
        db.session.commit()
        return redirect(url_for('employee_dashboard'))
        
    return render_template('apply_leave.html')

# Admin: View & Manage Leave Requests Route
@app.route('/manage_leaves')
def manage_leaves():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    leaves = db.session.query(Leave, Employee).join(Employee, Leave.employee_id == Employee.id).all()
    return render_template('manage_leaves.html', leaves=leaves)

# Admin: Update Leave Status (Approve / Reject)
@app.route('/update_leave/<int:leave_id>/<status>')
def update_leave(leave_id, status):
    if 'user_id' not in session or session.get('role') != 'Admin':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    leave = Leave.query.get(leave_id)
    if leave:
        leave.status = status
        db.session.commit()
        
    return redirect(url_for('manage_leaves'))


# --- PHASE 4: ADVANCED SALARY REPORTING ROUTE ---

@app.route('/salary_report')
def salary_report():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return "Access Denied! <a href='/'>Login Here</a>"
    
    # Sagle employees fetch kara (Admin vahun itar employees)
    employees = Employee.query.all()
    report_data = []
    
    # Samza mahinyatle total standard working days 26 ahet (Sundays & Holidays vahun)
    total_company_working_days = 26 
    
    for emp in employees:
        basic_salary = emp.basic_salary if emp.basic_salary else 15000.0
        
        # Per day salary formula: Basic Salary / Total Company Working Days
        per_day_salary = basic_salary / total_company_working_days if total_company_working_days > 0 else 0
        
        # Employee ne kiti divas kam kel (Attendance records count)
        attendances = Attendance.query.filter_by(employee_id=emp.id).all()
        present_days = len(attendances)
        
        # Net Payable Salary Calculation based on present days
        net_salary = present_days * per_day_salary
        
        report_data.append({
            'employee': emp,
            'present_days': present_days,
            'total_company_days': total_company_working_days,
            'per_day_salary': round(per_day_salary, 2),
            'net_salary': round(net_salary, 2)
        })
        
    return render_template('salary_report.html', report_data=report_data)


# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Default Admin check
        admin_exists = Employee.query.filter_by(email='admin@gmail.com').first()
        if not admin_exists:
            default_admin = Employee(
                name='Admin User',
                email='admin@gmail.com',
                password='123',
                role='Admin',
                basic_salary=25000.0
            )
            db.session.add(default_admin)
            db.session.commit()
            
    app.run(debug=True)