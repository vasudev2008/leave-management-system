# LOCKTITE INDIA PVT LTD
## Employee Leave Management System

A professional, secure, simple, and offline-first **Employee Leave Management System** custom-built for **Locktite India Pvt Ltd** official office use.

---

## 🏢 1. System Overview

* **Company Name:** Locktite India Pvt Ltd
* **Architecture:** Offline-First Desktop Application (FastAPI + SQLite + Native Desktop App Window)
* **Database:** Local SQLite (`locktite_leave.db`) with Write-Ahead Logging (WAL) and Foreign Key integrity
* **Security:** PBKDF2-HMAC-SHA256 password hashing with unique per-user salts, role-based access control (RBAC), and password-authorized administrative confirmations
* **Reports:** Print-ready official letterhead formats, ReportLab PDF generation, styled Excel (`.xlsx`) via openpyxl/pandas, and CSV exports

---

## 🚀 2. Quick Start & How to Run

### Option A: One-Click Desktop Batch File (Recommended for Office Staff)
Double-click `run_app.bat` inside this folder.
The application will automatically initialize the local database, start the offline service, and open directly in a standalone desktop window (using Microsoft Edge or Google Chrome desktop app mode with no browser address bar or tabs).

### Option B: Terminal Command
```powershell
python run_app.py
```
Or run directly with Uvicorn:
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open **`http://127.0.0.1:8000`** in your browser.

---

## 👥 3. Default User Accounts & Roles

The system comes pre-configured with three official staff accounts:

| User ID | Password | Role | Permissions |
| :--- | :--- | :--- | :--- |
| **`admin`** | `admin123` | **ADMIN** | Full system access: User management, employee CRUD, entitlement modification, leave entry/cancellations, reports & exports, audit trail, online database backup & restore, settings. |
| **`entry1`** | `entry123` | **ENTRY USER** | Office entry clerk: Employee directory search, add leave entries (ADD), process adjustments/cancellations (LESS), view leave history. |
| **`report1`** | `report123` | **REPORT USER** | Auditing & records: View and filter reports, print official employee statements, export PDF, Excel, and CSV files. |

> *Note: Users can change their password at any time via the **🔑 Password** button in the sidebar footer.*

---

## 📋 4. Core Modules & Functionality

### 1. Main Dashboard
* Displays company branding: **Locktite India Pvt Ltd**
* Current active date and live clock
* 5 Real-time Summary Metric Cards:
  1. **Total Employees**
  2. **Active Employees**
  3. **Employees on Leave Today** (with quick table of who is away today)
  4. **Total Leave Taken** (cumulative days across organization)
  5. **Low Leave Balance Alert** (employees with balance $\le$ 3.0 days)
* Quick Action Buttons: New Employee, Leave Entry, Leave Adjustment, Employee Report

### 2. Employee Master
* **Automatic Sequential Employee Number:** System automatically calculates and generates `EMP0001`, `EMP0002`, `EMP0003`... preventing manual entry mistakes and guaranteeing uniqueness.
* **Fields:** Employee Number (Auto), Name, Department, Designation, Date of Joining, Date of Birth, Mobile, Email, Residential Address, Leave Entitlement, Opening Balance, Status (Active/Inactive), Remarks.
* **Live Search & Filters:** Search by ID, Name, Department, or Status.
* **Master Security:** Modifying Leave Entitlement or Opening Balance requires the Administrator password to prevent unauthorized adjustments.
* **Safe Deactivation vs Deletion:** System encourages deactivating staff to maintain compliance history. Permanent deletion requires admin password and is blocked if leave transactions exist.

### 3. Leave Operations (Entry Module)
* **ADD Leave:**
  - Select employee (live profile & balance card displays instantly).
  - Select leave type: Casual Leave, Sick Leave, Earned Leave, Maternity Leave, Paternity Leave, Compensatory Off, Other Leave.
  - Choose From Date and To Date (days auto-calculate with half-day support).
  - Balance validation: Blocks entry if requested days exceed current available balance (e.g. *"Leave balance is insufficient. Available balance: 2.0 days"*). Admin override option available if authorized.
  - Prevents accidental duplicate submissions.
