// Authentication state
let authToken = localStorage.getItem('authToken');
let currentUser = null;

// Notification system
class NotificationManager {
  constructor() {
    this.container = null;
    this.notifications = new Map();
    this.nextId = 1;
  }

  init() {
    this.container = document.getElementById('notificationContainer');
  }

  show(message, type = 'info', duration = 0) {
    const id = this.nextId++;
    const notification = this.createElement(id, message, type);
    
    this.container.appendChild(notification);
    this.notifications.set(id, { element: notification, type, message });
    
    // Show clear all button when notifications exist
    this.updateClearAllButton();

    // Auto-remove after duration (0 means persistent)
    if (duration > 0) {
      setTimeout(() => this.remove(id), duration);
    }

    return id;
  }

  createElement(id, message, type) {
    const div = document.createElement('div');
    div.className = `notification p-4 rounded-md shadow-lg border ${this.getTypeClasses(type)}`;
    div.setAttribute('data-notification-id', id);
    
    div.innerHTML = `
      <div class="flex items-start justify-between">
        <div class="flex-1">
          <div class="flex items-center">
            ${this.getTypeIcon(type)}
            <span class="ml-2 text-sm font-medium">${this.getTypeTitle(type)}</span>
          </div>
          <p class="mt-1 text-sm">${message}</p>
        </div>
        <div class="ml-4 flex space-x-1">
          <button onclick="notifications.remove(${id})" 
                  class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
            </svg>
          </button>
        </div>
      </div>
    `;

    return div;
  }

  getTypeClasses(type) {
    const classes = {
      success: 'bg-green-50/80 border-green-200 text-green-800 dark:bg-green-900/80 dark:border-green-700 dark:text-green-200',
      error: 'bg-red-50/80 border-red-200 text-red-800 dark:bg-red-900/80 dark:border-red-700 dark:text-red-200',
      warning: 'bg-yellow-50/80 border-yellow-200 text-yellow-800 dark:bg-yellow-900/80 dark:border-yellow-700 dark:text-yellow-200',
      info: 'bg-blue-50/80 border-blue-200 text-blue-800 dark:bg-blue-900/80 dark:border-blue-700 dark:text-blue-200'
    };
    return classes[type] || classes.info;
  }

  getTypeIcon(type) {
    const icons = {
      success: '<svg class="w-5 h-5 text-green-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>',
      error: '<svg class="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>',
      warning: '<svg class="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>',
      info: '<svg class="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>'
    };
    return icons[type] || icons.info;
  }

  getTypeTitle(type) {
    const titles = {
      success: 'Success',
      error: 'Error',
      warning: 'Warning',
      info: 'Info'
    };
    return titles[type] || 'Info';
  }

  remove(id) {
    const notification = this.notifications.get(id);
    if (notification) {
      notification.element.classList.add('removing');
      setTimeout(() => {
        if (notification.element.parentNode) {
          notification.element.parentNode.removeChild(notification.element);
        }
        this.notifications.delete(id);
        this.updateClearAllButton();
      }, 300);
    }
  }

  clearAll() {
    this.notifications.forEach((_, id) => this.remove(id));
  }

  updateClearAllButton() {
    const clearAllContainer = document.getElementById('clearAllContainer');
    if (clearAllContainer) {
      if (this.notifications.size > 0) {
        clearAllContainer.classList.remove('hidden');
      } else {
        clearAllContainer.classList.add('hidden');
      }
    }
  }

  success(message, duration = 0) {
    return this.show(message, 'success', duration);
  }

  error(message, duration = 0) {
    return this.show(message, 'error', duration);
  }

  warning(message, duration = 0) {
    return this.show(message, 'warning', duration);
  }

  info(message, duration = 0) {
    return this.show(message, 'info', duration);
  }
}

// Global notification instance
const notifications = new NotificationManager();

// Check authentication on page load
document.addEventListener('DOMContentLoaded', () => {
  notifications.init(); // Initialize notification system
  
  if (authToken) {
    verifyToken();
    // Set up periodic token verification (every 5 minutes)
    // setInterval(verifyTokenSilently, 5 * 60 * 1000);
  } else {
    showLoginForm();
  }
});

function showLoginForm() {
  document.getElementById('loginForm').classList.remove('hidden');
  document.getElementById('adminInterface').classList.add('hidden');
}

function showAdminInterface() {
  document.getElementById('loginForm').classList.add('hidden');
  document.getElementById('adminInterface').classList.remove('hidden');
  
  // Restore the last viewed page from localStorage, default to 'users'
  const lastViewedPage = localStorage.getItem('lastViewedPage') || 'users';
  selectView(lastViewedPage);
}

function hideError() {
  document.getElementById('loginError').classList.add('hidden');
}

function showError(message) {
  document.getElementById('loginErrorText').textContent = message;
  document.getElementById('loginError').classList.remove('hidden');
}

// Login form submission
document.getElementById('loginFormElement').addEventListener('submit', async (e) => {
  e.preventDefault();
  hideError();
  
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  
  const formData = new FormData();
  formData.append('username', username);
  formData.append('password', password);
  
  try {
    const response = await fetch('/auth/login', {
      method: 'POST',
      body: formData
    });
    
    if (response.ok) {
      const data = await response.json();
      authToken = data.access_token;
      localStorage.setItem('authToken', authToken);
      await getCurrentUser();
      showAdminInterface();
    } else {
      const error = await response.json();
      notifications.error(error.detail || 'Login failed');
    }
  } catch (error) {
    notifications.error('Network error. Please try again.');
  }
});

async function verifyToken() {
  try {
    const response = await fetch('/auth/me', {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });
    
    if (response.ok) {
      await getCurrentUser();
      showAdminInterface();
    } else {
      logout();
    }
  } catch (error) {
    logout();
  }
}

async function getCurrentUser() {
  try {
    const response = await fetch('/auth/me', {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });
    
    if (response.ok) {
      currentUser = await response.json();
      document.getElementById('userInfo').textContent = `Logged in as: ${currentUser.username}`;
    }
  } catch (error) {
    console.error('Failed to get user info:', error);
  }
}

function logout() {
  authToken = null;
  currentUser = null;
  localStorage.removeItem('authToken');
  showLoginForm();
  // Clear any existing content to prevent confusion
  const mainContent = document.getElementById('mainContent');
  if (mainContent) {
    mainContent.innerHTML = '<div class="text-center text-gray-500 py-8">Please log in to continue.</div>';
  }
}

