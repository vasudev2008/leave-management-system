/**
 * Locktite India Pvt Ltd - Employee Leave Management System
 * Front-end Application Controller & State Engine
 */

// Application State
const State = {
  token: localStorage.getItem("locktite_token") || null,
  user: JSON.parse(localStorage.getItem("locktite_user") || "null"),
  activeTab: "dashboard",
  employees: [],
  leaveTypes: [],
  departments: ["Administration", "Accounts", "Human Resources", "Production", "Quality Assurance", "Logistics", "Sales & Marketing", "IT & Maintenance"],
  selectedEmployeeForEntry: null,
  dashboardStats: null,
};

// API Client Helper
async function api(endpoint, options = {}) {
  const headers = options.headers || {};
  if (State.token) {
    headers["Authorization"] = `Bearer ${State.token}`;
  }
  if (!(options.body instanceof FormData) && options.body && typeof options.body === "object") {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }
  options.headers = headers;

  try {
    const res = await fetch(endpoint, options);
    if (res.status === 401) {
      logout(false);
      showToast("Your session has expired. Please log in again.", "warning");
      throw new Error("Session expired");
    }
    if (!res.ok) {
      let errDetail = "An error occurred";
      try {
        const errJson = await res.json();
        errDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
      } catch (e) {
        errDetail = await res.text();
      }
      throw new Error(errDetail);
    }
    const contentType = res.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      return await res.json();
    }
    return res;
  } catch (err) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

