const state = {
    isLoggedIn: false,
    currentSession: null,
    sessions: [],
    isRecording: false,
    currentSessionId: null,
};

const elements = {
    splashScreen: null,
    authScreen: null,
    mainScreen: null,
    loginForm: null,
    registerForm: null,
    authMessage: null,
    userName: null,
    sessionList: null,
    conversation: null,
    blurOverlay: null,
    interimText: null,
    startRecordingBtn: null,
    stopRecordingBtn: null,
};

document.addEventListener('DOMContentLoaded', async () => {
    initElements();
    attachEventListeners();
    await checkLoginStatus();
});

function initElements() {
    elements.splashScreen = document.getElementById('splash-screen');
    elements.authScreen = document.getElementById('auth-screen');
    elements.mainScreen = document.getElementById('main-screen');
    elements.loginForm = document.getElementById('login-form');
    elements.registerForm = document.getElementById('register-form');
    elements.authMessage = document.getElementById('auth-message');
    elements.userName = document.getElementById('user-name');
    elements.sessionList = document.getElementById('session-list');
    elements.conversation = document.getElementById('conversation');
    elements.blurOverlay = document.getElementById('blur-overlay');
    elements.interimText = document.getElementById('interim-text');
    elements.startRecordingBtn = document.getElementById('start-recording-btn');
    elements.stopRecordingBtn = document.getElementById('stop-recording-btn');
}

function attachEventListeners() {
    document.getElementById('login-btn')?.addEventListener('click', handleLogin);
    document.getElementById('register-btn')?.addEventListener('click', handleRegister);
    document.getElementById('show-register-btn')?.addEventListener('click', showRegisterForm);
    document.getElementById('show-login-btn')?.addEventListener('click', showLoginForm);
    document.getElementById('logout-btn')?.addEventListener('click', handleLogout);
    document.getElementById('new-session-btn')?.addEventListener('click', handleNewSession);
    elements.startRecordingBtn?.addEventListener('click', handleStartRecording);
    elements.stopRecordingBtn?.addEventListener('click', handleStopRecording);

    document.getElementById('login-password')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleLogin();
    });
}

async function checkLoginStatus() {
    try {
        await sleep(1000);

        const result = await pywebview.api.check_login_status();

        if (result.logged_in && result.session) {
            state.isLoggedIn = true;
            state.currentSession = result.session;
            await showMainScreen();
        } else {
            showAuthScreen();
        }
    } catch (error) {
        console.error('Error checking login status:', error);
        showAuthScreen();
    }
}

