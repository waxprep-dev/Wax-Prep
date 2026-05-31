const { useState, useEffect, useRef } = React;

const apiFetch = async (url, options = {}) => {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) { localStorage.removeItem('token'); window.location.reload(); }
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: 'Request failed' })); throw new Error(err.detail || 'Request failed'); }
  return res.json();
};

const Toast = ({ message, type }) => React.createElement('div', { style: { position: 'fixed', bottom: 20, right: 20, background: type === 'error' ? '#ef4444' : '#22c55e', color: '#fff', padding: '12px 24px', borderRadius: 8, zIndex: 1000, fontSize: 14, boxShadow: '0 4px 12px rgba(0,0,0,0.3)' } }, message);

const WelcomePage = ({ onNavigate }) => React.createElement('div', { style: { minHeight: '100vh', background: '#0f1117', color: '#e2e8f0', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '20px', textAlign: 'center' } },
  React.createElement('div', { style: { fontSize: 48, marginBottom: 20 } }, '🦉'),
  React.createElement('h1', { style: { fontSize: 32, fontWeight: 700, marginBottom: 8, color: '#60a5fa' } }, 'WaxPrep'),
  React.createElement('p', { style: { fontSize: 18, color: '#94a3b8', marginBottom: 32 } }, 'The tutor that actually knows you'),
  React.createElement('div', { style: { display: 'flex', gap: 16, flexWrap: 'wrap', justifyContent: 'center', maxWidth: 400 } },
    React.createElement('button', { onClick: () => onNavigate('login'), style: { padding: '14px 32px', background: '#60a5fa', color: '#fff', border: 'none', borderRadius: 8, fontSize: 16, fontWeight: 600, cursor: 'pointer', minWidth: 140 } }, 'Login'),
    React.createElement('button', { onClick: () => onNavigate('register'), style: { padding: '14px 32px', background: 'transparent', color: '#60a5fa', border: '2px solid #60a5fa', borderRadius: 8, fontSize: 16, fontWeight: 600, cursor: 'pointer', minWidth: 140 } }, 'Register')
  ),
  React.createElement('div', { style: { marginTop: 48, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16, maxWidth: 600 } },
    React.createElement('div', { style: { background: '#1a1d2e', padding: 16, borderRadius: 8 } }, React.createElement('div', { style: { fontSize: 24, fontWeight: 700, color: '#60a5fa' } }, '20+'), React.createElement('div', { style: { fontSize: 13, color: '#94a3b8' } }, 'Subjects')),
    React.createElement('div', { style: { background: '#1a1d2e', padding: 16, borderRadius: 8 } }, React.createElement('div', { style: { fontSize: 24, fontWeight: 700, color: '#60a5fa' } }, 'WAEC'), React.createElement('div', { style: { fontSize: 13, color: '#94a3b8' } }, 'NECO JAMB BECE')),
    React.createElement('div', { style: { background: '#1a1d2e', padding: 16, borderRadius: 8 } }, React.createElement('div', { style: { fontSize: 24, fontWeight: 700, color: '#60a5fa' } }, '30+'), React.createElement('div', { style: { fontSize: 13, color: '#94a3b8' } }, 'Free Messages/Day'))
  )
);

