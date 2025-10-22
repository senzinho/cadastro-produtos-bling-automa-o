// ==================== PAINEL ADMINISTRATIVO - JAVASCRIPT ====================
// Arquivo: painel.js
// Versão: 1.0.1 (com correção do bug do campo nome)

// Configuração Axios
axios.defaults.withCredentials = true;

// Estado da aplicação
const state = {
    currentUser: null,
    users: [],
    logins: [],
    isDark: false,
    apiUrl: 'http://localhost:5000/api',
    currentTab: 'dashboard',
    editingUser: null
};

// ==================== AUTENTICAÇÃO ====================

async function checkAuth() {
    try {
        console.log('🔐 Verificando autenticação...');
        const response = await axios.get(`${state.apiUrl}/me`);
        state.currentUser = response.data;
        
        if (state.currentUser.role !== 'admin') {
            alert('Acesso negado. Apenas administradores podem acessar o painel.');
            window.location.href = '/calculadora';
            return false;
        }
        
        console.log('✅ Admin autenticado:', state.currentUser.name);
        return true;
    } catch (error) {
        console.error('❌ Erro de autenticação:', error);
        alert('Você precisa estar logado como administrador.');
        window.location.href = '/login';
        return false;
    }
}

function logout() {
    if (confirm('Deseja realmente sair?')) {
        axios.post(`${state.apiUrl}/logout`)
            .then(() => {
                window.location.href = '/login';
            })
            .catch(() => {
                window.location.href = '/login';
            });
    }
}

// ==================== TEMA ====================

function loadTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        state.isDark = savedTheme === 'dark';
    } else {
        state.isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    document.body.className = state.isDark ? 'dark' : 'light';
    updateThemeIcon();
}

function toggleTheme() {
    state.isDark = !state.isDark;
    document.body.className = state.isDark ? 'dark' : 'light';
    localStorage.setItem('theme', state.isDark ? 'dark' : 'light');
    updateThemeIcon();
}

function updateThemeIcon() {
    const themeBtn = document.getElementById('theme-toggle');
    themeBtn.innerHTML = state.isDark ? `
        <svg viewBox="0 0 24 24">
            <path d="M12.01 12c0 3.31-2.69 6-6 6s-6-2.69-6-6 2.69-6 6-6 6 2.69 6 6zM21 2l-1.5 1.5-3.5-3.5L14.5.5 16 2l3.5 3.5L21 2zM3.5 21.5L2 20l1.5-1.5L7 22l1.5-1.5L7 19l-3.5 2.5zM20 12.01h2c0-5.52-4.48-10-10-10v2c4.42 0 8 3.58 8 8z"/>
        </svg>
    ` : `
        <svg viewBox="0 0 24 24">
            <path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 4.58zm12.37 12.37c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0 .39-.39.39-1.03 0-1.41l-1.06-1.06zm1.06-10.96c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06zM7.05 18.36c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06z"/>
        </svg>
    `;
}

// ==================== TABS ====================

function setupTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.getAttribute('data-tab');
            switchTab(tabId);
        });
    });
}

function switchTab(tabId) {
    state.currentTab = tabId;
    
    // Atualizar tabs ativos
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
    
    // Atualizar conteúdo ativo
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`tab-${tabId}`).classList.add('active');
}

// ==================== DADOS ====================

async function loadUsers() {
    try {
        const response = await axios.get(`${state.apiUrl}/users`);
        state.users = response.data;
        renderUsers();
        updateStats();
    } catch (error) {
        console.error('❌ Erro ao carregar usuários:', error);
    }
}

async function loadLogins() {
    try {
        const response = await axios.get(`${state.apiUrl}/login-history`);
        state.logins = response.data;
        renderLogins();
        renderRecentLogins();
        updateStats();
    } catch (error) {
        console.error('❌ Erro ao carregar logins:', error);
    }
}

// ==================== RENDERIZAÇÃO ====================

function updateStats() {
    document.getElementById('stat-users').textContent = state.users.length;
    
    const today = new Date().toISOString().split('T')[0];
    const loginsToday = state.logins.filter(l => 
        l.created_at && l.created_at.startsWith(today)
    ).length;
    document.getElementById('stat-logins').textContent = loginsToday;
    
    const activeUsers = state.users.filter(u => u.active).length;
    document.getElementById('stat-active-users').textContent = activeUsers;
}