* **LESS / Cancel Leave (Adjustment):**
  - Used when leave was cancelled, entered incorrectly, or days need reduction.
  - **Maintains complete transaction history:** Never overwrites previous records; instead, it logs an official `LESS` transaction that credits the days back to the employee's balance.
  - Mandatory justification remarks required.
* **Leave Transaction History:**
  - Complete log with Transaction ID (`LTX-0001`), Employee details, Type (`ADD` / `LESS`), Dates, Days, Remarks, Recorded By, and Timestamp.
  - 1-click **"Less / Cancel"** shortcut button on prior entries.

### 4. Official Reports Module
* Official Header on every report:
  ```
  LOCKTITE INDIA PVT LTD
  EMPLOYEE LEAVE MANAGEMENT SYSTEM
  [REPORT TITLE]
  ```
* **Individual Employee Leave Statement:**
  - Complete statement of employee profile, entitlement, opening balance, leave taken, and current balance.
  - Detailed statement table with transaction types, days, dates, reasons, and recording staff.
  - Formal signature block: *Prepared By (Office Staff / HR)*, *Verified By (Department Head)*, *Authorized Signatory (Locktite India Pvt Ltd)*.
  - Actions: **Print**, **Export PDF** (ReportLab), **Export Excel** (`.xlsx`), **Export CSV**.
* **All Employees Leave Summary Report:**
  - Department and Status filters.
  - Table: Employee No, Name, Department, Designation, Entitlement, Opening, Taken, Balance, Status.
  - Summary row with totals across all columns.
  - Official sign-off blocks.
  - Actions: **Print**, **Export PDF**, **Export Excel**, **Export CSV**.

### 5. Administration & Governance
* **User Management:** Add staff, update roles, reset passwords, activate/deactivate accounts.
* **Leave Categories:** Create and toggle official leave types.
* **Immutable Audit Trail:** Logs all critical actions (employee created, edited, leaves added, adjustments, backups, logins) with user ID, employee number, timestamp, and description. Exportable to CSV.
* **Online SQLite Backup & Restore:**
  - Uses SQLite's online backup API for zero-downtime, non-locking database backups.
  - Download backups directly to USB or external drives.
  - Restore previous backups with mandatory confirmation warning and admin password authentication (system automatically saves a safety copy before any restore).

---

## 🧮 5. Leave Calculation Formula

The system uses an unambiguous, auditable mathematical formula:

$$\text{Leave Taken} = \sum (\text{Days for ADD transactions}) - \sum (\text{Days for LESS transactions})$$

$$\text{Current Available Balance} = \text{Opening Balance} - \text{Leave Taken}$$

*Example from Official Specifications:*
- Opening Balance = 20 days
- Add Casual Leave = 2 days
- Add Sick Leave = 1 day
- Less Casual Leave = 1 day (cancelled)
- Total Leave Taken = $2 + 1 - 1 = 2$ days
- Current Balance = $20 - 2 = 18$ days

---

## 🧪 6. Automated Test Suite

A complete test suite is provided in `tests/test_all_features.py` verifying all 13 core requirements:
```powershell
python tests/test_all_features.py
```
**Results: 13 / 13 Tests Passed (100% OK)**

---

## 📂 7. Project Structure

```
locktite_leave_management/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI REST APIs & request routing
│   ├── database.py          # SQLite schema, triggers, seed data, calculations
│   ├── auth.py              # PBKDF2 hashing, sessions, role authorization
│   ├── models.py            # Pydantic schemas and strict validation
│   ├── reports.py           # ReportLab PDF generation and openpyxl Excel exports
│   ├── audit.py             # Audit trail logger
│   ├── static/              # 100% offline assets (CSS, JS, fonts, icons)
│   │   ├── css/app.css      # Desktop styling, themes, print layout
│   │   └── js/app.js        # Single-page desktop app controller
│   └── templates/
│       └── index.html       # Standalone desktop single-page container
├── backups/                 # Timestamped SQLite database backup storage
├── tests/
│   └── test_all_features.py # Automated test suite covering all requirements
├── locktite_leave.db        # Production local SQLite database
├── run_app.bat              # One-click Windows desktop launcher
├── run_app.py               # Standalone desktop window launcher
├── requirements.txt         # Dependencies
└── README.md                # System documentation
```

---
**Locktite India Pvt Ltd &copy; 2026. Confidential — For Official Office Use Only.**
