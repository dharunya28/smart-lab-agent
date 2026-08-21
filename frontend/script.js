/**
 * Smart Laboratory Resource Agent - Frontend Orchestration Controller 2.0
 * Next-Gen Mission Control Architecture
 * Handles Multi-Agent Stepper, Telemetry Stream, Theme & Color Palette Switching,
 * Mock Simulation, Backend POST /api/request Integration, and Alerts.
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements - Theme & Mode
  const htmlRoot = document.documentElement;
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const sunIcon = themeToggleBtn?.querySelector('.sun-icon');
  const moonIcon = themeToggleBtn?.querySelector('.moon-icon');

  const paletteSwatches = document.getElementById('paletteSwatches');
  const paletteButtons = document.querySelectorAll('.palette-dot-btn');

  const mockModeToggle = document.getElementById('mockModeToggle');
  const modeLabel = document.getElementById('modeLabel');

  // DOM Elements - Request Form
  const requestForm = document.getElementById('requestForm');
  const promptInput = document.getElementById('promptInput');
  const clearTextBtn = document.getElementById('clearTextBtn');
  const submitBtn = document.getElementById('submitBtn');
  const resetBtn = document.getElementById('resetBtn');
  const btnSpinner = submitBtn.querySelector('.btn-spinner');
  const btnText = submitBtn.querySelector('.btn-text');

  // Pipeline & Telemetry
  const pipelineStatus = document.getElementById('pipelineStatus');
  const telemetryStream = document.getElementById('telemetryStream');
  const notificationArea = document.getElementById('notificationArea');
  const toastContainer = document.getElementById('toastContainer');

  // Result Voucher Elements
  const emptyResultState = document.getElementById('emptyResultState');
  const populatedResult = document.getElementById('populatedResult');
  const bookingStatusBadge = document.getElementById('bookingStatusBadge');
  const statusHighlightBox = document.getElementById('statusHighlightBox');
  const highlightIcon = document.getElementById('highlightIcon');
  const highlightTitle = document.getElementById('highlightTitle');
  const highlightSubtitle = document.getElementById('highlightSubtitle');

  const resEquipment = document.getElementById('resEquipment');
  const resDate = document.getElementById('resDate');
  const resTime = document.getElementById('resTime');
  const resStatus = document.getElementById('resStatus');
  const resReason = document.getElementById('resReason');

  const alternativeBox = document.getElementById('alternativeBox');
  const altText = document.getElementById('altText');
  const acceptAltBtn = document.getElementById('acceptAltBtn');
  const copyResultBtn = document.getElementById('copyResultBtn');
  const newRequestBtn = document.getElementById('newRequestBtn');

  // Agent Map
  const agents = {
    orchestrator: {
      el: document.getElementById('agent-orchestrator'),
      badge: document.getElementById('agent-orchestrator')?.querySelector('.node-badge'),
      log: document.getElementById('agent-orchestrator')?.querySelector('.node-log'),
    },
    inventory: {
      el: document.getElementById('agent-inventory'),
      badge: document.getElementById('agent-inventory')?.querySelector('.node-badge'),
      log: document.getElementById('agent-inventory')?.querySelector('.node-log'),
    },
    scheduling: {
      el: document.getElementById('agent-scheduling'),
      badge: document.getElementById('agent-scheduling')?.querySelector('.node-badge'),
      log: document.getElementById('agent-scheduling')?.querySelector('.node-log'),
    },
    conflict: {
      el: document.getElementById('agent-conflict'),
      badge: document.getElementById('agent-conflict')?.querySelector('.node-badge'),
      log: document.getElementById('agent-conflict')?.querySelector('.node-log'),
    },
    auditor: {
      el: document.getElementById('agent-auditor'),
      badge: document.getElementById('agent-auditor')?.querySelector('.node-badge'),
      log: document.getElementById('agent-auditor')?.querySelector('.node-log'),
    },
  };

  // State
  let isProcessing = false;
  let currentResultData = null;

  // Preset Scenario Data for Demo Testing
  const presetScenarios = {
    success: {
      prompt: 'I need 2 Arduino Uno tomorrow from 10 AM to 12 PM',
      equipment: '2x Arduino Uno Rev3',
      date: getRelativeDate(1),
      time: '10:00 AM - 12:00 PM',
      status: 'Booking Successful',
      statusType: 'success',
      reason: 'Sufficient inventory available (14 units in stock). Workbench #4 is open and reservation meets standard student safety guidelines.',
      agentLogs: {
        orchestrator: 'Extracted: [2x Arduino Uno, Tomorrow 10:00-12:00]. Dispatched to pipeline.',
        inventory: 'Catalog verified: 14 units in Station A. 2 units locked.',
        scheduling: 'Calendar slot 10:00 AM - 12:00 PM is OPEN on Workbench #4.',
        conflict: 'Zero scheduling or device conflicts detected. Fast-track bypass.',
        auditor: 'Compliance checked: Standard student low-voltage tier approved.',
      },
    },
    conflict: {
      prompt: 'Book 3 Digital Oscilloscopes for Friday 2 PM - 4 PM',
      equipment: '3x Rigol 100MHz Digital Oscilloscope',
      date: 'Next Friday',
      time: '02:00 PM - 04:00 PM',
      status: 'Alternative Slot Found',
      statusType: 'warning',
      alternative: 'Friday 04:00 PM - 06:00 PM on Bench #2 or Thursday 02:00 PM - 04:00 PM on Bench #1',
      reason: 'Conflict detected: Friday 2:00 PM - 4:00 PM is reserved for "EE-302 Lab". Found verified alternative availability on Friday 4:00 PM - 6:00 PM.',
      agentLogs: {
        orchestrator: 'Extracted resource intent: 3 Oscilloscopes on Friday afternoon.',
        inventory: 'Inventory verified: 3 oscilloscopes available in stock.',
        scheduling: 'CONFLICT DETECTED: Friday 2 PM - 4 PM slot reserved by "EE-302 Lab".',
        conflict: 'Arbitration engine solved clash. Alternate: Friday 4 PM - 6 PM.',
        auditor: 'Audited user credentials: Valid for oscilloscope usage.',
      },
    },
    low_stock: {
      prompt: 'Need 10 Raspberry Pi 4 boards today at 3 PM',
      equipment: '10x Raspberry Pi 4 Model B (4GB)',
      date: 'Today',
      time: '03:00 PM - 05:00 PM',
      status: 'Booking Rejected',
      statusType: 'danger',
      reason: 'Insufficient inventory: Lab currently only has 4 Raspberry Pi 4 boards unreserved. Request for 10 boards exceeds active capacity.',
      agentLogs: {
        orchestrator: 'Requested 10 units of Raspberry Pi 4 for immediate session.',
        inventory: 'FAILED: Only 4 units available in inventory (6 units short).',
        scheduling: 'Slot holds suspended due to inventory shortage.',
        conflict: 'No partial batch split authorized by user policy.',
        auditor: 'Logged as unfulfillable due to resource exhaustion.',
      },
    },
    auditor_reject: {
      prompt: 'Reserve Gas Chromatography Mass Spectrometer overnight without faculty supervisor',
      equipment: '1x GC-MS Triple Quadrupole Spectrometer',
      date: 'Tonight',
      time: '10:00 PM - 06:00 AM',
      status: 'Booking Rejected',
      statusType: 'danger',
      reason: 'Auditor Policy Rejection: High-hazard Class IV equipment requires certified faculty supervision and pre-approved hazardous waste handling protocol.',
      agentLogs: {
        orchestrator: 'Parsed high-hazard instrument request for overnight run.',
        inventory: 'Hardware is present in Cleanroom C.',
        scheduling: 'Overnight slot available on calendar.',
        conflict: 'Skipped - escalated to compliance assessment.',
        auditor: 'VIOLATION: Missing Faculty Supervisor accreditation for Level 4 hazardous equipment.',
      },
    },
  };

  // -------------------------------------------------------------------------
  // COLOR PALETTE SWITCHER
  // -------------------------------------------------------------------------
  const paletteNames = {
    emerald: 'Bio-Tech Emerald & Cyan',
    cobalt: 'Cyber Cobalt & Oceanic Blue',
    violet: 'Electric Violet & Indigo',
    amber: 'Solar Amber & Industrial Gold',
    crimson: 'Neon Crimson & Cyber Rose',
  };

  const savedPalette = localStorage.getItem('smartLab_palette') || 'emerald';
  setPalette(savedPalette, false);

  paletteButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const palette = btn.getAttribute('data-palette');
      if (palette) {
        setPalette(palette, true);
      }
    });
  });

  function setPalette(paletteKey, notify = true) {
    htmlRoot.setAttribute('data-palette', paletteKey);
    localStorage.setItem('smartLab_palette', paletteKey);

    paletteButtons.forEach((b) => {
      if (b.getAttribute('data-palette') === paletteKey) {
        b.classList.add('active');
      } else {
        b.classList.remove('active');
      }
    });

    if (notify) {
      const name = paletteNames[paletteKey] || paletteKey;
      showToast(`Palette: ${name}`, 'info');
      appendTelemetry('THEME', `Switched color palette to ${name}.`, 'system');
    }
  }

  // -------------------------------------------------------------------------
  // THEME TOGGLE (Dark / Light) - Default to Light
  // -------------------------------------------------------------------------
  const savedTheme = localStorage.getItem('smartLab_theme') || 'light';
  htmlRoot.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const currentTheme = htmlRoot.getAttribute('data-theme') || 'light';
      const nextTheme = currentTheme === 'light' ? 'dark' : 'light';
      htmlRoot.setAttribute('data-theme', nextTheme);
      localStorage.setItem('smartLab_theme', nextTheme);
      updateThemeIcon(nextTheme);
      showToast(`Switched to ${nextTheme === 'dark' ? 'Dark Mode' : 'Light Mode'}`, 'info');
      appendTelemetry('THEME', `Switched lighting mode to ${nextTheme.toUpperCase()}.`, 'system');
    });
  }

  function updateThemeIcon(theme) {
    if (sunIcon && moonIcon) {
      if (theme === 'dark') {
        sunIcon.classList.remove('hidden');
        moonIcon.classList.add('hidden');
      } else {
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
      }
    }
  }

  // -------------------------------------------------------------------------
  // EVENT LISTENERS
  // -------------------------------------------------------------------------

  // Mode Toggle
  mockModeToggle.addEventListener('change', (e) => {
    modeLabel.textContent = e.target.checked ? 'Mock Mode' : 'Live API Mode';
    showToast(
      e.target.checked 
        ? 'Demo Simulation Mode active' 
        : 'Live API Mode active (POST /api/request)', 
      'info'
    );
    appendTelemetry('SYSTEM', `Switched runtime mode to ${e.target.checked ? 'Mock Simulation' : 'Live API (/api/request)'}`, 'system');
  });

  // Clear text button
  clearTextBtn?.addEventListener('click', () => {
    promptInput.value = '';
    promptInput.focus();
  });

  // Preset Buttons
  document.querySelectorAll('.preset-pill').forEach((btn) => {
    btn.addEventListener('click', () => {
      const type = btn.getAttribute('data-type');
      if (presetScenarios[type]) {
        promptInput.value = presetScenarios[type].prompt;
        promptInput.focus();
      }
    });
  });

  // Keyboard shortcut: Ctrl + Enter / Cmd + Enter
  promptInput.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      requestForm.dispatchEvent(new Event('submit'));
    }
  });

  // Reset Form
  resetBtn.addEventListener('click', () => {
    promptInput.value = '';
    resetAgentsUI();
    hideResult();
    clearNotifications();
    appendTelemetry('USER', 'Session reset by user.', 'info');
  });

  newRequestBtn?.addEventListener('click', () => {
    promptInput.value = '';
    promptInput.focus();
    resetAgentsUI();
    hideResult();
    clearNotifications();
  });

  // Accept Alternative Slot
  acceptAltBtn?.addEventListener('click', () => {
    showBanner('success', 'Alternative Slot Confirmed', 'Your booking has been updated and locked for the recommended alternative slot.');
    showToast('Alternative slot confirmed & locked in lab calendar', 'success');
    appendTelemetry('CONFLICT', 'Alternative slot accepted by user. Calendar lock dispatched.', 'success');
    
    resStatus.textContent = 'Confirmed (Alternative Accepted)';
    bookingStatusBadge.className = 'status-stamp stamp-success';
    bookingStatusBadge.textContent = 'CONFIRMED (ALT)';
    alternativeBox.classList.add('hidden');
  });

  // Copy Results
  copyResultBtn?.addEventListener('click', () => {
    if (!currentResultData) return;
    const text = `Smart Lab Reservation Voucher:\nEquipment: ${currentResultData.equipment}\nDate: ${currentResultData.date}\nTime: ${currentResultData.time}\nStatus: ${currentResultData.status}\nReason: ${currentResultData.reason}`;
    navigator.clipboard.writeText(text).then(() => {
      showToast('Reservation voucher copied to clipboard!', 'info');
    }).catch(() => {
      showToast('Failed to copy to clipboard', 'danger');
    });
  });

  // Form Submit Handler
  requestForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const promptText = promptInput.value.trim();
    if (!promptText || isProcessing) return;

    setLoading(true);
    clearNotifications();
    resetAgentsUI();
    hideResult();

    appendTelemetry('USER', `New Prompt: "${promptText}"`, 'info');

    const isMock = mockModeToggle.checked;

    if (isMock) {
      await runMockSimulation(promptText);
    } else {
      await callLiveApi(promptText);
    }

    setLoading(false);
  });

  // -------------------------------------------------------------------------
  // MOCK MULTI-AGENT SIMULATION ENGINE
  // -------------------------------------------------------------------------
  async function runMockSimulation(promptText) {
    setPipelineState('running', 'Orchestrating Pipeline');

    const scenario = matchScenario(promptText);

    // Step 1: Orchestrator
    setAgentState('orchestrator', 'processing', 'Parsing intent, entities, and routing sub-tasks...');
    appendTelemetry('ORCHESTRATOR', 'Analyzing natural language syntax & extracting constraints...', 'system');
    await sleep(600);
    setAgentState('orchestrator', 'approved', scenario.agentLogs.orchestrator);
    appendTelemetry('ORCHESTRATOR', scenario.agentLogs.orchestrator, 'success');

    // Step 2: Inventory Agent
    setAgentState('inventory', 'processing', 'Querying hardware catalog and workbench stock levels...');
    appendTelemetry('INVENTORY', 'Running catalog inventory lookup...', 'info');
    await sleep(700);
    const invState = scenario.statusType === 'danger' && scenario.agentLogs.inventory.includes('FAILED') ? 'flagged' : 'approved';
    setAgentState('inventory', invState, scenario.agentLogs.inventory);
    appendTelemetry('INVENTORY', scenario.agentLogs.inventory, invState === 'flagged' ? 'danger' : 'success');

    if (invState === 'flagged') {
      setAgentState('scheduling', 'idle', 'Standby (insufficient inventory).');
      setAgentState('conflict', 'idle', 'Standby.');
      setAgentState('auditor', 'flagged', scenario.agentLogs.auditor);
      appendTelemetry('AUDITOR', scenario.agentLogs.auditor, 'danger');
      renderResult(scenario);
      triggerNotificationForScenario(scenario);
      setPipelineState('done', 'Completed (Rejected)');
      return;
    }

    // Step 3: Scheduling Agent
    setAgentState('scheduling', 'processing', 'Checking lab timetable and slot reservations...');
    appendTelemetry('SCHEDULING', 'Evaluating workbench calendars & timetable overlap...', 'info');
    await sleep(700);
    const isConflict = scenario.statusType === 'warning' || scenario.statusType === 'info';
    setAgentState('scheduling', isConflict ? 'conflict' : 'approved', scenario.agentLogs.scheduling);
    appendTelemetry('SCHEDULING', scenario.agentLogs.scheduling, isConflict ? 'warning' : 'success');

    // Step 4: Conflict Resolver
    setAgentState('conflict', 'processing', 'Evaluating calendar conflicts and resource substitutes...');
    await sleep(650);
    if (isConflict) {
      setAgentState('conflict', 'conflict', scenario.agentLogs.conflict);
      appendTelemetry('CONFLICT_RESOLVER', scenario.agentLogs.conflict, 'warning');
      showBanner('warning', 'Conflict Detected', 'Requested time slot is occupied. Searching for closest alternate availability...');
      await sleep(500);
    } else {
      setAgentState('conflict', 'approved', scenario.agentLogs.conflict);
      appendTelemetry('CONFLICT_RESOLVER', scenario.agentLogs.conflict, 'success');
    }

    // Step 5: Auditor
    setAgentState('auditor', 'processing', 'Checking lab safety protocols and user clearance...');
    appendTelemetry('AUDITOR', 'Verifying user safety credentials and laboratory compliance policy...', 'info');
    await sleep(600);
    const isAuditorReject = scenario.agentLogs.auditor.includes('VIOLATION');
    setAgentState('auditor', isAuditorReject ? 'flagged' : 'approved', scenario.agentLogs.auditor);
    appendTelemetry('AUDITOR', scenario.agentLogs.auditor, isAuditorReject ? 'danger' : 'success');

    // Pipeline Done
    setPipelineState('done', 'Pipeline Complete');
    renderResult(scenario);
    triggerNotificationForScenario(scenario);
  }

  // -------------------------------------------------------------------------
  // LIVE BACKEND API INTEGRATION (POST /api/request)
  // -------------------------------------------------------------------------
  async function callLiveApi(promptText) {
    setPipelineState('running', 'Calling POST /api/request');
    appendTelemetry('API', 'Dispatching JSON payload to POST /api/request...', 'system');
    setAgentState('orchestrator', 'processing', 'Sending request payload to POST /api/request...');

    try {
      const response = await fetch('/api/request', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: promptText }),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      appendTelemetry('API', 'Response received from server.', 'success');

      if (data.agents) {
        Object.keys(data.agents).forEach((agentKey) => {
          if (agents[agentKey]) {
            const agentData = data.agents[agentKey];
            setAgentState(agentKey, agentData.status || 'approved', agentData.log || 'Completed');
            appendTelemetry(agentKey.toUpperCase(), agentData.log || 'Completed', 'info');
          }
        });
      } else {
        setAgentState('orchestrator', 'approved', 'Live API request processed successfully.');
        setAgentState('inventory', 'approved', 'Inventory checked via backend.');
        setAgentState('scheduling', 'approved', 'Timetable slot allocated.');
        setAgentState('conflict', 'approved', 'No conflicts reported by backend.');
        setAgentState('auditor', 'approved', 'Compliance verification passed.');
      }

      const resultObj = {
        equipment: data.equipment || data.resource || 'Lab Equipment',
        date: data.date || 'Scheduled Date',
        time: data.time || data.timeSlot || 'Scheduled Time',
        status: data.status || 'Booking Successful',
        statusType: mapStatusToType(data.status),
        reason: data.reason || data.message || 'Request successfully processed by backend service.',
        alternative: data.alternative || null,
      };

      renderResult(resultObj);
      triggerNotificationForScenario(resultObj);
      setPipelineState('done', 'API Complete');

    } catch (err) {
      console.warn('Backend API offline or errored, falling back to simulated flow:', err);
      showToast('Backend offline - falling back to demo simulation', 'warning');
      appendTelemetry('API', 'POST /api/request unreachable. Executing simulated multi-agent fallback.', 'warning');
      await runMockSimulation(promptText);
    }
  }

  // -------------------------------------------------------------------------
  // UI & STATE HELPERS
  // -------------------------------------------------------------------------

  function setAgentState(agentKey, state, logMessage) {
    const agent = agents[agentKey];
    if (!agent || !agent.el) return;

    agent.el.className = 'agent-node';
    agent.badge.className = 'node-badge';

    switch (state) {
      case 'processing':
        agent.el.classList.add('state-active');
        agent.badge.classList.add('badge-processing');
        agent.badge.textContent = 'Analyzing';
        break;
      case 'approved':
        agent.el.classList.add('state-success');
        agent.badge.classList.add('badge-approved');
        agent.badge.textContent = 'Approved';
        break;
      case 'conflict':
        agent.el.classList.add('state-warning');
        agent.badge.classList.add('badge-conflict');
        agent.badge.textContent = 'Conflict';
        break;
      case 'flagged':
        agent.el.classList.add('state-danger');
        agent.badge.classList.add('badge-flagged');
        agent.badge.textContent = 'Flagged';
        break;
      case 'idle':
      default:
        agent.badge.classList.add('badge-idle');
        agent.badge.textContent = 'Idle';
        break;
    }

    if (logMessage && agent.log) {
      agent.log.textContent = logMessage;
    }
  }

  function setPipelineState(mode, label) {
    pipelineStatus.textContent = label;
    if (mode === 'running') {
      pipelineStatus.className = 'pipeline-state-badge state-running';
    } else {
      pipelineStatus.className = 'pipeline-state-badge';
    }
  }

  function resetAgentsUI() {
    Object.keys(agents).forEach((key) => {
      setAgentState(key, 'idle', 'Standby...');
    });
    setPipelineState('idle', 'Standby');
  }

  function renderResult(data) {
    currentResultData = data;
    emptyResultState.classList.add('hidden');
    populatedResult.classList.remove('hidden');

    resEquipment.textContent = data.equipment;
    resDate.textContent = data.date;
    resTime.textContent = data.time;
    resStatus.textContent = data.status;
    resReason.textContent = data.reason;

    // Highlight Card
    statusHighlightBox.className = `voucher-hero outcome-${data.statusType}`;
    
    // Status Badge & Icons
    if (data.statusType === 'success') {
      bookingStatusBadge.className = 'status-stamp stamp-success';
      bookingStatusBadge.textContent = 'CONFIRMED';
      highlightTitle.textContent = 'Resource Reserved';
      highlightSubtitle.textContent = 'Equipment allocated and workbench calendar locked.';
      highlightIcon.innerHTML = getStatusIconSvg('success');
    } else if (data.statusType === 'warning' || data.statusType === 'info') {
      bookingStatusBadge.className = 'status-stamp stamp-warning';
      bookingStatusBadge.textContent = 'CONFLICT RESOLVED';
      highlightTitle.textContent = 'Alternative Slot Proposed';
      highlightSubtitle.textContent = 'Initial slot conflicted; alternative availability ready.';
      highlightIcon.innerHTML = getStatusIconSvg('warning');
    } else {
      bookingStatusBadge.className = 'status-stamp stamp-danger';
      bookingStatusBadge.textContent = 'REJECTED';
      highlightTitle.textContent = 'Request Not Approved';
      highlightSubtitle.textContent = 'Blocked by inventory exhaustion or auditor safety policy.';
      highlightIcon.innerHTML = getStatusIconSvg('danger');
    }

    // Alternative Box
    if (data.alternative) {
      alternativeBox.classList.remove('hidden');
      altText.textContent = data.alternative;
    } else {
      alternativeBox.classList.add('hidden');
    }
  }

  function hideResult() {
    emptyResultState.classList.remove('hidden');
    populatedResult.classList.add('hidden');
    bookingStatusBadge.className = 'status-stamp stamp-neutral';
    bookingStatusBadge.textContent = 'AWAITING REQUEST';
    currentResultData = null;
  }

  function triggerNotificationForScenario(scenario) {
    if (scenario.statusType === 'success') {
      showBanner('success', 'Booking Successful', `Reserved ${scenario.equipment} for ${scenario.date} (${scenario.time}).`);
      showToast('Booking successfully confirmed!', 'success');
    } else if (scenario.statusType === 'warning' || scenario.statusType === 'info') {
      showBanner('info', 'Alternative Slot Found', `Original time conflicted. Recommended alternative: ${scenario.alternative}`);
      showToast('Alternative slot found for your request', 'info');
    } else if (scenario.statusType === 'danger') {
      showBanner('danger', 'Booking Rejected', scenario.reason);
      showToast('Booking request rejected by Lab Agent', 'danger');
    }
  }

  function showBanner(type, title, message) {
    const banner = document.createElement('div');
    banner.className = `notification-banner ${type}`;
    
    banner.innerHTML = `
      <div class="notif-content">
        <div class="notif-icon">${getStatusIconSvg(type)}</div>
        <div>
          <strong>${escapeHtml(title)}:</strong> ${escapeHtml(message)}
        </div>
      </div>
      <button type="button" class="notif-close" aria-label="Dismiss notification">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    `;

    banner.querySelector('.notif-close').addEventListener('click', () => {
      banner.remove();
    });

    notificationArea.appendChild(banner);
  }

  function clearNotifications() {
    notificationArea.innerHTML = '';
  }

  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <div class="toast-icon">${getStatusIconSvg(type)}</div>
      <div class="toast-msg">${escapeHtml(message)}</div>
    `;

    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 250);
    }, 4000);
  }

  function appendTelemetry(agentTag, message, level = 'info') {
    const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false });
    const entry = document.createElement('div');
    entry.className = `log-entry log-${level}`;
    entry.innerHTML = `
      <span class="log-time">[${timeStr}] [${escapeHtml(agentTag)}]</span>
      <span class="log-msg">${escapeHtml(message)}</span>
    `;
    telemetryStream.appendChild(entry);
    telemetryStream.scrollTop = telemetryStream.scrollHeight;
  }

  function setLoading(loading) {
    isProcessing = loading;
    submitBtn.disabled = loading;
    if (loading) {
      btnSpinner.classList.remove('hidden');
      btnText.textContent = 'Orchestrating Sub-Agents...';
    } else {
      btnSpinner.classList.add('hidden');
      btnText.textContent = 'Execute Multi-Agent Request';
    }
  }

  function matchScenario(promptText) {
    const lower = promptText.toLowerCase();

    if (lower.includes('spectrometer') || lower.includes('hazard') || lower.includes('overnight') || lower.includes('unsupervised')) {
      return { ...presetScenarios.auditor_reject, prompt: promptText };
    }
    if (lower.includes('10') || lower.includes('raspberry pi') || lower.includes('out of stock') || lower.includes('shortage')) {
      return { ...presetScenarios.low_stock, prompt: promptText };
    }
    if (lower.includes('oscilloscope') || lower.includes('conflict') || lower.includes('friday') || lower.includes('alt')) {
      return { ...presetScenarios.conflict, prompt: promptText };
    }
    if (lower.includes('arduino') || lower.includes('uno')) {
      return { ...presetScenarios.success, prompt: promptText };
    }

    // Dynamic fallback for custom inputs
    return {
      prompt: promptText,
      equipment: extractEquipmentFromPrompt(promptText) || 'Custom Lab Equipment',
      date: extractDateFromPrompt(promptText) || 'Tomorrow',
      time: extractTimeFromPrompt(promptText) || '10:00 AM - 12:00 PM',
      status: 'Booking Successful',
      statusType: 'success',
      reason: `Automated multi-agent allocation approved based on active catalog stock and open timetable schedule.`,
      agentLogs: {
        orchestrator: `Parsed custom request parameters from input.`,
        inventory: 'Stock count verified: Available units allocated.',
        scheduling: 'Timetable verified on Workstation #1.',
        conflict: 'Checked schedule collisions: Zero overlap.',
        auditor: 'User access credentials and safety guidelines verified.',
      },
    };
  }

  function extractEquipmentFromPrompt(text) {
    const match = text.match(/(?:need|book|reserve|for)\s+([0-9]+\s+[A-Za-z0-9\s]+?)(?:\s+tomorrow|\s+today|\s+from|\s+on|\s+at|$)/i);
    return match ? match[1].trim() : null;
  }

  function extractDateFromPrompt(text) {
    if (/tomorrow/i.test(text)) return getRelativeDate(1);
    if (/today/i.test(text)) return 'Today';
    const dayMatch = text.match(/\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b/i);
    return dayMatch ? dayMatch[1] : 'Tomorrow';
  }

  function extractTimeFromPrompt(text) {
    const timeMatch = text.match(/(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*(?:to|-)\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))/i);
    return timeMatch ? `${timeMatch[1]} - ${timeMatch[2]}` : '10:00 AM - 12:00 PM';
  }

  function mapStatusToType(statusStr) {
    if (!statusStr) return 'success';
    const s = statusStr.toLowerCase();
    if (s.includes('success') || s.includes('confirm') || s.includes('approved')) return 'success';
    if (s.includes('conflict') || s.includes('alt') || s.includes('slot')) return 'warning';
    if (s.includes('reject') || s.includes('cancel') || s.includes('fail') || s.includes('denied')) return 'danger';
    return 'success';
  }

  function getStatusIconSvg(type) {
    if (type === 'success') {
      return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
    }
    if (type === 'warning' || type === 'info') {
      return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
    }
    return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
  }

  function getRelativeDate(daysAhead) {
    const d = new Date();
    d.setDate(d.getDate() + daysAhead);
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, (m) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;',
    }[m]));
  }
});