// Toast Notifications
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  let icon = "ℹ️";
  if (type === "success") icon = "✅";
  if (type === "error") icon = "⚠️";
  if (type === "warning") icon = "🔔";

  toast.innerHTML = `<span>${icon}</span><span style="flex:1;">${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Modal Helpers
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = "flex";
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = "none";
}

// Date & Time formatting
function updateLiveClock() {
  const el = document.getElementById("live-clock");
  if (!el) return;
  const now = new Date();
  const options = { weekday: "short", day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" };
  el.textContent = now.toLocaleDateString("en-IN", options);
}
setInterval(updateLiveClock, 1000);

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
  updateLiveClock();
  setupEventListeners();

  if (State.token && State.user) {
    showApp();
  } else {
    showLogin();
  }
});

function setupEventListeners() {
  // Login Form Submission
  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", handleLoginSubmit);
  }

  // Quick Login Chips
  document.querySelectorAll(".chip[data-user]").forEach(chip => {
    chip.addEventListener("click", (e) => {
      const u = chip.getAttribute("data-user");
      const p = chip.getAttribute("data-pass");
      document.getElementById("login-user-id").value = u;
      document.getElementById("login-password").value = p;
    });
  });

  // App Exit Button
  const btnExit = document.getElementById("btn-login-exit");
  if (btnExit) {
    btnExit.addEventListener("click", () => {
      if (confirm("Are you sure you want to exit the Locktite Leave Management application?")) {
        window.close();
      }
    });
  }

  // Navigation Items
  document.querySelectorAll(".nav-item[data-tab]").forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const tab = item.getAttribute("data-tab");
      navigateTo(tab);
    });
  });

  // Top header logout & change pass
  const btnLogout = document.getElementById("btn-logout");
  if (btnLogout) btnLogout.addEventListener("click", () => logout(true));

  const btnChangePass = document.getElementById("btn-change-password-modal");
  if (btnChangePass) {
    btnChangePass.addEventListener("click", () => {
      document.getElementById("form-change-password").reset();
      openModal("modal-change-password");
    });
  }

  const formChangePass = document.getElementById("form-change-password");
  if (formChangePass) {
    formChangePass.addEventListener("submit", handleChangePasswordSubmit);
  }
}

// Authentication
async function handleLoginSubmit(e) {
  e.preventDefault();
  const userId = document.getElementById("login-user-id").value.trim();
  const password = document.getElementById("login-password").value;
  const errorBox = document.getElementById("login-error-msg");
  const btnLogin = document.getElementById("btn-login-submit");

  errorBox.style.display = "none";
  btnLogin.disabled = true;
  btnLogin.textContent = "Authenticating...";

  try {
    const data = await api("/api/auth/login", {
      method: "POST",
      body: { user_id: userId, password: password }
    });

    State.token = data.token;
    State.user = data.user;
    localStorage.setItem("locktite_token", data.token);
    localStorage.setItem("locktite_user", JSON.stringify(data.user));

    showToast(`Welcome, ${data.user.full_name}!`, "success");
    showApp();
  } catch (err) {
    errorBox.textContent = err.message || "Invalid credentials. Please verify your User ID and Password.";
    errorBox.style.display = "block";
  } finally {
    btnLogin.disabled = false;
    btnLogin.textContent = "Login";
  }
}

async function logout(promptConfirm = true) {
  if (promptConfirm && !confirm("Are you sure you want to log out of Locktite Leave Management?")) {
    return;
  }
  try {
    if (State.token) {
      await api("/api/auth/logout", { method: "POST" });
    }
  } catch (e) {
    // Ignore error on logout
  }
  State.token = null;
  State.user = null;
  localStorage.removeItem("locktite_token");
  localStorage.removeItem("locktite_user");
  showLogin();
}

function showLogin() {
  document.getElementById("login-screen").style.display = "flex";
  document.getElementById("app-container").style.display = "none";
}

function showApp() {
  document.getElementById("login-screen").style.display = "none";
  document.getElementById("app-container").style.display = "flex";

  // Update User Badge in sidebar
  document.getElementById("display-user-name").textContent = State.user.full_name;
  const roleEl = document.getElementById("display-user-role");
  roleEl.textContent = State.user.role;
  roleEl.className = "user-role-badge " + (
    State.user.role === "ADMIN" ? "role-admin" :
    State.user.role === "ENTRY USER" ? "role-entry" : "role-report"
  );
  document.getElementById("display-user-avatar").textContent = State.user.full_name.charAt(0).toUpperCase();

  // Role-based visibility
  const adminSections = document.querySelectorAll(".admin-only");
  adminSections.forEach(el => {
    el.style.display = (State.user.role === "ADMIN") ? "block" : "none";
  });

  const entrySections = document.querySelectorAll(".entry-only");
  entrySections.forEach(el => {
    el.style.display = (State.user.role === "ADMIN" || State.user.role === "ENTRY USER") ? "block" : "none";
  });

  loadLeaveTypes();
  loadEmployeesList();
  navigateTo("dashboard");
}

// Mobile Sidebar Drawer Toggle
function toggleMobileSidebar(open) {
  const sidebar = document.querySelector(".sidebar");
  const overlay = document.getElementById("sidebar-overlay");
  if (!sidebar) return;
  const shouldOpen = (open !== undefined) ? open : !sidebar.classList.contains("open");
  if (shouldOpen) {
    sidebar.classList.add("open");
    if (overlay) overlay.classList.add("active");
  } else {
    sidebar.classList.remove("open");
    if (overlay) overlay.classList.remove("active");
  }
}

// Navigation Router
function navigateTo(tab) {
  State.activeTab = tab;
  toggleMobileSidebar(false);

  // Update active sidebar nav item
  document.querySelectorAll(".nav-item").forEach(item => {
    if (item.getAttribute("data-tab") === tab) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Hide all viewports
  document.querySelectorAll(".page-view").forEach(v => v.style.display = "none");

  // Show target viewport
  const view = document.getElementById(`view-${tab}`);
  if (view) {
    view.style.display = "block";
  }

  // Load viewport specific data
  if (tab === "dashboard") renderDashboard();
  if (tab === "master-employees") renderMasterEmployees();
  if (tab === "entry-leave") renderLeaveEntryModule();
  if (tab === "reports") renderReportsModule();
  if (tab === "admin-users") renderAdminUsers();
  if (tab === "admin-leave-types") renderAdminLeaveTypes();
  if (tab === "admin-audit") renderAdminAuditLogs();
  if (tab === "admin-backup") renderAdminBackups();
  if (tab === "admin-settings") renderAdminSettings();
}

// Common Lookups
async function loadLeaveTypes() {
  try {
    const data = await api("/api/leave/types");
    State.leaveTypes = data.leave_types;
  } catch (e) {
    console.error("Failed to load leave types:", e);
  }
}

async function loadEmployeesList() {
  try {
    const data = await api("/api/employees");
    State.employees = data.employees;
  } catch (e) {
    console.error("Failed to load employees:", e);
  }
}

// --------------------------------------------------------------------------
// 1. DASHBOARD MODULE
// --------------------------------------------------------------------------
async function renderDashboard() {
  const container = document.getElementById("view-dashboard");
  container.innerHTML = `
    <div class="page-header">
      <div class="page-title-wrap">
        <h1>Dashboard Overview</h1>
        <p>Real-time official metrics and records for Locktite India Pvt Ltd</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-secondary btn-sm" onclick="renderDashboard()">🔄 Refresh</button>
      </div>
    </div>
    <div id="dashboard-loading" style="padding: 40px; text-align: center; color: var(--text-muted);">
      Loading dashboard metrics...
    </div>
    <div id="dashboard-content" style="display:none;"></div>
  `;

  try {
    const data = await api("/api/dashboard/stats");
    State.dashboardStats = data;

    const content = document.getElementById("dashboard-content");
    document.getElementById("dashboard-loading").style.display = "none";
    content.style.display = "block";

    content.innerHTML = `
      <!-- Quick Action Buttons -->
      <div class="quick-actions-bar">
        <span class="quick-actions-title">⚡ Quick Actions:</span>
        ${(State.user.role === "ADMIN" || State.user.role === "ENTRY USER") ? `
          <button class="btn btn-primary btn-sm" onclick="openAddEmployeeModal()">➕ New Employee</button>
          <button class="btn btn-accent btn-sm" onclick="navigateTo('entry-leave'); switchEntrySubTab('entry');">📝 Leave Entry</button>
          <button class="btn btn-secondary btn-sm" onclick="navigateTo('entry-leave'); switchEntrySubTab('adjustment');">⚖️ Leave Adjustment</button>
        ` : ''}
        <button class="btn btn-secondary btn-sm" onclick="navigateTo('reports')">📊 Employee Report</button>
      </div>

      <!-- 5 Key Summary Metric Cards -->
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-icon-wrap metric-icon-blue">👥</div>
          <div class="metric-info">
            <div class="metric-label">Total Employees</div>
            <div class="metric-value">${data.total_employees}</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon-wrap metric-icon-green">💼</div>
          <div class="metric-info">
            <div class="metric-label">Active Employees</div>
            <div class="metric-value">${data.active_employees}</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon-wrap metric-icon-amber">🏖️</div>
          <div class="metric-info">
            <div class="metric-label">On Leave Today</div>
            <div class="metric-value">${data.employees_on_leave_today}</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon-wrap metric-icon-purple">📅</div>
          <div class="metric-info">
            <div class="metric-label">Total Leave Taken</div>
            <div class="metric-value">${data.total_leave_taken.toFixed(1)} <span style="font-size:14px; font-weight:normal;">days</span></div>
          </div>
        </div>

        <div class="metric-card" style="${data.low_balance_count > 0 ? 'border-color: var(--danger-border);' : ''}">
          <div class="metric-icon-wrap metric-icon-red">⚠️</div>
          <div class="metric-info">
            <div class="metric-label">Low Leave Balance</div>
            <div class="metric-value" style="color: ${data.low_balance_count > 0 ? 'var(--danger)' : 'inherit'};">${data.low_balance_count}</div>
          </div>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(460px, 1fr)); gap: 20px;">
        <!-- Employees on Leave Today -->
        <div class="card">
          <div class="card-title">
            <span>🏖️ Employees on Leave Today (${data.current_date})</span>
            <span class="badge ${data.employees_on_leave_today > 0 ? 'badge-warning' : 'badge-inactive'}">${data.employees_on_leave_today} Staff</span>
          </div>
          ${data.on_leave_today_list.length === 0 ? `
            <p style="color: var(--text-muted); font-size: 13px; padding: 16px 0; text-align: center;">No employees are scheduled on leave today.</p>
          ` : `
            <div class="table-responsive">
              <table class="table">
                <thead>
                  <tr>
                    <th>Emp No</th>
                    <th>Employee Name</th>
                    <th>Department</th>
                    <th>Leave Type</th>
                    <th>Dates</th>
                  </tr>
                </thead>
                <tbody>
                  ${data.on_leave_today_list.map(emp => `
                    <tr>
                      <td><b>${escapeHtml(emp.employee_number)}</b></td>
                      <td>${escapeHtml(emp.employee_name)}</td>
                      <td>${escapeHtml(emp.department)}</td>
                      <td><span class="badge badge-add">${escapeHtml(emp.leave_type)}</span></td>
                      <td>${escapeHtml(emp.from_date)} to ${escapeHtml(emp.to_date)}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          `}
        </div>

        <!-- Low Balance Alert List -->
        <div class="card">
          <div class="card-title">
            <span>⚠️ Low Leave Balance Alert (&le; ${data.low_balance_threshold} days)</span>
            <span class="badge ${data.low_balance_count > 0 ? 'badge-warning' : 'badge-inactive'}">${data.low_balance_count} Employees</span>
          </div>
          ${data.low_balance_employees.length === 0 ? `
            <p style="color: var(--text-muted); font-size: 13px; padding: 16px 0; text-align: center;">All active employees maintain sufficient leave balance.</p>
          ` : `
            <div class="table-responsive">
              <table class="table">
                <thead>
                  <tr>
                    <th>Emp No</th>
                    <th>Name</th>
                    <th>Department</th>
                    <th>Balance</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${data.low_balance_employees.map(emp => `
                    <tr>
                      <td><b>${escapeHtml(emp.employee_number)}</b></td>
                      <td>${escapeHtml(emp.employee_name)}</td>
                      <td>${escapeHtml(emp.department)}</td>
                      <td><b style="color: var(--danger);">${emp.current_balance.toFixed(1)} days</b></td>
                      <td>
                        <button class="btn btn-secondary btn-sm" onclick="viewEmployeeDetails(${emp.id})">Statement</button>
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          `}
        </div>
      </div>

      <!-- Recent Transactions Table -->
      <div class="card" style="margin-top: 20px;">
        <div class="card-title">
          <span>📜 Recent Leave Transactions</span>
          <button class="btn btn-secondary btn-sm" onclick="navigateTo('entry-leave'); switchEntrySubTab('history');">View All History &rarr;</button>
        </div>
        <div class="table-responsive">
          <table class="table">
            <thead>
              <tr>
                <th>Tx ID</th>
                <th>Employee</th>
                <th>Leave Type</th>
                <th>Type</th>
                <th>Period</th>
                <th>Days</th>
                <th>Recorded By</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              ${data.recent_transactions.map(tx => `
                <tr>
                  <td><b>LTX-${String(tx.id).padStart(4, '0')}</b></td>
                  <td><b>${escapeHtml(tx.employee_number)}</b> - ${escapeHtml(tx.employee_name)}</td>
                  <td>${escapeHtml(tx.leave_type_name)}</td>
                  <td>
                    <span class="badge ${tx.transaction_type === 'ADD' ? 'badge-add' : 'badge-less'}">
                      ${tx.transaction_type}
                    </span>
                  </td>
                  <td>${escapeHtml(tx.from_date)} &rarr; ${escapeHtml(tx.to_date)}</td>
                  <td><b>${tx.days.toFixed(1)}</b></td>
                  <td>${escapeHtml(tx.created_by)}</td>
                  <td style="max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    ${escapeHtml(tx.reason || '-')}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    document.getElementById("dashboard-loading").innerHTML = `
      <div class="alert alert-danger">Error loading dashboard: ${escapeHtml(err.message)}</div>
    `;
  }
}

// --------------------------------------------------------------------------
// 2. MASTER — EMPLOYEE MANAGEMENT
// --------------------------------------------------------------------------
async function renderMasterEmployees() {
  const container = document.getElementById("view-master-employees");
  container.innerHTML = `
    <div class="page-header">
      <div class="page-title-wrap">
        <h1>Employee Master</h1>
        <p>Official master records for Locktite India Pvt Ltd employees</p>
      </div>
      <div class="page-actions">
        ${(State.user.role === "ADMIN" || State.user.role === "ENTRY USER") ? `
          <button class="btn btn-primary" onclick="openAddEmployeeModal()">➕ Add New Employee</button>
        ` : ''}
        <button class="btn btn-secondary" onclick="exportEmployeesCSV()">📥 Export List</button>
      </div>
    </div>

    <!-- Filter & Search Bar -->
    <div class="filter-bar">
      <div class="filter-item" style="flex: 2; min-width: 220px;">
        <input type="text" id="emp-search-query" class="form-control" placeholder="🔍 Search Employee Number, Name, Department..." oninput="filterEmployeesMaster()">
      </div>
      <div class="filter-item">
        <label class="form-label" style="margin: 0; white-space: nowrap;">Department:</label>
        <select id="emp-dept-filter" class="form-control" style="width: 170px;" onchange="filterEmployeesMaster()">
          <option value="All">All Departments</option>
          ${State.departments.map(d => `<option value="${d}">${d}</option>`).join('')}
        </select>
      </div>
      <div class="filter-item">
        <label class="form-label" style="margin: 0; white-space: nowrap;">Status:</label>
        <select id="emp-status-filter" class="form-control" style="width: 130px;" onchange="filterEmployeesMaster()">
          <option value="All">All Status</option>
          <option value="Active" selected>Active Only</option>
          <option value="Inactive">Inactive Only</option>
        </select>
      </div>
      <button class="btn btn-secondary btn-sm" onclick="resetMasterFilters()">Clear</button>
    </div>

    <!-- Master Table -->
    <div class="card" style="padding: 0; overflow: hidden;">
      <div class="table-responsive">
        <table class="table" id="master-employees-table">
          <thead>
            <tr>
              <th>Employee No</th>
              <th>Employee Name</th>
              <th>Department</th>
              <th>Designation</th>
              <th>Joining Date</th>
              <th>Entitlement</th>
              <th>Opening</th>
              <th>Taken</th>
              <th>Balance</th>
              <th>Status</th>
              <th style="text-align: right;">Actions</th>
            </tr>
          </thead>
          <tbody id="master-employees-tbody">
            <tr><td colspan="11" style="text-align: center; padding: 30px; color: var(--text-muted);">Loading employee directory...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  filterEmployeesMaster();
}

async function filterEmployeesMaster() {
  const query = document.getElementById("emp-search-query")?.value || "";
  const dept = document.getElementById("emp-dept-filter")?.value || "All";
  const status = document.getElementById("emp-status-filter")?.value || "All";

  try {
    const params = new URLSearchParams();
    if (query) params.append("query", query);
    if (dept) params.append("department", dept);
    if (status) params.append("status", status);

    const res = await api(`/api/employees?${params.toString()}`);
    const tbody = document.getElementById("master-employees-tbody");
    if (!tbody) return;

    if (res.employees.length === 0) {
      tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; padding: 30px; color: var(--text-muted);">No employees match the current filters.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.employees.map(emp => {
      const balColor = emp.current_balance <= 3 ? 'var(--danger)' : 'var(--success)';
      return `
        <tr>
          <td><b style="color: var(--primary);">${escapeHtml(emp.employee_number)}</b></td>
          <td><b>${escapeHtml(emp.employee_name)}</b></td>
          <td>${escapeHtml(emp.department)}</td>
          <td>${escapeHtml(emp.designation)}</td>
          <td>${escapeHtml(emp.date_of_joining)}</td>
          <td>${emp.leave_entitlement.toFixed(1)}</td>
          <td>${emp.opening_balance.toFixed(1)}</td>
          <td><b style="color: var(--danger);">${emp.leave_taken.toFixed(1)}</b></td>
          <td><b style="color: ${balColor};">${emp.current_balance.toFixed(1)}</b></td>
          <td>
            <span class="badge ${emp.status === 'Active' ? 'badge-active' : 'badge-inactive'}">
              ${emp.status}
            </span>
          </td>
          <td style="text-align: right; white-space: nowrap;">
            <button class="btn btn-secondary btn-sm" title="View Profile & Statement" onclick="viewEmployeeDetails(${emp.id})">👁️ View</button>
            ${State.user.role === 'ADMIN' ? `
              <button class="btn btn-secondary btn-sm" title="Edit Employee" onclick="openEditEmployeeModal(${emp.id})">✏️ Edit</button>
              <button class="btn btn-secondary btn-sm" title="${emp.status === 'Active' ? 'Deactivate' : 'Activate'}" onclick="toggleEmployeeStatus(${emp.id})">
                ${emp.status === 'Active' ? '⏸️' : '▶️'}
              </button>
              <button class="btn btn-danger btn-sm" title="Delete Employee" onclick="openDeleteEmployeeModal(${emp.id}, '${escapeHtml(emp.employee_number)}')">🗑️</button>
            ` : ''}
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    showToast(`Failed to load employees: ${err.message}`, "error");
  }
}

function resetMasterFilters() {
  const q = document.getElementById("emp-search-query");
  const d = document.getElementById("emp-dept-filter");
  const s = document.getElementById("emp-status-filter");
  if (q) q.value = "";
  if (d) d.value = "All";
  if (s) s.value = "Active";
  filterEmployeesMaster();
}

// Add Employee Modal
async function openAddEmployeeModal() {
  try {
    const data = await api("/api/employees/next-number");
    const autoNumber = data.next_employee_number;

    const modalBody = document.getElementById("modal-employee-body");
    modalBody.innerHTML = `
      <form id="form-add-employee" onsubmit="handleAddEmployeeSubmit(event)">
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label required">Employee Number</label>
            <input type="text" class="form-control" id="add-emp-number" value="${autoNumber}" readonly style="font-weight: 700; color: var(--primary); background: #f8fafc;">
            <div class="form-help">System automatically generates the next sequential number.</div>
          </div>
          <div class="form-group">
            <label class="form-label required">Employee Name</label>
            <input type="text" class="form-control" id="add-emp-name" required placeholder="e.g. Ramesh Kumar">
          </div>
          <div class="form-group">
            <label class="form-label required">Department</label>
            <select class="form-control" id="add-emp-dept" required>
              ${State.departments.map(d => `<option value="${d}">${d}</option>`).join('')}
            </select>
          </div>
          <div class="form-group">
            <label class="form-label required">Designation</label>
            <input type="text" class="form-control" id="add-emp-desig" required placeholder="e.g. Senior Officer">
          </div>
          <div class="form-group">
            <label class="form-label required">Date of Joining</label>
            <input type="date" class="form-control" id="add-emp-doj" required value="${new Date().toISOString().split('T')[0]}">
          </div>
          <div class="form-group">
            <label class="form-label">Date of Birth</label>
            <input type="date" class="form-control" id="add-emp-dob">
          </div>
          <div class="form-group">
            <label class="form-label">Mobile Number</label>
            <input type="tel" class="form-control" id="add-emp-mobile" placeholder="10-digit mobile">
          </div>
          <div class="form-group">
            <label class="form-label">Email Address</label>
            <input type="email" class="form-control" id="add-emp-email" placeholder="name@locktite.in">
          </div>
          <div class="form-group">
            <label class="form-label required">Leave Entitlement (Annual)</label>
            <input type="number" step="0.5" class="form-control" id="add-emp-entitlement" value="20" required>
          </div>
          <div class="form-group">
            <label class="form-label required">Opening Leave Balance</label>
            <input type="number" step="0.5" class="form-control" id="add-emp-opening" value="20" required>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Residential Address</label>
          <input type="text" class="form-control" id="add-emp-address" placeholder="Full residential street address">
        </div>

        <div class="form-group">
          <label class="form-label">Remarks</label>
          <textarea class="form-control" id="add-emp-remarks" placeholder="Optional HR / Office notes"></textarea>
        </div>

        <div class="modal-footer" style="padding-left:0; padding-right:0; margin-bottom:-10px;">
          <button type="button" class="btn btn-secondary" onclick="closeModal('modal-employee')">Cancel</button>
          <button type="submit" class="btn btn-primary" id="btn-save-add-emp">Save Employee</button>
        </div>
      </form>
    `;

    document.getElementById("modal-employee-title").textContent = "Add New Employee — Locktite India Pvt Ltd";
    openModal("modal-employee");
  } catch (err) {
    showToast(`Error preparing employee form: ${err.message}`, "error");
  }
}

async function handleAddEmployeeSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById("btn-save-add-emp");
  btn.disabled = true;
  btn.textContent = "Saving...";

  const payload = {
    employee_name: document.getElementById("add-emp-name").value.trim(),
    department: document.getElementById("add-emp-dept").value,
    designation: document.getElementById("add-emp-desig").value.trim(),
    date_of_joining: document.getElementById("add-emp-doj").value,
    date_of_birth: document.getElementById("add-emp-dob").value || null,
    mobile: document.getElementById("add-emp-mobile").value.trim() || null,
    email: document.getElementById("add-emp-email").value.trim() || null,
    address: document.getElementById("add-emp-address").value.trim() || null,
    leave_entitlement: parseFloat(document.getElementById("add-emp-entitlement").value),
    opening_balance: parseFloat(document.getElementById("add-emp-opening").value),
    status: "Active",
    remarks: document.getElementById("add-emp-remarks").value.trim() || null
  };

  try {
    const res = await api("/api/employees", {
      method: "POST",
      body: payload
    });

    showToast(res.message, "success");
    closeModal("modal-employee");
    loadEmployeesList();
    filterEmployeesMaster();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Save Employee";
  }
}

// Edit Employee Modal
async function openEditEmployeeModal(id) {
  try {
    const data = await api(`/api/employees/${id}`);
    const emp = data.employee;

    const modalBody = document.getElementById("modal-employee-body");
    modalBody.innerHTML = `
      <form id="form-edit-employee" onsubmit="handleEditEmployeeSubmit(event, ${emp.id})">
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">Employee Number</label>
            <input type="text" class="form-control" value="${escapeHtml(emp.employee_number)}" readonly style="font-weight:700; color:var(--primary); background:#f8fafc;">
          </div>
          <div class="form-group">
            <label class="form-label required">Employee Name</label>
            <input type="text" class="form-control" id="edit-emp-name" value="${escapeHtml(emp.employee_name)}" required>
          </div>
          <div class="form-group">
            <label class="form-label required">Department</label>
            <select class="form-control" id="edit-emp-dept" required>
              ${State.departments.map(d => `<option value="${d}" ${d === emp.department ? 'selected' : ''}>${d}</option>`).join('')}
            </select>
          </div>
          <div class="form-group">
            <label class="form-label required">Designation</label>
            <input type="text" class="form-control" id="edit-emp-desig" value="${escapeHtml(emp.designation)}" required>
          </div>
          <div class="form-group">
            <label class="form-label required">Date of Joining</label>
            <input type="date" class="form-control" id="edit-emp-doj" value="${emp.date_of_joining}" required>
          </div>
          <div class="form-group">
            <label class="form-label">Date of Birth</label>
            <input type="date" class="form-control" id="edit-emp-dob" value="${emp.date_of_birth || ''}">
          </div>
          <div class="form-group">
            <label class="form-label">Mobile Number</label>
            <input type="tel" class="form-control" id="edit-emp-mobile" value="${escapeHtml(emp.mobile || '')}">
          </div>
          <div class="form-group">
            <label class="form-label">Email Address</label>
            <input type="email" class="form-control" id="edit-emp-email" value="${escapeHtml(emp.email || '')}">
          </div>
          <div class="form-group">
            <label class="form-label required">Leave Entitlement</label>
            <input type="number" step="0.5" class="form-control" id="edit-emp-entitlement" value="${emp.leave_entitlement}" required onchange="checkEntitlementChanged(${emp.leave_entitlement}, ${emp.opening_balance})">
          </div>
          <div class="form-group">
            <label class="form-label required">Opening Leave Balance</label>
            <input type="number" step="0.5" class="form-control" id="edit-emp-opening" value="${emp.opening_balance}" required onchange="checkEntitlementChanged(${emp.leave_entitlement}, ${emp.opening_balance})">
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Residential Address</label>
          <input type="text" class="form-control" id="edit-emp-address" value="${escapeHtml(emp.address || '')}">
        </div>

        <div class="form-group">
          <label class="form-label">Remarks</label>
          <textarea class="form-control" id="edit-emp-remarks">${escapeHtml(emp.remarks || '')}</textarea>
        </div>

        <!-- Security Password Required if Entitlement/Opening Balance is modified -->
        <div id="entitlement-password-box" style="display:none;" class="alert alert-warning">
          <label class="form-label required" style="color: #92400e;">⚠️ Administrator Password Required to Modify Leave Entitlement / Balance</label>
          <input type="password" class="form-control" id="edit-emp-admin-password" placeholder="Enter your Administrator password to confirm this change">
        </div>

        <div class="modal-footer" style="padding-left:0; padding-right:0; margin-bottom:-10px;">
          <button type="button" class="btn btn-secondary" onclick="closeModal('modal-employee')">Cancel</button>
          <button type="submit" class="btn btn-primary" id="btn-save-edit-emp">Update Employee</button>
        </div>
      </form>
    `;

    document.getElementById("modal-employee-title").textContent = `Edit Employee: ${emp.employee_number} - ${emp.employee_name}`;
    openModal("modal-employee");
  } catch (err) {
    showToast(`Error fetching employee: ${err.message}`, "error");
  }
}

function checkEntitlementChanged(origEnt, origOp) {
  const newEnt = parseFloat(document.getElementById("edit-emp-entitlement").value);
  const newOp = parseFloat(document.getElementById("edit-emp-opening").value);
  const box = document.getElementById("entitlement-password-box");
  if (newEnt !== origEnt || newOp !== origOp) {
    box.style.display = "block";
  } else {
    box.style.display = "none";
  }
}

async function handleEditEmployeeSubmit(e, id) {
  e.preventDefault();
  const btn = document.getElementById("btn-save-edit-emp");
  btn.disabled = true;
  btn.textContent = "Updating...";

  const passInput = document.getElementById("edit-emp-admin-password");
  const payload = {
    employee_name: document.getElementById("edit-emp-name").value.trim(),
    department: document.getElementById("edit-emp-dept").value,
    designation: document.getElementById("edit-emp-desig").value.trim(),
    date_of_joining: document.getElementById("edit-emp-doj").value,
    date_of_birth: document.getElementById("edit-emp-dob").value || null,
    mobile: document.getElementById("edit-emp-mobile").value.trim() || null,
    email: document.getElementById("edit-emp-email").value.trim() || null,
    address: document.getElementById("edit-emp-address").value.trim() || null,
    leave_entitlement: parseFloat(document.getElementById("edit-emp-entitlement").value),
    opening_balance: parseFloat(document.getElementById("edit-emp-opening").value),
    remarks: document.getElementById("edit-emp-remarks").value.trim() || null,
    confirmation_password: passInput ? passInput.value : null
  };

  try {
    const res = await api(`/api/employees/${id}`, {
      method: "PUT",
      body: payload
    });

    showToast(res.message, "success");
    closeModal("modal-employee");
    loadEmployeesList();
    filterEmployeesMaster();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Update Employee";
  }
}

// Toggle Status (Active / Inactive)
async function toggleEmployeeStatus(id) {
  try {
    const res = await api(`/api/employees/${id}/toggle-status`, { method: "POST" });
    showToast(res.message, "success");
    filterEmployeesMaster();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Delete Employee Modal
function openDeleteEmployeeModal(id, empNumber) {
  const modalBody = document.getElementById("modal-sensitive-body");
  modalBody.innerHTML = `
    <div class="alert alert-danger">
      <b>Warning:</b> You are about to permanently delete employee <b>${empNumber}</b>.
      <br/><br/>
      Note: Official policy prefers deactivating employees rather than deleting them. If any leave records exist, the system will prevent deletion to preserve official office history.
    </div>
    <div class="form-group">
      <label class="form-label required">Administrator Password</label>
      <input type="password" id="delete-admin-password" class="form-control" placeholder="Enter your password to authorize deletion" required>
    </div>
    <div class="form-group">
      <label class="form-label">Reason for Deletion</label>
      <input type="text" id="delete-admin-reason" class="form-control" placeholder="e.g. Created by clerical mistake">
    </div>
  `;
  document.getElementById("modal-sensitive-title").textContent = `Confirm Permanent Deletion: ${empNumber}`;
  const btnConfirm = document.getElementById("btn-sensitive-confirm");
  btnConfirm.onclick = () => confirmDeleteEmployee(id);
  openModal("modal-sensitive");
}

async function confirmDeleteEmployee(id) {
  const password = document.getElementById("delete-admin-password").value;
  const reason = document.getElementById("delete-admin-reason").value;

  if (!password) {
    showToast("Administrator password is required.", "error");
    return;
  }

  try {
    const res = await api(`/api/employees/${id}`, {
      method: "DELETE",
      body: { password: password, reason: reason }
    });
    showToast(res.message, "success");
    closeModal("modal-sensitive");
    loadEmployeesList();
    filterEmployeesMaster();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// View Employee Details Modal (Full profile + Leave Statement)
async function viewEmployeeDetails(id) {
  try {
    const data = await api(`/api/employees/${id}`);
    const emp = data.employee;

    const modalBody = document.getElementById("modal-details-body");
    modalBody.innerHTML = `
      <!-- Employee Profile Header -->
      <div style="background: linear-gradient(135deg, #1e3a8a, #0f172a); color: #fff; padding: 20px; border-radius: var(--radius-md); margin-bottom: 20px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div>
            <h2 style="font-size: 20px; font-weight: 700;">${escapeHtml(emp.employee_name)}</h2>
            <div style="font-size: 13px; color: #94a3b8; margin-top: 4px;">
              <b>${escapeHtml(emp.employee_number)}</b> &bull; ${escapeHtml(emp.designation)} &bull; ${escapeHtml(emp.department)}
            </div>
          </div>
          <span class="badge ${emp.status === 'Active' ? 'badge-active' : 'badge-inactive'}" style="font-size: 12px; padding: 4px 10px;">
            ${emp.status}
          </span>
        </div>
      </div>

      <!-- Balance Summary 4-Col Grid -->
      <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px;">
        <div style="background:#f8fafc; border:1px solid var(--border); padding:12px; border-radius:6px; text-align:center;">
          <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Entitlement</div>
          <div style="font-size:20px; font-weight:800; color:var(--secondary);">${emp.leave_entitlement.toFixed(1)}</div>
        </div>
        <div style="background:#f8fafc; border:1px solid var(--border); padding:12px; border-radius:6px; text-align:center;">
          <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Opening Balance</div>
          <div style="font-size:20px; font-weight:800; color:var(--secondary);">${emp.opening_balance.toFixed(1)}</div>
        </div>
        <div style="background:#fee2e2; border:1px solid var(--danger-border); padding:12px; border-radius:6px; text-align:center;">
          <div style="font-size:11px; text-transform:uppercase; color:var(--danger); font-weight:700;">Leave Taken</div>
          <div style="font-size:20px; font-weight:800; color:var(--danger);">${emp.leave_taken.toFixed(1)}</div>
        </div>
        <div style="background:#dcfce7; border:1px solid var(--success-border); padding:12px; border-radius:6px; text-align:center;">
          <div style="font-size:11px; text-transform:uppercase; color:var(--success); font-weight:700;">Current Balance</div>
          <div style="font-size:20px; font-weight:800; color:var(--success);">${emp.current_balance.toFixed(1)}</div>
        </div>
      </div>

      <!-- Additional Details Grid -->
      <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap: 10px; font-size: 13px; margin-bottom: 20px; background:#f8fafc; padding:14px; border-radius:6px;">
        <div><b>Date of Joining:</b> ${escapeHtml(emp.date_of_joining)}</div>
        <div><b>Date of Birth:</b> ${escapeHtml(emp.date_of_birth || '-')}</div>
        <div><b>Mobile:</b> ${escapeHtml(emp.mobile || '-')}</div>
        <div><b>Email:</b> ${escapeHtml(emp.email || '-')}</div>
        <div style="grid-column: span 2;"><b>Address:</b> ${escapeHtml(emp.address || '-')}</div>
        <div style="grid-column: span 2;"><b>Remarks:</b> ${escapeHtml(emp.remarks || '-')}</div>
      </div>

      <!-- Transaction History Table -->
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 10px;">
        <h3 style="font-size: 15px; font-weight: 700;">Leave Statement History</h3>
        <div style="display:flex; gap: 8px;">
          <button class="btn btn-secondary btn-sm" onclick="downloadIndividualPDF(${emp.id})">📄 Download PDF</button>
          <button class="btn btn-secondary btn-sm" onclick="downloadIndividualExcel(${emp.id})">📊 Excel</button>
        </div>
      </div>

      <div class="table-responsive">
        <table class="table">
          <thead>
            <tr>
              <th>Tx ID</th>
              <th>Period</th>
              <th>Leave Type</th>
              <th>Type</th>
              <th>Days</th>
              <th>Reason</th>
              <th>Recorded By</th>
            </tr>
          </thead>
          <tbody>
            ${emp.transactions.length === 0 ? `
              <tr><td colspan="7" style="text-align:center; padding:20px; color:var(--text-muted);">No leave transactions recorded.</td></tr>
            ` : emp.transactions.map(t => `
              <tr>
                <td><b>LTX-${String(t.id).padStart(4, '0')}</b></td>
                <td>${escapeHtml(t.from_date)} &rarr; ${escapeHtml(t.to_date)}</td>
                <td>${escapeHtml(t.leave_type_name)}</td>
                <td><span class="badge ${t.transaction_type === 'ADD' ? 'badge-add' : 'badge-less'}">${t.transaction_type}</span></td>
                <td><b>${t.days.toFixed(1)}</b></td>
                <td>${escapeHtml(t.reason || '-')}</td>
                <td>${escapeHtml(t.created_by)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;

    document.getElementById("modal-details-title").textContent = `Locktite India Pvt Ltd — Statement for ${emp.employee_number}`;
    openModal("modal-details");
  } catch (err) {
    showToast(err.message, "error");
  }
}

// --------------------------------------------------------------------------
// 3. ENTRY MODULE — LEAVE ENTRY & LEAVE ADJUSTMENT & HISTORY
// --------------------------------------------------------------------------
function renderLeaveEntryModule() {
  const container = document.getElementById("view-entry-leave");
  container.innerHTML = `
    <div class="page-header">
      <div class="page-title-wrap">
        <h1>Leave Entry & Adjustment</h1>
        <p>Record new employee leaves, process cancellations/reductions, and view audit trail</p>
      </div>
    </div>

    <!-- Sub-tab Navigation -->
    <div style="display:flex; gap: 8px; border-bottom: 2px solid var(--border); margin-bottom: 20px;">
      <button id="subtab-btn-entry" class="btn btn-secondary" style="border-bottom: 3px solid var(--primary); font-weight:700;" onclick="switchEntrySubTab('entry')">
        📝 Add Leave Entry
      </button>
      <button id="subtab-btn-adjustment" class="btn btn-secondary" onclick="switchEntrySubTab('adjustment')">
        ⚖️ Leave Adjustment (Less / Cancel)
      </button>
      <button id="subtab-btn-history" class="btn btn-secondary" onclick="switchEntrySubTab('history')">
        📜 Leave Transaction History
      </button>
    </div>

    <!-- Section 1: Add Leave Entry Form -->
    <div id="section-entry" class="entry-subview">
      <div style="display:grid; grid-template-columns: 1fr 1.3fr; gap: 24px;">
        <!-- Left: Employee Selection & Balance Card -->
        <div>
          <div class="card">
            <div class="card-title">1. Select Employee</div>
            <div class="form-group">
              <label class="form-label required">Search Employee</label>
              <select id="entry-employee-select" class="form-control" onchange="handleEntryEmployeeSelected()">
                <option value="">-- Choose Employee (Number or Name) --</option>
                ${State.employees.map(e => `
                  <option value="${e.id}">${e.employee_number} - ${e.employee_name} (${e.department})</option>
                `).join('')}
              </select>
            </div>
            
            <div id="entry-employee-card" style="display:none; margin-top: 16px; border: 1px solid var(--primary-border); background: var(--primary-light); border-radius: var(--radius-md); padding: 16px;">
              <!-- Selected Employee Profile & Balance Details Loaded Dynamically -->
            </div>
          </div>
        </div>

        <!-- Right: Leave Entry Form -->
        <div>
          <div class="card">
            <div class="card-title">2. Leave Details</div>
            <form id="form-add-leave" onsubmit="handleAddLeaveSubmit(event)">
              <div class="form-group">
                <label class="form-label required">Leave Type</label>
                <select id="leave-type-select" class="form-control" required>
                  <option value="">-- Select Leave Category --</option>
                  ${State.leaveTypes.map(lt => `<option value="${lt.id}">${lt.name}</option>`).join('')}
                </select>
              </div>

              <div class="form-grid" style="grid-template-columns: 1fr 1fr;">
                <div class="form-group">
                  <label class="form-label required">From Date</label>
                  <input type="date" id="leave-from-date" class="form-control" required value="${new Date().toISOString().split('T')[0]}" onchange="calculateLeaveDays('entry')">
                </div>
                <div class="form-group">
                  <label class="form-label required">To Date</label>
                  <input type="date" id="leave-to-date" class="form-control" required value="${new Date().toISOString().split('T')[0]}" onchange="calculateLeaveDays('entry')">
                </div>
              </div>

              <div class="form-group">
                <label class="form-label required">Number of Leave Days</label>
                <input type="number" step="0.5" id="leave-days" class="form-control" required value="1" min="0.5">
                <div class="form-help">Calculated automatically; you can edit for half-day leaves (e.g. 0.5 days).</div>
              </div>

              <div class="form-group">
                <label class="form-label">Reason / Remarks</label>
                <textarea id="leave-reason" class="form-control" placeholder="Specify official reason (e.g. Personal emergency, Medical consultation, etc.)"></textarea>
              </div>

              ${State.user.role === 'ADMIN' ? `
                <div class="form-group" style="margin-top: 10px;">
                  <label style="display:flex; align-items:center; gap:8px; font-size:12.5px; cursor:pointer;">
                    <input type="checkbox" id="leave-override-balance">
                    <span><b>Admin Override:</b> Allow leave even if balance is insufficient</span>
                  </label>
                </div>
              ` : ''}

              <button type="submit" class="btn btn-primary btn-lg" style="width:100%; margin-top: 10px;" id="btn-submit-add-leave">
                💾 ADD LEAVE TRANSACTION
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>

    <!-- Section 2: Leave Adjustment (Less / Cancel) -->
    <div id="section-adjustment" class="entry-subview" style="display:none;">
      <div style="max-width: 720px; margin: 0 auto;">
        <div class="card">
          <div class="card-title">
            <span>⚖️ Less / Cancel Leave Form</span>
            <span class="badge badge-less">CREDIT BACK TO BALANCE</span>
          </div>
          <p style="color:var(--text-muted); font-size:13px; margin-bottom: 16px;">
            Use this official form when previously booked leave was cancelled, entered incorrectly, or days need reduction. 
            The system preserves complete transaction history without modifying previous records.
          </p>

          <form id="form-less-leave" onsubmit="handleLessLeaveSubmit(event)">
            <div class="form-group">
              <label class="form-label required">Select Employee</label>
              <select id="adj-employee-select" class="form-control" required onchange="handleAdjEmployeeSelected()">
                <option value="">-- Choose Employee --</option>
                ${State.employees.map(e => `
                  <option value="${e.id}">${e.employee_number} - ${e.employee_name} (${e.department})</option>
                `).join('')}
              </select>
            </div>

            <div id="adj-employee-card" style="display:none; margin-bottom: 16px; border: 1px solid var(--border); background: #f8fafc; border-radius: var(--radius-md); padding: 14px;">
              <!-- Dynamic employee stats -->
            </div>

            <div class="form-group">
              <label class="form-label required">Leave Type to Adjust</label>
              <select id="adj-leave-type-select" class="form-control" required>
                <option value="">-- Select Leave Category --</option>
                ${State.leaveTypes.map(lt => `<option value="${lt.id}">${lt.name}</option>`).join('')}
              </select>
            </div>

            <div class="form-grid" style="grid-template-columns: 1fr 1fr;">
              <div class="form-group">
                <label class="form-label required">From Date</label>
                <input type="date" id="adj-from-date" class="form-control" required value="${new Date().toISOString().split('T')[0]}" onchange="calculateLeaveDays('adj')">
              </div>
              <div class="form-group">
                <label class="form-label required">To Date</label>
                <input type="date" id="adj-to-date" class="form-control" required value="${new Date().toISOString().split('T')[0]}" onchange="calculateLeaveDays('adj')">
              </div>
            </div>

            <div class="form-group">
              <label class="form-label required">Days to Reduce / Cancel (LESS)</label>
              <input type="number" step="0.5" id="adj-days" class="form-control" required value="1" min="0.5">
            </div>

            <div class="form-group">
              <label class="form-label required">Mandatory Reason / Justification</label>
              <textarea id="adj-reason" class="form-control" required placeholder="State exact reason for cancellation / correction (e.g. Reported to duty early, incorrect date entry, client trip cancelled)"></textarea>
            </div>

            <button type="submit" class="btn btn-success btn-lg" style="width: 100%;" id="btn-submit-adj-leave">
              ⚖️ RECORD LESS / CANCEL TRANSACTION
            </button>
          </form>
        </div>
      </div>
    </div>

    <!-- Section 3: Leave Transaction History -->
    <div id="section-history" class="entry-subview" style="display:none;">
      <div class="filter-bar">
        <div class="filter-item">
          <label class="form-label" style="margin:0;">Employee:</label>
          <select id="hist-employee-filter" class="form-control" style="width: 220px;" onchange="loadLeaveHistory()">
            <option value="">All Employees</option>
            ${State.employees.map(e => `<option value="${e.id}">${e.employee_number} - ${e.employee_name}</option>`).join('')}
          </select>
        </div>
        <div class="filter-item">
          <label class="form-label" style="margin:0;">Type:</label>
          <select id="hist-type-filter" class="form-control" style="width: 120px;" onchange="loadLeaveHistory()">
            <option value="All">All Types</option>
            <option value="ADD">ADD (Taken)</option>
            <option value="LESS">LESS (Cancelled)</option>
          </select>
        </div>
        <div class="filter-item">
          <label class="form-label" style="margin:0;">From:</label>
          <input type="date" id="hist-from-date" class="form-control" onchange="loadLeaveHistory()">
        </div>
        <div class="filter-item">
          <label class="form-label" style="margin:0;">To:</label>
          <input type="date" id="hist-to-date" class="form-control" onchange="loadLeaveHistory()">
        </div>
        <button class="btn btn-secondary btn-sm" onclick="resetHistoryFilters()">Clear</button>
      </div>

      <div class="card" style="padding:0; overflow:hidden;">
        <div class="table-responsive">
          <table class="table">
            <thead>
              <tr>
                <th>Tx ID</th>
                <th>Employee</th>
                <th>Leave Type</th>
                <th>Type</th>
                <th>From Date</th>
                <th>To Date</th>
                <th>Days</th>
                <th>Reason</th>
                <th>Recorded By</th>
                <th>Timestamp</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody id="leave-history-tbody">
              <tr><td colspan="11" style="text-align:center; padding:30px; color:var(--text-muted);">Loading transaction history...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  // Auto-calculate days on initial load
  calculateLeaveDays('entry');
}

function switchEntrySubTab(tab) {
  document.querySelectorAll(".entry-subview").forEach(el => el.style.display = "none");
  const sec = document.getElementById(`section-${tab}`);
  if (sec) sec.style.display = "block";

  // Tab button styling
  ["entry", "adjustment", "history"].forEach(t => {
    const btn = document.getElementById(`subtab-btn-${t}`);
    if (btn) {
      if (t === tab) {
        btn.style.borderBottom = "3px solid var(--primary)";
        btn.style.fontWeight = "700";
      } else {
        btn.style.borderBottom = "none";
        btn.style.fontWeight = "500";
      }
    }
  });

  if (tab === "history") loadLeaveHistory();
}

// Calculate days difference between From Date and To Date
function calculateLeaveDays(prefix) {
  const fromEl = document.getElementById(prefix === "entry" ? "leave-from-date" : "adj-from-date");
  const toEl = document.getElementById(prefix === "entry" ? "leave-to-date" : "adj-to-date");
  const daysEl = document.getElementById(prefix === "entry" ? "leave-days" : "adj-days");

  if (!fromEl || !toEl || !daysEl) return;
  if (!fromEl.value || !toEl.value) return;

  const d1 = new Date(fromEl.value);
  const d2 = new Date(toEl.value);

  if (d2 < d1) {
    showToast("From Date cannot be after To Date.", "warning");
    daysEl.value = 1;
    return;
  }

  const diffTime = d2.getTime() - d1.getTime();
  const diffDays = Math.round(diffTime / (1000 * 3600 * 24)) + 1;
  daysEl.value = diffDays > 0 ? diffDays : 1;
}

async function handleEntryEmployeeSelected() {
  const select = document.getElementById("entry-employee-select");
  const card = document.getElementById("entry-employee-card");
  const empId = select.value;

  if (!empId) {
    card.style.display = "none";
    State.selectedEmployeeForEntry = null;
    return;
  }

  try {
    const data = await api(`/api/leave/balance/${empId}`);
    const summary = data.balance_summary;
    State.selectedEmployeeForEntry = summary;

    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
          <h4 style="font-size:15px; font-weight:700; color:var(--primary);">${escapeHtml(summary.employee_name)}</h4>
          <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">
            <b>${summary.employee_number}</b> &bull; ${escapeHtml(summary.designation)} &bull; ${escapeHtml(summary.department)}
          </div>
        </div>
        <span class="badge ${summary.status === 'Active' ? 'badge-active' : 'badge-inactive'}">${summary.status}</span>
      </div>

      <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 14px; text-align: center;">
        <div style="background:#fff; border:1px solid var(--border); border-radius:4px; padding:6px;">
          <div style="font-size:10px; color:var(--text-muted); font-weight:700;">ENTITLEMENT</div>
          <div style="font-size:16px; font-weight:800;">${summary.leave_entitlement.toFixed(1)}</div>
        </div>
        <div style="background:#fff; border:1px solid var(--border); border-radius:4px; padding:6px;">
          <div style="font-size:10px; color:var(--text-muted); font-weight:700;">OPENING</div>
          <div style="font-size:16px; font-weight:800;">${summary.opening_balance.toFixed(1)}</div>
        </div>
        <div style="background:#fff; border:1px solid var(--border); border-radius:4px; padding:6px;">
          <div style="font-size:10px; color:var(--danger); font-weight:700;">TAKEN</div>
          <div style="font-size:16px; font-weight:800; color:var(--danger);">${summary.leave_taken.toFixed(1)}</div>
        </div>
        <div style="background:#fff; border:1px solid var(--border); border-radius:4px; padding:6px;">
          <div style="font-size:10px; color:var(--success); font-weight:700;">AVAILABLE</div>
          <div style="font-size:16px; font-weight:800; color:var(--success);">${summary.current_balance.toFixed(1)}</div>
        </div>
      </div>
    `;
    card.style.display = "block";
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleAddLeaveSubmit(e) {
  e.preventDefault();
  const empSelect = document.getElementById("entry-employee-select");
  if (!empSelect || !empSelect.value) {
    showToast("Please select an employee.", "warning");
    return;
  }

  const btn = document.getElementById("btn-submit-add-leave");
  btn.disabled = true;
  btn.textContent = "Processing...";

  const overrideCheckbox = document.getElementById("leave-override-balance");

  const payload = {
    employee_id: parseInt(empSelect.value),
    leave_type_id: parseInt(document.getElementById("leave-type-select").value),
    from_date: document.getElementById("leave-from-date").value,
    to_date: document.getElementById("leave-to-date").value,
    days: parseFloat(document.getElementById("leave-days").value),
    reason: document.getElementById("leave-reason").value.trim() || null,
    override_balance_check: overrideCheckbox ? overrideCheckbox.checked : false
  };

  try {
    const res = await api("/api/leave/entry", {
      method: "POST",
      body: payload
    });

    showToast(res.message, "success");
    handleEntryEmployeeSelected();
    document.getElementById("leave-reason").value = "";
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "💾 ADD LEAVE TRANSACTION";
  }
}

async function handleAdjEmployeeSelected() {
  const select = document.getElementById("adj-employee-select");
  const card = document.getElementById("adj-employee-card");
  const empId = select.value;

  if (!empId) {
    card.style.display = "none";
    return;
  }

  try {
    const data = await api(`/api/leave/balance/${empId}`);
    const summary = data.balance_summary;
    card.innerHTML = `
      <div style="display:flex; justify-content:space-between;">
        <b>${escapeHtml(summary.employee_name)} (${summary.employee_number})</b>
        <span>Current Taken: <b style="color:var(--danger);">${summary.leave_taken.toFixed(1)} days</b> | Available: <b style="color:var(--success);">${summary.current_balance.toFixed(1)} days</b></span>
      </div>
    `;
    card.style.display = "block";
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleLessLeaveSubmit(e) {
  e.preventDefault();
  const empSelect = document.getElementById("adj-employee-select");
  if (!empSelect || !empSelect.value) {
    showToast("Please select an employee.", "warning");
    return;
  }

  const btn = document.getElementById("btn-submit-adj-leave");
  btn.disabled = true;
  btn.textContent = "Saving Adjustment...";

  const payload = {
    employee_id: parseInt(empSelect.value),
    leave_type_id: parseInt(document.getElementById("adj-leave-type-select").value),
    from_date: document.getElementById("adj-from-date").value,
    to_date: document.getElementById("adj-to-date").value,
    days: parseFloat(document.getElementById("adj-days").value),
    reason: document.getElementById("adj-reason").value.trim()
  };

  try {
    const res = await api("/api/leave/adjustment", {
      method: "POST",
      body: payload
    });

    showToast(res.message, "success");
    handleAdjEmployeeSelected();
    document.getElementById("adj-reason").value = "";
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "⚖️ RECORD LESS / CANCEL TRANSACTION";
  }
}

async function loadLeaveHistory() {
  const empId = document.getElementById("hist-employee-filter")?.value || "";
  const txType = document.getElementById("hist-type-filter")?.value || "All";
  const fromDate = document.getElementById("hist-from-date")?.value || "";
  const toDate = document.getElementById("hist-to-date")?.value || "";

  const params = new URLSearchParams();
  if (empId) params.append("employee_id", empId);
  if (txType && txType !== "All") params.append("transaction_type", txType);
  if (fromDate) params.append("from_date", fromDate);
  if (toDate) params.append("to_date", toDate);

  try {
    const res = await api(`/api/leave/history?${params.toString()}`);
    const tbody = document.getElementById("leave-history-tbody");
    if (!tbody) return;

    if (res.history.length === 0) {
      tbody.innerHTML = `<tr><td colspan="11" style="text-align:center; padding:30px; color:var(--text-muted);">No leave transactions recorded matching criteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.history.map(t => `
      <tr>
        <td><b>LTX-${String(t.id).padStart(4, '0')}</b></td>
        <td><b>${escapeHtml(t.employee_number)}</b> - ${escapeHtml(t.employee_name)}</td>
        <td>${escapeHtml(t.leave_type_name)}</td>
        <td>
          <span class="badge ${t.transaction_type === 'ADD' ? 'badge-add' : 'badge-less'}">
            ${t.transaction_type}
          </span>
        </td>
        <td>${escapeHtml(t.from_date)}</td>
        <td>${escapeHtml(t.to_date)}</td>
        <td><b>${t.days.toFixed(1)}</b></td>
        <td style="max-width:200px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
          ${escapeHtml(t.reason || '-')}
        </td>
        <td>${escapeHtml(t.created_by)}</td>
        <td style="font-size:12px; color:var(--text-muted);">${escapeHtml(t.created_at)}</td>
        <td>
          ${t.transaction_type === 'ADD' ? `
            <button class="btn btn-secondary btn-sm" onclick="quickAdjustTx(${t.employee_id}, ${t.leave_type_id}, '${t.from_date}', '${t.to_date}', ${t.days})">
              ⚖️ Less / Cancel
            </button>
          ` : ''}
        </td>
      </tr>
    `).join('');
  } catch (err) {
    showToast(err.message, "error");
  }
}

function quickAdjustTx(empId, ltId, fromDate, toDate, days) {
  switchEntrySubTab("adjustment");
  const selEmp = document.getElementById("adj-employee-select");
  const selLt = document.getElementById("adj-leave-type-select");
  const fDate = document.getElementById("adj-from-date");
  const tDate = document.getElementById("adj-to-date");
  const dVal = document.getElementById("adj-days");

  if (selEmp) { selEmp.value = empId; handleAdjEmployeeSelected(); }
  if (selLt) selLt.value = ltId;
  if (fDate) fDate.value = fromDate;
  if (tDate) tDate.value = toDate;
  if (dVal) dVal.value = days;
}

function resetHistoryFilters() {
  document.getElementById("hist-employee-filter").value = "";
  document.getElementById("hist-type-filter").value = "All";
  document.getElementById("hist-from-date").value = "";
  document.getElementById("hist-to-date").value = "";
  loadLeaveHistory();
}

// --------------------------------------------------------------------------
// 4. REPORTS MODULE
// --------------------------------------------------------------------------
function renderReportsModule() {
  const container = document.getElementById("view-reports");
  container.innerHTML = `
    <div class="page-header">
      <div class="page-title-wrap">
        <h1>Official Reports & Statements</h1>
        <p>LOCKTITE INDIA PVT LTD &bull; Employee Leave Management System</p>
      </div>
    </div>

    <!-- Report Types Sub-Navigation -->
    <div style="display:flex; gap: 8px; border-bottom: 2px solid var(--border); margin-bottom: 20px;">
      <button id="report-subtab-individual" class="btn btn-secondary" style="border-bottom: 3px solid var(--primary); font-weight:700;" onclick="switchReportSubTab('individual')">
        👤 Individual Employee Statement
      </button>
      <button id="report-subtab-all" class="btn btn-secondary" onclick="switchReportSubTab('all')">
        👥 All Employees Leave Summary
      </button>
    </div>

    <!-- Sub-Report 1: Individual Employee Statement -->
    <div id="report-section-individual" class="report-subview">
      <div class="filter-bar">
        <div class="filter-item">
          <label class="form-label required" style="margin:0;">Select Employee:</label>
          <select id="rep-ind-employee" class="form-control" style="width: 260px;" onchange="generateIndividualReport()">
            <option value="">-- Choose Employee --</option>
            ${State.employees.map(e => `<option value="${e.id}">${e.employee_number} - ${e.employee_name} (${e.department})</option>`).join('')}
          </select>
        </div>
        <div class="filter-item">
          <label class="form-label" style="margin:0;">From Date:</label>
          <input type="date" id="rep-ind-from" class="form-control" onchange="generateIndividualReport()">
        </div>
        <div class="filter-item">
          <label class="form-label" style="margin:0;">To Date:</label>
          <input type="date" id="rep-ind-to" class="form-control" onchange="generateIndividualReport()">
        </div>
        <button class="btn btn-primary btn-sm" onclick="generateIndividualReport()">🔍 Generate Statement</button>
        <button class="btn btn-secondary btn-sm" onclick="printReport()">🖨️ Print</button>
        <button class="btn btn-secondary btn-sm" id="btn-rep-pdf" onclick="exportIndPDF()">📄 Export PDF</button>
        <button class="btn btn-secondary btn-sm" id="btn-rep-excel" onclick="exportIndExcel()">📊 Export Excel</button>
      </div>

      <div id="individual-report-preview" class="card" style="background: #ffffff; padding: 30px;">
        <p style="color: var(--text-muted); text-align: center; padding: 40px;">Select an employee above and click "Generate Statement" to view official statement.</p>
      </div>
    </div>

    <!-- Sub-Report 2: All Employees Leave Summary -->
    <div id="report-section-all" class="report-subview" style="display:none;">
      <div class="filter-bar">
        <div class="filter-item">
          <label class="form-label" style="margin:0;">Department:</label>
          <select id="rep-all-dept" class="form-control" style="width: 180px;" onchange="generateAllEmployeesReport()">
            <option value="All">All Departments</option>
            ${State.departments.map(d => `<option value="${d}">${d}</option>`).join('')}
          </select>
        </div>
        <div class="filter-item">
          <label class="form-label" style="margin:0;">Status:</label>
          <select id="rep-all-status" class="form-control" style="width: 140px;" onchange="generateAllEmployeesReport()">
            <option value="All">All Status</option>
            <option value="Active" selected>Active Only</option>
            <option value="Inactive">Inactive Only</option>
          </select>
        </div>
        <button class="btn btn-primary btn-sm" onclick="generateAllEmployeesReport()">🔍 Generate Summary</button>
        <button class="btn btn-secondary btn-sm" onclick="printReport()">🖨️ Print</button>
        <button class="btn btn-secondary btn-sm" onclick="exportAllPDF()">📄 Export PDF</button>
        <button class="btn btn-secondary btn-sm" onclick="exportAllExcel()">📊 Export Excel</button>
        <button class="btn btn-secondary btn-sm" onclick="exportAllCSV()">📥 Export CSV</button>
      </div>

      <div id="all-employees-report-preview" class="card" style="background: #ffffff; padding: 30px;">
        <p style="color: var(--text-muted); text-align: center; padding: 40px;">Click "Generate Summary" to view all employees report.</p>
      </div>
    </div>
  `;

  // Auto-generate if employees exist
  if (State.employees.length > 0) {
    document.getElementById("rep-ind-employee").value = State.employees[0].id;
    generateIndividualReport();
  }
}

function switchReportSubTab(tab) {
  document.querySelectorAll(".report-subview").forEach(el => el.style.display = "none");
  const sec = document.getElementById(`report-section-${tab}`);
  if (sec) sec.style.display = "block";

  ["individual", "all"].forEach(t => {
    const btn = document.getElementById(`report-subtab-${t}`);
    if (btn) {
      if (t === tab) {
        btn.style.borderBottom = "3px solid var(--primary)";
        btn.style.fontWeight = "700";
      } else {
        btn.style.borderBottom = "none";
        btn.style.fontWeight = "500";
      }
    }
  });

  if (tab === "all") generateAllEmployeesReport();
}

async function generateIndividualReport() {
  const empId = document.getElementById("rep-ind-employee")?.value;
  const fromDate = document.getElementById("rep-ind-from")?.value;
  const toDate = document.getElementById("rep-ind-to")?.value;
  const preview = document.getElementById("individual-report-preview");

  if (!empId) {
    preview.innerHTML = `<p style="color: var(--text-muted); text-align:center; padding: 40px;">Please choose an employee from the dropdown.</p>`;
    return;
  }

  const params = new URLSearchParams();
  if (fromDate) params.append("from_date", fromDate);
  if (toDate) params.append("to_date", toDate);

  try {
    const data = await api(`/api/reports/individual/${empId}?${params.toString()}`);
    const emp = data.employee;
    const txs = data.transactions;

    let totAdd = 0;
    let totLess = 0;
    txs.forEach(t => {
      if (t.transaction_type === "ADD") totAdd += t.days;
      if (t.transaction_type === "LESS") totLess += t.days;
    });

    preview.innerHTML = `
      <!-- Official Header as per Prompt -->
      <div style="text-align: center; border-bottom: 2px solid #0f172a; padding-bottom: 12px; margin-bottom: 20px;">
        <h2 style="font-size: 20px; font-weight: 800; color: #0f172a; letter-spacing: 0.5px;">LOCKTITE INDIA PVT LTD</h2>
        <div style="font-size: 13px; font-weight: 700; color: var(--accent); margin-top: 2px;">EMPLOYEE LEAVE MANAGEMENT SYSTEM</div>
        <h3 style="font-size: 15px; font-weight: 700; color: #1e293b; margin-top: 6px;">EMPLOYEE LEAVE STATEMENT</h3>
        <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">
          Generated on: ${new Date().toLocaleDateString("en-IN", { dateStyle: "long", timeStyle: "short" })} &bull; Official HR Copy
        </div>
      </div>

      <!-- Employee Information Card -->
      <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 16px; margin-bottom: 20px;">
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; font-size: 13px;">
          <div><b>Employee No:</b> ${escapeHtml(emp.employee_number)}</div>
          <div><b>Department:</b> ${escapeHtml(emp.department)}</div>
          <div><b>Leave Entitlement:</b> <span style="font-weight:700;">${emp.leave_entitlement.toFixed(1)}</span></div>

          <div><b>Employee Name:</b> ${escapeHtml(emp.employee_name)}</div>
          <div><b>Designation:</b> ${escapeHtml(emp.designation)}</div>
          <div><b>Opening Balance:</b> <span style="font-weight:700;">${emp.opening_balance.toFixed(1)}</span></div>

          <div><b>Date of Joining:</b> ${escapeHtml(emp.date_of_joining)}</div>
          <div><b>Status:</b> ${escapeHtml(emp.status)}</div>
          <div><b>Leave Taken:</b> <span style="font-weight:700; color:var(--danger);">${emp.leave_taken.toFixed(1)}</span></div>

          <div><b>Contact:</b> ${escapeHtml(emp.mobile || '-')}</div>
          <div><b>Period:</b> ${fromDate || 'Start'} to ${toDate || 'Present'}</div>
          <div><b>Current Balance:</b> <span style="font-weight:800; color:var(--success); font-size: 15px;">${emp.current_balance.toFixed(1)}</span></div>
        </div>
      </div>

      <!-- Statement Transactions Table -->
      <div class="table-responsive">
        <table class="table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Leave Type</th>
              <th>Transaction</th>
              <th style="text-align: right;">Days</th>
              <th>Remarks</th>
              <th>Recorded By</th>
            </tr>
          </thead>
          <tbody>
            ${txs.length === 0 ? `
              <tr><td colspan="6" style="text-align: center; padding: 25px; color: var(--text-muted);">No leave transactions recorded for this period.</td></tr>
            ` : txs.map(t => `
              <tr>
                <td>${escapeHtml(t.from_date)}${t.from_date !== t.to_date ? ` to ${t.to_date}` : ''}</td>
                <td>${escapeHtml(t.leave_type_name)}</td>
                <td><span class="badge ${t.transaction_type === 'ADD' ? 'badge-add' : 'badge-less'}">${t.transaction_type}</span></td>
                <td style="text-align: right;"><b>${t.days.toFixed(1)}</b></td>
                <td>${escapeHtml(t.reason || '-')}</td>
                <td>${escapeHtml(t.created_by)}</td>
              </tr>
            `).join('')}
          </tbody>
          <tfoot>
            <tr>
              <td colspan="3"><b>TOTALS SUMMARY</b></td>
              <td style="text-align: right;">
                <b>+ADD: ${totAdd.toFixed(1)} | -LESS: ${totLess.toFixed(1)}</b>
              </td>
              <td colspan="2">
                <b>Net Taken: ${(totAdd - totLess).toFixed(1)} | Final Leave Balance: ${emp.current_balance.toFixed(1)} days</b>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      <!-- Official Signatures Block -->
      <div style="display: flex; justify-content: space-between; margin-top: 45px; padding-top: 20px; page-break-inside: avoid;">
        <div style="text-align: center; width: 180px; border-top: 1px solid #000; padding-top: 6px; font-size: 12px; font-weight: bold;">
          Prepared By<br/><span style="font-size: 10px; font-weight: normal; color: var(--text-muted);">Office Staff / HR</span>
        </div>
        <div style="text-align: center; width: 180px; border-top: 1px solid #000; padding-top: 6px; font-size: 12px; font-weight: bold;">
          Verified By<br/><span style="font-size: 10px; font-weight: normal; color: var(--text-muted);">Department Head</span>
        </div>
        <div style="text-align: center; width: 180px; border-top: 1px solid #000; padding-top: 6px; font-size: 12px; font-weight: bold;">
          Authorized Signatory<br/><span style="font-size: 10px; font-weight: normal; color: var(--text-muted);">Locktite India Pvt Ltd</span>
        </div>
      </div>
    `;
  } catch (err) {
    preview.innerHTML = `<div class="alert alert-danger">Error: ${escapeHtml(err.message)}</div>`;
  }
}

async function generateAllEmployeesReport() {
  const dept = document.getElementById("rep-all-dept")?.value || "All";
  const status = document.getElementById("rep-all-status")?.value || "All";
  const preview = document.getElementById("all-employees-report-preview");

  try {
    const data = await api(`/api/reports/all-employees?department=${dept}&status=${status}`);
    const rows = data.data;

    let totEnt = 0, totOp = 0, totTaken = 0, totBal = 0;
    rows.forEach(r => {
      totEnt += r.leave_entitlement;
      totOp += r.opening_balance;
      totTaken += r.leave_taken;
      totBal += r.current_balance;
    });

    preview.innerHTML = `
      <div style="text-align: center; border-bottom: 2px solid #0f172a; padding-bottom: 12px; margin-bottom: 20px;">
        <h2 style="font-size: 20px; font-weight: 800; color: #0f172a; letter-spacing: 0.5px;">LOCKTITE INDIA PVT LTD</h2>
        <div style="font-size: 13px; font-weight: 700; color: var(--accent); margin-top: 2px;">EMPLOYEE LEAVE MANAGEMENT SYSTEM</div>
        <h3 style="font-size: 15px; font-weight: 700; color: #1e293b; margin-top: 6px;">ALL EMPLOYEES LEAVE SUMMARY REPORT</h3>
        <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">
          Filter: Department (${dept}) &bull; Status (${status}) &bull; Generated on: ${new Date().toLocaleDateString("en-IN", { dateStyle: "long", timeStyle: "short" })}
        </div>
      </div>

      <div class="table-responsive">
        <table class="table">
          <thead>
            <tr>
              <th>Employee No</th>
              <th>Employee Name</th>
              <th>Department</th>
              <th>Designation</th>
              <th style="text-align: right;">Entitlement</th>
              <th style="text-align: right;">Opening</th>
              <th style="text-align: right;">Taken</th>
              <th style="text-align: right;">Balance</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(emp => `
              <tr>
                <td><b>${escapeHtml(emp.employee_number)}</b></td>
                <td><b>${escapeHtml(emp.employee_name)}</b></td>
                <td>${escapeHtml(emp.department)}</td>
                <td>${escapeHtml(emp.designation)}</td>
                <td style="text-align: right;">${emp.leave_entitlement.toFixed(1)}</td>
                <td style="text-align: right;">${emp.opening_balance.toFixed(1)}</td>
                <td style="text-align: right; color: var(--danger); font-weight:700;">${emp.leave_taken.toFixed(1)}</td>
                <td style="text-align: right; color: ${emp.current_balance <= 3 ? 'var(--danger)' : 'var(--success)'}; font-weight:800;">
                  ${emp.current_balance.toFixed(1)}
                </td>
                <td><span class="badge ${emp.status === 'Active' ? 'badge-active' : 'badge-inactive'}">${emp.status}</span></td>
              </tr>
            `).join('')}
          </tbody>
          <tfoot>
            <tr>
              <td colspan="4"><b>TOTALS (${rows.length} Employees)</b></td>
              <td style="text-align: right;"><b>${totEnt.toFixed(1)}</b></td>
              <td style="text-align: right;"><b>${totOp.toFixed(1)}</b></td>
              <td style="text-align: right; color: var(--danger);"><b>${totTaken.toFixed(1)}</b></td>
              <td style="text-align: right; color: var(--success);"><b>${totBal.toFixed(1)}</b></td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>

      <!-- Signatures -->
      <div style="display: flex; justify-content: space-between; margin-top: 45px; padding-top: 20px; page-break-inside: avoid;">
        <div style="text-align: center; width: 180px; border-top: 1px solid #000; padding-top: 6px; font-size: 12px; font-weight: bold;">
          HR & Admin Head<br/><span style="font-size: 10px; font-weight: normal; color: var(--text-muted);">Locktite India Pvt Ltd</span>
        </div>
        <div style="text-align: center; width: 180px; border-top: 1px solid #000; padding-top: 6px; font-size: 12px; font-weight: bold;">
          Operations Manager<br/><span style="font-size: 10px; font-weight: normal; color: var(--text-muted);">Locktite India Pvt Ltd</span>
        </div>
        <div style="text-align: center; width: 180px; border-top: 1px solid #000; padding-top: 6px; font-size: 12px; font-weight: bold;">
          Managing Director<br/><span style="font-size: 10px; font-weight: normal; color: var(--text-muted);">Locktite India Pvt Ltd</span>
        </div>
      </div>
    `;
  } catch (err) {
    preview.innerHTML = `<div class="alert alert-danger">Error: ${escapeHtml(err.message)}</div>`;
  }
}

function printReport() {
  window.print();
}

function exportIndPDF() {
  const empId = document.getElementById("rep-ind-employee")?.value;
  if (!empId) { showToast("Select an employee first", "warning"); return; }
  const fromDate = document.getElementById("rep-ind-from")?.value || "";
  const toDate = document.getElementById("rep-ind-to")?.value || "";
  window.open(`/api/reports/individual/${empId}/pdf?from_date=${fromDate}&to_date=${toDate}&session_token=${State.token}`);
}

function exportIndExcel() {
  const empId = document.getElementById("rep-ind-employee")?.value;
  if (!empId) { showToast("Select an employee first", "warning"); return; }
  const fromDate = document.getElementById("rep-ind-from")?.value || "";
  const toDate = document.getElementById("rep-ind-to")?.value || "";
  window.open(`/api/reports/individual/${empId}/excel?from_date=${fromDate}&to_date=${toDate}&session_token=${State.token}`);
}

function exportAllPDF() {
  const dept = document.getElementById("rep-all-dept")?.value || "All";
  const status = document.getElementById("rep-all-status")?.value || "All";
  window.open(`/api/reports/all-employees/pdf?department=${dept}&status=${status}&session_token=${State.token}`);
}

function exportAllExcel() {
  const dept = document.getElementById("rep-all-dept")?.value || "All";
  const status = document.getElementById("rep-all-status")?.value || "All";
  window.open(`/api/reports/all-employees/excel?department=${dept}&status=${status}&session_token=${State.token}`);
}

function exportAllCSV() {
  const dept = document.getElementById("rep-all-dept")?.value || "All";
  const status = document.getElementById("rep-all-status")?.value || "All";
  window.open(`/api/reports/all-employees/csv?department=${dept}&status=${status}&session_token=${State.token}`);
}

function exportEmployeesCSV() {
  window.open(`/api/reports/all-employees/csv?department=All&status=All&session_token=${State.token}`);
}

function downloadIndividualPDF(id) {
  window.open(`/api/reports/individual/${id}/pdf?session_token=${State.token}`);
}

function downloadIndividualExcel(id) {
  window.open(`/api/reports/individual/${id}/excel?session_token=${State.token}`);
}

// --------------------------------------------------------------------------
// 5. ADMINISTRATION MODULE (USERS, LEAVE TYPES, AUDIT LOG, BACKUP & RESTORE, SETTINGS)
// --------------------------------------------------------------------------
async function renderAdminUsers() {
  const container = document.getElementById("view-admin-users");
  container.innerHTML = `
    <div class="page-header">
      <div class="page-title-wrap">
        <h1>User Management</h1>
        <p>Manage office system users and role permissions for Locktite India Pvt Ltd</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary" onclick="openAddUserModal()">➕ Add New User</button>
      </div>
    </div>
    <div class="card" style="padding:0; overflow:hidden;">
      <div class="table-responsive">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>User ID</th>
              <th>Full Name</th>
              <th>Role</th>
              <th>Status</th>
              <th>Created Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="admin-users-tbody">
            <tr><td colspan="7" style="text-align:center; padding:30px; color:var(--text-muted);">Loading users...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  try {
    const data = await api("/api/admin/users");
    const tbody = document.getElementById("admin-users-tbody");
    tbody.innerHTML = data.users.map(u => `
      <tr>
        <td>${u.id}</td>
        <td><b>${escapeHtml(u.user_id)}</b></td>
        <td>${escapeHtml(u.full_name)}</td>
        <td>
          <span class="user-role-badge ${u.role === 'ADMIN' ? 'role-admin' : u.role === 'ENTRY USER' ? 'role-entry' : 'role-report'}">
            ${u.role}
          </span>
        </td>
        <td>
          <span class="badge ${u.active ? 'badge-active' : 'badge-inactive'}">
            ${u.active ? 'Active' : 'Inactive'}
          </span>
        </td>
        <td>${escapeHtml(u.created_at)}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="openEditUserModal(${u.id}, '${escapeHtml(u.user_id)}', '${escapeHtml(u.full_name)}', '${u.role}', ${u.active})">✏️ Edit</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    showToast(err.message, "error");
  }
}

function openAddUserModal() {
  const modalBody = document.getElementById("modal-admin-body");
  modalBody.innerHTML = `
    <form id="form-add-user" onsubmit="handleAddUserSubmit(event)">
      <div class="form-group">
        <label class="form-label required">User ID (Login Username)</label>
        <input type="text" id="add-user-userid" class="form-control" required placeholder="e.g. jsmith">
      </div>
      <div class="form-group">
        <label class="form-label required">Full Name</label>
        <input type="text" id="add-user-fullname" class="form-control" required placeholder="e.g. John Smith">
      </div>
      <div class="form-group">
        <label class="form-label required">Role</label>
        <select id="add-user-role" class="form-control" required>
          <option value="ENTRY USER">ENTRY USER (Leave Entry & History)</option>
          <option value="REPORT USER">REPORT USER (Reports & Exports)</option>
          <option value="ADMIN">ADMIN (Full Access & Settings)</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label required">Initial Password</label>
        <input type="password" id="add-user-password" class="form-control" required minlength="6" placeholder="Minimum 6 characters">
      </div>
      <div class="modal-footer" style="padding-left:0; padding-right:0; margin-bottom:-10px;">
        <button type="button" class="btn btn-secondary" onclick="closeModal('modal-admin')">Cancel</button>
        <button type="submit" class="btn btn-primary">Create User</button>
      </div>
    </form>
  `;
  document.getElementById("modal-admin-title").textContent = "Create New System User";
  openModal("modal-admin");
}

async function handleAddUserSubmit(e) {
  e.preventDefault();
  const payload = {
    user_id: document.getElementById("add-user-userid").value.trim(),
    full_name: document.getElementById("add-user-fullname").value.trim(),
    role: document.getElementById("add-user-role").value,
    password: document.getElementById("add-user-password").value
  };

  try {
    const res = await api("/api/admin/users", { method: "POST", body: payload });
    showToast(res.message, "success");
    closeModal("modal-admin");
    renderAdminUsers();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function openEditUserModal(id, userId, fullName, role, active) {
  const modalBody = document.getElementById("modal-admin-body");
  modalBody.innerHTML = `
    <form id="form-edit-user" onsubmit="handleEditUserSubmit(event, ${id})">
      <div class="form-group">
        <label class="form-label">User ID</label>
        <input type="text" class="form-control" value="${userId}" readonly style="background:#f8fafc; font-weight:700;">
      </div>
      <div class="form-group">
        <label class="form-label required">Full Name</label>
        <input type="text" id="edit-user-fullname" class="form-control" value="${fullName}" required>
      </div>
      <div class="form-group">
        <label class="form-label required">Role</label>
        <select id="edit-user-role" class="form-control" required>
          <option value="ENTRY USER" ${role === 'ENTRY USER' ? 'selected' : ''}>ENTRY USER</option>
          <option value="REPORT USER" ${role === 'REPORT USER' ? 'selected' : ''}>REPORT USER</option>
          <option value="ADMIN" ${role === 'ADMIN' ? 'selected' : ''}>ADMIN</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Account Status</label>
        <select id="edit-user-active" class="form-control">
          <option value="true" ${active ? 'selected' : ''}>Active</option>
          <option value="false" ${!active ? 'selected' : ''}>Inactive (Blocked)</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Reset Password (leave blank to keep current)</label>
        <input type="password" id="edit-user-password" class="form-control" placeholder="New password (optional)">
      </div>
      <div class="modal-footer" style="padding-left:0; padding-right:0; margin-bottom:-10px;">
        <button type="button" class="btn btn-secondary" onclick="closeModal('modal-admin')">Cancel</button>
        <button type="submit" class="btn btn-primary">Save Changes</button>
      </div>
    </form>
  `;
  document.getElementById("modal-admin-title").textContent = `Edit User: ${userId}`;
  openModal("modal-admin");
}

async function handleEditUserSubmit(e, id) {
  e.preventDefault();
  const payload = {
    full_name: document.getElementById("edit-user-fullname").value.trim(),
    role: document.getElementById("edit-user-role").value,
    active: document.getElementById("edit-user-active").value === "true",
    new_password: document.getElementById("edit-user-password").value || null
  };

  try {
    const res = await api(`/api/admin/users/${id}`, { method: "PUT", body: payload });
    showToast(res.message, "success");
    closeModal("modal-admin");
    renderAdminUsers();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Leave Types Admin
async function renderAdminLeaveTypes() {
  const container = document.getElementById("view-admin-leave-types");
  container.innerHTML = `
    <div class="page-header">
      <div class="page-title-wrap">
        <h1>Leave Types Management</h1>
        <p>Configure active leave categories available in Locktite India Pvt Ltd</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary" onclick="openAddLeaveTypeModal()">➕ Add Leave Type</button>
      </div>
    </div>
    <div class="card" style="padding:0; overflow:hidden;">
      <div class="table-responsive">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Leave Type Name</th>
              <th>Description</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody id="admin-leavetypes-tbody">
            <tr><td colspan="5" style="text-align:center; padding:30px; color:var(--text-muted);">Loading leave types...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  try {
    const data = await api("/api/admin/leave-types");
    const tbody = document.getElementById("admin-leavetypes-tbody");
    tbody.innerHTML = data.leave_types.map(lt => `
      <tr>
        <td>${lt.id}</td>
        <td><b>${escapeHtml(lt.name)}</b></td>
        <td>${escapeHtml(lt.description || '-')}</td>
        <td><span class="badge ${lt.active ? 'badge-active' : 'badge-inactive'}">${lt.active ? 'Active' : 'Inactive'}</span></td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="openEditLeaveTypeModal(${lt.id}, '${escapeHtml(lt.name)}', '${escapeHtml(lt.description || '')}', ${lt.active})">✏️ Edit</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    showToast(err.message, "error");
  }
}

function openAddLeaveTypeModal() {
  const modalBody = document.getElementById("modal-admin-body");
  modalBody.innerHTML = `
    <form id="form-add-lt" onsubmit="handleAddLeaveTypeSubmit(event)">
      <div class="form-group">
        <label class="form-label required">Leave Type Name</label>
        <input type="text" id="add-lt-name" class="form-control" required placeholder="e.g. Bereavement Leave">
      </div>
      <div class="form-group">
        <label class="form-label">Description / Policy Details</label>
        <input type="text" id="add-lt-desc" class="form-control" placeholder="Brief description of when this applies">
      </div>
      <div class="modal-footer" style="padding-left:0; padding-right:0; margin-bottom:-10px;">
        <button type="button" class="btn btn-secondary" onclick="closeModal('modal-admin')">Cancel</button>
        <button type="submit" class="btn btn-primary">Create Leave Type</button>
      </div>
    </form>
  `;
  document.getElementById("modal-admin-title").textContent = "Add Official Leave Type";
  openModal("modal-admin");
}

async function handleAddLeaveTypeSubmit(e) {
  e.preventDefault();
  const payload = {
    name: document.getElementById("add-lt-name").value.trim(),
    description: document.getElementById("add-lt-desc").value.trim() || null,
    active: true
  };
  try {
    const res = await api("/api/admin/leave-types", { method: "POST", body: payload });
    showToast(res.message, "success");
    closeModal("modal-admin");
    loadLeaveTypes();
    renderAdminLeaveTypes();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function openEditLeaveTypeModal(id, name, desc, active) {
  const modalBody = document.getElementById("modal-admin-body");
  modalBody.innerHTML = `
    <form id="form-edit-lt" onsubmit="handleEditLeaveTypeSubmit(event, ${id})">
      <div class="form-group">
        <label class="form-label required">Leave Type Name</label>
        <input type="text" id="edit-lt-name" class="form-control" value="${name}" required>
      </div>
      <div class="form-group">
        <label class="form-label">Description</label>
        <input type="text" id="edit-lt-desc" class="form-control" value="${desc}">
      </div>
      <div class="form-group">
        <label class="form-label">Status</label>
        <select id="edit-lt-active" class="form-control">
          <option value="true" ${active ? 'selected' : ''}>Active</option>
          <option value="false" ${!active ? 'selected' : ''}>Inactive</option>
        </select>
      </div>
      <div class="modal-footer" style="padding-left:0; padding-right:0; margin-bottom:-10px;">
        <button type="button" class="btn btn-secondary" onclick="closeModal('modal-admin')">Cancel</button>
        <button type="submit" class="btn btn-primary">Update Leave Type</button>
      </div>
    </form>
  `;
  document.getElementById("modal-admin-title").textContent = `Edit Leave Type: ${name}`;
  openModal("modal-admin");
}

async function handleEditLeaveTypeSubmit(e, id) {
  e.preventDefault();
  const payload = {
    name: document.getElementById("edit-lt-name").value.trim(),
    description: document.getElementById("edit-lt-desc").value.trim() || null,
    active: document.getElementById("edit-lt-active").value === "true"
  };
  try {
    const res = await api(`/api/admin/leave-types/${id}`, { method: "PUT", body: payload });
    showToast(res.message, "success");
    closeModal("modal-admin");
    loadLeaveTypes();
    renderAdminLeaveTypes();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Audit Logs
async function renderAdminAuditLogs() {
  const container = document.getElementById("view-admin-audit");
  container.innerHTML = `
    <div class="page-header">
      <div class="page-title-wrap">
        <h1>Audit Trail & System Logs</h1>
        <p>Comprehensive immutable activity log for Locktite India Pvt Ltd compliance</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-secondary" onclick="window.open('/api/admin/audit-logs/csv?session_token=' + State.token)">📥 Export CSV</button>
      </div>
    </div>

    <div class="filter-bar">
      <div class="filter-item">
        <label class="form-label" style="margin:0;">Module:</label>
        <select id="audit-module-filter" class="form-control" style="width: 160px;" onchange="loadAuditLogs()">
          <option value="All">All Modules</option>
          <option value="MASTER">MASTER</option>
          <option value="ENTRY">ENTRY</option>
          <option value="ADJUSTMENT">ADJUSTMENT</option>
          <option value="REPORTS">REPORTS</option>
          <option value="ADMINISTRATION">ADMINISTRATION</option>
          <option value="SECURITY">SECURITY</option>
          <option value="SYSTEM">SYSTEM</option>
        </select>
      </div>
      <button class="btn btn-secondary btn-sm" onclick="loadAuditLogs()">🔄 Refresh</button>
    </div>

    <div class="card" style="padding:0; overflow:hidden;">
      <div class="table-responsive">
        <table class="table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>User ID</th>
              <th>User Name</th>
              <th>Module</th>
              <th>Action</th>
              <th>Emp No</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody id="audit-logs-tbody">
            <tr><td colspan="7" style="text-align:center; padding:30px; color:var(--text-muted);">Loading audit trail...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;
  loadAuditLogs();
}

async function loadAuditLogs() {
  const mod = document.getElementById("audit-module-filter")?.value || "All";
  const params = new URLSearchParams();
  if (mod && mod !== "All") params.append("module", mod);

  try {
    const res = await api(`/api/admin/audit-logs?${params.toString()}`);
    const tbody = document.getElementById("audit-logs-tbody");
    if (!tbody) return;

    if (res.audit_logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:30px; color:var(--text-muted);">No audit logs found.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.audit_logs.map(log => `
      <tr>
        <td style="font-size:12px; color:var(--text-muted); white-space:nowrap;">${escapeHtml(log.created_at)}</td>
        <td><b>${escapeHtml(log.user_id)}</b></td>
        <td>${escapeHtml(log.user_name || '-')}</td>
        <td><span class="badge badge-inactive">${log.module}</span></td>
        <td><b>${escapeHtml(log.action)}</b></td>
        <td><b>${escapeHtml(log.employee_number || '-')}</b></td>
        <td>${escapeHtml(log.description)}</td>
      </tr>
    `).join('');
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Backup & Restore
async function renderAdminBackups() {
  const container = document.getElementById("view-admin-backup");
  container.innerHTML = `
    <div class="page-header">
      <div class="page-title-wrap">
        <h1>Database Backup & Restore</h1>
        <p>Protect official office records for Locktite India Pvt Ltd with online SQLite backups</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary" onclick="createDatabaseBackup()">💾 Create Backup Now</button>
      </div>
    </div>

    <div class="alert alert-info">
      <b>💡 Online Backup Guarantee:</b> Locktite Leave Management uses SQLite's official online backup API. Backups can be safely taken at any time without locking the office database or disrupting staff.
    </div>

    <div class="card">
      <div class="card-title">Available Database Backups</div>
      <div class="table-responsive">
        <table class="table">
          <thead>
            <tr>
              <th>Backup File Name</th>
              <th>File Size</th>
              <th>Created Date / Time</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="backups-tbody">
            <tr><td colspan="4" style="text-align:center; padding:20px; color:var(--text-muted);">Scanning backup repository...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;
  loadBackupsList();
}

async function loadBackupsList() {
  try {
    const data = await api("/api/admin/backups");
    const tbody = document.getElementById("backups-tbody");
    if (!tbody) return;

    if (data.backups.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:20px; color:var(--text-muted);">No backups found. Click "Create Backup Now" above.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.backups.map(b => `
      <tr>
        <td><b>${escapeHtml(b.filename)}</b></td>
        <td>${b.size_kb} KB</td>
        <td>${escapeHtml(b.created_at)}</td>
        <td>
          <a class="btn btn-secondary btn-sm" href="/api/admin/backup/download/${b.filename}?session_token=${State.token}" download>📥 Download</a>
          <button class="btn btn-danger btn-sm" onclick="promptRestoreDatabase('${b.filename}')">🔄 Restore</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function createDatabaseBackup() {
  try {
    showToast("Generating SQLite database snapshot...", "info");
    const res = await api("/api/admin/backup", { method: "POST" });
    showToast(res.message, "success");
    loadBackupsList();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function promptRestoreDatabase(filename) {
  const modalBody = document.getElementById("modal-sensitive-body");
  modalBody.innerHTML = `
    <div class="alert alert-danger">
      <h3 style="font-size:15px; font-weight:800; margin-bottom:6px;">⚠️ Warning: Restoring Database</h3>
      <b>Restoring a backup will replace the current database. Do you want to continue?</b>
      <br/><br/>
      Selected backup file: <b>${escapeHtml(filename)}</b>
      <br/>
      <i>Note: The system will automatically generate a safety copy of your current database before applying this restore.</i>
    </div>
    <div class="form-group">
      <label class="form-label required">Confirm with Administrator Password</label>
      <input type="password" id="restore-admin-password" class="form-control" required placeholder="Enter administrator password">
    </div>
  `;
  document.getElementById("modal-sensitive-title").textContent = "Authorize Database Restore";
  const btn = document.getElementById("btn-sensitive-confirm");
  btn.onclick = () => executeRestoreDatabase(filename);
  openModal("modal-sensitive");
}

async function executeRestoreDatabase(filename) {
  const password = document.getElementById("restore-admin-password").value;
  if (!password) {
    showToast("Password is required to restore database.", "error");
    return;
  }

  try {
    showToast("Restoring database from snapshot...", "info");
    const res = await api(`/api/admin/restore?filename=${encodeURIComponent(filename)}&password=${encodeURIComponent(password)}`, {
      method: "POST"
    });
    showToast(res.message, "success");
    closeModal("modal-sensitive");
    loadEmployeesList();
    loadBackupsList();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// System Settings
async function renderAdminSettings() {
  const container = document.getElementById("view-admin-settings");
  container.innerHTML = `
    <div class="page-header">
      <div class="page-title-wrap">
        <h1>System Settings & Configuration</h1>
        <p>Operational policies for Locktite India Pvt Ltd Leave System</p>
      </div>
    </div>
    <div class="card" style="max-width: 640px;">
      <form id="form-settings" onsubmit="handleSettingsSubmit(event)">
        <div class="form-group">
          <label class="form-label">Company Name</label>
          <input type="text" id="setting-company" class="form-control" value="Locktite India Pvt Ltd" readonly style="background:#f8fafc; font-weight:700;">
        </div>
        <div class="form-group">
          <label class="form-label">Low Leave Balance Alert Threshold (Days)</label>
          <input type="number" step="0.5" id="setting-threshold" class="form-control" value="3.0" required>
          <div class="form-help">Employees with current leave balance equal to or less than this value will appear on the dashboard alert card.</div>
        </div>
        <div class="form-group">
          <label class="form-label">Allow Negative Leave Balance</label>
          <select id="setting-negative" class="form-control">
            <option value="0">No (Strictly Block leave entries exceeding available balance)</option>
            <option value="1">Yes (Allow negative balance with warning)</option>
          </select>
        </div>
        <button type="submit" class="btn btn-primary" id="btn-save-settings">Save Settings</button>
      </form>
    </div>
  `;

  try {
    const data = await api("/api/admin/settings");
    const s = data.settings;
    if (s.low_balance_threshold) document.getElementById("setting-threshold").value = s.low_balance_threshold;
    if (s.allow_negative_balance) document.getElementById("setting-negative").value = s.allow_negative_balance;
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleSettingsSubmit(e) {
  e.preventDefault();
  const payload = {
    low_balance_threshold: document.getElementById("setting-threshold").value,
    allow_negative_balance: document.getElementById("setting-negative").value
  };

  try {
    const res = await api("/api/admin/settings", { method: "POST", body: payload });
    showToast(res.message, "success");
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Change Password
async function handleChangePasswordSubmit(e) {
  e.preventDefault();
  const curr = document.getElementById("cp-current").value;
  const newP = document.getElementById("cp-new").value;
  const confP = document.getElementById("cp-confirm").value;

  if (newP !== confP) {
    showToast("New passwords do not match.", "error");
    return;
  }

  try {
    const res = await api("/api/auth/change-password", {
      method: "POST",
      body: { current_password: curr, new_password: newP }
    });
    showToast(res.message, "success");
    closeModal("modal-change-password");
  } catch (err) {
    showToast(err.message, "error");
  }
}
