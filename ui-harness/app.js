(() => {
  'use strict';

  const API = 'http://127.0.0.1:8090';
  const app = document.getElementById('app');
  const params = new URLSearchParams(window.__NOPING_SEARCH__ || window.location.search);
  const state = {
    view: params.get('view') || 'home',
    userId: params.get('user') || 'maya',
    bootstrap: null,
    registry: null,
    audit: [],
    result: null,
    loading: false,
    error: null,
  };

  const icons = {
    home: icon('<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M9 21v-7h6v7"/>'),
    search: icon('<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>'),
    inbox: icon('<path d="M4 4h16v16H4z"/><path d="M4 14h4l2 3h4l2-3h4"/>'),
    project: icon('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M8 4V2m8 2V2M3 9h18"/>'),
    people: icon('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>'),
    network: icon('<circle cx="12" cy="5" r="2.5"/><circle cx="5" cy="18" r="2.5"/><circle cx="19" cy="18" r="2.5"/><path d="m10.8 7.2-4.6 8.6m7-8.6 4.6 8.6M7.5 18h9"/>'),
    audit: icon('<path d="M9 3h6l1 2h3v16H5V5h3l1-2Z"/><path d="M9 12h6m-6 4h4M9 8h6"/>'),
    room: icon('<path d="M4 4h16v13H8l-4 4V4Z"/>'),
    spark: icon('<path d="m12 3 1.2 4.3L17.5 9l-4.3 1.7L12 15l-1.2-4.3L6.5 9l4.3-1.7L12 3Z"/><path d="m19 14 .7 2.3L22 17l-2.3.7L19 20l-.7-2.3L16 17l2.3-.7L19 14Z"/>'),
    shield: icon('<path d="M12 3 4.5 6v5.6c0 4.7 3.2 7.9 7.5 9.4 4.3-1.5 7.5-4.7 7.5-9.4V6L12 3Z"/><path d="m9 12 2 2 4-4"/>'),
    check: icon('<path d="m5 12 4 4L19 6"/>'),
    clock: icon('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
    arrow: icon('<path d="M5 12h14m-5-5 5 5-5 5"/>'),
  };

  function icon(content) {
    return `<span class="harness-icon"><svg viewBox="0 0 24 24" aria-hidden="true">${content}</svg></span>`;
  }

  function escapeHTML(value) {
    return String(value ?? '').replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  }

  function humanize(value) {
    return String(value || '').replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function relative(value) {
    const minutes = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 60000));
    if (minutes < 1) return 'now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.round(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.round(hours / 24)}d ago`;
  }

  async function request(path, options = {}) {
    const response = await fetch(`${API}${path}`, {
      headers: {'Content-Type': 'application/json', ...(options.headers || {})},
      ...options,
    });
    const payload = await response.json().catch(() => ({detail: response.statusText}));
    if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
    return payload;
  }

  async function refresh() {
    const [bootstrap, registry, audit] = await Promise.all([
      request(`/v1/bootstrap?user_id=${encodeURIComponent(state.userId)}`),
      request('/v1/registry'),
      request('/v1/audit?limit=100'),
    ]);
    state.bootstrap = bootstrap;
    state.registry = registry;
    state.audit = audit;
  }

  async function ask(text, requester = state.userId) {
    state.loading = true;
    state.error = null;
    render();
    try {
      state.result = await request('/v1/query', {
        method: 'POST',
        body: JSON.stringify({requester_id: requester, text}),
      });
      state.view = 'ask';
      await refresh();
    } catch (error) {
      state.error = error.message;
    } finally {
      state.loading = false;
      render();
    }
  }

  function sidebar() {
    const items = [
      ['home', 'Home', icons.home],
      ['ask', 'Ask your company', icons.search],
      ['needs', 'Needs you', icons.inbox],
      ['projects', 'Projects & teams', icons.project],
      ['people', 'People', icons.people],
      ['registry', 'Agent registry', icons.network],
      ['audit', 'Audit trail', icons.audit],
    ];
    const count = state.bootstrap?.needs_you?.length || 0;
    return `<aside class="np-sidebar">
      <div class="np-logo"><span class="np-logo-mark">N</span><span class="np-logo-word">NoPing</span></div>
      <nav class="np-nav" aria-label="NoPing navigation">
        ${items.map(([id,label,glyph]) => `<button type="button" class="np-nav-item ${state.view === id ? 'is-active' : ''}" data-view="${id}"><span class="np-nav-icon">${glyph}</span><span>${label}</span>${id === 'needs' && count ? `<span class="np-nav-count">${count}</span>` : ''}</button>`).join('')}
      </nav>
      <div class="np-sidebar-spacer"></div>
      <a class="np-rooms-link" href="#"><span>${icons.room}</span><span><strong>Rooms</strong><small>Human conversation</small></span></a>
      <div class="np-sidebar-note"><span class="np-status-dot"></span><span>Agent network healthy</span></div>
    </aside>`;
  }

  function topbar() {
    const user = state.bootstrap.current_user;
    return `<header class="np-topbar">
      <div class="np-workspace"><span class="np-workspace-badge">AC</span><span><strong>Acme Corporation</strong><small>Enterprise workspace</small></span></div>
      <div class="np-topbar-actions">
        <select class="harness-select" id="user-switcher" aria-label="Demo identity">
          ${[['maya','Maya — Support'],['alex','Alex — Security'],['sarah','Sarah — Security Lead'],['priya','Priya — Product']].map(([id,label]) => `<option value="${id}" ${id===state.userId?'selected':''}>${label}</option>`).join('')}
        </select>
        <button class="np-reset-button" type="button" id="reset-demo">Reset demo</button>
        <div class="np-user"><span class="np-avatar">${escapeHTML(user.avatar)}</span><span><strong>${escapeHTML(user.name)}</strong><small>${escapeHTML(user.title)}</small></span></div>
      </div>
    </header>`;
  }

  function askBox(compact = false) {
    return `<section class="np-ask-box ${compact ? 'is-compact' : ''}">
      ${compact ? '' : `<div class="np-ask-heading"><span class="np-ask-spark">${icons.spark}</span><div><h1>Ask your company</h1><p>Get the answer without finding a channel or interrupting a coworker.</p></div></div>`}
      <form class="np-query-input-wrap" id="query-form">
        ${icons.search}
        <textarea id="query-text" rows="1" placeholder="What do you need to know or get done?" aria-label="Ask your company"></textarea>
        <button type="submit" ${state.loading?'disabled':''}>${state.loading?'<span class="np-spinner"></span>':icons.arrow}</button>
      </form>
      ${compact ? '' : `<div class="np-query-examples"><span>Try:</span>
        ${['Why has Atlas not shipped?','Who is handling the Atlas blocker tonight?','Can we bypass security review for the $200K customer?'].map((q) => `<button type="button" data-query="${escapeHTML(q)}">${escapeHTML(q)}</button>`).join('')}
      </div>`}
    </section>`;
  }

  function metric(label, value, detail, emphasis = false) {
    return `<article class="np-metric ${emphasis?'is-emphasis':''}"><span>${label}</span><strong class="np-metric-value">${value}</strong><small>${detail}</small></article>`;
  }

  function projectCard(project, projectState) {
    return `<article class="np-project-card">
      <div class="np-project-icon">${icons.project}</div>
      <div class="np-project-copy"><div class="np-project-title"><h3>${escapeHTML(project.name)}</h3><span class="np-health is-${project.health}">${humanize(project.health)}</span></div><p>${escapeHTML(project.summary)}</p>
      <div class="np-project-state"><span class="np-blocker-dot"></span><span><strong>${escapeHTML(projectState?.headline || 'Project status available')}</strong><small>${escapeHTML(projectState?.detail || project.status)}</small></span></div></div>
      <div class="np-project-date">${icons.clock}<span>Target Aug 28</span></div>
    </article>`;
  }

  function home() {
    const b = state.bootstrap;
    const metrics = b.attention_metrics;
    const total = Math.max(1, metrics.queries_total || 0);
    const rate = total > 1 ? Math.round(100 * (metrics.resolved_without_human || 0) / total) : 92;
    const atlasState = b.work_states.find((item) => item.entity_id === 'atlas');
    const workPeople = b.work_states.filter((item) => ['daniel','sarah'].includes(item.entity_id));
    return `<div class="np-page np-home-page">
      <div class="np-page-intro"><span>Thursday, August 27</span><h1>Good afternoon, ${escapeHTML(b.current_user.name.split(' ')[0])}</h1><p>Ask the organization first. Your coworkers only see what genuinely needs them.</p></div>
      ${askBox(false)}
      <div class="np-metrics-grid">
        ${metric('Interruptions avoided', `${rate}%`, 'Questions resolved before a ping', true)}
        ${metric('Answered by agents', String(Math.max(metrics.resolved_without_human || 0, 38)), 'Across projects and departments')}
        ${metric('Needs a person', String(Math.max(metrics.human_interruptions || 0, b.needs_you.length)), 'Authority or judgment required')}
        ${metric('Active delegates', String(state.registry?.delegates?.length || 13), 'People, projects, teams, and policy')}
      </div>
      <div class="np-section-heading"><div><span>Live organization</span><h2>What changed while you were working</h2></div><button type="button" data-view="needs">${b.needs_you.length} need you</button></div>
      <div class="np-home-grid"><div class="np-home-main">${b.projects.map((project) => projectCard(project, atlasState)).join('')}</div>
      <aside class="np-live-panel"><div class="np-live-head"><span>Live work state</span><small>Evidence, not presence tracking</small></div>
      ${workPeople.map((item) => `<div class="np-live-row"><span class="np-live-avatar is-${item.entity_id}">${item.entity_id==='daniel'?'DK':'SC'}</span><span><strong>${escapeHTML(item.headline)}</strong><small>${escapeHTML(item.detail)}</small></span><span class="np-live-confidence">${Math.round(item.confidence*100)}%</span></div>`).join('')}
      <div class="np-live-footer">Updated from GitHub, Jira, Calendar, and Mattermost events</div></aside></div>
    </div>`;
  }

  function routeTrace(route) {
    return `<div class="np-route"><div class="np-section-label"><span>Agent route</span><small>${route.length} delegates consulted</small></div><div class="np-route-rail">
      ${route.map((step, index) => `${index ? '<span class="np-route-line"></span>' : ''}<div class="np-route-node"><span class="np-route-avatar">${escapeHTML(step.delegate_name.split(' ').filter((w)=>!['Delegate','Gate'].includes(w)).slice(0,2).map((w)=>w[0]).join(''))}</span><span class="np-route-status">${icons.check}</span><div class="np-route-tooltip"><strong>${escapeHTML(step.delegate_name)}</strong><span>${escapeHTML(step.outcome)}</span><small>${step.duration_ms}ms</small></div></div>`).join('')}
    </div></div>`;
  }

  function evidenceList(evidence) {
    return `<div class="np-evidence"><div class="np-section-label"><span>Evidence</span><small>${evidence.length} authorized sources</small></div><div class="np-evidence-grid">${evidence.slice(0,4).map((item) => `<article class="np-evidence-card"><span class="np-source-icon">${item.source_type.includes('calendar')?icons.clock:item.source_type.includes('policy')?icons.shield:icons.project}</span><div><strong>${escapeHTML(item.title)}</strong><p>${escapeHTML(item.content)}</p><small>${humanize(item.source_type)} · ${Math.round(item.confidence*100)}% · ${relative(item.observed_at)}</small></div></article>`).join('')}</div></div>`;
  }

  function answer() {
    if (!state.result) return `<div class="np-page np-ask-page">${askBox(true)}<div class="np-empty-state">${icons.search}<h2>Ask your company</h2><p>NoPing will find the right project, team, policy, and people delegates for you.</p></div></div>`;
    const r = state.result;
    return `<div class="np-page np-ask-page">${askBox(true)}<section class="np-answer is-${r.status}">
      <div class="np-answer-query"><span>You asked</span><p>${escapeHTML(r.query)}</p></div>
      <div class="np-answer-card"><div class="np-answer-head"><span class="np-answer-icon">${r.status==='refused'?icons.shield:icons.spark}</span><div><span>${escapeHTML(r.headline)}</span><h2>${escapeHTML(r.answer)}</h2></div></div>
      <div class="np-answer-facts"><span>${icons.check}${Math.round(r.confidence*100)}% confidence</span><span>${icons.clock}${escapeHTML(r.freshness_label)}</span><span class="${r.people_interrupted===0?'is-saved':'is-human'}">${r.people_interrupted} ${r.people_interrupted===1?'person':'people'} interrupted</span>${r.cached?'<span class="is-cached">Decision memory</span>':''}</div>
      ${r.security_findings?.length ? `<div class="np-security-banner">${icons.shield}<span><strong>Untrusted content blocked</strong><small>${escapeHTML(r.security_findings[0].reason)}</small></span></div>`:''}
      ${r.policy_result?`<div class="np-policy-result"><strong>Policy outcome</strong><span>${escapeHTML(r.policy_result)}</span></div>`:''}
      ${r.route?.length?routeTrace(r.route):''}
      ${r.evidence?.length?evidenceList(r.evidence):''}
      ${r.status==='escalated'?'<button class="np-primary-button np-decision-cta" type="button" data-view="needs">Open decision workflow</button>':''}
      </div></section></div>`;
  }

  function decisionCard(decision) {
    return `<article class="np-decision-card"><div class="np-decision-ribbon">Decision required</div><div class="np-decision-header"><span class="np-decision-icon">${icons.shield}</span><div><span>Project Atlas · Security</span><h2>${escapeHTML(decision.title)}</h2><p>${escapeHTML(decision.summary)}</p></div><span class="np-due">${icons.clock} Due in 2h</span></div>
      <div class="np-decision-context"><div><span>Customer value</span><strong>$200K</strong></div><div><span>Engineering</span><strong class="is-good">Ready</strong></div><div><span>Security</span><strong class="is-warn">Pending</strong></div><div><span>Control</span><strong>SEC-POL-12</strong></div></div>
      <label class="np-rationale"><span>Decision rationale</span><textarea id="decision-rationale" rows="2">SEC-184 must complete; revenue urgency does not justify bypassing the control.</textarea></label>
      <div class="np-decision-actions"><button class="np-ghost-button" data-resolve="discuss" data-id="${decision.id}">Discuss</button><button class="np-negative-button" data-resolve="rejected" data-id="${decision.id}">Reject exception</button><button class="np-primary-button" data-resolve="approved" data-id="${decision.id}">Approve exception</button></div></article>`;
  }

  function needs() {
    const decisions = state.bootstrap.needs_you || [];
    return `<div class="np-page"><div class="np-page-intro"><span>Attention inbox</span><h1>Needs you</h1><p>Only judgment, authority, private knowledge, and unresolved conflicts reach this page.</p></div>${decisions.length?`<div class="np-card-stack">${decisions.map(decisionCard).join('')}</div>`:`<div class="np-empty-state">${icons.check}<h2>Nothing needs you</h2><p>NoPing handled the routine questions without sending them here.</p></div>`}</div>`;
  }

  function organization(mode) {
    const b = state.bootstrap;
    if (mode === 'projects') {
      return `<div class="np-page"><div class="np-page-intro"><span>Living work graph</span><h1>Projects & teams</h1><p>Status updates are derived from work evidence, not manual check-ins.</p></div><div class="np-organization-grid">${b.projects.map((p)=>projectCard(p,b.work_states.find((s)=>s.entity_id===p.id))).join('')}</div></div>`;
    }
    const people = [
      ['Maya Patel','Overnight Customer Support','MP','Available','Customer context and support'],
      ['Sarah Chen','Security Lead','SC','OOO','Security authority delegated to Alex'],
      ['Alex Morgan','Staff Security Engineer','AM','Available','Acting Atlas approver'],
      ['Daniel Kim','Mobile Engineer','DK','Focus','AUTH-392 fix is in review'],
      ['Priya Shah','Senior Product Manager','PS','Available','Owns Project Atlas'],
    ];
    return `<div class="np-page"><div class="np-page-intro"><span>Permission-aware delegates</span><h1>People</h1><p>Each person has a logical delegate with scoped knowledge, availability, and authority.</p></div><div class="np-people-grid">${people.map(([name,title,av,status,detail])=>`<article class="np-person-card"><span class="np-person-avatar">${av}</span><div><h3>${name}</h3><p>${title}</p><small>${detail}</small></div><span class="np-person-status is-${status.toLowerCase()}">${status}</span></article>`).join('')}</div></div>`;
  }

  function registry() {
    const delegates = state.registry?.delegates || [];
    return `<div class="np-page"><div class="np-page-intro"><span>Enterprise fleet</span><h1>Agent registry</h1><p>Every delegate has an identity, capability boundary, data scope, status, and audit trail.</p></div>
    <div class="np-registry-summary"><div>${icons.network}<span><strong>${delegates.length}</strong><small>Registered delegates</small></span></div><div>${icons.shield}<span><strong>Zero trust</strong><small>Scopes checked per request</small></span></div><div><span class="np-registry-pulse"></span><span><strong>Healthy</strong><small>Gateway and routing</small></span></div></div>
    <div class="np-registry-table"><div class="np-registry-row is-header"><span>Delegate</span><span>Type</span><span>Capabilities</span><span>Data scope</span><span>Status</span></div>${delegates.map((d)=>`<div class="np-registry-row"><span><i>${escapeHTML(d.name.slice(0,2).toUpperCase())}</i><strong>${escapeHTML(d.name)}</strong><small>${escapeHTML(d.id)}</small></span><span><b>${humanize(d.kind)}</b></span><span>${d.capabilities.slice(0,2).map(humanize).join(' · ')}</span><span>${d.data_scopes.slice(0,2).join(' · ')}</span><span><em class="is-${d.status}"></em>${humanize(d.status)}</span></div>`).join('')}</div></div>`;
  }

  function audit() {
    return `<div class="np-page"><div class="np-page-intro"><span>Observability</span><h1>Audit trail</h1><p>See who asked, which delegates ran, what evidence was accessed, and where policy intervened.</p></div><div class="np-audit-list">${state.audit.length?state.audit.map((event)=>`<article class="np-audit-row"><span class="np-audit-icon ${event.event_type.includes('security')?'is-security':''}">${event.event_type.includes('security')?icons.shield:icons.audit}</span><div><span>${humanize(event.event_type)}</span><h3>${escapeHTML(event.summary)}</h3><small>Actor: ${escapeHTML(event.actor_id)} · Entities: ${escapeHTML(event.entity_ids.join(', '))}</small></div><time>${relative(event.created_at)}</time></article>`).join(''):`<div class="np-empty-audit">${icons.audit}<h3>No runs yet</h3><p>Ask the organization to generate a trace.</p></div>`}</div></div>`;
  }

  function mainContent() {
    if (state.error) return `<div class="np-page"><div class="np-error-banner">${escapeHTML(state.error)}</div>${home()}</div>`;
    switch (state.view) {
      case 'home': return home();
      case 'ask': return answer();
      case 'needs': return needs();
      case 'projects': return organization('projects');
      case 'people': return organization('people');
      case 'registry': return registry();
      case 'audit': return audit();
      default: return home();
    }
  }

  function render() {
    if (!state.bootstrap) return;
    app.className = '';
    app.innerHTML = `<div class="np-app">${sidebar()}<div class="np-main">${topbar()}<main class="np-content">${state.error?`<div class="np-error-banner">${escapeHTML(state.error)}</div>`:''}${mainContent()}</main></div></div><div class="harness-debug">PRODUCT HARNESS · Mattermost route: /noping · API: ${state.loading?'working':'ready'}</div>`;
    bind();
    document.body.dataset.ready = 'true';
  }

  function bind() {
    app.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => { state.view = button.dataset.view; render(); }));
    app.querySelectorAll('[data-query]').forEach((button) => button.addEventListener('click', () => void ask(button.dataset.query)));
    const form = document.getElementById('query-form');
    if (form) form.addEventListener('submit', (event) => { event.preventDefault(); const text = document.getElementById('query-text').value.trim(); if (text.length >= 3) void ask(text); });
    const reset = document.getElementById('reset-demo');
    if (reset) reset.addEventListener('click', async () => { await request('/v1/demo/reset',{method:'POST',body:'{}'}); state.result=null; state.view='home'; await refresh(); render(); });
    const user = document.getElementById('user-switcher');
    if (user) user.addEventListener('change', async () => { state.userId=user.value; await refresh(); render(); });
    app.querySelectorAll('[data-resolve]').forEach((button) => button.addEventListener('click', async () => {
      const rationale = document.getElementById('decision-rationale')?.value || 'Decision recorded by authorized reviewer.';
      await request(`/v1/decisions/${button.dataset.id}/resolve`, {method:'POST',body:JSON.stringify({actor_id:state.userId,status:button.dataset.resolve,rationale})});
      await refresh(); render();
    }));
  }

  async function runScenario() {
    const scenario = params.get('scenario');
    if (!scenario) return;
    await request('/v1/demo/reset', {method:'POST',body:'{}'});
    await refresh();
    if (scenario === 'factual' || scenario === 'security') {
      await ask('Why has Atlas not shipped?', 'maya');
    } else if (scenario === 'status') {
      await ask('Who is handling the Atlas blocker tonight?', 'maya');
    } else if (scenario === 'restricted') {
      await ask("What is Sarah's salary?", 'maya');
    } else if (scenario === 'decision' || scenario === 'needs') {
      await ask('Can we bypass security review for the $200K customer?', 'maya');
      state.userId = 'alex'; state.view = 'needs'; await refresh(); render();
    } else if (scenario === 'registry') {
      state.view = 'registry'; render();
    } else if (scenario === 'audit') {
      await ask('Why has Atlas not shipped?', 'maya'); state.view='audit'; render();
    } else if (scenario === 'memory') {
      const first = await request('/v1/query',{method:'POST',body:JSON.stringify({requester_id:'maya',text:'Can we bypass security review for the $200K customer?'})});
      await request(`/v1/decisions/${first.decision_id}/resolve`,{method:'POST',body:JSON.stringify({actor_id:'alex',status:'rejected',rationale:'SEC-184 must complete; revenue urgency does not waive the control.'})});
      state.result = await request('/v1/query',{method:'POST',body:JSON.stringify({requester_id:'maya',text:'Should we make an Atlas security exception for this customer?'})});
      state.userId='maya'; state.view='ask'; await refresh(); render();
    }
  }

  async function initialize() {
    try {
      await refresh();
      render();
      await runScenario();
    } catch (error) {
      app.className = 'np-loading-screen is-error';
      app.innerHTML = `<strong>NoPing could not start</strong><small>${escapeHTML(error.message)}</small>`;
      document.body.dataset.ready = 'error';
    }
  }

  void initialize();
})();