const AuthPage = ({ onLogin, defaultTab }) => {
  const [tab, setTab] = useState(defaultTab || 'login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const endpoint = tab === 'login' ? '/api/v1/web/login' : '/api/v1/web/register';
      const body = tab === 'login' ? { email, password } : { email, password, username };
      const data = await apiFetch(endpoint, { method: 'POST', body: JSON.stringify(body) });
      if (data.token) { localStorage.setItem('token', data.token); onLogin(data); }
    } catch (err) { setError(err.message); } finally { setLoading(false); }
  };

  return React.createElement('div', { style: { minHeight: '100vh', background: '#0f1117', color: '#e2e8f0', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 20 } },
    React.createElement('div', { style: { maxWidth: 400, width: '100%' } },
      React.createElement('div', { style: { display: 'flex', marginBottom: 24, background: '#1a1d2e', borderRadius: 8, overflow: 'hidden' } },
        React.createElement('button', { onClick: () => setTab('login'), style: { flex: 1, padding: '12px', border: 'none', cursor: 'pointer', fontSize: 15, fontWeight: 600, background: tab === 'login' ? '#60a5fa' : 'transparent', color: tab === 'login' ? '#fff' : '#94a3b8' } }, 'Login'),
        React.createElement('button', { onClick: () => setTab('register'), style: { flex: 1, padding: '12px', border: 'none', cursor: 'pointer', fontSize: 15, fontWeight: 600, background: tab === 'register' ? '#60a5fa' : 'transparent', color: tab === 'register' ? '#fff' : '#94a3b8' } }, 'Register')
      ),
      error && React.createElement('div', { style: { background: '#fef2f2', color: '#dc2626', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 } }, error),
      React.createElement('form', { onSubmit: handleSubmit },
        tab === 'register' && React.createElement('input', { type: 'text', placeholder: 'Username', value: username, onChange: (e) => setUsername(e.target.value), required: true, style: { width: '100%', padding: 12, marginBottom: 12, background: '#1a1d2e', border: '1px solid #2d3148', borderRadius: 8, color: '#e2e8f0', fontSize: 15, outline: 'none', boxSizing: 'border-box' } }),
        React.createElement('input', { type: 'email', placeholder: 'Email', value: email, onChange: (e) => setEmail(e.target.value), required: true, style: { width: '100%', padding: 12, marginBottom: 12, background: '#1a1d2e', border: '1px solid #2d3148', borderRadius: 8, color: '#e2e8f0', fontSize: 15, outline: 'none', boxSizing: 'border-box' } }),
        React.createElement('input', { type: 'password', placeholder: 'Password', value: password, onChange: (e) => setPassword(e.target.value), required: true, minLength: 6, style: { width: '100%', padding: 12, marginBottom: 20, background: '#1a1d2e', border: '1px solid #2d3148', borderRadius: 8, color: '#e2e8f0', fontSize: 15, outline: 'none', boxSizing: 'border-box' } }),
        React.createElement('button', { type: 'submit', disabled: loading, style: { width: '100%', padding: 14, background: '#60a5fa', color: '#fff', border: 'none', borderRadius: 8, fontSize: 16, fontWeight: 600, cursor: 'pointer', opacity: loading ? 0.7 : 1 } }, loading ? 'Please wait...' : tab === 'login' ? 'Login' : 'Create Account')
      )
    )
  );
};

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatRef = useRef(null);

  const sendMessage = async (text) => {
    if (!text.trim() || loading) return;
    const userMsg = { role: 'user', content: text };
    setMessages(m => [...m, userMsg]);
    setInput('');
    setLoading(true);
    try {
      const data = await apiFetch('/api/v1/web/chat', { method: 'POST', body: JSON.stringify({ message: text }) });
      setMessages(m => [...m, { role: 'assistant', content: data.response || data.message }]);
    } catch (err) { setMessages(m => [...m, { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' }]); } finally { setLoading(false); }
  };

  useEffect(() => { chatRef.current?.scrollTo(0, chatRef.current.scrollHeight); }, [messages]);

  return React.createElement('div', { style: { display: 'flex', flexDirection: 'column', height: '100vh', maxWidth: 700, margin: '0 auto', background: '#0f1117' } },
    React.createElement('div', { ref: chatRef, style: { flex: 1, overflow: 'auto', padding: 16 } },
      messages.length === 0 && React.createElement('div', { style: { textAlign: 'center', color: '#64748b', marginTop: 60 } },
        React.createElement('div', { style: { fontSize: 40, marginBottom: 12 } }, '🦉'),
        React.createElement('div', { style: { fontSize: 18, fontWeight: 600, color: '#94a3b8', marginBottom: 8 } }, 'WaxPrep Web'),
        React.createElement('div', { style: { fontSize: 14 } }, 'The tutor that actually knows you. Start a conversation.')
      ),
      messages.map((m, i) => React.createElement('div', { key: i, style: { marginBottom: 16, display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' } },
        React.createElement('div', { style: { maxWidth: '80%', padding: '12px 16px', borderRadius: 12, background: m.role === 'user' ? '#60a5fa' : '#1a1d2e', color: m.role === 'user' ? '#fff' : '#e2e8f0', fontSize: 14, lineHeight: 1.5, whiteSpace: 'pre-wrap' } }, m.content)
      )),
      loading && React.createElement('div', { style: { color: '#64748b', fontSize: 14, padding: 8 } }, 'WaxPrep is typing...')
    ),
    React.createElement('div', { style: { padding: '12px 16px', borderTop: '1px solid #1e2130', background: '#0f1117' } },
      React.createElement('div', { style: { display: 'flex', gap: 8 } },
        React.createElement('input', { type: 'text', value: input, onChange: (e) => setInput(e.target.value), onKeyDown: (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }, placeholder: 'Ask WaxPrep anything...', style: { flex: 1, padding: 12, background: '#1a1d2e', border: '1px solid #2d3148', borderRadius: 8, color: '#e2e8f0', fontSize: 14, outline: 'none' } }),
        React.createElement('button', { onClick: () => sendMessage(input), disabled: loading || !input.trim(), style: { padding: '12px 20px', background: '#60a5fa', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600, opacity: loading || !input.trim() ? 0.5 : 1 } }, 'Send')
      )
    )
  );
};

const KnowledgePage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { apiFetch('/api/v1/web/knowledge-map').then(setData).catch(() => {}).finally(() => setLoading(false)); }, []);

  if (loading) return React.createElement('div', { style: { color: '#94a3b8', textAlign: 'center', padding: 40 } }, 'Loading knowledge map...');
  if (!data || !data.subjects) return React.createElement('div', { style: { color: '#94a3b8', textAlign: 'center', padding: 40 } }, 'No knowledge data yet. Start chatting to build your map.');

  return React.createElement('div', { style: { padding: 20, maxWidth: 700, margin: '0 auto' } },
    React.createElement('h2', { style: { color: '#e2e8f0', marginBottom: 20 } }, 'Your Knowledge Map'),
    data.subjects.map((subj, si) =>
      React.createElement('div', { key: si, style: { marginBottom: 24, background: '#1a1d2e', borderRadius: 12, padding: 16 } },
        React.createElement('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 } },
          React.createElement('span', { style: { color: '#e2e8f0', fontWeight: 600, fontSize: 16 } }, subj.name),
          React.createElement('span', { style: { color: '#60a5fa', fontSize: 14 } }, Math.round(subj.mastery || 0) + '% Mastery')
        ),
        React.createElement('div', { style: { background: '#2d3148', borderRadius: 4, height: 8, marginBottom: 12 } },
          React.createElement('div', { style: { background: '#60a5fa', borderRadius: 4, height: 8, width: (subj.mastery || 0) + '%' } })
        ),
        subj.concepts && subj.concepts.map((c, ci) =>
          React.createElement('div', { key: ci, style: { display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderTop: '1px solid #2d3148', fontSize: 13 } },
            React.createElement('span', { style: { color: '#94a3b8' } }, c.name),
            React.createElement('span', { style: { color: c.mastery >= 70 ? '#22c55e' : c.mastery >= 40 ? '#f59e0b' : '#ef4444' } }, c.mastery + '%')
          )
        )
      )
    )
  );
};

const AchievementsPage = () => {
  const [achievements, setAchievements] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { apiFetch('/api/v1/web/dashboard').then(d => setAchievements(d.achievements || [])).catch(() => {}).finally(() => setLoading(false)); }, []);

  return React.createElement('div', { style: { padding: 20, maxWidth: 700, margin: '0 auto' } },
    React.createElement('h2', { style: { color: '#e2e8f0', marginBottom: 20 } }, 'Achievements'),
    loading ? React.createElement('div', { style: { color: '#94a3b8' } }, 'Loading...') :
    achievements.length === 0 ? React.createElement('div', { style: { color: '#94a3b8' } }, 'No achievements yet. Keep studying!') :
    React.createElement('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12 } },
      achievements.map((a, i) => React.createElement('div', { key: i, style: { background: '#1a1d2e', borderRadius: 12, padding: 16, textAlign: 'center', border: a.rarity === 'legendary' ? '2px solid #f59e0b' : '1px solid #2d3148' } },
        React.createElement('div', { style: { fontSize: 32, marginBottom: 8 } }, a.icon || '🏆'),
        React.createElement('div', { style: { color: '#e2e8f0', fontWeight: 600, fontSize: 14, marginBottom: 4 } }, a.name),
        React.createElement('div', { style: { color: '#64748b', fontSize: 12 } }, a.description)
      ))
    )
  );
};

const StudyPlanPage = () => {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchPlan = () => { setLoading(true); apiFetch('/api/v1/web/study-plan').then(setPlan).catch(() => {}).finally(() => setLoading(false)); };
  useEffect(() => { fetchPlan(); }, []);

  return React.createElement('div', { style: { padding: 20, maxWidth: 700, margin: '0 auto' } },
    React.createElement('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 } },
      React.createElement('h2', { style: { color: '#e2e8f0', margin: 0 } }, 'Study Plan'),
      React.createElement('button', { onClick: fetchPlan, style: { padding: '8px 16px', background: '#1a1d2e', color: '#60a5fa', border: '1px solid #2d3148', borderRadius: 6, cursor: 'pointer', fontSize: 13 } }, 'Regenerate')
    ),
    loading ? React.createElement('div', { style: { color: '#94a3b8' } }, 'Loading...') :
    !plan ? React.createElement('div', { style: { color: '#94a3b8' } }, 'No study plan yet. Chat with WaxPrep to generate one.') :
    React.createElement('div', {}, plan.weeks && plan.weeks.map((w, wi) =>
      React.createElement('div', { key: wi, style: { background: '#1a1d2e', borderRadius: 12, padding: 16, marginBottom: 12 } },
        React.createElement('div', { style: { color: '#60a5fa', fontWeight: 600, marginBottom: 8 } }, w.title || 'Week ' + (wi + 1)),
        w.topics && w.topics.map((t, ti) => React.createElement('div', { key: ti, style: { color: '#94a3b8', fontSize: 13, padding: '4px 0' } }, '• ' + t))
      )
    ))
  );
};

const HomePage = ({ onNavigate, onLogout }) => {
  const [dashboard, setDashboard] = useState(null);
  useEffect(() => { apiFetch('/api/v1/web/dashboard').then(setDashboard).catch(() => {}); }, []);

  return React.createElement('div', { style: { minHeight: '100vh', background: '#0f1117', color: '#e2e8f0' } },
    React.createElement('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid #1e2130' } },
      React.createElement('span', { style: { fontSize: 20, fontWeight: 700, color: '#60a5fa' } }, '🦉 WaxPrep'),
      React.createElement('button', { onClick: onLogout, style: { padding: '8px 16px', background: 'transparent', color: '#94a3b8', border: '1px solid #2d3148', borderRadius: 6, cursor: 'pointer', fontSize: 13 } }, 'Logout')
    ),
    React.createElement('div', { style: { padding: 20 } },
      dashboard && React.createElement('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 24 } },
        React.createElement('div', { style: { background: '#1a1d2e', borderRadius: 12, padding: 16, textAlign: 'center' } }, React.createElement('div', { style: { fontSize: 28, fontWeight: 700, color: '#60a5fa' } }, dashboard.total_xp || 0), React.createElement('div', { style: { fontSize: 12, color: '#64748b' } }, 'XP')),
        React.createElement('div', { style: { background: '#1a1d2e', borderRadius: 12, padding: 16, textAlign: 'center' } }, React.createElement('div', { style: { fontSize: 28, fontWeight: 700, color: '#22c55e' } }, dashboard.concepts_mastered || 0), React.createElement('div', { style: { fontSize: 12, color: '#64748b' } }, 'Mastered')),
        React.createElement('div', { style: { background: '#1a1d2e', borderRadius: 12, padding: 16, textAlign: 'center' } }, React.createElement('div', { style: { fontSize: 28, fontWeight: 700, color: '#f59e0b' } }, dashboard.session_count || 0), React.createElement('div', { style: { fontSize: 12, color: '#64748b' } }, 'Sessions')),
        React.createElement('div', { style: { background: '#1a1d2e', borderRadius: 12, padding: 16, textAlign: 'center' } }, React.createElement('div', { style: { fontSize: 28, fontWeight: 700, color: '#a78bfa' } }, dashboard.study_streak || 0), React.createElement('div', { style: { fontSize: 12, color: '#64748b' } }, 'Day Streak'))
      ),
      React.createElement('div', { style: { background: '#1a1d2e', borderRadius: 12, padding: 20, textAlign: 'center', cursor: 'pointer' }, onClick: () => onNavigate('chat') },
        React.createElement('div', { style: { fontSize: 18, color: '#e2e8f0', marginBottom: 8 } }, 'Continue Studying'),
        React.createElement('div', { style: { fontSize: 14, color: '#64748b' } }, 'Pick up where you left off with your AI tutor')
      )
    ),
    React.createElement('div', { style: { position: 'fixed', bottom: 0, left: 0, right: 0, display: 'flex', background: '#0f1117', borderTop: '1px solid #1e2130' } },
      ['home', 'chat', 'knowledge', 'achievements', 'plan'].map(tab =>
        React.createElement('button', { key: tab, onClick: () => onNavigate(tab), style: { flex: 1, padding: '14px 8px', background: 'transparent', color: '#94a3b8', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 500 } }, tab.charAt(0).toUpperCase() + tab.slice(1))
      )
    )
  );
};

