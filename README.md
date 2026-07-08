#  Smart Employee Wellness and Productivity Assistant

A web-based Employee Management System developed using **Python Django** to improve employee productivity, security, and well-being through AI-assisted monitoring and analytics.

---

##  Overview

Smart Employee Wellness and Productivity Assistant is that combines traditional employee management with intelligent wellness monitoring.

The system helps organizations:

- Manage employees efficiently
- Track attendance securely
- Monitor employee wellness
- Analyze productivity
- Manage payroll and leave
- Generate reports and dashboards

---

##  Features

###  User Management
- Employee Registration
- Secure Login
- Role-Based Access (Admin, HR, Employee)
- User Approval System

###  Smart Attendance
- Face Recognition Attendance
- GPS Validation
- Wi-Fi Validation
- Login/Logout Tracking
- Working Hours Calculation

###  Employee Wellness
- Stress Monitoring
- Mood Tracking
- Mental Fatigue Analysis
- Burnout Risk Detection
- Break Time Monitoring

###  Productivity Analysis
- Task Tracking
- Performance Analysis
- Efficiency Score
- Productivity Reports

###  Leave Management
- Apply Leave
- Leave Approval
- Leave Status Tracking

###  Payroll Management
- Salary Calculation
- HRA
- DA
- TA
- PF
- Payslip Generation

###  Dashboard & Reports
- Attendance Reports
- Productivity Reports
- Wellness Reports
- Payroll Reports
- Interactive Charts

---

## Tech Stack

### Frontend
- HTML5
- CSS3
- JavaScript
- Bootstrap

### Backend
- Python
- Django

### Database
- SQLite
- PostgreSQL (Supported)

### AI & Data Analysis
- Face Recognition
- Pandas
- Matplotlib
- Plotly

---

## User Roles

### Admin
- Manage Employees
- View Reports
- Payroll
- Leave Management
- Analytics Dashboard

### HR
- Employee Management
- Attendance Management
- Leave Approval
- Payroll

### Employee
- Mark Attendance
- Wellness Scan
- Apply Leave
- View Payslip
- Profile Management

---

## ⚙️ Installation

### Clone Repository

```bash
git clone https://github.com/Megatron-z/smart-employee-wellness-productivity-assistant.git
```

### Move into Project

```bash
cd smart-employee-wellness-productivity-assistant
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Environment

#### Linux / macOS

```bash
source venv/bin/activate
```

#### Windows

```bash
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Apply Migrations

```bash
python manage.py migrate
```

### Create Superuser

```bash
python manage.py createsuperuser
```

### Run Server

```bash
python manage.py runserver
```

Open:

```
http://127.0.0.1:8000
```

