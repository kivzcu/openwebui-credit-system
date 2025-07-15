// Authentication state
let authToken = localStorage.getItem('authToken');
let currentUser = null;

// Check authentication on page load
document.addEventListener('DOMContentLoaded', () => {
  if (authToken) {
    verifyToken();
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
  selectView('users');
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
      showError(error.detail || 'Login failed');
    }
  } catch (error) {
    showError('Network error. Please try again.');
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
  
  const response = await fetch(url, {
    ...options,
    headers
  });
  
  if (response.status === 401) {
    logout();
    throw new Error('Authentication expired');
  }
  
  return response;
}

function selectView(view) {
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
}

function filterModels(query) {
  const lower = query.toLowerCase();
  const rows = document.querySelectorAll("#mainContent table tbody tr");
  rows.forEach(row => {
    row.style.display = row.innerText.toLowerCase().includes(lower) ? "" : "none";
  });
}


function filterGroups(query) {
  const lower = query.toLowerCase();
  const rows = document.querySelectorAll("#mainContent table tbody tr");
  rows.forEach(row => {
    row.style.display = row.innerText.toLowerCase().includes(lower) ? "" : "none";
  });
}


function filterModelsByStatus(status) {
  const rows = document.querySelectorAll("#mainContent table tbody tr");
  rows.forEach(row => {
    const statusCell = row.querySelector('td:nth-child(2)');
    if (!statusCell) return;
    
    const isAvailable = statusCell.textContent.includes('Available') && !statusCell.textContent.includes('Unavailable');
    
    let shouldShow = true;
    if (status === 'available' && !isAvailable) {
      shouldShow = false;
    } else if (status === 'unavailable' && isAvailable) {
      shouldShow = false;
    }
    
    row.style.display = shouldShow ? "" : "none";
  });
  
  // Update the dropdown to match the filter
  const statusFilter = document.getElementById('statusFilter');
  if (statusFilter) {
    statusFilter.value = status;
  }
  
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
        class="w-full text-sm bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 outline-none"
        placeholder="Search"
        oninput="filterUsers(this.value)"
      />
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
    alert("No user data available for export.");
    return;
  }
  const worksheet = XLSX.utils.json_to_sheet(currentUsers);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Users");
  XLSX.writeFile(workbook, "users_export.xlsx");
}

function exportGroupsToExcel() {
  if (!currentGroups.length) {
    alert("No group data available for export.");
    return;
  }
  const worksheet = XLSX.utils.json_to_sheet(currentGroups);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Groups");
  XLSX.writeFile(workbook, "groups_export.xlsx");
}

function exportModelsToExcel() {
  if (!currentModels.length) {
    alert("No model data available for export.");
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
    alert(`Credits successfully updated to ${newCredits}`);
    document.querySelector('.fixed').remove();
    renderUsersView();
  } else {
    alert('Error saving credits');
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
      alert('Users synced successfully from OpenWebUI!');
      renderUsersView(); // Refresh the user list
    } else {
      alert(`Sync failed: ${result.message}`);
    }
  } catch (error) {
    alert(`Sync failed: ${error.message}`);
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
      alert('Models synced successfully from OpenWebUI!');
      renderModelsView(); // Refresh the models list
    } else {
      alert(`Model sync failed: ${result.message}`);
    }
  } catch (error) {
    alert(`Model sync failed: ${error.message}`);
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
      <input class="w-full text-sm bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 outline-none"
             placeholder="Search" oninput="filterGroups(this.value)">
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
    alert(`Group credits successfully set to ${newCredits}`);
    document.querySelector('.fixed').remove();
    renderGroupsView();
  } else {
    alert('Error saving group credits');
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
        </select>
      </div>
      <div class="flex items-center border border-gray-300 dark:border-gray-700 rounded-xl px-2 py-1 w-64 bg-white dark:bg-gray-900">
        <div class="self-center mr-2 text-gray-500 dark:text-gray-400">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
            <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clip-rule="evenodd"/>
          </svg>
        </div>
        <input class="w-full text-sm bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 outline-none"
               placeholder="Search models..." oninput="filterModels(this.value)">
      </div>
    </div>
  </div>`;


  try {
    const res = await authenticatedFetch('/api/credits/models');
    currentModels = await res.json();

    let table = `<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
      <thead class="text-xs uppercase bg-gray-50 dark:bg-gray-850">
        <tr>
          <th class="px-3 py-1.5">Model</th>
          <th class="px-3 py-1.5">Status</th>
          <th class="px-3 py-1.5">Context Token Price</th>
          <th class="px-3 py-1.5">Generation Token Price</th>
          <th class="px-3 py-1.5 text-right">Actions</th>
        </tr>
      </thead>
      <tbody>`;

    for (const model of currentModels) {
      const isAvailable = model.is_available === true || model.is_available === 1;
      const statusBadge = isAvailable
        ? '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"><span class="w-2 h-2 bg-green-400 rounded-full mr-1.5"></span>Available</span>'
        : '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"><span class="w-2 h-2 bg-red-400 rounded-full mr-1.5"></span>Unavailable</span>';
      
      const rowClass = 'bg-white dark:bg-gray-900 border-t';
      
      const nameClass = '';
      const priceClass = '';
        
      table += `
        <tr class="${rowClass}">
          <td class="px-3 py-1 ${nameClass}">${model.name}</td>
          <td class="px-3 py-1">${statusBadge}</td>
          <td class="px-3 py-1 ${priceClass}">${model.context_price}</td>
          <td class="px-3 py-1 ${priceClass}">${model.generation_price}</td>
          <td class="px-3 py-1 text-right">
            <button class="px-2 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700" onclick="editModel('${model.id}')">Edit</button>
          </td>
        </tr>`;
    }

    table += '</tbody></table>';

    // Add model summary
    const availableCount = currentModels.filter(m => m.is_available === true || m.is_available === 1).length;
    const unavailableCount = currentModels.length - availableCount;

    container.innerHTML += `
      <div class="flex items-center gap-4 mb-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <div class="legend-item flex items-center gap-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 px-2 py-1 rounded transition-colors" onclick="filterModelsByStatus('available')" title="Click to show only available models">
          <span class="w-3 h-3 bg-green-400 rounded-full"></span>
          <span class="text-sm"><strong>${availableCount}</strong> Available Models</span>
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
    container.innerHTML += `<p class="text-red-500">Error loading models: ${err.message}</p>`;
  }
}

