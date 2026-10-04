from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'

db = SQLAlchemy(app)

# 1. Employee Model (Updated with Shift 1/2/3, Branch, Advance & Bonus)
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

# 2. Attendance Model (Updated for Late Minutes, Overtime & Status tracking)
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    in_time = db.Column(db.String(20), nullable=True)
    out_time = db.Column(db.String(20), nullable=True)
    working_hours = db.Column(db.Float, nullable=True, default=0.0)
    late_minutes = db.Column(db.Integer, default=0)       # Kiti minute ushi ala
    overtime_hours = db.Column(db.Float, default=0.0)     # Kiti extra taas kam kele
    status = db.Column(db.String(20), nullable=False, default='Present') # Present, Half-Day

# 3. Leave Model
class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    start_date = db.Column(db.String(20), nullable=False)
    end_date = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.String(250), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')

# 4. Holiday Model (New Feature for Public Holidays)
class Holiday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)

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

# Add Employee Route (Supports Shift 1/2/3 & Branch)
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
        db.session.add(new_emp)
        db.session.commit()
        return redirect(url_for('dashboard'))
        
    return render_template('add_employee.html')

# Edit Employee Route
@app.route('/edit_employee/<int:id>', methods=['GET', 'POST'])
def edit_employee(id):
    if 'user_id' not in session or session.get('role') != 'Admin':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    employee = Employee.query.get_or_404(id)
    
    if request.method == 'POST':
        employee.name = request.form.get('name')
        employee.email = request.form.get('email')
        employee.fingerprint_id = int(request.form.get('fingerprint_id')) if request.form.get('fingerprint_id') else None
        employee.basic_salary = float(request.form.get('basic_salary', 15000.0))
        employee.shift = request.form.get('shift', employee.shift)
        employee.branch = request.form.get('branch', employee.branch)
        employee.advance_salary = float(request.form.get('advance_salary', 0.0))
        employee.bonus = float(request.form.get('bonus', 0.0))
        
        db.session.commit()
        return redirect(url_for('dashboard'))
        
    return render_template('edit_employee.html', employee=employee)

# Holiday Calendar Management Route (Admin)
@app.route('/manage_holidays', methods=['GET', 'POST'])
def manage_holidays():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    if request.method == 'POST':
        date = request.form.get('date')
        name = request.form.get('name')
        
        existing = Holiday.query.filter_by(date=date).first()
        if not existing:
            db.session.add(Holiday(date=date, name=name))
            db.session.commit()
        return redirect(url_for('manage_holidays'))
        
    holidays = Holiday.query.order_by(Holiday.date.asc()).all()
    return render_template('manage_holidays.html', holidays=holidays)

# Delete Holiday Route (Admin)
@app.route('/delete_holiday/<int:id>')
def delete_holiday(id):
    if 'user_id' not in session or session.get('role') != 'Admin':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    holiday = Holiday.query.get(id)
    if holiday:
        db.session.delete(holiday)
        db.session.commit()
    return redirect(url_for('manage_holidays'))

# Employee Dashboard Route
@app.route('/employee_dashboard')
def employee_dashboard():
    if 'user_id' not in session or session.get('role') != 'Employee':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    emp_id = session['user_id']
    employee = Employee.query.get(emp_id)
    today_date = datetime.now().strftime('%Y-%m-%d')
    today_attendance = Attendance.query.filter_by(employee_id=emp_id, date=today_date).first()
    emp_leaves = Leave.query.filter_by(employee_id=emp_id).all()
    history = Attendance.query.filter_by(employee_id=emp_id).order_by(Attendance.date.desc()).all()
    
    return render_template('employee_dashboard.html', employee=employee, attendance=today_attendance, leaves=emp_leaves, history=history)

# Punch In Route (With Holiday Check, Anti-Passback & Shift-based Late calculation)
@app.route('/punch_in', methods=['POST'])
def punch_in():
    if 'user_id' not in session or session.get('role') != 'Employee':
        return redirect(url_for('login'))
        
    emp_id = session['user_id']
    employee = Employee.query.get(emp_id)
    today_date = datetime.now().strftime('%Y-%m-%d')
    current_time_str = datetime.now().strftime('%H:%M:%S')
    
    # 1. Holiday Check
    is_holiday = Holiday.query.filter_by(date=today_date).first()
    if is_holiday:
        return f"Today is a Public Holiday ({is_holiday.name})! Attendance not required. <a href='/employee_dashboard'>Go Back</a>"
    
    # 2. Anti-Passback / Double Punch Prevention Check
    existing = Attendance.query.filter_by(employee_id=emp_id, date=today_date).first()
    if existing:
        return "Error: You have already punched in today! Double punch is not allowed. <a href='/employee_dashboard'>Go Back</a>"
        
    # Shift timing selection
    shift_start_time = "09:00:00"
    if "Shift 2" in employee.shift or "2" in employee.shift:
        shift_start_time = "14:00:00"
    elif "Shift 3" in employee.shift or "3" in employee.shift:
        shift_start_time = "22:00:00"
        
    fmt = '%H:%M:%S'
    t_in = datetime.strptime(current_time_str, fmt)
    t_standard = datetime.strptime(shift_start_time, fmt)
    
    late_mins = 0
    if t_in > t_standard:
        diff = t_in - t_standard
        late_mins = int(diff.total_seconds() / 60)
        
    new_attendance = Attendance(
        employee_id=emp_id,
        date=today_date,
        in_time=current_time_str,
        late_minutes=late_mins,
        status='Present'
    )
    db.session.add(new_attendance)
    db.session.commit()
        
    return redirect(url_for('employee_dashboard'))