const App = () => {
  const [page, setPage] = useState('welcome');
  const [user, setUser] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) { apiFetch('/api/v1/web/dashboard').then(d => { setUser(d); setPage('home'); }).catch(() => localStorage.removeItem('token')); }
  }, []);

  const handleLogin = (data) => { setUser(data); setPage('home'); };
  const handleLogout = () => { localStorage.removeItem('token'); setUser(null); setPage('welcome'); };

  if (page === 'welcome') return React.createElement(WelcomePage, { onNavigate: (p) => setPage(p === 'login' ? 'login' : 'register') });
  if (page === 'login' || page === 'register') return React.createElement(AuthPage, { onLogin: handleLogin, defaultTab: page });

  const renderPage = () => {
    switch (page) {
      case 'chat': return React.createElement(ChatPage);
      case 'knowledge': return React.createElement(KnowledgePage);
      case 'achievements': return React.createElement(AchievementsPage);
      case 'plan': return React.createElement(StudyPlanPage);
      default: return React.createElement(HomePage, { onNavigate: setPage, onLogout: handleLogout });
    }
  };

  return React.createElement('div', {},
    renderPage(),
    page !== 'home' && React.createElement('div', { style: { position: 'fixed', bottom: 0, left: 0, right: 0, display: 'flex', background: '#0f1117', borderTop: '1px solid #1e2130' } },
      ['home', 'chat', 'knowledge', 'achievements', 'plan'].map(tab =>
        React.createElement('button', { key: tab, onClick: () => setPage(tab), style: { flex: 1, padding: '14px 8px', background: page === tab ? '#1a1d2e' : 'transparent', color: page === tab ? '#60a5fa' : '#94a3b8', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 500 } }, tab.charAt(0).toUpperCase() + tab.slice(1))
      )
    )
  );
};