function editModel(modelId) {
  const model = currentModels.find(m => m.id === modelId);
  if (!model) return;

  const modal = document.createElement('div');
  modal.className = 'fixed inset-0 bg-black/30 flex items-center justify-center z-50';
  modal.innerHTML = `
    <div class="bg-white dark:bg-gray-800 p-6 rounded-lg w-full max-w-md shadow-xl">
      <div class="flex justify-between mb-4">
        <h2 class="text-lg font-bold">Edit Model: ${model.name}</h2>
        <button onclick="this.closest('.fixed').remove()">✕</button>
      </div>
      <div class="space-y-3">
        <label class="block text-sm">Context Token Price</label>
        <input type="number" id="contextPriceInput" value="${model.context_price}" step="0.001" class="w-full px-2 py-1 border rounded-md bg-transparent dark:border-gray-700">
        <label class="block text-sm">Generation Token Price</label>
        <input type="number" id="generationPriceInput" value="${model.generation_price}" step="0.0001" class="w-full px-2 py-1 border rounded-md bg-transparent dark:border-gray-700">
      </div>
      <div class="flex justify-end gap-2 pt-4">
        <button onclick="this.closest('.fixed').remove()" class="px-3 py-1 bg-gray-200 dark:bg-gray-700 rounded-md">Cancel</button>
        <button onclick="saveModelPricing('${model.id}')" class="px-3 py-1 bg-blue-600 text-white rounded-md">Save</button>
      </div>
    </div>`;

  document.getElementById('modalRoot').appendChild(modal);
}

async function saveModelPricing(modelId) {
  const contextInput = document.getElementById('contextPriceInput');
  const generationInput = document.getElementById('generationPriceInput');
  const contextPrice = parseFloat(contextInput.value);
  const generationPrice = parseFloat(generationInput.value);

  const res = await authenticatedFetch('/api/credits/models/update', {
    method: 'POST',
    body: JSON.stringify({ model_id: modelId, context_price: contextPrice, generation_price: generationPrice, actor: 'admin' })
  });

  const result = await res.json();
  if (result.status === 'success') {
    alert(`Model pricing successfully updated.`);
    document.querySelector('.fixed').remove();
    renderModelsView();
  } else {
    alert('Error saving model pricing');
  }
}

async function renderSystemLogsView() {
  const container = document.getElementById('mainContent');
  container.innerHTML = '<h2 class="text-2xl font-bold mb-4">System Logs</h2>';

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
    container.innerHTML += `<p class="text-red-500">Error loading system logs: ${err.message}</p>`;
  }
}

async function renderTransactionLogsView() {
  const container = document.getElementById('mainContent');
  container.innerHTML = '<h2 class="text-2xl font-bold mb-4">Transaction Logs</h2>';

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
    container.innerHTML += `<p class="text-red-500">Error loading transaction logs: ${err.message}</p>`;
  }
}