async function handleLogin() {
    const eid = document.getElementById('login-eid').value.trim();
    const password = document.getElementById('login-password').value;

    if (!eid || !password) {
        showAuthMessage('请输入工号和密码', 'error');
        return;
    }

    try {
        const result = await pywebview.api.login(eid, password);

        if (result.success) {
            state.isLoggedIn = true;
            state.currentSession = result.session;
            await showMainScreen();
        } else {
            showAuthMessage(result.message || '登录失败', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showAuthMessage('登录失败，请重试', 'error');
    }
}

async function handleRegister() {
    const eid = document.getElementById('register-eid').value.trim();
    const password = document.getElementById('register-password').value;
    const passwordConfirm = document.getElementById('register-password-confirm').value;
    const name = document.getElementById('register-name').value.trim();
    const department = document.getElementById('register-department').value.trim();
    const title = document.getElementById('register-title').value.trim();
    const hospital = document.getElementById('register-hospital').value.trim();

    if (!eid || !password || !name) {
        showAuthMessage('请填写必填项', 'error');
        return;
    }

    if (password !== passwordConfirm) {
        showAuthMessage('两次密码输入不一致', 'error');
        return;
    }

    try {
        const result = await pywebview.api.register(
            eid, password, name,
            department || null,
            title || null,
            hospital || null
        );

        if (result.success) {
            showAuthMessage('注册成功！请登录', 'success');
            setTimeout(showLoginForm, 1500);
        } else {
            showAuthMessage(result.message || '注册失败', 'error');
        }
    } catch (error) {
        console.error('Register error:', error);
        showAuthMessage('注册失败，请重试', 'error');
    }
}

async function handleLogout() {
    try {
        await pywebview.api.logout();
        state.isLoggedIn = false;
        state.currentSession = null;
        state.sessions = [];
        showAuthScreen();
    } catch (error) {
        console.error('Logout error:', error);
    }
}

function showAuthScreen() {
    elements.splashScreen?.classList.add('hidden');
    elements.mainScreen?.classList.add('hidden');
    elements.authScreen?.classList.remove('hidden');
    showLoginForm();
}

async function showMainScreen() {
    elements.splashScreen?.classList.add('hidden');
    elements.authScreen?.classList.add('hidden');
    elements.mainScreen?.classList.remove('hidden');

    if (state.currentSession && state.currentSession.doctor_name) {
        elements.userName.textContent = state.currentSession.doctor_name;
    } else {
        elements.userName.textContent = state.currentSession?.eid || '用户';
    }

    await loadSessions();
}

function showLoginForm() {
    elements.loginForm?.classList.remove('hidden');
    elements.registerForm?.classList.add('hidden');
    elements.authMessage.textContent = '';
}

function showRegisterForm() {
    elements.loginForm?.classList.add('hidden');
    elements.registerForm?.classList.remove('hidden');
    elements.authMessage.textContent = '';
}

function showAuthMessage(message, type = 'error') {
    elements.authMessage.textContent = message;
    elements.authMessage.className = `auth-message ${type}`;
}

async function loadSessions() {
    try {
        const result = await pywebview.api.get_sessions(0, 20);

        if (result.success) {
            state.sessions = result.sessions;
            renderSessionList();
        }
    } catch (error) {
        console.error('Error loading sessions:', error);
    }
}

function renderSessionList() {
    elements.sessionList.innerHTML = '';

    if (state.sessions.length === 0) {
        elements.sessionList.innerHTML = `
            <div style="padding: 20px; text-align: center; color: #757575;">
                暂无会话记录
            </div>
        `;
        return;
    }

    state.sessions.forEach(session => {
        const item = document.createElement('div');
        item.className = 'session-item';
        if (session.id === state.currentSessionId) {
            item.classList.add('active');
        }

        item.innerHTML = `
            <div class="session-item-header">
                <span class="session-patient">${session.patient_name || '未命名患者'}</span>
                <span class="session-status">${getStatusText(session.status)}</span>
            </div>
            <div class="session-clinic">${session.clinic_number || '无门诊号'}</div>
        `;

        item.addEventListener('click', () => selectSession(session.id));
        elements.sessionList.appendChild(item);
    });
}

function getStatusText(status) {
    const statusMap = {
        'draft': '草稿',
        'in_progress': '进行中',
        'completed': '已完成',
        'cancelled': '已取消',
    };
    return statusMap[status] || status;
}

async function selectSession(sessionId) {
    state.currentSessionId = sessionId;
    renderSessionList();
    await loadConversation(sessionId);
}

async function loadConversation(sessionId) {
    try {
        clearConversation();
        const result = await pywebview.api.get_utterances(sessionId);

        if (result.success && result.utterances.length > 0) {
            result.utterances.forEach(utterance => {
                addMessage(utterance.text, utterance.speaker === 'doctor');
            });
        }
    } catch (error) {
        console.error('Error loading conversation:', error);
    }
}

async function handleNewSession() {
    const patientName = prompt('请输入患者姓名（选填）：');
    const clinicNumber = prompt('请输入门诊号（选填）：');

    try {
        const result = await pywebview.api.create_session(
            patientName || null,
            clinicNumber || null
        );

        if (result.success) {
            await loadSessions();
            selectSession(result.session.id);
        }
    } catch (error) {
        console.error('Error creating session:', error);
        alert('创建会话失败');
    }
}

async function handleStartRecording() {
    if (!state.currentSessionId) {
        alert('请先选择或创建一个会话');
        return;
    }

    try {
        const result = await pywebview.api.start_recording(state.currentSessionId);

        if (result.success) {
            state.isRecording = true;
            elements.startRecordingBtn.classList.add('hidden');
            elements.stopRecordingBtn.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Error starting recording:', error);
        alert('开始录音失败');
    }
}

async function handleStopRecording() {
    try {
        const result = await pywebview.api.stop_recording(state.currentSessionId);

        if (result.success) {
            state.isRecording = false;
            elements.startRecordingBtn.classList.remove('hidden');
            elements.stopRecordingBtn.classList.add('hidden');
            elements.blurOverlay.classList.add('hidden');

            await loadConversation(state.currentSessionId);
        }
    } catch (error) {
        console.error('Error stopping recording:', error);
        alert('停止录音失败');
    }
}

function clearConversation() {
    elements.conversation.innerHTML = `
        <div class="conversation-placeholder">
            <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="22"></line></svg>
            <p>点击下方开始录音</p>
        </div>
    `;
}

function showInterimText(text) {
    elements.interimText.textContent = text;
    elements.blurOverlay.classList.remove('hidden');
}

function hideInterimText() {
    elements.blurOverlay.classList.add('hidden');
}

function addMessage(text, isDoctor) {
    const placeholder = elements.conversation.querySelector('.conversation-placeholder');
    if (placeholder) {
        placeholder.remove();
    }

    const message = document.createElement('div');
    message.className = `message ${isDoctor ? 'doctor' : 'patient'}`;

    const now = new Date();
    const timeStr = now.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
    });

    message.innerHTML = `
        <div class="message-text">${text}</div>
        <div class="message-time">${timeStr}</div>
    `;

    elements.conversation.appendChild(message);
    elements.conversation.scrollTop = elements.conversation.scrollHeight;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