# Punch Out Route (With Overtime & Half-Day Calculation)
@app.route('/punch_out', methods=['POST'])
def punch_out():
    if 'user_id' not in session or session.get('role') != 'Employee':
        return redirect(url_for('login'))
        
    emp_id = session['user_id']
    today_date = datetime.now().strftime('%Y-%m-%d')
    current_time_str = datetime.now().strftime('%H:%M:%S')
    
    attendance = Attendance.query.filter_by(employee_id=emp_id, date=today_date).first()
    if attendance and not attendance.out_time:
        attendance.out_time = current_time_str
        fmt = '%H:%M:%S'
        t1 = datetime.strptime(attendance.in_time, fmt)
        t2 = datetime.strptime(current_time_str, fmt)
        hours = round((t2 - t1).total_seconds() / 3600, 2)
        attendance.working_hours = hours
        
        if hours > 8.0:
            attendance.overtime_hours = round(hours - 8.0, 2)
        else:
            attendance.overtime_hours = 0.0
            
        if hours < 4.5:
            attendance.status = 'Half-Day'
        else:
            attendance.status = 'Present'
            
        db.session.commit()
        
    return redirect(url_for('employee_dashboard'))

# Live Attendance Logs Route (Admin)
@app.route('/attendance_logs')
def attendance_logs():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    logs = db.session.query(Attendance, Employee).join(Employee, Attendance.employee_id == Employee.id).order_by(Attendance.date.desc()).all()
    return render_template('attendance_logs.html', logs=logs)

# Apply Leave Route
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

# Manage Leaves Route (Admin)
@app.route('/manage_leaves')
def manage_leaves():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    leaves = db.session.query(Leave, Employee).join(Employee, Leave.employee_id == Employee.id).all()
    return render_template('manage_leaves.html', leaves=leaves)

# Update Leave Status Route (Admin)
@app.route('/update_leave/<int:leave_id>/<status>')
def update_leave(leave_id, status):
    if 'user_id' not in session or session.get('role') != 'Admin':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    leave = Leave.query.get(leave_id)
    if leave:
        leave.status = status
        db.session.commit()
        
    return redirect(url_for('manage_leaves'))

# Enhanced Helper Function for Salary Calculation
def calculate_salary_data():
    employees = Employee.query.all()
    report_data = []
    total_company_working_days = 26 
    
    for emp in employees:
        basic_salary = emp.basic_salary if emp.basic_salary else 15000.0
        per_day_salary = basic_salary / total_company_working_days if total_company_working_days > 0 else 0
        per_hour_salary = per_day_salary / 8.0 
        
        attendances = Attendance.query.filter_by(employee_id=emp.id).all()
        full_days = sum(1 for a in attendances if a.status == 'Present')
        half_days = sum(1 for a in attendances if a.status == 'Half-Day')
        total_overtime_hours = sum(a.overtime_hours for a in attendances)
        
        effective_present_days = full_days + (half_days * 0.5)
        overtime_pay = total_overtime_hours * per_hour_salary * 1.5
        gross_salary = (effective_present_days * per_day_salary) + overtime_pay
        net_salary = gross_salary + emp.bonus - emp.advance_salary
        
        report_data.append({
            'employee': emp,
            'present_days': full_days,
            'half_days': half_days,
            'effective_days': effective_present_days,
            'total_company_days': total_company_working_days,
            'per_day_salary': round(per_day_salary, 2),
            'total_overtime_hours': round(total_overtime_hours, 2),
            'overtime_pay': round(overtime_pay, 2),
            'bonus': emp.bonus,
            'advance_salary': emp.advance_salary,
            'net_salary': round(max(0, net_salary), 2)
        })
    return report_data

# Salary Report Route (Admin)
@app.route('/salary_report')
def salary_report():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    report_data = calculate_salary_data()
    return render_template('salary_report.html', report_data=report_data)

# Print / PDF Report Route (Admin)
@app.route('/print_report')
def print_report():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    report_data = calculate_salary_data()
    return render_template('print_report.html', report_data=report_data)

# EXCEL REPORT DOWNLOAD ROUTE
@app.route('/download_excel')
def download_excel():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return "Access Denied! <a href='/'>Login Here</a>"
        
    report_data = calculate_salary_data()
    excel_list = []
    
    for item in report_data:
        excel_list.append({
            'Employee Name': item['employee'].name,
            'Email': item['employee'].email,
            'Branch': item['employee'].branch,
            'Shift': item['employee'].shift,
            'Basic Salary (INR)': item['employee'].basic_salary,
            'Full Days': item['present_days'],
            'Half Days': item['half_days'],
            'Effective Days': item['effective_days'],
            'Overtime Hours': item['total_overtime_hours'],
            'Overtime Pay (INR)': item['overtime_pay'],
            'Bonus (INR)': item['bonus'],
            'Advance Deduction (INR)': item['advance_salary'],
            'Net Payable Salary (INR)': item['net_salary']
        })
        
    df = pd.DataFrame(excel_list)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Salary Report')
    output.seek(0)
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='Advanced_Salary_Report.xlsx')

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
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
            
    app.run(debug=True)