function renderUsers() {
    const tbody = document.getElementById('users-table');
    
    if (state.users.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6">
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24">
                            <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
                        </svg>
                        <h3>Nenhum usuário encontrado</h3>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = state.users.map(user => `
        <tr>
            <td>${user.name}</td>
            <td>${user.email}</td>
            <td><span class="badge badge-${user.role === 'admin' ? 'admin' : 'user'}">${user.role === 'admin' ? 'Admin' : 'Usuário'}</span></td>
            <td><span class="badge badge-${user.active ? 'success' : 'danger'}">${user.active ? 'Ativo' : 'Inativo'}</span></td>
            <td>${formatDate(user.created_at)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn-action btn-edit" onclick="editUser(${user.id})" title="Editar">
                        <svg viewBox="0 0 24 24">
                            <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                        </svg>
                    </button>
                    <button class="btn-action btn-delete" onclick="deleteUser(${user.id})" title="Excluir">
                        <svg viewBox="0 0 24 24">
                            <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                        </svg>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function renderLogins() {
    const tbody = document.getElementById('logins-table');
    
    if (state.logins.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4">
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24">
                            <path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/>
                        </svg>
                        <h3>Nenhum login registrado</h3>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = state.logins.map(login => `
        <tr>
            <td>${login.email}</td>
            <td>${login.ip_address || 'N/A'}</td>
            <td><span class="badge badge-${login.success ? 'success' : 'danger'}">${login.success ? 'Sucesso' : 'Falhou'}</span></td>
            <td>${formatDate(login.created_at)}</td>
        </tr>
    `).join('');
}

function renderRecentLogins() {
    const tbody = document.getElementById('recent-logins');
    const recentLogins = state.logins.slice(0, 5);
    
    if (recentLogins.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4">
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24">
                            <path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/>
                        </svg>
                        <h3>Nenhum login recente</h3>
                        <p>Os logins aparecerão aqui quando disponíveis</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = recentLogins.map(login => `
        <tr>
            <td>${login.email}</td>
            <td>${login.ip_address || 'N/A'}</td>
            <td><span class="badge badge-${login.success ? 'success' : 'danger'}">${login.success ? 'Sucesso' : 'Falhou'}</span></td>
            <td>${formatDate(login.created_at)}</td>
        </tr>
    `).join('');
}

// ==================== USUÁRIOS ====================

// ✅ FUNÇÃO CORRIGIDA - Agora limpa todos os campos explicitamente
function openUserModal(user = null) {
    state.editingUser = user;
    const modal = document.getElementById('modal-user');
    const title = document.getElementById('modal-user-title');
    const form = document.getElementById('form-user');
    
    if (user) {
        // Modo de edição
        title.textContent = 'Editar Usuário';
        document.getElementById('user-id').value = user.id;
        document.getElementById('user-name').value = user.name;
        document.getElementById('user-email').value = user.email;
        document.getElementById('user-password').value = '';
        document.getElementById('user-role').value = user.role;
        document.getElementById('user-active').value = user.active.toString();
    } else {
        // ✅ Modo de criação - LIMPAR EXPLICITAMENTE TODOS OS CAMPOS
        title.textContent = 'Novo Usuário';
        form.reset();
        document.getElementById('user-id').value = '';
        document.getElementById('user-name').value = '';      // ✅ CORRIGIDO
        document.getElementById('user-email').value = '';     // ✅ CORRIGIDO
        document.getElementById('user-password').value = '';  // ✅ CORRIGIDO
        document.getElementById('user-role').value = 'user';
        document.getElementById('user-active').value = 'true';
    }
    
    modal.classList.add('active');
}

function closeUserModal() {
    document.getElementById('modal-user').classList.remove('active');
    state.editingUser = null;
}

async function saveUser(e) {
    e.preventDefault();
    
    console.log('🔍 Form submetido, iniciando debug...');
    
    // Debug detalhado dos elementos
    const userIdElement = document.getElementById('user-id');
    const userNameElement = document.getElementById('user-name');
    const userEmailElement = document.getElementById('user-email');
    const userPasswordElement = document.getElementById('user-password');
    const userRoleElement = document.getElementById('user-role');
    const userActiveElement = document.getElementById('user-active');
    
    console.log('🔍 Elementos encontrados:');
    console.log('  user-id:', !!userIdElement);
    console.log('  user-name:', !!userNameElement);
    console.log('  user-email:', !!userEmailElement);
    console.log('  user-password:', !!userPasswordElement);
    console.log('  user-role:', !!userRoleElement);
    console.log('  user-active:', !!userActiveElement);
    
    console.log('🔍 Valores brutos dos campos:');
    console.log('  user-name value:', `"${userNameElement.value}"`);
    console.log('  user-email value:', `"${userEmailElement.value}"`);
    console.log('  user-password value:', `"${userPasswordElement.value}"`);
    
    // Verificar se modal está aberto
    const modal = document.getElementById('modal-user');
    console.log('🔍 Modal estado:', modal.className);
    
    // Tentar obter dados do FormData também
    const formData = new FormData(e.target);
    console.log('🔍 FormData entries:');
    for (let [key, value] of formData.entries()) {
        console.log('  ', key + ':', `"${value}"`);
    }
    
    // Verificar se elementos existem
    if (!userIdElement || !userNameElement || !userEmailElement || 
        !userPasswordElement || !userRoleElement || !userActiveElement) {
        console.error('❌ Elementos não encontrados:', {
            userIdElement: !userIdElement,
            userNameElement: !userNameElement,
            userEmailElement: !userEmailElement,
            userPasswordElement: !userPasswordElement,
            userRoleElement: !userRoleElement,
            userActiveElement: !userActiveElement
        });
        alert('Erro: Elementos do formulário não encontrados. Recarregue a página.');
        return;
    }
    
    // Extrair valores com verificações extras
    const userId = userIdElement ? userIdElement.value.trim() : '';
    const nameRaw = userNameElement.value;
    const name = nameRaw ? nameRaw.trim() : '';
    const emailRaw = userEmailElement.value;
    const email = emailRaw ? emailRaw.trim() : '';
    const password = userPasswordElement.value || '';
    const role = userRoleElement.value || 'user';
    const active = userActiveElement.value === 'true';
    
    console.log('🔍 Processamento dos valores:');
    console.log('  nameRaw:', `"${nameRaw}"`);
    console.log('  name (após trim):', `"${name}"`);
    console.log('  name length:', name.length);
    console.log('  emailRaw:', `"${emailRaw}"`);
    console.log('  email (após trim):', `"${email}"`);
    console.log('  password length:', password.length);
    console.log('  role:', role);
    console.log('  active:', active);
    
    console.log('🔍 Dados extraídos finais:', { userId, name, email, role, active, hasPassword: !!password });
    
    // Validação com debug extra
    if (!name || name.length === 0) {
        console.error('❌ VALIDAÇÃO FALHOU - Nome vazio');
        console.error('❌ name value:', `"${name}"`);
        console.error('❌ name length:', name.length);
        console.error('❌ name truthy:', !!name);
        console.error('❌ Original input value:', `"${userNameElement.value}"`);
        console.error('❌ Input element:', userNameElement);
        
        alert('⚠️ O nome é obrigatório. Digite um nome válido.');
        userNameElement.focus();
        userNameElement.style.border = '2px solid red';
        return;
    }
    
    if (!email || email.length === 0) {
        console.error('❌ Email vazio');
        alert('⚠️ O email é obrigatório');
        userEmailElement.focus();
        userEmailElement.style.border = '2px solid red';
        return;
    }
    
    // Para novos usuários, senha é obrigatória
    if (!userId && !password) {
        console.error('❌ Senha obrigatória para novo usuário');
        alert('⚠️ A senha é obrigatória para novos usuários');
        userPasswordElement.focus();
        userPasswordElement.style.border = '2px solid red';
        return;
    }
    
    // Remover bordas vermelhas se chegou até aqui
    userNameElement.style.border = '';
    userEmailElement.style.border = '';
    userPasswordElement.style.border = '';
    
    // Monta o objeto userData
    const userData = {
        name: name,
        email: email,
        role: role,
        active: active
    };
    
    // Adiciona password se fornecida
    if (password) {
        userData.password = password;
    }
    
    console.log('🔍 Objeto userData final para envio:', userData);
    console.log('🔍 JSON.stringify(userData):', JSON.stringify(userData));
    
    try {
        console.log('🔍 Iniciando requisição...');
        
        let response;
        const url = userId ? `${state.apiUrl}/users/${userId}` : `${state.apiUrl}/users`;
        const method = userId ? 'PUT' : 'POST';
        
        console.log(`🔍 ${method} ${url}`);
        console.log('🔍 Payload:', userData);
        
        if (userId) {
            console.log(`🔍 Atualizando usuário ID: ${userId}`);
            response = await axios.put(url, userData);
        } else {
            console.log('🔍 Criando novo usuário');
            response = await axios.post(url, userData);
        }
        
        console.log('✅ Resposta completa:', response);
        console.log('✅ Response data:', response.data);
        console.log('✅ Response status:', response.status);
        
        alert(userId ? '✅ Usuário atualizado com sucesso!' : '✅ Usuário criado com sucesso!');
        
        closeUserModal();
        await loadUsers();
        
    } catch (error) {
        console.error('❌ Erro completo:', error);
        console.error('❌ Error message:', error.message);
        console.error('❌ Response data:', error.response?.data);
        console.error('❌ Response status:', error.response?.status);
        console.error('❌ Response headers:', error.response?.headers);
        console.error('❌ Request config:', error.config);
        
        let errorMessage = 'Erro desconhecido';
        
        if (error.response?.data?.error) {
            errorMessage = error.response.data.error;
        } else if (error.response?.status === 400) {
            errorMessage = 'Dados inválidos: ' + (error.response.data?.error || 'Verificar campos');
        } else if (error.response?.status === 401) {
            errorMessage = 'Não autorizado. Faça login novamente.';
        } else if (error.response?.status === 500) {
            errorMessage = 'Erro interno do servidor';
        } else if (error.message) {
            errorMessage = error.message;
        }
        
        alert('❌ Erro ao salvar usuário: ' + errorMessage);
    }
}

window.editUser = function(userId) {
    const user = state.users.find(u => u.id === userId);
    if (user) {
        openUserModal(user);
    }
};

window.deleteUser = async function(userId) {
    if (!confirm('Tem certeza que deseja excluir este usuário?')) {
        return;
    }
    
    try {
        await axios.delete(`${state.apiUrl}/users/${userId}`);
        alert('✅ Usuário excluído com sucesso!');
        await loadUsers();
    } catch (error) {
        console.error('❌ Erro ao excluir usuário:', error);
        alert('❌ Erro ao excluir usuário: ' + (error.response?.data?.error || error.message));
    }
};

// ==================== UTILIDADES ====================

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) {
        const hours = Math.floor(diff / (1000 * 60 * 60));
        if (hours === 0) {
            const minutes = Math.floor(diff / (1000 * 60));
            return minutes <= 1 ? 'Agora' : `${minutes} min atrás`;
        }
        return hours === 1 ? '1 hora atrás' : `${hours} horas atrás`;
    } else if (days === 1) {
        return 'Ontem';
    } else if (days < 7) {
        return `${days} dias atrás`;
    }
    
    return date.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ==================== EVENT LISTENERS ====================

function setupEventListeners() {
    // Tema
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
    
    // Logout
    document.getElementById('btn-logout').addEventListener('click', logout);
    
    // Modal Usuário
    document.getElementById('btn-add-user').addEventListener('click', () => openUserModal());
    document.getElementById('modal-user-close').addEventListener('click', closeUserModal);
    document.getElementById('btn-cancel-user').addEventListener('click', closeUserModal);
    document.getElementById('form-user').addEventListener('submit', saveUser);
    
    // Fechar modal ao clicar fora
    document.getElementById('modal-user').addEventListener('click', (e) => {
        if (e.target.id === 'modal-user') {
            closeUserModal();
        }
    });
}

// ==================== INICIALIZAÇÃO ====================

async function init() {
    console.log('🚀 Iniciando painel administrativo...');
    
    // Verificar autenticação
    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) {
        return;
    }
    
    // Atualizar UI com usuário
    document.getElementById('current-user-name').textContent = state.currentUser.name;
    document.getElementById('user-avatar').textContent = state.currentUser.name.charAt(0).toUpperCase();
    
    // Carregar tema
    loadTheme();
    
    // Setup
    setupTabs();
    setupEventListeners();
    
    // Carregar dados
    await Promise.all([
        loadUsers(),
        loadLogins()
    ]);
    
    // Esconder loading e mostrar app
    document.getElementById('auth-loading').style.display = 'none';
    document.getElementById('app').classList.add('loaded');
    
    console.log('✅ Painel inicializado com sucesso!');
}

// Iniciar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', init);