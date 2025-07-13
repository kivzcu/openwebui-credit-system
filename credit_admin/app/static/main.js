document.addEventListener('DOMContentLoaded', () => {
  selectView('users');
});

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
    const res = await fetch('/api/credits/users');
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
  <button onclick="exportUsersToExcel()" class="mt-4 flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
      <path stroke-linecap="round" stroke-linejoin="round" d="m9 12.75 3 3m0 0 3-3m-3 3v-7.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
    Export Users to Excel
  </button>
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

  const res = await fetch('/api/credits/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
    const res = await fetch('/api/credits/groups');
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

  const res = await fetch('/api/credits/groups/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
    <div class="flex items-center border border-gray-300 dark:border-gray-700 rounded-xl px-2 py-1 w-64 bg-white dark:bg-gray-900">
      <div class="self-center mr-2 text-gray-500 dark:text-gray-400">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
          <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clip-rule="evenodd"/>
        </svg>
      </div>
      <input class="w-full text-sm bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 outline-none"
             placeholder="Search" oninput="filterModels(this.value)">
    </div>
  </div>`;


  try {
    const res = await fetch('/api/credits/models');
    currentModels = await res.json();

    let table = `<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
      <thead class="text-xs uppercase bg-gray-50 dark:bg-gray-850">
        <tr>
          <th class="px-3 py-1.5">Model</th>
          <th class="px-3 py-1.5">Context Token Price</th>
          <th class="px-3 py-1.5">Generation Token Price</th>
          <th class="px-3 py-1.5 text-right">Actions</th>
        </tr>
      </thead>
      <tbody>`;

    for (const model of currentModels) {
      table += `
        <tr class="bg-white dark:bg-gray-900 border-t">
          <td class="px-3 py-1">${model.name}</td>
          <td class="px-3 py-1">${model.context_price}</td>
          <td class="px-3 py-1">${model.generation_price}</td>
          <td class="px-3 py-1 text-right">
            <button class="px-2 py-1 text-sm bg-blue-600 text-white rounded" onclick="editModel('${model.id}')">Edit</button>
          </td>
        </tr>`;
    }

    table += '</tbody></table>';
container.innerHTML += table;
container.innerHTML += `
  <button onclick="exportModelsToExcel()" class="mt-4 flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
      <path stroke-linecap="round" stroke-linejoin="round" d="m9 12.75 3 3m0 0 3-3m-3 3v-7.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
    Export Models to Excel
  </button>
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

  const res = await fetch('/api/credits/models/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
    const res = await fetch('/api/credits/system-logs');
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
    const res = await fetch('/api/credits/transactions');
    const data = await res.json();
    const transactions = data.transactions || [];

    let table = `<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
      <thead class="text-xs uppercase bg-gray-50 dark:bg-gray-850">
        <tr>
          <th class="px-3 py-1.5">Timestamp</th>
          <th class="px-3 py-1.5">User ID</th>
          <th class="px-3 py-1.5">Amount</th>
          <th class="px-3 py-1.5">Type</th>
          <th class="px-3 py-1.5">Actor</th>
          <th class="px-3 py-1.5">Balance After</th>
          <th class="px-3 py-1.5">Reason</th>
        </tr>
      </thead>
      <tbody>`;

    for (const transaction of transactions) {
      const timestamp = new Date(transaction.created_at).toLocaleString();
      const amountClass = transaction.amount >= 0 ? 'text-green-600' : 'text-red-600';
      table += `
        <tr class="bg-white dark:bg-gray-900 border-t">
          <td class="px-3 py-1 text-xs">${timestamp}</td>
          <td class="px-3 py-1 text-xs font-mono">${transaction.user_id}</td>
          <td class="px-3 py-1 text-xs ${amountClass}">${transaction.amount > 0 ? '+' : ''}${transaction.amount}</td>
          <td class="px-3 py-1 text-xs">${transaction.transaction_type}</td>
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