/** Shared modal markup appended on every authenticated page. */
export const MODALS_AND_TOAST_HTML = `
  <div class="modal-overlay" id="addEmpModal">
    <div class="modal">
      <div class="modal-header"><h3>Add New Employee</h3><button type="button" class="modal-close" data-close>&times;</button></div>
      <div class="modal-body">
        <div class="form-grid">
          <label class="form-field"><span>First Name</span><input type="text" id="newEmpFirst" placeholder="e.g. Jane" required /></label>
          <label class="form-field"><span>Last Name</span><input type="text" id="newEmpLast" placeholder="e.g. Smith" required /></label>
          <label class="form-field"><span>Email</span><input type="email" id="newEmpEmail" placeholder="jane@company.com" required /></label>
          <label class="form-field"><span>Phone</span><input type="tel" id="newEmpPhone" placeholder="+1 (555) 000-0000" /></label>
          <label class="form-field"><span>Department</span><select id="newEmpDept"><option>Engineering</option><option>Finance</option><option>Support</option><option>Marketing</option><option>Human Resources</option></select></label>
          <label class="form-field"><span>Role</span><select id="newEmpRole"><option value="employee">Employee</option><option value="manager">Manager</option><option value="admin">Admin</option></select></label>
          <label class="form-field"><span>Salary</span><input type="number" id="newEmpSalary" placeholder="5000" required /></label>
          <label class="form-field"><span>Start Date</span><input type="date" id="newEmpStart" required /></label>
          <label class="form-field"><span>Manager</span><select id="newEmpManager"><option value="">None</option></select></label>
          <label class="form-field"><span>Password</span><input type="text" id="newEmpPassword" placeholder="Auto-generated" /></label>
        </div>
        <div class="login-error" id="addEmpError" style="margin-top:.5rem"></div>
      </div>
      <div class="modal-footer"><button type="button" class="btn btn-outline" data-close>Cancel</button><button type="button" class="btn btn-primary" id="confirmAddEmp">Add Employee</button></div>
    </div>
  </div>
  <div class="modal-overlay" id="leaveModal">
    <div class="modal">
      <div class="modal-header"><h3>Request Leave</h3><button type="button" class="modal-close" data-close>&times;</button></div>
      <div class="modal-body">
        <div class="form-grid">
          <label class="form-field"><span>Leave Type</span><select id="leaveType"><option value="Paid Leave">Paid Leave</option><option value="Sick Leave">Sick Leave</option><option value="Personal">Personal</option><option value="Unpaid">Unpaid</option></select></label>
          <label class="form-field"><span>Start Date</span><input type="date" id="leaveStart" required /></label>
          <label class="form-field"><span>End Date</span><input type="date" id="leaveEnd" required /></label>
          <label class="form-field full"><span>Reason</span><textarea rows="3" id="leaveReason" placeholder="Optional reason…"></textarea></label>
        </div>
        <div class="login-error" id="leaveError" style="margin-top:.5rem"></div>
      </div>
      <div class="modal-footer"><button type="button" class="btn btn-outline" data-close>Cancel</button><button type="button" class="btn btn-primary" id="confirmLeave">Submit Request</button></div>
    </div>
  </div>
  <div class="modal-overlay" id="taskModal">
    <div class="modal">
      <div class="modal-header"><h3>Assign New Task</h3><button type="button" class="modal-close" data-close>&times;</button></div>
      <div class="modal-body">
        <div class="form-grid">
          <label class="form-field full"><span>Task Title</span><input type="text" id="taskTitle" placeholder="e.g. Complete quarterly review" required /></label>
          <label class="form-field"><span>Assignee</span><select id="taskAssignee"></select></label>
          <label class="form-field"><span>Priority</span><select id="taskPriority"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option></select></label>
          <label class="form-field"><span>Due Date</span><input type="date" id="taskDue" required /></label>
          <label class="form-field"><span>Status</span><select id="taskStatus"><option value="todo">To Do</option><option value="inprogress">In Progress</option></select></label>
        </div>
        <div class="login-error" id="taskError" style="margin-top:.5rem"></div>
      </div>
      <div class="modal-footer"><button type="button" class="btn btn-outline" data-close>Cancel</button><button type="button" class="btn btn-primary" id="confirmTask">Assign Task</button></div>
    </div>
  </div>
  <div class="notif-panel" id="notifPanel">
    <div class="notif-header"><h3>Notifications</h3><button type="button" class="btn btn-sm btn-outline" id="clearNotifs">Clear All</button></div>
    <ul class="notif-list" id="notifList"></ul>
  </div>
  <div class="toast" id="toast"></div>
`;