// Update fetch function to include auth header
async function authenticatedFetch(url, options = {}) {
  if (!authToken) {
    logout();
    throw new Error('Not authenticated');
  }
  
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${authToken}`,
    ...options.headers
  };
  
  try {
    const response = await fetch(url, {
      ...options,
      headers
    });
    
    if (response.status === 401) {
      // Token is invalid or expired
      logout();
      throw new AuthenticationError('Authentication expired. Please log in again.');
    }
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return response;
  } catch (error) {
    if (error instanceof AuthenticationError) {
      // Re-throw authentication errors so they can be handled specially
      throw error;
    }
    // For network errors or other issues, also check if it might be auth-related
    if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
      // Could be a network issue, but let's verify the token is still valid
      await verifyTokenSilently();
    }
    throw error;
  }
}

// Custom error class for authentication issues
class AuthenticationError extends Error {
  constructor(message) {
    super(message);
    this.name = 'AuthenticationError';
  }
}

// Silent token verification (doesn't show login form on success)
async function verifyTokenSilently() {
  if (!authToken) {
    logout();
    return false;
  }
  
  try {
    const response = await fetch('/auth/me', {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });
    
    if (!response.ok) {
      logout();
      return false;
    }
    
    return true;
  } catch (error) {
    logout();
    return false;
  }
}

function updateNavigationHighlight(activeView) {
  // Remove active class from all navigation buttons
  const navButtons = document.querySelectorAll('[data-view]');
  navButtons.forEach(button => {
    button.classList.remove('bg-blue-600', 'text-white');
    button.classList.add('hover:bg-gray-200', 'dark:hover:bg-gray-800');
  });
  
  // Add active class to the current view button
  const activeButton = document.querySelector(`[data-view="${activeView}"]`);
  if (activeButton) {
    activeButton.classList.add('bg-blue-600', 'text-white');
    activeButton.classList.remove('hover:bg-gray-200', 'dark:hover:bg-gray-800');
  }
}

function selectView(view) {
  // Save the current view to localStorage
  localStorage.setItem('lastViewedPage', view);
  
  // Update navigation highlighting
  updateNavigationHighlight(view);
  
  switch (view) {
    case 'users':
      renderUsersView();
      break;
    case 'groups':
      renderGroupsView();
      break;
    case 'models':
      renderModelsView();
      break;
    case 'systemLogs':
      renderSystemLogsView();
      break;
    case 'transactionLogs':
      renderTransactionLogsView();
      break;
    case 'settings':
      renderSettingsView();
      break;
    case 'statistics':
    case 'currentUsage':
    case 'monthlyStats':
      renderCurrentUsageView();
      break;
    case 'yearlyStats':
      renderYearlyStatsView();
      break;
  }
}

let currentUsers = [];
let currentGroups = [];
let currentModels = [];


function filterUsers(query) {
  const lower = query.toLowerCase();
  const rows = document.querySelectorAll("#mainContent table tbody tr");
  rows.forEach(row => {
    const text = row.innerText.toLowerCase();
    row.style.display = text.includes(lower) ? "" : "none";
  });
  
  // Show/hide clear button based on whether there's search text
  const clearButton = document.getElementById('clearUserSearch');
  if (clearButton) {
    clearButton.style.display = query.length > 0 ? 'block' : 'none';
  }
}

function filterModels(query) {
  // Store the current search query globally so status filter can use it
  window.currentModelSearchQuery = query.toLowerCase();
  
  // Apply combined filtering
  applyModelFilters();
  
  // Show/hide clear button based on whether there's search text
  const clearButton = document.getElementById('clearModelSearch');
  if (clearButton) {
    clearButton.style.display = query.length > 0 ? 'block' : 'none';
  }
}

function applyModelFilters() {
  const searchQuery = window.currentModelSearchQuery || '';
  const statusFilter = document.getElementById('statusFilter')?.value || 'all';
  
  const rows = document.querySelectorAll("#mainContent table tbody tr");
  rows.forEach(row => {
    let shouldShow = true;
    
    // Apply text search filter
    if (searchQuery && !row.innerText.toLowerCase().includes(searchQuery)) {
      shouldShow = false;
    }
    
    // Apply status filter
    if (shouldShow && statusFilter !== 'all') {
      const statusCell = row.querySelector('td:nth-child(2)');
      const modelNameCell = row.querySelector('td:nth-child(1)');
      if (statusCell && modelNameCell) {
        const isAvailable = statusCell.textContent.includes('Available') && !statusCell.textContent.includes('Unavailable');
        const isFree = modelNameCell.textContent.includes('FREE');
        
        if (statusFilter === 'available' && !isAvailable) {
          shouldShow = false;
        } else if (statusFilter === 'unavailable' && isAvailable) {
          shouldShow = false;
        } else if (statusFilter === 'free' && !isFree) {
          shouldShow = false;
        }
      }
    }
    
    row.style.display = shouldShow ? "" : "none";
  });
}

function clearModelSearch() {
  const searchInput = document.getElementById('modelSearchInput');
  const clearButton = document.getElementById('clearModelSearch');
  
  if (searchInput) {
    searchInput.value = '';
    window.currentModelSearchQuery = ''; // Clear the global search query
    applyModelFilters(); // Apply combined filtering (will keep status filter but clear text filter)
    searchInput.focus(); // Refocus the input
  }
  
  if (clearButton) {
    clearButton.style.display = 'none';
  }
}

function clearUserSearch() {
  const searchInput = document.getElementById('userSearchInput');
  const clearButton = document.getElementById('clearUserSearch');
  
  if (searchInput) {
    searchInput.value = '';
    filterUsers(''); // Clear the filter
    searchInput.focus(); // Refocus the input
  }
  
  if (clearButton) {
    clearButton.style.display = 'none';
  }
}

function clearGroupSearch() {
  const searchInput = document.getElementById('groupSearchInput');
  const clearButton = document.getElementById('clearGroupSearch');
  
  if (searchInput) {
    searchInput.value = '';
    filterGroups(''); // Clear the filter
    searchInput.focus(); // Refocus the input
  }
  
  if (clearButton) {
    clearButton.style.display = 'none';
  }
}


function filterGroups(query) {
  const lower = query.toLowerCase();
  const rows = document.querySelectorAll("#mainContent table tbody tr");
  rows.forEach(row => {
    row.style.display = row.innerText.toLowerCase().includes(lower) ? "" : "none";
  });
  
  // Show/hide clear button based on whether there's search text
  const clearButton = document.getElementById('clearGroupSearch');
  if (clearButton) {
    clearButton.style.display = query.length > 0 ? 'block' : 'none';
  }
}


function filterModelsByStatus(status) {
  // Update the dropdown to match the filter
  const statusFilter = document.getElementById('statusFilter');
  if (statusFilter) {
    statusFilter.value = status;
  }
  
  // Apply combined filtering (respects both text search and status)
  applyModelFilters();
  
  // Update legend highlighting
  updateLegendHighlight(status);
}

function updateLegendHighlight(activeFilter) {
  // Remove existing highlights
  const legendItems = document.querySelectorAll('.legend-item');
  legendItems.forEach(item => {
    item.classList.remove('ring-2', 'ring-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
  });
  
  // Add highlight to active filter
  let activeItem = null;
  if (activeFilter === 'available') {
    activeItem = document.querySelector('[onclick="filterModelsByStatus(\'available\')"]');
  } else if (activeFilter === 'unavailable') {
    activeItem = document.querySelector('[onclick="filterModelsByStatus(\'unavailable\')"]');
  } else if (activeFilter === 'free') {
    activeItem = document.querySelector('[onclick="filterModelsByStatus(\'free\')"]');
  } else if (activeFilter === 'all') {
    activeItem = document.querySelector('[onclick="filterModelsByStatus(\'all\')"]');
  }
  
  if (activeItem) {
    activeItem.classList.add('ring-2', 'ring-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
  }
}


async function renderUsersView() {
  const container = document.getElementById('mainContent');
  container.innerHTML = '<h2 class="text-2xl font-bold mb-4">User Credit Management</h2>';
  container.innerHTML = `
  <div class="flex items-center justify-between mb-4">
    <h2 class="text-2xl font-bold">User Credit Management</h2>
    <div class="flex items-center border border-gray-300 dark:border-gray-700 rounded-xl px-2 py-1 w-64 bg-white dark:bg-gray-900">
      <div class="self-center mr-2 text-gray-500 dark:text-gray-400">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
          <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clip-rule="evenodd"></path>
        </svg>
      </div>
      <input 
        id="userSearchInput"
        class="w-full text-sm bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 outline-none"
        placeholder="Search"
        oninput="filterUsers(this.value)"
      />
      <button id="clearUserSearch" onclick="clearUserSearch()" class="ml-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors" style="display: none;" title="Clear search">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
          <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"/>
        </svg>
      </button>
    </div>
  </div>`;

  try {
    const res = await authenticatedFetch('/api/credits/users');
    currentUsers = await res.json();

    let table = `<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
      <thead class="text-xs uppercase bg-gray-50 dark:bg-gray-850">
        <tr>
          <th class="px-3 py-1.5">Group</th>
          <th class="px-3 py-1.5">Name</th>
          <th class="px-3 py-1.5">Email</th>
          <th class="px-3 py-1.5">Credits</th>
          <th class="px-3 py-1.5 text-right">Actions</th>
        </tr>
      </thead>
      <tbody>`;

    for (const user of currentUsers) {
      table += `
        <tr class="bg-white dark:bg-gray-900 border-t">
          <td class="px-3 py-1 text-xs font-bold text-blue-600 dark:text-blue-300">${user.role}</td>
          <td class="px-3 py-1">${user.name}</td>
          <td class="px-3 py-1">${user.email}</td>
          <td class="px-3 py-1">${user.credits}</td>
          <td class="px-3 py-1 text-right">
            <button class="px-2 py-1 text-sm bg-blue-600 text-white rounded" onclick="editUser('${user.id}')">Edit</button>
          </td>
        </tr>`;
    }

    table += '</tbody></table>';
container.innerHTML += table;
container.innerHTML += `
  <div class="flex gap-2 mt-4">
    <button onclick="exportUsersToExcel()" class="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
        <path stroke-linecap="round" stroke-linejoin="round" d="m9 12.75 3 3m0 0 3-3m-3 3v-7.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
      </svg>
      Export Users to Excel
    </button>
    <button onclick="syncUsersFromOpenWebUI()" class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
        <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
      </svg>
      Sync Users from OpenWebUI
    </button>
  </div>
  <div id="modalRoot"></div>`;


    container.innerHTML += `<div id="modalRoot"></div>`;
  } catch (err) {
    if (err instanceof AuthenticationError) {
      // Authentication error - user will already be redirected to login
      return;
    }
    container.innerHTML += `<p class="text-red-500">Error loading users: ${err.message}</p>`;
  }
}

function editUser(userId) {
  const user = currentUsers.find(u => u.id === userId);
  if (!user) return;

  const modal = document.createElement('div');
  modal.className = 'fixed inset-0 bg-black/30 flex items-center justify-center z-50';
  modal.innerHTML = `
    <div class="bg-white dark:bg-gray-800 p-6 rounded-lg w-full max-w-md shadow-xl">
      <div class="flex justify-between mb-4">
        <h2 class="text-lg font-bold">Edit Credits for ${user.name}</h2>
        <button onclick="this.closest('.fixed').remove()">✕</button>
      </div>
      <div class="space-y-3">
        <label class="block text-sm">Credit Amount</label>
        <input type="number" id="creditInput" value="${user.credits}" class="w-full px-2 py-1 border rounded-md bg-transparent dark:border-gray-700">
      </div>
      <div class="flex justify-end gap-2 pt-4">
        <button onclick="this.closest('.fixed').remove()" class="px-3 py-1 bg-gray-200 dark:bg-gray-700 rounded-md">Cancel</button>
        <button onclick="saveUserCredits('${user.id}')" class="px-3 py-1 bg-blue-600 text-white rounded-md">Save</button>
      </div>
    </div>`;

  document.getElementById('modalRoot').appendChild(modal);
}
function exportUsersToExcel() {
  if (!currentUsers.length) {
    notifications.warning("No user data available for export.");
    return;
  }
  const worksheet = XLSX.utils.json_to_sheet(currentUsers);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Users");
  XLSX.writeFile(workbook, "users_export.xlsx");
}

function exportGroupsToExcel() {
  if (!currentGroups.length) {
    notifications.warning("No group data available for export.");
    return;
  }
  const worksheet = XLSX.utils.json_to_sheet(currentGroups);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Groups");
  XLSX.writeFile(workbook, "groups_export.xlsx");
}

function exportModelsToExcel() {
  if (!currentModels.length) {
    notifications.warning("No model data available for export.");
    return;
  }
  const worksheet = XLSX.utils.json_to_sheet(currentModels);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Models");
  XLSX.writeFile(workbook, "models_export.xlsx");
}


async function saveUserCredits(userId) {
  const input = document.getElementById('creditInput');
  const newCredits = parseFloat(input.value);

  const res = await authenticatedFetch('/api/credits/update', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, credits: newCredits, actor: 'admin' })
  });

  const result = await res.json();
  if (result.status === 'success') {
    notifications.success(`Credits successfully updated to ${newCredits}`);
    document.querySelector('.fixed').remove();
    renderUsersView();
  } else {
    notifications.error('Error saving credits');
  }
}

async function syncUsersFromOpenWebUI() {
  const button = event.target;
  const originalText = button.innerHTML;
  
  // Show loading state
  button.innerHTML = `
    <svg class="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="m12 2v4m0 12v4m10-10h-4M6 12H2"></path>
    </svg>
    Syncing...
  `;
  button.disabled = true;

  try {
    const res = await authenticatedFetch('/api/credits/sync-users', {
      method: 'POST'
    });
    
    const result = await res.json();
    if (result.status === 'success') {
      notifications.success('Users synced successfully from OpenWebUI!');
      renderUsersView(); // Refresh the user list
    } else {
      notifications.error(`Sync failed: ${result.message}`);
    }
  } catch (error) {
    if (error instanceof AuthenticationError) {
      // Authentication error - user will already be redirected to login
      return;
    }
    notifications.error(`Sync failed: ${error.message}`);
  } finally {
    // Restore button state
    button.innerHTML = originalText;
    button.disabled = false;
  }
}

async function syncModelsFromOpenWebUI() {
  const button = event.target;
  const originalText = button.innerHTML;
  
  // Show loading state
  button.innerHTML = `
    <svg class="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="m12 2v4m0 12v4m10-10h-4M6 12H2"></path>
    </svg>
    Syncing...
  `;
  button.disabled = true;

  try {
    const res = await authenticatedFetch('/api/credits/sync-models', {
      method: 'POST'
    });
    
    const result = await res.json();
    if (result.status === 'success') {
      notifications.success('Models synced successfully from OpenWebUI!');
      renderModelsView(); // Refresh the models list
    } else {
      notifications.error(`Model sync failed: ${result.message}`);
    }
  } catch (error) {
    if (error instanceof AuthenticationError) {
      // Authentication error - user will already be redirected to login
      return;
    }
    notifications.error(`Model sync failed: ${error.message}`);
  } finally {
    // Restore button state
    button.innerHTML = originalText;
    button.disabled = false;
  }
}

async function renderGroupsView() {
  const container = document.getElementById('mainContent');
  container.innerHTML = `
  <div class="flex items-center justify-between mb-4">
    <h2 class="text-2xl font-bold">Group Management</h2>
    <div class="flex items-center border border-gray-300 dark:border-gray-700 rounded-xl px-2 py-1 w-64 bg-white dark:bg-gray-900">
      <div class="self-center mr-2 text-gray-500 dark:text-gray-400">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
          <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clip-rule="evenodd"/>
        </svg>
      </div>
      <input id="groupSearchInput" class="w-full text-sm bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 outline-none"
             placeholder="Search" oninput="filterGroups(this.value)">
      <button id="clearGroupSearch" onclick="clearGroupSearch()" class="ml-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors" style="display: none;" title="Clear search">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
          <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"/>
        </svg>
      </button>
    </div>
  </div>`;


  try {
    const res = await authenticatedFetch('/api/credits/groups');
    currentGroups = await res.json();

    let table = `<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
      <thead class="text-xs uppercase bg-gray-50 dark:bg-gray-850">
        <tr>
          <th class="px-3 py-1.5">Group Name</th>
          <th class="px-3 py-1.5">Default Credits</th>
          <th class="px-3 py-1.5 text-right">Actions</th>
        </tr>
      </thead>
      <tbody>`;

    for (const group of currentGroups) {
      table += `
        <tr class="bg-white dark:bg-gray-900 border-t">
          <td class="px-3 py-1">${group.name}</td>
          <td class="px-3 py-1">${group.default_credits}</td>
          <td class="px-3 py-1 text-right">
            <button class="px-2 py-1 text-sm bg-blue-600 text-white rounded" onclick="editGroup('${group.id}')">Edit</button>
          </td>
        </tr>`;
    }

   table += '</tbody></table>';
container.innerHTML += table;
container.innerHTML += `
  <button onclick="exportGroupsToExcel()" class="mt-4 flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
      <path stroke-linecap="round" stroke-linejoin="round" d="m9 12.75 3 3m0 0 3-3m-3 3v-7.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
    Export Groups to Excel
  </button>
  <div id="modalRoot"></div>`;


  } catch (err) {
    if (err instanceof AuthenticationError) {
      // Authentication error - user will already be redirected to login
      return;
    }
    container.innerHTML += `<p class="text-red-500">Error loading groups: ${err.message}</p>`;
  }
}

function editGroup(groupId) {
  const group = currentGroups.find(g => g.id === groupId);
  if (!group) return;

  const modal = document.createElement('div');
  modal.className = 'fixed inset-0 bg-black/30 flex items-center justify-center z-50';
  modal.innerHTML = `
    <div class="bg-white dark:bg-gray-800 p-6 rounded-lg w-full max-w-md shadow-xl">
      <div class="flex justify-between mb-4">
        <h2 class="text-lg font-bold">Edit Group: ${group.name}</h2>
        <button onclick="this.closest('.fixed').remove()">✕</button>
      </div>
      <div class="space-y-3">
        <label class="block text-sm">Default Credits</label>
        <input type="number" id="groupCreditInput" value="${group.default_credits}" class="w-full px-2 py-1 border rounded-md bg-transparent dark:border-gray-700">
      </div>
      <div class="flex justify-end gap-2 pt-4">
        <button onclick="this.closest('.fixed').remove()" class="px-3 py-1 bg-gray-200 dark:bg-gray-700 rounded-md">Cancel</button>
        <button onclick="saveGroupCredits('${group.id}')" class="px-3 py-1 bg-blue-600 text-white rounded-md">Save</button>
      </div>
    </div>`;

  document.getElementById('modalRoot').appendChild(modal);
}

async function saveGroupCredits(groupId) {
  const input = document.getElementById('groupCreditInput');
  const newCredits = parseFloat(input.value);
  
  // Get the group name from current groups
  const group = currentGroups.find(g => g.id === groupId);
  const groupName = group ? group.name : 'Unknown';

  const res = await authenticatedFetch('/api/credits/groups/update', {
    method: 'POST',
    body: JSON.stringify({ group_id: groupId, name: groupName, default_credits: newCredits, actor: 'admin' })
  });

  const result = await res.json();
  if (result.status === 'success') {
    notifications.success(`Group credits successfully set to ${newCredits}`);
    document.querySelector('.fixed').remove();
    renderGroupsView();
  } else {
    notifications.error('Error saving group credits');
  }
}

async function renderModelsView() {
  const container = document.getElementById('mainContent');
  container.innerHTML = `
  <div class="flex items-center justify-between mb-4">
    <h2 class="text-2xl font-bold">Model Pricing Management</h2>
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-2">
        <label class="text-sm font-medium">Filter:</label>
        <select id="statusFilter" onchange="filterModelsByStatus(this.value)" class="px-2 py-1 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-900 text-sm">
          <option value="all">All Models</option>
          <option value="available">Available Only</option>
          <option value="unavailable">Unavailable Only</option>
          <option value="free">Free Models Only</option>
        </select>
      </div>
      <div class="flex items-center border border-gray-300 dark:border-gray-700 rounded-xl px-2 py-1 w-64 bg-white dark:bg-gray-900">
        <div class="self-center mr-2 text-gray-500 dark:text-gray-400">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
            <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clip-rule="evenodd"/>
          </svg>
        </div>
        <input id="modelSearchInput" class="w-full text-sm bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 outline-none"
               placeholder="Search models..." oninput="filterModels(this.value)">
        <button id="clearModelSearch" onclick="clearModelSearch()" class="ml-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors" style="display: none;" title="Clear search">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"/>
          </svg>
        </button>
      </div>
    </div>
  </div>`;


  try {
    // Fetch both models and settings to get the token multiplier
    const [modelsRes, settingsRes] = await Promise.all([
      authenticatedFetch('/api/credits/models'),
      authenticatedFetch('/api/credits/settings')
    ]);
    
    currentModels = await modelsRes.json();
    const settings = await settingsRes.json();
    const tokenMultiplier = settings.token_multiplier || 1000; // Default to 1K tokens
    
    // Helper function to get display unit text
    const getDisplayUnit = (multiplier) => {
      if (multiplier === 1) return '1 token';
      if (multiplier === 1000) return '1K tokens';
      if (multiplier === 1000000) return '1M tokens';
      return `${multiplier} tokens`;
    };
    
    const displayUnit = getDisplayUnit(tokenMultiplier);

    let table = `<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
      <thead class="text-xs uppercase bg-gray-50 dark:bg-gray-850">
        <tr>
          <th class="px-3 py-1.5">Model</th>
          <th class="px-3 py-1.5">Status</th>
          <th class="px-3 py-1.5">Context Price (per ${displayUnit})</th>
          <th class="px-3 py-1.5">Generation Price (per ${displayUnit})</th>
          <th class="px-3 py-1.5 text-right">Actions</th>
        </tr>
      </thead>
      <tbody>`;

    for (const model of currentModels) {
      const isAvailable = model.is_available === true || model.is_available === 1;
      
      const rowClass = 'bg-white dark:bg-gray-900 border-t';
      
      const nameClass = '';
      const priceClass = '';
      
      // Apply token multiplier to display prices
      const displayContextPrice = (model.context_price * tokenMultiplier).toFixed(6);
      const displayGenerationPrice = (model.generation_price * tokenMultiplier).toFixed(6);
      const displayContextPriceUsd = model.context_price_usd ? (model.context_price_usd * tokenMultiplier).toFixed(6) : 'N/A';
      const displayGenerationPriceUsd = model.generation_price_usd ? (model.generation_price_usd * tokenMultiplier).toFixed(6) : 'N/A';
      
      // Check if model is free
      const isFree = model.is_free === true || model.is_free === 1;
      
      // Create status badge with free indicator for free models
      let statusBadge;
      if (isFree) {
        // For free models, show both availability and free status side by side
        statusBadge = isAvailable
          ? '<div class="flex items-center gap-1"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"><span class="w-2 h-2 bg-green-400 rounded-full mr-1.5"></span>Available</span><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">🆓 FREE</span></div>'
          : '<div class="flex items-center gap-1"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"><span class="w-2 h-2 bg-red-400 rounded-full mr-1.5"></span>Unavailable</span><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">🆓 FREE</span></div>';
      } else {
        // For paid models, show only availability
        statusBadge = isAvailable
          ? '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"><span class="w-2 h-2 bg-green-400 rounded-full mr-1.5"></span>Available</span>'
          : '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"><span class="w-2 h-2 bg-red-400 rounded-full mr-1.5"></span>Unavailable</span>';
      }
      
      // Remove the duplicate FREE badge from model name since it's now in status
      const freeBadge = '';
      
      const priceDisplay = isFree 
        ? '<div class="text-xs"><div><strong>FREE</strong></div><div class="text-gray-500">No charge</div></div>'
        : `<div class="text-xs"><div><strong>${displayContextPrice}</strong> credits</div><div class="text-gray-500">$${displayContextPriceUsd}</div></div>`;
      
      const genPriceDisplay = isFree 
        ? '<div class="text-xs"><div><strong>FREE</strong></div><div class="text-gray-500">No charge</div></div>'
        : `<div class="text-xs"><div><strong>${displayGenerationPrice}</strong> credits</div><div class="text-gray-500">$${displayGenerationPriceUsd}</div></div>`;
        
      table += `
        <tr class="${rowClass}">
          <td class="px-3 py-1 ${nameClass}">${model.name}${freeBadge}</td>
          <td class="px-3 py-1">${statusBadge}</td>
          <td class="px-3 py-1 ${priceClass}">
            ${priceDisplay}
          </td>
          <td class="px-3 py-1 ${priceClass}">
            ${genPriceDisplay}
          </td>
          <td class="px-3 py-1 text-right">
            <button class="px-2 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700" onclick="editModel('${model.id}')">Edit</button>
          </td>
        </tr>`;
    }

    table += '</tbody></table>';

    // Add model summary
    const availableCount = currentModels.filter(m => m.is_available === true || m.is_available === 1).length;
    const unavailableCount = currentModels.length - availableCount;
    const freeCount = currentModels.filter(m => m.is_free === true || m.is_free === 1).length;

    container.innerHTML += `
      <div class="flex items-center gap-4 mb-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <div class="legend-item flex items-center gap-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 px-2 py-1 rounded transition-colors" onclick="filterModelsByStatus('available')" title="Click to show only available models">
          <span class="w-3 h-3 bg-green-400 rounded-full"></span>
          <span class="text-sm"><strong>${availableCount}</strong> Available Models</span>
        </div>
        <div class="legend-item flex items-center gap-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 px-2 py-1 rounded transition-colors" onclick="filterModelsByStatus('free')" title="Click to show only free models">
          <span class="w-3 h-3 bg-blue-400 rounded-full"></span>
          <span class="text-sm"><strong>${freeCount}</strong> Free Models</span>
        </div>
        <div class="legend-item flex items-center gap-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 px-2 py-1 rounded transition-colors" onclick="filterModelsByStatus('unavailable')" title="Click to show only unavailable models">
          <span class="w-3 h-3 bg-red-400 rounded-full"></span>
          <span class="text-sm"><strong>${unavailableCount}</strong> Unavailable Models</span>
        </div>
        <div class="legend-item text-sm text-gray-500 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 px-2 py-1 rounded transition-colors" onclick="filterModelsByStatus('all')" title="Click to show all models">
          Total: <strong>${currentModels.length}</strong> models
        </div>
      </div>
    `;

container.innerHTML += table;
container.innerHTML += `
  <div class="flex gap-2 mt-4">
    <button onclick="exportModelsToExcel()" class="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
        <path stroke-linecap="round" stroke-linejoin="round" d="m9 12.75 3 3m0 0 3-3m-3 3v-7.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
      </svg>
      Export Models to Excel
    </button>
    <button onclick="syncModelsFromOpenWebUI()" class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
        <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
      </svg>
      Sync Models from OpenWebUI
    </button>
  </div>
  <div id="modalRoot"></div>`;


  } catch (err) {
    if (err instanceof AuthenticationError) {
      // Authentication error - user will already be redirected to login
      return;
    }
    container.innerHTML += `<p class="text-red-500">Error loading models: ${err.message}</p>`;
  }
}

async function editModel(modelId) {
  const model = currentModels.find(m => m.id === modelId);
  if (!model) return;

  // Fetch current settings for conversion ratio and token multiplier
  let usdToCreditRatio = 1000.0; // Default fallback
  let tokenMultiplier = 1000; // Default fallback
  try {
    const settingsRes = await authenticatedFetch('/api/credits/settings');
    const settings = await settingsRes.json();
    usdToCreditRatio = settings.usd_to_credit_ratio || 1000.0;
    tokenMultiplier = settings.token_multiplier || 1000;
  } catch (err) {
    console.warn('Could not fetch settings, using default values:', err);
  }
  
  // Helper function to get display unit text
  const getDisplayUnit = (multiplier) => {
    if (multiplier === 1) return '1 token';
    if (multiplier === 1000) return '1K tokens';
    if (multiplier === 1000000) return '1M tokens';
    return `${multiplier} tokens`;
  };
  
  const displayUnit = getDisplayUnit(tokenMultiplier);
  
  // Apply token multiplier to display values (prices are stored per 1 token in DB)
  const displayContextPrice = (model.context_price * tokenMultiplier).toFixed(6);
  const displayGenerationPrice = (model.generation_price * tokenMultiplier).toFixed(6);
  
  const modal = document.createElement('div');
  modal.className = 'fixed inset-0 bg-black/30 flex items-center justify-center z-50';
  modal.innerHTML = `
    <div class="bg-white dark:bg-gray-800 p-6 rounded-lg w-full max-w-md shadow-xl">
      <div class="flex justify-between mb-4">
        <h2 class="text-lg font-bold">Edit Model: ${model.name}</h2>
        <button onclick="this.closest('.fixed').remove()">✕</button>
      </div>
      
      <div class="mb-4" id="pricingModeSection">
        <label class="block text-sm font-medium mb-2">Pricing Mode</label>
        <div class="flex border border-gray-300 dark:border-gray-700 rounded-md overflow-hidden">
          <button id="creditModeBtn" onclick="switchPricingMode('credits')" 
                  class="flex-1 px-3 py-2 text-sm bg-blue-600 text-white">Credits</button>
          <button id="usdModeBtn" onclick="switchPricingMode('usd')" 
                  class="flex-1 px-3 py-2 text-sm bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200">USD</button>
        </div>
      </div>
      
      <div class="mb-4">
        <label class="flex items-center gap-2">
          <input type="checkbox" id="freeModelCheckbox" ${(model.is_free === true || model.is_free === 1) ? 'checked' : ''} 
                 onchange="toggleFreeModel()" 
                 class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600">
          <span class="text-sm font-medium">🆓 Free Model (no credits charged)</span>
        </label>
      </div>
      
      <div class="space-y-3" id="pricingFields">
        <div>
          <label class="block text-sm">Context Token Price <span id="contextUnit">(credits per ${displayUnit})</span></label>
          <input type="number" id="contextPriceInput" value="${displayContextPrice}" step="any" 
                 oninput="updateConversion()" 
                 class="w-full px-2 py-1 border rounded-md bg-transparent dark:border-gray-700">
          <div id="contextConversion" class="text-xs text-gray-500 mt-1">
            ≈ $${model.context_price_usd ? (model.context_price_usd * tokenMultiplier).toFixed(6) : 'N/A'} USD per ${displayUnit}
          </div>
        </div>
        
        <div>
          <label class="block text-sm">Generation Token Price <span id="generationUnit">(credits per ${displayUnit})</span></label>
          <input type="number" id="generationPriceInput" value="${displayGenerationPrice}" step="any" 
                 oninput="updateConversion()" 
                 class="w-full px-2 py-1 border rounded-md bg-transparent dark:border-gray-700">
          <div id="generationConversion" class="text-xs text-gray-500 mt-1">
            ≈ $${model.generation_price_usd ? (model.generation_price_usd * tokenMultiplier).toFixed(6) : 'N/A'} USD per ${displayUnit}
          </div>
        </div>
      </div>
      
      <div class="flex justify-end gap-2 pt-4">
        <button onclick="this.closest('.fixed').remove()" class="px-3 py-1 bg-gray-200 dark:bg-gray-700 rounded-md">Cancel</button>
        <button onclick="saveModelPricing('${model.id}')" class="px-3 py-1 bg-blue-600 text-white rounded-md">Save</button>
      </div>
    </div>`;

  document.getElementById('modalRoot').appendChild(modal);
  
  // Store the current pricing mode, model data, conversion ratio, token multiplier, and original credit values
  window.currentPricingMode = 'credits';
  window.currentModelData = model;
  window.usdToCreditRatio = usdToCreditRatio;
  window.tokenMultiplier = tokenMultiplier;
  // Always store the original credit values (per 1 token from DB) for accurate conversion
  window.originalContextCredits = model.context_price;
  window.originalGenerationCredits = model.generation_price;
  
  // Initialize the free model state after the modal is in the DOM
  setTimeout(() => {
    toggleFreeModel();
  }, 10);
}

function toggleFreeModel() {
  const freeCheckbox = document.getElementById('freeModelCheckbox');
  const pricingFields = document.getElementById('pricingFields');
  const pricingModeSection = document.getElementById('pricingModeSection');
  
  if (freeCheckbox && pricingFields && pricingModeSection) {
    const isFree = freeCheckbox.checked;
    
    if (isFree) {
      // Hide pricing fields and mode buttons when free is checked
      pricingFields.style.display = 'none';
      pricingModeSection.style.display = 'none';
    } else {
      // Show pricing fields and mode buttons when free is unchecked
      pricingFields.style.display = 'block';
      pricingModeSection.style.display = 'block';
    }
  }
}

function updateConversion() {
  const contextInput = document.getElementById('contextPriceInput');
  const generationInput = document.getElementById('generationPriceInput');
  const contextConversion = document.getElementById('contextConversion');
  const generationConversion = document.getElementById('generationConversion');
  
  if (!contextInput || !generationInput || !window.usdToCreditRatio || !window.tokenMultiplier) return;
  
  const contextValue = parseFloat(contextInput.value) || 0;
  const generationValue = parseFloat(generationInput.value) || 0;
  const ratio = window.usdToCreditRatio;
  const tokenMultiplier = window.tokenMultiplier;
  
  // Helper function to get display unit text
  const getDisplayUnit = (multiplier) => {
    if (multiplier === 1) return '1 token';
    if (multiplier === 1000) return '1K tokens';
    if (multiplier === 1000000) return '1M tokens';
    return `${multiplier} tokens`;
  };
  
  const displayUnit = getDisplayUnit(tokenMultiplier);
  
  if (window.currentPricingMode === 'usd') {
    // Converting USD (per displayUnit) to credits (per displayUnit) for display
    contextConversion.textContent = `≈ ${(contextValue * ratio).toFixed(6)} credits per ${displayUnit}`;
    generationConversion.textContent = `≈ ${(generationValue * ratio).toFixed(6)} credits per ${displayUnit}`;
  } else {
    // Converting credits (per displayUnit) to USD (per displayUnit) for display
    contextConversion.textContent = `≈ $${(contextValue / ratio).toFixed(6)} USD per ${displayUnit}`;
    generationConversion.textContent = `≈ $${(generationValue / ratio).toFixed(6)} USD per ${displayUnit}`;
  }
}

function switchPricingMode(mode) {
  const ratio = window.usdToCreditRatio;
  const tokenMultiplier = window.tokenMultiplier;
  const originalContextCredits = window.originalContextCredits;
  const originalGenerationCredits = window.originalGenerationCredits;
  
  if (!ratio || !tokenMultiplier || originalContextCredits === undefined || originalGenerationCredits === undefined) return;
  
  const contextInput = document.getElementById('contextPriceInput');
  const generationInput = document.getElementById('generationPriceInput');
  const contextUnit = document.getElementById('contextUnit');
  const generationUnit = document.getElementById('generationUnit');
  const creditBtn = document.getElementById('creditModeBtn');
  const usdBtn = document.getElementById('usdModeBtn');
  
  // Helper function to get display unit text
  const getDisplayUnit = (multiplier) => {
    if (multiplier === 1) return '1 token';
    if (multiplier === 1000) return '1K tokens';
    if (multiplier === 1000000) return '1M tokens';
    return `${multiplier} tokens`;
  };
  
  const displayUnit = getDisplayUnit(tokenMultiplier);
  
  if (mode === 'usd') {
    // Switch to USD mode - convert original credit values to USD and apply token multiplier for display
    contextInput.value = ((originalContextCredits / ratio) * tokenMultiplier).toFixed(7);
    generationInput.value = ((originalGenerationCredits / ratio) * tokenMultiplier).toFixed(7);
    contextUnit.textContent = `(USD per ${displayUnit})`;
    generationUnit.textContent = `(USD per ${displayUnit})`;
    
    creditBtn.className = 'flex-1 px-3 py-2 text-sm bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200';
    usdBtn.className = 'flex-1 px-3 py-2 text-sm bg-blue-600 text-white';
    
    window.currentPricingMode = 'usd';
  } else {
    // Switch to credits mode - show original credit values multiplied by token multiplier for display
    contextInput.value = (originalContextCredits * tokenMultiplier).toFixed(6);
    generationInput.value = (originalGenerationCredits * tokenMultiplier).toFixed(6);
    contextUnit.textContent = `(credits per ${displayUnit})`;
    generationUnit.textContent = `(credits per ${displayUnit})`;
    
    creditBtn.className = 'flex-1 px-3 py-2 text-sm bg-blue-600 text-white';
    usdBtn.className = 'flex-1 px-3 py-2 text-sm bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200';
    
    window.currentPricingMode = 'credits';
  }
  
  // Update conversion display
  updateConversion();
}

async function saveModelPricing(modelId) {
  const contextInput = document.getElementById('contextPriceInput');
  const generationInput = document.getElementById('generationPriceInput');
  const freeCheckbox = document.getElementById('freeModelCheckbox');
  const displayContextPrice = parseFloat(contextInput.value) || 0;
  const displayGenerationPrice = parseFloat(generationInput.value) || 0;
  const priceMode = window.currentPricingMode || 'credits';
  const tokenMultiplier = window.tokenMultiplier || 1000;
  const isFree = freeCheckbox.checked;

  // Convert displayed prices back to per-token prices for storage in database
  let contextPrice, generationPrice;
  
  if (isFree) {
    // For free models, set prices to 0
    contextPrice = 0;
    generationPrice = 0;
  } else if (priceMode === 'usd') {
    // Input is in USD per displayUnit, convert to USD per token
    contextPrice = displayContextPrice / tokenMultiplier;
    generationPrice = displayGenerationPrice / tokenMultiplier;
  } else {
    // Input is in credits per displayUnit, convert to credits per token
    contextPrice = displayContextPrice / tokenMultiplier;
    generationPrice = displayGenerationPrice / tokenMultiplier;
  }

  const res = await authenticatedFetch('/api/credits/models/update', {
    method: 'POST',
    body: JSON.stringify({ 
      model_id: modelId, 
      context_price: contextPrice, 
      generation_price: generationPrice, 
      price_mode: priceMode,
      is_free: isFree,
      actor: 'admin' 
    })
  });

  const result = await res.json();
  if (result.status === 'success') {
    notifications.success(`Model pricing successfully updated.`);
    document.querySelector('.fixed').remove();
    renderModelsView();
  } else {
    notifications.error('Error saving model pricing');
  }
}

// Reusable SVG for refresh icon
function getRefreshIconSVG() {
  return `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
      <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
    </svg>
  `;
}

async function renderSystemLogsView() {
  const container = document.getElementById('mainContent');
  container.innerHTML = `
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-2xl font-bold">System Logs</h2>
      <button onclick="renderSystemLogsView()" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors flex items-center gap-2" title="Refresh logs">
        ${getRefreshIconSVG()}
        Refresh
      </button>
    </div>
  `;

  try {
    const res = await authenticatedFetch('/api/credits/system-logs');
    const data = await res.json();
    const logs = data.logs || [];

    let table = `<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
      <thead class="text-xs uppercase bg-gray-50 dark:bg-gray-850">
        <tr>
          <th class="px-3 py-1.5">Timestamp</th>
          <th class="px-3 py-1.5">Type</th>
          <th class="px-3 py-1.5">Actor</th>
          <th class="px-3 py-1.5">Message</th>
        </tr>
      </thead>
      <tbody>`;

    for (const log of logs) {
      const timestamp = new Date(log.created_at).toLocaleString();
      table += `
        <tr class="bg-white dark:bg-gray-900 border-t">
          <td class="px-3 py-1 text-xs">${timestamp}</td>
          <td class="px-3 py-1 text-xs font-mono">${log.log_type}</td>
          <td class="px-3 py-1 text-xs">${log.actor}</td>
          <td class="px-3 py-1 text-xs">${log.message || ''}</td>
        </tr>`;
    }

    table += '</tbody></table>';
    container.innerHTML += table;
  } catch (err) {
    if (err instanceof AuthenticationError) {
      // Authentication error - user will already be redirected to login
      return;
    }
    container.innerHTML += `<p class="text-red-500">Error loading system logs: ${err.message}</p>`;
  }
}

async function renderTransactionLogsView() {
  const container = document.getElementById('mainContent');
  container.innerHTML = `
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-2xl font-bold">Transaction Logs</h2>
      <button onclick="renderTransactionLogsView()" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors flex items-center gap-2" title="Refresh logs">
        ${getRefreshIconSVG()}
        Refresh
      </button>
    </div>
  `;

  try {
    const res = await authenticatedFetch('/api/credits/transactions');
    const data = await res.json();
    const transactions = data.transactions || [];

    // Add CSS for transaction type colors if not already added
    if (!document.getElementById('transactionTypeStyles')) {
      const style = document.createElement('style');
      style.id = 'transactionTypeStyles';
      style.textContent = `
        .transaction-type-deduct { color: #dc3545; background-color: #f8d7da; }
        .transaction-type-sync { color: #007bff; background-color: #d1ecf1; }
        .transaction-type-manual_update { color: #28a745; background-color: #d4edda; }
        .transaction-type-update { color: #28a745; background-color: #d4edda; }
        .transaction-type-credit { color: #28a745; background-color: #d4edda; }
        .transaction-type-auto { color: #6c757d; background-color: #e2e3e5; }
        .transaction-type { 
          padding: 2px 6px; 
          border-radius: 4px; 
          font-size: 11px; 
          font-weight: 500; 
          text-transform: uppercase;
        }
        .user-display {
          cursor: help;
          border-bottom: 1px dotted #6c757d;
        }
      `;
      document.head.appendChild(style);
    }

    let table = `<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
      <thead class="text-xs uppercase bg-gray-50 dark:bg-gray-850">
        <tr>
          <th class="px-3 py-1.5">Timestamp</th>
          <th class="px-3 py-1.5">User</th>
          <th class="px-3 py-1.5">Amount</th>
          <th class="px-3 py-1.5">Type</th>
          <th class="px-3 py-1.5">Model</th>
          <th class="px-3 py-1.5">Actor</th>
          <th class="px-3 py-1.5">Balance After</th>
          <th class="px-3 py-1.5">Reason</th>
        </tr>
      </thead>
      <tbody>`;

    for (const transaction of transactions) {
      const timestamp = new Date(transaction.created_at).toLocaleString();
      const amountClass = transaction.amount >= 0 ? 'text-green-600' : 'text-red-600';
      
      // Get transaction type color class
      const typeClass = `transaction-type transaction-type-${transaction.transaction_type.toLowerCase().replace(/[^a-z0-9]/g, '_')}`;
      
      // Display user name with user_id tooltip
      const userName = transaction.user_name || transaction.user_id;
      const userDisplay = transaction.user_name 
        ? `<span class="user-display" title="User ID: ${transaction.user_id}">${transaction.user_name}</span>`
        : `<span class="font-mono">${transaction.user_id}</span>`;
      
      // Display model information with token details if available
      let modelInfo = transaction.model_id || '';
      if (transaction.model_id && (transaction.prompt_tokens || transaction.completion_tokens)) {
        const promptTokens = transaction.prompt_tokens || 0;
        const completionTokens = transaction.completion_tokens || 0;
        modelInfo = `<span title="Prompt: ${promptTokens} tokens, Completion: ${completionTokens} tokens">${transaction.model_id}</span>`;
      }
      
      table += `
        <tr class="bg-white dark:bg-gray-900 border-t">
          <td class="px-3 py-1 text-xs">${timestamp}</td>
          <td class="px-3 py-1 text-xs">${userDisplay}</td>
          <td class="px-3 py-1 text-xs ${amountClass}">${transaction.amount > 0 ? '+' : ''}${transaction.amount}</td>
          <td class="px-3 py-1 text-xs"><span class="${typeClass}">${transaction.transaction_type}</span></td>
          <td class="px-3 py-1 text-xs">${modelInfo}</td>
          <td class="px-3 py-1 text-xs">${transaction.actor}</td>
          <td class="px-3 py-1 text-xs">${transaction.balance_after}</td>
          <td class="px-3 py-1 text-xs">${transaction.reason || ''}</td>
        </tr>`;
    }

    table += '</tbody></table>';
    container.innerHTML += table;
  } catch (err) {
    if (err instanceof AuthenticationError) {
      // Authentication error - user will already be redirected to login
      return;
    }
    container.innerHTML += `<p class="text-red-500">Error loading transaction logs: ${err.message}</p>`;
  }
}

// Global variables for settings
let currentSettings = {};

async function renderSettingsView() {
  const container = document.getElementById('mainContent');
  container.innerHTML = `
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-2xl font-bold">System Settings</h2>
    </div>
  `;

  try {
    const res = await authenticatedFetch('/api/credits/settings');
    currentSettings = await res.json();

    container.innerHTML += `
      <div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg max-w-2xl">
        <h3 class="text-lg font-semibold mb-4">Currency Conversion</h3>
        <div class="space-y-4">
          <div>
            <label for="usdToCreditRatio" class="block text-sm font-medium mb-2">
              USD to Credit Conversion Ratio
            </label>
            <p class="text-sm text-gray-600 dark:text-gray-400 mb-2">
              How many credits equal $1 USD? (e.g., 1000 means $1 = 1000 credits)
            </p>
            <input type="number" id="usdToCreditRatio" value="${currentSettings.usd_to_credit_ratio}" 
                   step="0.01" min="0.01" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-transparent">
          </div>
          
          <div>
            <label for="tokenMultiplier" class="block text-sm font-medium mb-2">
              Token Display Multiplier
            </label>
            <p class="text-sm text-gray-600 dark:text-gray-400 mb-2">
              How should token prices be displayed? (1 = per token, 1000 = per 1K tokens, 1000000 = per 1M tokens)
            </p>
            <select id="tokenMultiplier" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800">
              <option value="1" ${currentSettings.token_multiplier == 1 ? 'selected' : ''}>1 token</option>
              <option value="1000" ${currentSettings.token_multiplier == 1000 ? 'selected' : ''}>1K tokens (1,000)</option>
              <option value="1000000" ${currentSettings.token_multiplier == 1000000 ? 'selected' : ''}>1M tokens (1,000,000)</option>
            </select>
          </div>
          
          <div class="flex items-center justify-between bg-gray-50 dark:bg-gray-700 p-3 rounded">
            <div>
              <p class="text-sm font-medium">Current Rates:</p>
              <p class="text-xs text-gray-600 dark:text-gray-400">$1 USD = ${currentSettings.usd_to_credit_ratio} credits</p>
              <p class="text-xs text-gray-600 dark:text-gray-400">1 credit = $${(1/currentSettings.usd_to_credit_ratio).toFixed(6)} USD</p>
              <p class="text-xs text-gray-600 dark:text-gray-400">Display unit: ${currentSettings.token_multiplier == 1 ? '1 token' : currentSettings.token_multiplier == 1000 ? '1K tokens' : '1M tokens'}</p>
            </div>
          </div>
          <button onclick="saveSettings()" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
            Save Settings
          </button>
        </div>
      </div>
    `;

  } catch (err) {
    if (err instanceof AuthenticationError) {
      return;
    }
    container.innerHTML += `<p class="text-red-500">Error loading settings: ${err.message}</p>`;
  }
}

async function saveSettings() {
  const ratio = parseFloat(document.getElementById('usdToCreditRatio').value);
  const multiplier = parseInt(document.getElementById('tokenMultiplier').value);
  
  if (isNaN(ratio) || ratio <= 0) {
    notifications.warning('Please enter a valid conversion ratio greater than 0');
    return;
  }
  
  if (isNaN(multiplier) || ![1, 1000, 1000000].includes(multiplier)) {
    notifications.warning('Please select a valid token multiplier');
    return;
  }

  try {
    const res = await authenticatedFetch('/api/credits/settings', {
      method: 'POST',
      body: JSON.stringify({ 
        usd_to_credit_ratio: ratio,
        token_multiplier: multiplier,
        actor: 'admin' 
      })
    });

    const result = await res.json();
    if (result.status === 'success') {
      notifications.success('Settings saved successfully!');
      renderSettingsView(); // Refresh the view
    } else {
      notifications.error('Error saving settings');
    }
  } catch (err) {
    notifications.error(`Error saving settings: ${err.message}`);
  }
}

// Utility function to escape HTML
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Statistics Views
async function renderCurrentUsageView() {
  try {
    // Fetch both current usage and prepare for monthly data
    const currentRes = await authenticatedFetch('/api/credits/statistics/current-usage');
    if (!currentRes.ok) throw new Error(`HTTP ${currentRes.status}`);
    
    const currentData = await currentRes.json();
    
    // Calculate summary statistics for current month
    const totalCreditsUsed = currentData.current_usage.reduce((sum, user) => sum + user.usage.credits_used, 0);
    const totalTransactions = currentData.current_usage.reduce((sum, user) => sum + user.usage.transactions_count, 0);
    const activeUsers = currentData.current_usage.length;
    
    // Get unique models used
    const allModels = new Set();
    currentData.current_usage.forEach(user => {
      user.usage.models_used.forEach(model => allModels.add(model));
    });
    const modelsUsed = allModels.size;
    
    // Try to get last month's data for the historical section
    const lastMonth = new Date();
    lastMonth.setMonth(lastMonth.getMonth() - 1);
    const lastYear = lastMonth.getFullYear();
    const lastMonthNum = lastMonth.getMonth() + 1;
    
    let monthlyData = { summary: null };
    try {
      const monthlyRes = await authenticatedFetch(`/api/credits/statistics/monthly?year=${lastYear}&month=${lastMonthNum}`);
      if (monthlyRes.ok) {
        monthlyData = await monthlyRes.json();
      }
    } catch (err) {
      console.log('Could not load monthly data:', err);
    }
    
    document.getElementById('mainContent').innerHTML = `
      <div class="space-y-6">
        <div class="flex justify-between items-center">
          <h1 class="text-2xl font-bold">📊 Usage Statistics</h1>
          <div class="flex space-x-2">
            <select id="monthSelect" onchange="loadMonthlyData()" class="px-3 py-2 border rounded-md bg-white dark:bg-gray-800">
              <option value="">Select Month</option>
            </select>
            <button onclick="loadMonthlyData()" class="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600">
              🔄 Refresh
            </button>
          </div>
        </div>

        <!-- Statistics Container -->
        <div id="statisticsContainer" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
          <div id="statisticsHeader">
            <h2 class="text-xl font-semibold mb-4">� Current Month Usage (${currentData.year}-${String(currentData.month).padStart(2, '0')}) - Pending</h2>
          </div>
          
          <!-- Warning for current month (incomplete data) -->
          <div id="incompleteWarning" class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-4">
            <div class="flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-yellow-600 dark:text-yellow-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <span class="text-sm text-yellow-800 dark:text-yellow-200">
                <strong>Pending Usage:</strong> This shows current month usage that hasn't been finalized in monthly statistics yet.
              </span>
            </div>
          </div>

          <!-- Summary Cards -->
          <div id="summaryCards" class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
              <div class="text-sm font-medium text-green-800 dark:text-green-200">Total Credits Used</div>
              <div id="totalCredits" class="text-2xl font-bold text-green-600 dark:text-green-400">${totalCreditsUsed.toFixed(2)}</div>
            </div>
            <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <div class="text-sm font-medium text-blue-800 dark:text-blue-200">Total Transactions</div>
              <div id="totalTransactions" class="text-2xl font-bold text-blue-600 dark:text-blue-400">${totalTransactions}</div>
            </div>
            <div class="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
              <div class="text-sm font-medium text-purple-800 dark:text-purple-200">Active Users</div>
              <div id="totalUsers" class="text-2xl font-bold text-purple-600 dark:text-purple-400">${activeUsers}</div>
            </div>
            <div class="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4">
              <div class="text-sm font-medium text-orange-800 dark:text-orange-200">Models Used</div>
              <div id="totalModels" class="text-2xl font-bold text-orange-600 dark:text-orange-400">${modelsUsed}</div>
            </div>
          </div>

          <!-- Unified Data Table -->
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead class="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">User</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Credits Used</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Transactions</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Models Used</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Current Balance</th>
                </tr>
              </thead>
              <tbody id="statisticsTableBody" class="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                ${currentData.current_usage.map(user => `
                  <tr class="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">${escapeHtml(user.user_name)}</div>
                        <div class="text-sm text-gray-500 dark:text-gray-400">${escapeHtml(user.user_email)}</div>
                      </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                      <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                        ${user.usage.credits_used.toFixed(2)}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">${user.usage.transactions_count}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">${user.usage.models_used.length}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">${user.current_balance.toFixed(2)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    // Populate month selector after the HTML is rendered
    populateMonthSelector();
    
  } catch (err) {
    document.getElementById('mainContent').innerHTML = `
      <div class="text-center py-8">
        <p class="text-red-600 dark:text-red-400">Error loading statistics: ${err.message}</p>
      </div>
    `;
  }
}

// Function to populate the month selector dropdown
function populateMonthSelector() {
  const select = document.getElementById('monthSelect');
  
  if (!select) {
    console.log('❌ monthSelect element not found!');
    return;
  }
  
  // Clear existing options except the first one
  select.innerHTML = '<option value="">Current Month</option>';
  
  const currentDate = new Date();
  const currentYear = currentDate.getFullYear();
  const currentMonth = currentDate.getMonth() + 1;
  
  // Generate last 12 months excluding the current month
  for (let i = 1; i <= 12; i++) {
    const date = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1);
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const monthName = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    
    const option = document.createElement('option');
    option.value = `${year}-${month}`;
    option.textContent = monthName;
    select.appendChild(option);
  }
}

// Function to load monthly data when a month is selected
async function loadMonthlyData() {
  const select = document.getElementById('monthSelect');
  const selectedValue = select.value;
  
  // If no month selected, show current month data
  if (!selectedValue) {
    try {
      const res = await authenticatedFetch('/api/credits/statistics/current-usage');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      const currentData = await res.json();
      
      // Update header and show incomplete warning
      document.getElementById('statisticsHeader').innerHTML = 
        `<h2 class="text-xl font-semibold mb-4">📅 Current Month Usage (${currentData.year}-${String(currentData.month).padStart(2, '0')}) - Pending</h2>`;
      
      // Show incomplete warning
      document.getElementById('incompleteWarning').style.display = 'block';
      
      // Calculate summary statistics for current month
      const totalCreditsUsed = currentData.current_usage.reduce((sum, user) => sum + user.usage.credits_used, 0);
      const totalTransactions = currentData.current_usage.reduce((sum, user) => sum + user.usage.transactions_count, 0);
      const activeUsers = currentData.current_usage.length;
      
      // Get unique models used
      const allModels = new Set();
      currentData.current_usage.forEach(user => {
        user.usage.models_used.forEach(model => allModels.add(model));
      });
      const modelsUsed = allModels.size;
      
      // Show and update summary cards for current month
      const summaryCards = document.getElementById('summaryCards');
      summaryCards.style.display = 'grid';
      document.getElementById('totalCredits').textContent = totalCreditsUsed.toFixed(2);
      document.getElementById('totalTransactions').textContent = totalTransactions;
      document.getElementById('totalUsers').textContent = activeUsers;
      document.getElementById('totalModels').textContent = modelsUsed;
      
      // Update table with current usage data
      const tbody = document.getElementById('statisticsTableBody');
      
      // Update table header for current month (show Current Balance, not Balance Before Reset)
      const tableHeader = document.querySelector('#statisticsTableBody').closest('table').querySelector('thead tr');
      tableHeader.innerHTML = `
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">User</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Credits Used</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Transactions</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Models Used</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Current Balance</th>
      `;
      
      tbody.innerHTML = currentData.current_usage.map(user => `
        <tr class="hover:bg-gray-50 dark:hover:bg-gray-800">
          <td class="px-6 py-4 whitespace-nowrap">
            <div>
              <div class="text-sm font-medium text-gray-900 dark:text-gray-100">${escapeHtml(user.user_name)}</div>
              <div class="text-sm text-gray-500 dark:text-gray-400">${escapeHtml(user.user_email)}</div>
            </div>
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
            <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
              ${user.usage.credits_used.toFixed(2)}
            </span>
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">${user.usage.transactions_count}</td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">${user.usage.models_used.length}</td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">${user.current_balance.toFixed(2)}</td>
        </tr>
      `).join('');
      
      if (currentData.current_usage.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="5" class="text-center py-8 text-gray-500 dark:text-gray-400">
              No usage data for current month
            </td>
          </tr>
        `;
        
        // Also reset summary cards for empty data
        document.getElementById('totalCredits').textContent = '0.00';
        document.getElementById('totalTransactions').textContent = '0';
        document.getElementById('totalUsers').textContent = '0';
        document.getElementById('totalModels').textContent = '0';
      }
      
    } catch (err) {
      notifications.error(`Error loading current usage: ${err.message}`);
    }
    return;
  }

  // Load historical month data
  const [year, month] = selectedValue.split('-').map(Number);
  
  if (!year || !month) {
    notifications.warning('Invalid month selection');
    return;
  }

  try {
    const res = await authenticatedFetch(`/api/credits/statistics/monthly?year=${year}&month=${month}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    
    const data = await res.json();
    
    // Check if this is the current month
    const currentDate = new Date();
    const isCurrentMonth = (year === currentDate.getFullYear() && month === (currentDate.getMonth() + 1));
    
    // Update header
    const monthName = getMonthName(month);
    document.getElementById('statisticsHeader').innerHTML = 
      `<h2 class="text-xl font-semibold mb-4">📅 ${monthName} ${year} Statistics${isCurrentMonth ? ' - Pending' : ''}</h2>`;
    
    // Show/hide incomplete warning based on whether it's current month
    document.getElementById('incompleteWarning').style.display = isCurrentMonth ? 'block' : 'none';
    
    // Show/hide summary cards based on data availability
    const hasSummary = data.summary && data.summary.total_transactions > 0;
    const summaryCards = document.getElementById('summaryCards');
    if (hasSummary) {
      summaryCards.style.display = 'grid';
      document.getElementById('totalCredits').textContent = data.summary.total_credits_used.toFixed(2);
      document.getElementById('totalTransactions').textContent = data.summary.total_transactions;
      document.getElementById('totalUsers').textContent = data.summary.unique_users;
      document.getElementById('totalModels').textContent = data.summary.unique_models;
    } else {
      summaryCards.style.display = 'none';
    }
    
    // Update table with monthly statistics
    const tbody = document.getElementById('statisticsTableBody');
    
    // Update table header for historical month (show Balance Before Reset, not Current Balance)
    const tableHeader = document.querySelector('#statisticsTableBody').closest('table').querySelector('thead tr');
    tableHeader.innerHTML = `
      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">User</th>
      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Credits Used</th>
      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Transactions</th>
      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Models Used</th>
      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Balance Before Reset</th>
    `;
    
    if (data.user_statistics && data.user_statistics.length > 0) {
      tbody.innerHTML = data.user_statistics.map(user => `
        <tr class="hover:bg-gray-50 dark:hover:bg-gray-800">
          <td class="px-6 py-4 whitespace-nowrap">
            <div>
              <div class="text-sm font-medium text-gray-900 dark:text-gray-100">${escapeHtml(user.user_name)}</div>
              <div class="text-sm text-gray-500 dark:text-gray-400">${escapeHtml(user.user_email)}</div>
            </div>
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
            <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full ${isCurrentMonth ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'}">
              ${user.credits_used.toFixed(2)}
            </span>
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">${user.transactions_count}</td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">${user.models_used ? (typeof user.models_used === 'string' ? JSON.parse(user.models_used).length : user.models_used.length) : 0}</td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
            ${user.balance_before_reset !== null && user.balance_before_reset !== undefined ? 
              `<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                ${user.balance_before_reset.toFixed(2)}
              </span>` : 
              '<span class="text-gray-500 dark:text-gray-400 italic">N/A</span>'
            }
          </td>
        </tr>
      `).join('');
    } else {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center py-8 text-gray-500 dark:text-gray-400">
            No statistics data for ${monthName} ${year}
          </td>
        </tr>
      `;
    }
    
  } catch (err) {
    notifications.error(`Error loading monthly data: ${err.message}`);
  }
}

async function renderYearlyStatsView() {
  const mainContent = document.getElementById('mainContent');
  mainContent.innerHTML = '<p class="text-center">Loading yearly statistics...</p>';

  try {
    const currentYear = new Date().getFullYear();
    const res = await authenticatedFetch(`/api/credits/statistics/yearly?year=${currentYear}`);
    const data = await res.json();

    mainContent.innerHTML = `
      <div class="space-y-6">
        <div class="flex justify-between items-center">
          <h1 class="text-2xl font-bold">📊 Yearly Statistics</h1>
          <div class="flex space-x-2">
            <select id="yearSelect" onchange="loadYearlyData()" class="px-3 py-2 border rounded-md bg-white dark:bg-gray-800">
              ${Array.from({length: 5}, (_, i) => currentYear - i).map(year => 
                `<option value="${year}" ${year === currentYear ? 'selected' : ''}>${year}</option>`
              ).join('')}
            </select>
          </div>
        </div>

        <div id="yearlyStatsContent">
          <!-- Yearly Summary -->
          ${data.yearly_summary ? `
            <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6 mb-6">
              <h2 class="text-xl font-semibold mb-4">📅 ${data.year} Summary</h2>
              <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                  <div class="text-sm font-medium text-green-800 dark:text-green-200">Total Credits Used</div>
                  <div class="text-3xl font-bold text-green-600 dark:text-green-400">${data.yearly_summary.total_credits_used.toFixed(2)}</div>
                </div>
                <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                  <div class="text-sm font-medium text-blue-800 dark:text-blue-200">Total Transactions</div>
                  <div class="text-3xl font-bold text-blue-600 dark:text-blue-400">${data.yearly_summary.total_transactions}</div>
                </div>
                <div class="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
                  <div class="text-sm font-medium text-purple-800 dark:text-purple-200">Active Users</div>
                  <div class="text-3xl font-bold text-purple-600 dark:text-purple-400">${data.yearly_summary.unique_users}</div>
                </div>
                <div class="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4">
                  <div class="text-sm font-medium text-orange-800 dark:text-orange-200">Models Used</div>
                  <div class="text-3xl font-bold text-orange-600 dark:text-orange-400">${data.yearly_summary.unique_models}</div>
                </div>
              </div>
            </div>
          ` : `<div class="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 mb-6">
            <p class="text-gray-500 dark:text-gray-400">No data available for ${data.year}</p>
          </div>`}

          <!-- Monthly Breakdown -->
          <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
            <h2 class="text-xl font-semibold mb-4">📊 Monthly Breakdown for ${data.year}</h2>
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead class="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Month</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Credits Used</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Transactions</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Active Users</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Models Used</th>
                  </tr>
                </thead>
                <tbody class="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                  ${data.monthly_breakdown.map(month => {
                    const hasData = month.summary && month.summary.total_transactions > 0;
                    const rowClass = hasData ? 'hover:bg-gray-50 dark:hover:bg-gray-800' : 'opacity-50';
                    return `
                      <tr class="${rowClass}">
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                          ${month.month_name}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                          ${hasData ? month.summary.total_credits_used.toFixed(2) : '0.00'}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                          ${hasData ? month.summary.total_transactions : '0'}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                          ${hasData ? month.summary.unique_users : '0'}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                          ${hasData ? month.summary.unique_models : '0'}
                        </td>
                      </tr>
                    `;
                  }).join('')}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    `;

  } catch (err) {
    mainContent.innerHTML = `<p class="text-red-500">Error loading yearly statistics: ${err.message}</p>`;
  }
}

async function loadYearlyData() {
  const select = document.getElementById('yearSelect');
  const year = parseInt(select.value);
  
  if (!year) {
    notifications.warning('Please select a year');
    return;
  }

  const contentContainer = document.getElementById('yearlyStatsContent');
  if (!contentContainer) {
    notifications.error('Content container not found');
    return;
  }

  // Show loading state
  contentContainer.innerHTML = '<p class="text-center text-gray-500">Loading data for ' + year + '...</p>';

  try {
    const res = await authenticatedFetch(`/api/credits/statistics/yearly?year=${year}`);
    const data = await res.json();

    contentContainer.innerHTML = `
      <!-- Yearly Summary -->
      ${data.yearly_summary ? `
        <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6 mb-6">
          <h2 class="text-xl font-semibold mb-4">📅 ${data.year} Summary</h2>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
              <div class="text-sm font-medium text-green-800 dark:text-green-200">Total Credits Used</div>
              <div class="text-3xl font-bold text-green-600 dark:text-green-400">${data.yearly_summary.total_credits_used.toFixed(2)}</div>
            </div>
            <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <div class="text-sm font-medium text-blue-800 dark:text-blue-200">Total Transactions</div>
              <div class="text-3xl font-bold text-blue-600 dark:text-blue-400">${data.yearly_summary.total_transactions}</div>
            </div>
            <div class="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
              <div class="text-sm font-medium text-purple-800 dark:text-purple-200">Active Users</div>
              <div class="text-3xl font-bold text-purple-600 dark:text-purple-400">${data.yearly_summary.unique_users}</div>
            </div>
            <div class="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4">
              <div class="text-sm font-medium text-orange-800 dark:text-orange-200">Models Used</div>
              <div class="text-3xl font-bold text-orange-600 dark:text-orange-400">${data.yearly_summary.unique_models}</div>
            </div>
          </div>
        </div>
      ` : `<div class="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 mb-6">
        <p class="text-gray-500 dark:text-gray-400">No data available for ${data.year}</p>
      </div>`}

      <!-- Monthly Breakdown -->
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
        <h2 class="text-xl font-semibold mb-4">📊 Monthly Breakdown for ${data.year}</h2>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Month</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Credits Used</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Transactions</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Active Users</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Models Used</th>
              </tr>
            </thead>
            <tbody class="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
              ${data.monthly_breakdown.map(month => {
                const hasData = month.summary && month.summary.total_transactions > 0;
                const rowClass = hasData ? 'hover:bg-gray-50 dark:hover:bg-gray-800' : 'opacity-50';
                return `
                  <tr class="${rowClass}">
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                      ${month.month_name}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                      ${hasData ? month.summary.total_credits_used.toFixed(2) : '0.00'}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                      ${hasData ? month.summary.total_transactions : '0'}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                      ${hasData ? month.summary.unique_users : '0'}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                      ${hasData ? month.summary.unique_models : '0'}
                    </td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
    
  } catch (err) {
    contentContainer.innerHTML = `<p class="text-red-500">Error loading yearly data for ${year}: ${err.message}</p>`;
    notifications.error(`Error loading yearly data: ${err.message}`);
  }
}

function getMonthName(month) {
  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  return months[month - 1] || 'Unknown';
}