
# Computer Equipment Checkout and Tracking System

## CIT Capstone Project
William Paterson University

## Project Overview

The Computer Equipment Checkout and Tracking System is a web-based application designed to help college IT departments manage equipment loans to students.

The system tracks laptops, tablets, chargers, and other equipment throughout the checkout and return process.

It replaces manual tracking methods with a centralized system that helps technicians monitor equipment availability, student borrowing records, and overdue loans.

## Project Goals

- Improve the accuracy of equipment inventory records.
- Reduce the risk of lost or untracked equipment.
- Help IT technicians manage student equipment loans.
- Track equipment availability and overdue checkouts.
- Potentially reduce unnecessary replacement costs through better asset tracking.


## Application Features

### 1. Technician Authentication
- Uses Django's authentication system.
- Restricts equipment management pages to authorized staff.
- Records the technician responsible for equipment checkouts and returns.

### 2. Student Lookup
- Searches for students using their university student ID.
- Displays student information and enrollment status.
- Uses fictional student records for testing.

### 3. Equipment Inventory
- Tracks equipment using unique asset tags.
- Stores equipment type, manufacturer, model, and status.
- Supports laptops, tablets, chargers, and other accessories.
- Maintains equipment availability information.

### 4. Equipment Checkout
- Allows authorized technicians to issue available equipment.
- Supports loan periods from 3 hours to 7 days.
- Automatically includes an available charger when required.
- Prevents students from borrowing multiple laptops simultaneously.
- Prevents inactive students from checking out equipment.
- Records checkout dates, due dates, and technician information.

### 5. Equipment Return
- Allows technicians to select active checkouts.
- Requires confirmation that equipment has been returned and inspected.
- Records the return date and receiving technician.
- Updates returned equipment to Available status.

### 6. Inventory Dashboard
- Displays total equipment.
- Shows available, checked-out, and maintenance equipment counts.
- Displays the number of active and overdue loans.

### 7. Automated Testing
- Includes Django unit tests for equipment availability and staff permissions.
- Uses a local SQLite database for development and testing.


## System Requirements

- Python 3.13 or compatible version
- Django 5.2
- Git
- Web browser
- SQLite (included with Python)

## Installation Instructions

### 1. Clone the Repository

```powershell
git clone https://github.com/Jay-Milton2026/EquipmentCheckoutSystem.git
cd EquipmentCheckoutSystem
```

Note: The repository is currently private. Access must be granted before it can be cloned.

### 2. Create a Virtual Environment

```powershell
python -m venv .venv
```

Activate the virtual environment on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure the Environment

Create a file named `.env` in the main project folder.

Add the following variable:

```text
DJANGO_SECRET_KEY=replace-with-a-unique-secret-key
```

Generate a unique secret key for your own installation. Do not reuse another installation's secret key or commit the `.env` file to GitHub.

### 5. Set Up the Database

```powershell
python manage.py migrate
```

### 6. Create an Administrator Account

```powershell
python manage.py createsuperuser
```

Follow the prompts to create your administrator account.

### 7. Start the Application

```powershell
python manage.py runserver
```

Open your browser and visit:

http://127.0.0.1:8000/admin/

Sign in as the administrator to add students and equipment before testing the checkout workflow.

## Application Pages

- Dashboard: http://127.0.0.1:8000/dashboard/
- Student Lookup: http://127.0.0.1:8000/student-lookup/
- Equipment Checkout: http://127.0.0.1:8000/equipment-checkout/
- Equipment Return: http://127.0.0.1:8000/equipment-return/

## Run Automated Tests

```powershell
python manage.py test inventory
```

The application uses fictional student and equipment records for demonstration purposes.


## Current Limitations

- The application uses fictional student records rather than connecting to William Paterson University's student information system.
- SQLite is used for local development and testing. A production deployment would require additional evaluation of database concurrency and reliability.
- Charger assignment is based on equipment category and does not yet verify model-specific compatibility.
- Missing or damaged equipment requires administrative handling; a dedicated incident reporting workflow has not been implemented.
- Equipment records can be edited through Django's administration interface, so additional safeguards would be needed before deploying the system in a real IT department.
- The application is a working academic prototype, not a production-ready university system.

## Future Enhancements

- Barcode or QR-code scanning for faster equipment identification.
- Automated email reminders for overdue equipment.
- An incident reporting system for lost or damaged equipment.
- Supervisor approval workflows for borrowing exceptions.
- Equipment repair and maintenance history.
- Improved reporting and inventory audit capabilities.
- A production-grade database and deployment configuration.
- Integration with an authorized university student information system.

## Project Status

The minimum viable product (MVP) has been implemented using Python, Django, and SQLite.

The application supports technician authentication, student lookup, equipment inventory management, equipment checkout and return workflows, and an inventory dashboard.

Additional security testing, deployment preparation, and production safeguards would be required before real-world institutional use.
