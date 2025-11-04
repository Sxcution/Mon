document.addEventListener('DOMContentLoaded', function () {
      // --- GLOBAL SCRIPT ---
      const urlParams = new URLSearchParams(window.location.search);
      const tab = urlParams.get('tab');
      if (tab) {
            const tabTrigger = document.querySelector(`button[data-bs-target="#${tab}-tool-pane"], button[data-bs-target="#${tab}-tab-pane"]`);
            if (tabTrigger) new bootstrap.Tab(tabTrigger).show();
      }
      document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tabEl => {
            tabEl.addEventListener('shown.bs.tab', function (event) {
                  if (event.target.id.includes('-v-pills-')) return;
                  const newUrl = new URL(window.location);
                  const tabId = event.target.dataset.bsTarget.replace('#', '').replace('-tool-pane', '').replace('-tab-pane', '');
                  if (tabId === 'home') newUrl.searchParams.delete('tab');
                  else newUrl.searchParams.set('tab', tabId);
                  history.pushState({}, '', newUrl);
            });
      });
      else if (t === 'error') { h.classList.add('bg-danger', 'text-white'); i.textContent = 'Lỗi'; }
            else { h.classList.add('bg-info', 'text-white'); i.textContent = title; }
            new bootstrap.Toast(e).show();
      }

      // --- PASSWORD MANAGER SCRIPT ---
      (() => {
            const pane = document.getElementById('password-tool-pane');
            if (!pane) return;
            const filterForm = document.getElementById('pwd-filter-form');
            const typeFilter = document.getElementById('pwd-type-filter');
            typeFilter.addEventListener('change', () => filterForm.submit());
            pane.querySelectorAll('.pwd-toggle-visibility').forEach(button => {
                  button.addEventListener('click', function () {
                        const passwordSpan = this.closest('.password-cell').querySelector('.password-text');
                        const icon = this.querySelector('i');
                        if (passwordSpan.style.webkitTextSecurity === 'disc') {
                              passwordSpan.style.webkitTextSecurity = 'none';
                              icon.classList.replace('bi-eye-fill', 'bi-eye-slash-fill');
                        } else {
                              passwordSpan.style.webkitTextSecurity = 'disc';
                              icon.classList.replace('bi-eye-slash-fill', 'bi-eye-fill');
                        }
                  });
            });
            pane.querySelectorAll('.pwd-btn-copy').forEach(button => {
                  button.addEventListener('click', function () {
                        navigator.clipboard.writeText(this.dataset.password).then(() => {
                              const originalIcon = this.innerHTML;
                              this.innerHTML = '<i class="bi bi-check-lg text-success"></i>';
                              setTimeout(() => { this.innerHTML = originalIcon; }, 1500);
                        });
                  });
            });
            const editModal = document.getElementById('pwd-editAccountModal');
            editModal.addEventListener('show.bs.modal', function (event) {
                  const button = event.relatedTarget;
                  const form = document.getElementById('pwd-editForm');
                  form.action = `/password/update/${button.dataset.id}`;
                  document.getElementById('pwd-editType').value = button.dataset.type;
                  document.getElementById('pwd-editUsername').value = button.dataset.username;
                  document.getElementById('pwd-editPassword').value = button.dataset.password;
                  document.getElementById('pwd-editTwofa').value = button.dataset.twofa;
                  document.getElementById('pwd-editNotes').value = button.dataset.notes;
            });

            // START: New Password Badge Color Change Logic
            const passwordBadgeMenu = document.getElementById('password-badge-context-menu');
            const passwordTable = pane.querySelector('.table tbody');
            let currentBadgeType = null;

            passwordTable.addEventListener('contextmenu', function(e) {
                const badge = e.target.closest('.badge[data-type]');
                if (badge) {
                    e.preventDefault();
                    e.stopPropagation(); // Prevent the dashboard menu from opening
                    currentBadgeType = badge.dataset.type;
                    passwordBadgeMenu.style.top = `${e.clientY}px`;
                    passwordBadgeMenu.style.left = `${e.clientX}px`;
                    passwordBadgeMenu.style.display = 'block';
                }
            });

            passwordBadgeMenu.addEventListener('click', async function(e) {
                const colorSwatch = e.target.closest('.color-palette span');
                if (colorSwatch && currentBadgeType) {
                    const newColor = colorSwatch.dataset.color;
                    
                    try {
                        const response = await fetch('/password/types/update_color', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ name: currentBadgeType, color: newColor })
                        });
                        const result = await response.json();
                        if (!response.ok) throw new Error(result.error || 'Update failed');
                        
                        // Update color on the fly
                        const dynamicStyle = document.getElementById('dynamic-type-styles');
                        const rule = `.table .badge[data-type="${currentBadgeType}"] { background-color: ${newColor} !important; }`;
                        
                        // This is a simpler way to update styles: just add the new rule.
                        // The browser will apply the latest rule if selectors are the same.
                        dynamicStyle.sheet.insertRule(rule, dynamicStyle.sheet.cssRules.length);

                    } catch (error) {
                        showToast(`Lỗi: ${error.message}`, 'error');
                    } finally {
                        passwordBadgeMenu.style.display = 'none';
                        currentBadgeType = null;
                    }
                }
            });

            document.addEventListener('click', function(e) {
                if (!passwordBadgeMenu.contains(e.target) && !e.target.closest('.badge[data-type]')) {
                    passwordBadgeMenu.style.display = 'none';
                }
            });
            // END: New Password Badge Color Change Logic
      })();

      // --- FACEBOOK MANAGER SCRIPT ---
      (() => {
            const pane = document.getElementById('facebook-tool-pane');
            if (!pane) return;
            const editModal = document.getElementById('fb-editAccountModal');
            editModal.addEventListener('show.bs.modal', function (event) {
                  const button = event.relatedTarget;
                  const form = document.getElementById('fb-editForm');
                  form.action = `/facebook/update/${button.dataset.id}`;
                  document.getElementById('fb-editNickname').value = button.dataset.nickname;
                  document.getElementById('fb-editUrl').value = button.dataset.url;
                  document.getElementById('fb-editNotes').value = button.dataset.notes;
            });
      })();

      // --- TELEGRAM MANAGER SCRIPT ---
      (async () => {
            const telegramPane = document.getElementById('telegram-tool-pane');
            if (!telegramPane) return;
            // --- START: Load and manage saved parameters ---
            const coreInput = document.getElementById('tg-core-input');
            const delaySessionInput = document.getElementById('tg-delay-session-input');
            const delayBatchInput = document.getElementById('tg-delay-batch-input');
            const adminSwitch = document.getElementById('tg-admin-reply-switch');
            const adminDelayInput = document.getElementById('tg-admin-delay-input');

            // Load values on startup
            coreInput.value = localStorage.getItem('tg_core') || '5';
            delaySessionInput.value = localStorage.getItem('tg_delay_session') || '10';
            delayBatchInput.value = localStorage.getItem('tg_delay_batch') || '600';
            adminSwitch.checked = localStorage.getItem('tg_admin_enabled') === 'true';
            adminDelayInput.value = localStorage.getItem('tg_admin_delay') || '10';
            
            // Set initial enabled/disabled state for the admin delay input
            adminDelayInput.disabled = !adminSwitch.checked;

            // Add event listeners to save changes
            coreInput.addEventListener('change', () => localStorage.setItem('tg_core', coreInput.value));
            delaySessionInput.addEventListener('change', () => localStorage.setItem('tg_delay_session', delaySessionInput.value));
            delayBatchInput.addEventListener('change', () => localStorage.setItem('tg_delay_batch', delayBatchInput.value));
            adminDelayInput.addEventListener('change', () => localStorage.setItem('tg_admin_delay', adminDelayInput.value));
            adminSwitch.addEventListener('change', () => {
                localStorage.setItem('tg_admin_enabled', adminSwitch.checked);
                // Enable or disable the input based on the switch state
                adminDelayInput.disabled = !adminSwitch.checked;
            });
            // --- END: Load and manage saved parameters ---

            let tg_pollingInterval = null, tg_currentTaskId = null, tg_lastCheckedCheckbox = null,
                  tg_currentTaskConfig = {}, tg_completedInTask = new Set(), tg_allGroups = [];

            async function tg_handleRunStopClick(event) {
                  const button = event.currentTarget;
                  if (button.dataset.taskRunning === 'true') {
                        if (!tg_currentTaskId) return;
                        try {
                              await fetch(`/telegram/api/stop-task/${tg_currentTaskId}`, { method: 'POST' });
                        } catch (error) { showToast(`Lỗi khi dừng: ${error.message}`, 'error'); }
                  } else {
                        const isGroupTaskSelected = tg_currentTaskConfig && tg_currentTaskConfig.task && ['seedingGroup', 'joinGroup', 'buffViewIcon'].includes(tg_currentTaskConfig.task);
                        if (isGroupTaskSelected) {
                              await tg_handleRunGroupTask();
                        } else {
                              await tg_handleCheckLive();
                        }
                  }
            }

            async function tg_handleRunGroupTask() {
                  const selectedFilenames = Array.from(telegramPane.querySelectorAll('.tg-session-checkbox:checked:not(#tg-selectAllCheckbox):not(#tg-selectAllCheckbox-right)')).map(cb => cb.closest('tr').dataset.filename);
                  let sessionsForTask = selectedFilenames;
                  if (sessionsForTask.length === 0 && tg_currentTaskConfig.task === 'seedingGroup' && tg_currentTaskConfig.session_filenames?.length > 0) {
                        sessionsForTask = tg_currentTaskConfig.session_filenames;
                        showToast('Không có session nào được chọn. Sử dụng danh sách đã lưu trong cấu hình.', 'info');
                  }
                  if (sessionsForTask.length === 0) return showToast('Vui lòng chọn hoặc lưu session trong cấu hình.', 'error');
                  
                  const payload = {
                      groupId: document.getElementById('tg-group-session-select').value,
                      task: tg_currentTaskConfig.task,
                      config: tg_currentTaskConfig,
                      filenames: sessionsForTask,
                      core: parseInt(document.getElementById('tg-core-input').value, 10),
                      delay_per_session: parseInt(document.getElementById('tg-delay-session-input').value, 10),
                      delay_between_batches: parseInt(document.getElementById('tg-delay-batch-input').value, 10),
                      admin_enabled: document.getElementById('tg-admin-reply-switch').checked,
                      admin_delay: parseInt(document.getElementById('tg-admin-delay-input').value, 10)
                  };

                  if (!payload.groupId) return showToast('Vui lòng chọn nhóm session.', 'error');

                  const taskDesc = telegramPane.querySelector('#tg-group-task-cards .card.card-selected .card-title')?.textContent.trim() || "tác vụ";
                  tg_startTaskUI(sessionsForTask.length, `Bắt đầu "${taskDesc}"...`);
                  try {
                        const response = await fetch('/telegram/api/run-task', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                        if (!response.ok) throw new Error((await response.json()).error || 'Lỗi server.');
                        const { task_id } = await response.json();
                        tg_currentTaskId = task_id;
                        tg_setRunStopButtonState('running');
                        tg_pollTaskStatus(tg_currentTaskId);
                  } catch (error) { showToast(`Lỗi: ${error.message}`, 'error'); tg_setRunStopButtonState('idle'); }
            }

            // START: Replacement for tg_handleCheckLive
            async function tg_handleCheckLive() {
                  if (tg_pollingInterval) return showToast('Tác vụ khác đang chạy.', 'error');

                  const groupId = document.getElementById('tg-group-session-select').value;
                  if (!groupId) return showToast('Vui lòng chọn nhóm.', 'error');

                  const selectedFilenames = Array.from(telegramPane.querySelectorAll('.tg-session-checkbox:checked:not(#tg-selectAllCheckbox):not(#tg-selectAllCheckbox-right)')).map(cb => cb.closest('tr').dataset.filename);
                  if (selectedFilenames.length === 0) return showToast('Vui lòng chọn ít nhất một session.', 'error');

                  // Deselect any group task cards to avoid confusion
                  telegramPane.querySelectorAll('#tg-group-task-cards .card').forEach(d => d.classList.remove('card-selected'));
                  tg_currentTaskConfig = {};

                  const payload = {
                        groupId: groupId,
                        task: "check-live", // Set the correct task name
                        filenames: selectedFilenames,
                        core: parseInt(document.getElementById('tg-core-input').value, 10),
                        delay_per_session: parseInt(document.getElementById('tg-delay-session-input').value, 10),
                        delay_between_batches: parseInt(document.getElementById('tg-delay-batch-input').value, 10),
                        admin_enabled: false, // Not applicable for check-live
                        admin_delay: 0      // Not applicable for check-live
                  };

                  tg_startTaskUI(selectedFilenames.length, `Bắt đầu Check Live...`);

                  try {
                        // Call the correct, generic run-task endpoint
                        const response = await fetch('/telegram/api/run-task', {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify(payload)
                        });

                        if (!response.ok) throw new Error((await response.json()).error || 'Lỗi server.');

                        const { task_id } = await response.json();
                        tg_currentTaskId = task_id;
                        tg_setRunStopButtonState('running');
                        tg_pollTaskStatus(tg_currentTaskId);

                  } catch (error) {
                        showToast(`Lỗi: ${error.message}`, 'error');
                        tg_setRunStopButtonState('idle');
                  }
            }
            // END: Replacement for tg_handleCheckLive

            function tg_startTaskUI(total, msg) {
                  tg_completedInTask.clear();
                  showToast(msg, 'info');
                  document.getElementById('tg-status-success-count').textContent = '0';
                  document.getElementById('tg-status-failed-count').textContent = '0';
                  document.getElementById('tg-status-progress-text').textContent = `0/${total}`;
                  telegramPane.querySelectorAll('.tg-session-checkbox:checked').forEach(cb => {
                        const row = cb.closest('tr');
                        if (row) row.cells[6].innerHTML = `<span class="status-checking">Đang xử lý...</span>`;
                  });
            }

            function tg_setRunStopButtonState(state) {
                  const button = document.getElementById('tg-runStopBtn');
                  const statusText = document.getElementById('tg-status-progress-text');
                  if (state === 'running') {
                        button.dataset.taskRunning = 'true';
                        statusText.dataset.taskRunning = 'true';
                        button.innerHTML = `<i class="bi bi-stop-fill"></i> Stop`;
                        button.classList.replace('btn-primary', 'btn-danger');
                  } else {
                        button.dataset.taskRunning = 'false';
                        statusText.dataset.taskRunning = 'false';
                        button.innerHTML = `<i class="bi bi-play-fill"></i> Run`;
                        button.classList.replace('btn-danger', 'btn-primary');
                  }
            }

            function tg_pollTaskStatus(taskId) {
                  if (tg_pollingInterval) clearInterval(tg_pollingInterval);
                  tg_pollingInterval = setInterval(async () => {
                        if (!tg_currentTaskId) { clearInterval(tg_pollingInterval); return; }
                        try {
                              const response = await fetch(`/telegram/api/task-status/${taskId}`);
                              if (!response.ok) { clearInterval(tg_pollingInterval); tg_setRunStopButtonState('idle'); return; }
                              const task = await response.json();
                              tg_updateUiWithTaskProgress(task);
                              if (task.status === 'completed' || task.status === 'stopped') {
                                    clearInterval(tg_pollingInterval);
                                    tg_pollingInterval = null; tg_currentTaskId = null;
                                    showToast(task.status === 'completed' ? 'Hoàn tất tác vụ!' : 'Tác vụ đã dừng.', 'success');
                                    document.getElementById('tg-status-progress-text').textContent = "Idle";
                                    tg_setRunStopButtonState('idle');
                                    tg_updateSessionCountDisplay();
                              }
                        } catch (error) { clearInterval(tg_pollingInterval); console.error('Lỗi khi polling:', error); tg_setRunStopButtonState('idle'); }
                  }, 1500);
            }

            function tg_updateUiWithTaskProgress(task) {
                  document.getElementById('tg-status-progress-text').textContent = `${task.processed}/${task.total}`;
                  document.getElementById('tg-status-success-count').textContent = task.success;
                  document.getElementById('tg-status-failed-count').textContent = task.failed;

                  // Update status for completed sessions in this poll
                  task.results.forEach(result => {
                        const row = telegramPane.querySelector(`tr[data-filename="${result.filename}"]`);
                        if (!row) return;
                        
                        tg_completedInTask.add(result.filename); // Mark this session as processed
                        
                        if (result.full_name) row.cells[3].textContent = result.full_name;
                        if (result.username) row.cells[4].textContent = result.username;
                        row.cells[5].innerHTML = result.is_live ? `<i class="bi bi-check-circle-fill text-success"></i>` : `<i class="bi bi-x-circle-fill text-danger"></i>`;
                        row.cells[6].innerHTML = `<span class="${result.is_live ? 'text-success' : 'text-danger'}">${result.status_text}</span>`;
                  });

                  // Handle global task messages, including the new countdown logic
                  if (task.messages && task.messages.length > 0) {
                        const latestMessage = task.messages[task.messages.length - 1];
                        document.getElementById('tg-status-progress-text').textContent = latestMessage;

                        // --- NEW COUNTDOWN LOGIC ---
                        const countdownMatch = latestMessage.match(/Đang chờ đợt tiếp...\s*(\d+s)/);
                        if (countdownMatch) {
                            const countdownText = `Chờ: ${countdownMatch[1]}`;
                            // Find all checked sessions that have NOT been processed yet
                            telegramPane.querySelectorAll('.tg-session-checkbox:checked').forEach(cb => {
                                const row = cb.closest('tr');
                                if (row) {
                                    const filename = row.dataset.filename;
                                    if (filename && !tg_completedInTask.has(filename)) {
                                        // This is a waiting session, so update its status cell
                                        const statusCell = row.cells[6];
                                        if (statusCell) {
                                            statusCell.innerHTML = `<span class="text-info">${countdownText}</span>`;
                                        }
                                    }
                                }
                            });
                        }
                        // --- END OF NEW LOGIC ---
                  }
            }

            async function tg_loadGroups() {
                  try {
                        const r = await fetch('/telegram/api/groups');
                        tg_allGroups = await r.json();
                        const s = document.getElementById('tg-group-session-select');
                        s.innerHTML = '<option selected disabled>-- Chọn nhóm --</option>';
                        tg_allGroups.forEach(g => {
                              if (g.name !== 'Adminsession') s.add(new Option(g.name, g.id));
                        });
                        const storedId = localStorage.getItem('tg_selectedGroupId');
                        if (storedId && tg_allGroups.some(g => g.id == storedId)) {
                              s.value = storedId;
                              await s.dispatchEvent(new Event('change'));
                        }
                  } catch (e) { showToast('Không thể tải nhóm Telegram.', 'error'); }
            }

            async function tg_handleGroupSelect(e) {
                  tg_lastCheckedCheckbox = null;
                  const groupId = e.target.value;
                  localStorage.setItem('tg_selectedGroupId', groupId);
                  const leftBody = document.getElementById('tg-sessions-table-left-body');
                  const rightBody = document.getElementById('tg-sessions-table-right-body');
                  leftBody.innerHTML = `<tr><td colspan="7" class="text-center"><div class="spinner-border spinner-border-sm"></div></td></tr>`;
                  rightBody.innerHTML = '';
                  try {
                        const res = await fetch(`/telegram/api/groups/${groupId}/sessions`);
                        tg_renderSessions(await res.json());
                  } catch (e) {
                        leftBody.innerHTML = `<tr><td colspan="7" class="text-danger text-center">Lỗi tải session</td></tr>`;
                  }
            }

            function tg_renderSessions(sessions) {
                  const leftBody = document.getElementById('tg-sessions-table-left-body'), rightBody = document.getElementById('tg-sessions-table-right-body');
                  leftBody.innerHTML = rightBody.innerHTML = '';
                  document.getElementById('tg-total-sessions-count').textContent = sessions.length;
                  const rowHtml = (s, i) => {
                        const liveIcon = s.is_live === null ? '<i class="bi bi-question-circle-fill text-secondary"></i>' : (s.is_live ? '<i class="bi bi-check-circle-fill text-success"></i>' : '<i class="bi bi-x-circle-fill text-danger"></i>');
                        const statusClass = s.is_live === null ? 'text-secondary' : (s.is_live ? 'text-success' : 'text-danger');
                        return `<tr data-filename="${s.filename}"><td><input class="form-check-input tg-session-checkbox" type="checkbox"></td><td>${i + 1}</td><td>${s.phone}</td><td class="d-none d-md-table-cell" style="cursor: text;">${s.full_name || 'N/A'}</td><td class="d-none d-md-table-cell" style="cursor: text;">${s.username || ''}</td><td class="text-center">${liveIcon}</td><td><span class="${statusClass}">${s.status_text || 'Sẵn sàng'}</span></td></tr>`;
                  };
                  const mid = Math.ceil(sessions.length / 2);
                  leftBody.innerHTML = sessions.slice(0, mid).map((s, i) => rowHtml(s, i)).join('');
                  rightBody.innerHTML = sessions.slice(mid).map((s, i) => rowHtml(s, mid + i)).join('');
                  tg_updateSessionCountDisplay();
            }

            function tg_updateSessionCountDisplay() {
                  const statusEl = document.getElementById('tg-status-progress-text');
                  if (statusEl && statusEl.dataset.taskRunning !== 'true') {
                        const selected = telegramPane.querySelectorAll('.tg-session-checkbox:checked').length;
                        const total = telegramPane.querySelectorAll('.tg-session-checkbox').length;
                        statusEl.textContent = selected > 0 ? `${selected}/${total} Selected` : 'Idle';
                  }
            }

            window.tg_openConfigModal = async (taskId, event) => {
                  if (event) event.stopPropagation();
                  await tg_selectCardAndLoadConfig(taskId);
                  const modalId = `tg-${taskId}Modal`;
                  const configModal = document.getElementById(modalId);
                  if (configModal) {
                        if (taskId === 'joinGroup') tg_populateJoinGroupModal();
                        if (taskId === 'seedingGroup') await tg_populateSeedingGroupModal();
                        new bootstrap.Modal(configModal).show();
                  }
            };

            async function tg_selectCardAndLoadConfig(taskId) {
                  telegramPane.querySelectorAll('#tg-group-task-cards .card').forEach(d => d.classList.remove('card-selected'));
                  const card = telegramPane.querySelector(`#tg-group-task-cards .card[data-task-id="${taskId}"]`);
                  if (card) card.classList.add('card-selected');
                  localStorage.setItem('tg_lastSelectedTask', taskId);
                  try {
                        const response = await fetch(`/telegram/api/config/${taskId}`);
                        tg_currentTaskConfig = response.ok ? await response.json() : {};
                        tg_currentTaskConfig.task = taskId;
                  } catch (error) { tg_currentTaskConfig = { task: taskId }; }
            }

            function tg_populateJoinGroupModal() { document.getElementById('tg-joinGroupLinks').value = (tg_currentTaskConfig?.links || []).join('\n'); }

            async function tg_populateSeedingGroupModal() {
                  const { group_links, messages, admin_messages, selected_reactions, admin_session_file } = tg_currentTaskConfig;
                  document.getElementById('tg-seedingGroupLinks').value = (group_links || []).join('\n');
                  document.getElementById('tg-seedingGroupMessages').value = (messages || []).join('\n');
                  document.getElementById('tg-seedingAdminMessages').value = (admin_messages || []).join('\n');
                  telegramPane.querySelectorAll('.tg-reaction-checkbox').forEach(cb => { cb.checked = Array.isArray(selected_reactions) && selected_reactions.includes(cb.value); });
                  const adminSelect = document.getElementById('tg-seedingAdminSessionSelect');
                  adminSelect.innerHTML = '<option value="">-- Đang tải... --</option>';
                  const adminGroup = tg_allGroups.find(g => g.name === 'Adminsession');
                  if (!adminGroup) { adminSelect.innerHTML = '<option value="">-- Không có nhóm Adminsession --</option>'; return; }
                  try {
                        const res = await fetch(`/telegram/api/groups/${adminGroup.id}/sessions`);
                        const adminSessions = await res.json();
                        adminSelect.innerHTML = '<option value="">-- Không sử dụng Admin --</option>';
                        adminSessions.forEach(s => adminSelect.add(new Option(s.phone || s.filename, s.filename)));
                        if (admin_session_file) adminSelect.value = admin_session_file;
                  } catch (error) { adminSelect.innerHTML = '<option value="">-- Lỗi tải session --</option>'; }
            }

            async function tg_saveJoinGroupConfig() {
                  const links = document.getElementById('tg-joinGroupLinks').value.trim().split(/\r?\n/).filter(Boolean);
                  const configToSave = { links };
                  try {
                        await fetch('/telegram/api/config/joinGroup', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(configToSave) });
                        tg_currentTaskConfig = { ...tg_currentTaskConfig, ...configToSave };
                        bootstrap.Modal.getInstance(document.getElementById('tg-joinGroupModal')).hide();
                        showToast('Đã lưu cấu hình Join Group!', 'success');
                  } catch (error) { showToast(`Lỗi: ${error.message}`, 'error'); }
            }

            async function tg_saveSeedingGroupConfig() {
                  const configToSave = {
                        group_links: document.getElementById('tg-seedingGroupLinks').value.trim().split(/\r?\n/).filter(Boolean),
                        messages: document.getElementById('tg-seedingGroupMessages').value.trim().split(/\r?\n/).filter(Boolean),
                        admin_messages: document.getElementById('tg-seedingAdminMessages').value.trim().split(/\r?\n/).filter(Boolean),
                        admin_session_file: document.getElementById('tg-seedingAdminSessionSelect').value,
                        session_filenames: Array.from(telegramPane.querySelectorAll('.tg-session-checkbox:checked:not(#tg-selectAllCheckbox):not(#tg-selectAllCheckbox-right)')).map(cb => cb.closest('tr').dataset.filename),
                        selected_reactions: Array.from(telegramPane.querySelectorAll('.tg-reaction-checkbox:checked')).map(cb => cb.value)
                  };
                  try {
                        await fetch('/telegram/api/config/seedingGroup', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(configToSave) });
                        tg_currentTaskConfig = { ...tg_currentTaskConfig, ...configToSave };
                        bootstrap.Modal.getInstance(document.getElementById('tg-seedingGroupModal')).hide();
                        showToast('Đã lưu cấu hình Seeding Group!', 'success');
                  } catch (error) { showToast(`Lỗi: ${error.message}`, 'error'); }
            }

            async function tg_handleSaveGroup(event) {
                  event.preventDefault();
                  const form = document.getElementById('tg-addSessionForm');
                  const nameInput = document.getElementById('tg-groupName');
                  const filesInput = document.getElementById('tg-sessionFiles');
                  if (!nameInput.value.trim() || !filesInput.files.length) return showToast('Vui lòng nhập tên nhóm và chọn file.', 'error');
                  const formData = new FormData(form);
                  try {
                        const r = await fetch('/telegram/api/groups', { method: 'POST', body: formData });
                        const j = await r.json();
                        if (!r.ok) throw new Error(j.error || 'Lỗi server.');
                        showToast(j.message || 'Thành công!', 'success');
                        bootstrap.Modal.getInstance(document.getElementById('tg-addSessionModal')).hide();
                        form.reset();
                        await tg_loadGroups();
                  } catch (e) { showToast(`Lỗi: ${e.message}`, 'error'); }
            }

            async function tg_handleUploadAdminSession() {
                  const files = this.files;
                  if (!files.length) return;
                  const formData = new FormData();
                  for (const file of files) formData.append('admin_session_files', file);
                  try {
                        const response = await fetch('/telegram/api/upload-admin-sessions', { method: 'POST', body: formData });
                        const result = await response.json();
                        if (!response.ok) throw new Error(result.error);
                        showToast(result.message, 'success');
                        await tg_loadGroups();
                        await tg_populateSeedingGroupModal();
                  } catch (error) { showToast(`Lỗi: ${error.message}`, 'error'); }
            }

            async function tg_resumeActiveTasks() {
                  try {
                        const response = await fetch('/telegram/api/active-tasks');
                        if (!response.ok) return;
                        const activeTasks = await response.json();
                        const taskIds = Object.keys(activeTasks);
                        if (taskIds.length > 0) {
                              const taskIdToResume = taskIds[0];
                              const taskData = activeTasks[taskIdToResume];
                              showToast(`Khôi phục trạng thái tác vụ: ${taskData.task_name}`, 'info');
                              tg_currentTaskId = taskIdToResume;
                              document.getElementById('tg-status-success-count').textContent = taskData.success;
                              document.getElementById('tg-status-failed-count').textContent = taskData.failed;
                              document.getElementById('tg-status-progress-text').textContent = `${taskData.processed}/${taskData.total}`;
                              const groupSelect = document.getElementById('tg-group-session-select');
                              if (groupSelect.querySelector(`option[value="${taskData.group_id}"]`)) {
                                    if (groupSelect.value !== taskData.group_id) {
                                          groupSelect.value = taskData.group_id;
                                          await groupSelect.dispatchEvent(new Event('change'));
                                    }
                              }
                              tg_setRunStopButtonState('running');
                              tg_pollTaskStatus(taskIdToResume);
                        }
                  } catch (error) { console.error("Lỗi khi khôi phục tác vụ:", error); }
            }

            document.getElementById('telegram-tool-tab').addEventListener('shown.bs.tab', async () => {
                  if (tg_allGroups.length === 0) {
                        await tg_loadGroups();
                        await tg_resumeActiveTasks();
                  }
            }, { once: true });

            if (telegramPane.classList.contains('active')) {
                  if (tg_allGroups.length === 0) {
                        await tg_loadGroups();
                        await tg_resumeActiveTasks();
                  }
            }

            document.getElementById('tg-runStopBtn').addEventListener('click', tg_handleRunStopClick);
            document.getElementById('tg-checkLiveBtn').addEventListener('click', tg_handleCheckLive);
            document.getElementById('tg-group-session-select').addEventListener('change', tg_handleGroupSelect);
            document.getElementById('tg-saveGroupBtn').addEventListener('click', tg_handleSaveGroup);
            document.getElementById('tg-saveJoinGroupConfigBtn').addEventListener('click', tg_saveJoinGroupConfig);
            document.getElementById('tg-saveSeedingGroupConfigBtn').addEventListener('click', tg_saveSeedingGroupConfig);
            document.getElementById('tg-uploadAdminSession').addEventListener('change', tg_handleUploadAdminSession);

            document.getElementById('tg-shuffleMessagesBtn').addEventListener('click', () => {
                  const memberTextarea = document.getElementById('tg-seedingGroupMessages');
                  const adminTextarea = document.getElementById('tg-seedingAdminMessages');
                  const shuffleTextarea = (textarea) => {
                        let lines = textarea.value.split('\n').filter(line => line.trim() !== '');
                        for (let i = lines.length - 1; i > 0; i--) {
                              const j = Math.floor(Math.random() * (i + 1));
                              [lines[i], lines[j]] = [lines[j], lines[i]];
                        }
                        textarea.value = lines.join('\n');
                  };
                  shuffleTextarea(memberTextarea);
                  shuffleTextarea(adminTextarea);
                  showToast('Đã xáo trộn tin nhắn!', 'success');
            });

            document.getElementById('tg-group-task-cards').addEventListener('click', e => {
                  const card = e.target.closest('.card[data-task-id]');
                  if (card && !e.target.closest('button')) {
                        tg_selectCardAndLoadConfig(card.dataset.taskId);
                  }
            });

            document.getElementById('tg-session-tables-container').addEventListener('click', e => {
                  const checkbox = e.target;

                  // First, handle the specific "Select All" case
                  if (checkbox.id === 'tg-selectAllCheckbox') {
                      const allSessionCheckboxes = telegramPane.querySelectorAll('.tg-session-checkbox:not(#tg-selectAllCheckbox)');
                      allSessionCheckboxes.forEach(cb => {
                          if (!cb.disabled) {
                              cb.checked = checkbox.checked;
                          }
                      });
                      const rightSelectAll = document.getElementById('tg-selectAllCheckbox-right');
                      if (rightSelectAll) {
                          rightSelectAll.checked = checkbox.checked;
                      }
                      tg_updateSessionCountDisplay();

                  // THEN, handle clicks on individual session checkboxes
                  } else if (checkbox.classList.contains('tg-session-checkbox')) {
                      if (e.shiftKey && tg_lastCheckedCheckbox) {
                          const allCheckboxes = Array.from(telegramPane.querySelectorAll('.tg-session-checkbox:not(#tg-selectAllCheckbox):not(#tg-selectAllCheckbox-right)'));
                          const start = allCheckboxes.indexOf(tg_lastCheckedCheckbox);
                          const end = allCheckboxes.indexOf(checkbox);
                          
                          if (start !== -1 && end !== -1) {
                              const lower = Math.min(start, end);
                              const upper = Math.max(start, end);
                              for (let i = lower; i <= upper; i++) {
                                  allCheckboxes[i].checked = checkbox.checked;
                              }
                          }
                      }
                      tg_lastCheckedCheckbox = checkbox;
                      tg_updateSessionCountDisplay();
                  }
            });

            document.getElementById('tg-addSessionModal').addEventListener('show.bs.modal', async () => {
                  const listEl = document.getElementById('tg-existing-groups-list');
                  listEl.innerHTML = `<div class="text-center"><div class="spinner-border spinner-border-sm"></div></div>`;
                  try {
                        const r = await fetch('/telegram/api/groups');
                        const groups = await r.json();
                        listEl.innerHTML = groups.map(g => `<div class="d-flex justify-content-between align-items-center p-2 border-bottom"><span>${g.name}</span><button class="btn btn-sm btn-outline-danger tg-delete-group-btn" data-group-id="${g.id}"><i class="bi bi-trash-fill"></i></button></div>`).join('') || '<p class="text-muted text-center">Chưa có nhóm nào.</p>';
                  } catch (e) { listEl.innerHTML = `<div class="text-danger text-center">Lỗi tải nhóm.</div>`; }
            });

            document.getElementById('tg-existing-groups-list').addEventListener('click', async e => {
                  const deleteBtn = e.target.closest('.tg-delete-group-btn');
                  if (deleteBtn) {
                        const groupId = deleteBtn.dataset.groupId;
                        window.confirmDeleteAction(async () => {
                              try {
                                    const res = await fetch(`/telegram/api/groups/${groupId}`, { method: 'DELETE' });
                                    if (!res.ok) throw new Error("Lỗi server");
                                    deleteBtn.closest('.d-flex').remove();
                                    await tg_loadGroups();
                              } catch (err) { showToast('Lỗi xóa nhóm', 'error'); }
                        }, 'Bạn có chắc muốn xóa nhóm này?');
                        return;
                  }
            });

            const proxyModalEl = document.getElementById('tg-proxyModal');
            const proxyTextarea = document.getElementById('tg-proxy-list');
            const saveProxyBtn = document.getElementById('tg-save-proxy-btn');
            const proxyEnableCheckbox = document.getElementById('tg-proxy-enabled');

            if (proxyModalEl) {
                proxyModalEl.addEventListener('show.bs.modal', async () => {
                    try {
                        const response = await fetch('/telegram/api/proxies');
                        const config = await response.json();
                        proxyTextarea.value = (config.proxies || []).join('\n');
                        proxyEnableCheckbox.checked = config.enabled || false;
                    } catch (error) {
                        showToast('Lỗi tải cấu hình proxy.', 'error');
                    }
                });

                saveProxyBtn.addEventListener('click', async () => {
                    try {
                        const payload = {
                            enabled: proxyEnableCheckbox.checked,
                            proxies: proxyTextarea.value
                        };
                        const response = await fetch('/telegram/api/proxies', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(payload)
                        });
                        const result = await response.json();
                        if (!response.ok) throw new Error(result.error || 'Lỗi server');
                        showToast(result.message, 'success');
                        bootstrap.Modal.getInstance(proxyModalEl).hide();
                    } catch (error) {
                        showToast(`Lỗi lưu proxy: ${error.message}`, 'error');
                    }
                });
            }

            // --- START: NEW FUNCTION TO ADD ---
            function tg_makeCellEditable(cell, field, filename) {
                const originalText = cell.textContent.trim();
                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'form-control form-control-sm';
                input.value = originalText;
                
                cell.innerHTML = '';
                cell.appendChild(input);
                input.focus();
                input.select();

                const saveChanges = async () => {
                    const newValue = input.value.trim();
                    if (newValue === originalText) {
                        cell.textContent = originalText;
                        return;
                    }

                    const statusCell = cell.closest('tr').cells[6];
                    const oldStatusHTML = statusCell.innerHTML;
                    statusCell.innerHTML = `<span class="text-info">Updating...</span>`;
                    showToast(`Updating ${field}...`, 'info');

                    try {
                        const groupId = document.getElementById('tg-group-session-select').value;
                        const response = await fetch(`/telegram/api/update-session-info`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                group_id: groupId,
                                filename: filename,
                                field: field,
                                value: newValue
                            })
                        });

                        const result = await response.json();
                        if (!response.ok) throw new Error(result.error || 'Unknown error');

                        cell.textContent = result.updated_value;
                        if (field === 'username' && result.updated_full_name) {
                            cell.closest('tr').cells[3].textContent = result.updated_full_name;
                        }
                        statusCell.innerHTML = `<span class="text-success">Success!</span>`;
                        showToast(result.message, 'success');

                    } catch (error) {
                        cell.textContent = originalText;
                        statusCell.innerHTML = oldStatusHTML;
                        showToast(`Error: ${error.message}`, 'error');
                    }
                };

                input.addEventListener('blur', saveChanges);
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        input.blur();
                    } else if (e.key === 'Escape') {
                        cell.textContent = originalText;
                        input.removeEventListener('blur', saveChanges);
                        input.blur();
                    }
                });
            }
            // --- END: NEW FUNCTION TO ADD ---

            // --- START: NEW EVENT LISTENER TO ADD ---
            document.getElementById('tg-session-tables-container').addEventListener('dblclick', (e) => {
                const cell = e.target.closest('td');
                if (!cell) return;
                
                const tr = cell.closest('tr');
                const filename = tr.dataset.filename;
                if (!filename) return;

                const cellIndex = cell.cellIndex;
                let field = null;

                if (cellIndex === 3) { // Full Name column
                    field = 'full_name';
                } else if (cellIndex === 4) { // Username column
                    field = 'username';
                }
                
                if (field) {
                    tg_makeCellEditable(cell, field, filename);
                }
            });
            // --- END: NEW EVENT LISTENER TO ADD ---

            // --- START: MODIFICATION FOR tg_renderSessions ---
            function tg_renderSessions(sessions) {
                const leftBody = document.getElementById('tg-sessions-table-left-body'), rightBody = document.getElementById('tg-sessions-table-right-body');
                leftBody.innerHTML = rightBody.innerHTML = '';
                document.getElementById('tg-total-sessions-count').textContent = sessions.length;
                const rowHtml = (s, i) => {
                    const liveIcon = s.is_live === null ? '<i class="bi bi-question-circle-fill text-secondary"></i>' : (s.is_live ? '<i class="bi bi-check-circle-fill text-success"></i>' : '<i class="bi bi-x-circle-fill text-danger"></i>');
                    const statusClass = s.is_live === null ? 'text-secondary' : (s.is_live ? 'text-success' : 'text-danger');
                    // MODIFY THE RETURN STATEMENT TO THE FOLLOWING:
                    return `<tr data-filename="${s.filename}"><td><input class="form-check-input tg-session-checkbox" type="checkbox"></td><td>${i + 1}</td><td>${s.phone}</td><td class="d-none d-md-table-cell" style="cursor: text;">${s.full_name || 'N/A'}</td><td class="d-none d-md-table-cell" style="cursor: text;">${s.username || ''}</td><td class="text-center">${liveIcon}</td><td><span class="${statusClass}">${s.status_text || 'Sẵn sàng'}</span></td></tr>`;
                };
                const mid = Math.ceil(sessions.length / 2);
                leftBody.innerHTML = sessions.slice(0, mid).map((s, i) => rowHtml(s, i)).join('');
                rightBody.innerHTML = sessions.slice(mid).map((s, i) => rowHtml(s, mid + i)).join('');
                tg_updateSessionCountDisplay();
            }
            // --- END: MODIFICATION FOR tg_renderSessions ---
      })();

      // --- IMAGE EDITOR SCRIPT ---
      (() => {
            const imageEditorPane = document.getElementById('image-editor-tool-pane');
            if (!imageEditorPane) return;

            // === DOM Elements ===
            const uploadInput = document.getElementById('ie-image-upload');
            const uploadBtn = document.getElementById('ie-image-upload-btn');
            const thumbnailsContainer = document.getElementById('ie-uploaded-thumbnails');
            const layoutContainer = document.getElementById('ie-layout-templates');
            const saveBtn = document.getElementById('ie-save-btn');
            const spaceInput = document.getElementById('ie-space-input');
            const colorInput = document.getElementById('ie-color-input');
            const imageCountSpan = document.getElementById('ie-image-count');
            const resetBtn = document.getElementById('ie-reset-btn');
            const addTextBtn = document.getElementById('ie-add-text-btn');
            const canvasWrapper = document.getElementById('ie-canvas-wrapper');
            const canvas = document.getElementById('ie-canvas');
            const ctx = canvas.getContext('2d');
            const placeholder = document.getElementById('ie-canvas-placeholder');
            const textToolbar = document.getElementById('ie-text-toolbar');
            const fontSelect = document.getElementById('ie-font-select');
            const fontSizeInput = document.getElementById('ie-font-size-input');
            const textColorInput = document.getElementById('ie-color-text-input');
            const textAlignBtns = document.getElementById('ie-text-align-btns');
            const textStyleBtns = document.getElementById('ie-text-style-btns');

            // === State Variables ===
            let ie_uploadedFilesInfo = []; // Stores {url, originalFilename}
            let ie_sessionId = null;
            let ie_draggedThumbnailIndex = null;
            let textObjects = [];
            let backgroundImage = null;
            let selectedTextIndex = -1;
            let isDragging = false;
            let isResizing = false;
            let dragOffsetX = 0, dragOffsetY = 0;
            let activeResizeHandle = null;
            const handleSize = 8;
            // FIX: Add a state variable for rainbow border instead of relying on input value
            let ie_isRainbowBorder = false;

            const layoutsByCount = {
                  1: { 'layout_1_1': '<div class="cell"></div>' },
                  2: {
                        'layout_2_h': '<div class="cell"></div><div class="cell"></div>',
                        'layout_2_v': '<div class="cell"></div><div class="cell"></div>'
                  },
                  3: {
                        'layout_3_top_1': '<div class="row1"><div class="cell"></div></div><div class="row2"><div class="cell"></div><div class="cell"></div></div>',
                        'layout_3_left_1': '<div class="col1"><div class="cell"></div></div><div class="col2"><div class="cell"></div><div class="cell"></div></div>',
                        'layout_3_v': '<div class="cell"></div><div class="cell"></div><div class="cell"></div>'
                  },
                  4: {
                        'layout_4_2x2': '<div class="cell"></div><div class="cell"></div><div class="cell"></div><div class="cell"></div>',
                        'layout_4_left_1': '<div class="col1"><div class="cell"></div></div><div class="col2"><div class="cell"></div><div class="cell"></div><div class="cell"></div></div>'
                  },
                  5: {
                        'layout_5_2_3': '<div class="row1"><div class="cell"></div><div class="cell"></div></div><div class="row2"><div class="cell"></div><div class="cell"></div><div class="cell"></div></div>',
                        'layout_5_left_1_4': '<div class="col1"><div class="cell"></div></div><div class="col2"><div class="cell"></div><div class="cell"></div><div class="cell"></div><div class="cell"></div></div>'
                  }
            };
            const fonts = [
                  'Arial', 'Verdana', 'Georgia', 'Times New Roman', 'Courier New',
                  'Impact', 'Comic Sans MS', 'Trebuchet MS',
                  'Lobster', 'Pacifico', 'Anton', 'Oswald', 'Roboto'
            ];

            // === Main Functions ===
            function init() {
                  populateFonts();
                  setupEventListeners();
            }

            function resetEditor() {
                  ie_uploadedFilesInfo = [];
                  ie_sessionId = null;
                  textObjects = [];
                  backgroundImage = null;
                  selectedTextIndex = -1;
                  // FIX: Reset rainbow border state
                  ie_isRainbowBorder = false;

                  ctx.clearRect(0, 0, canvas.width, canvas.height);
                  canvas.width = 0;
                  canvas.height = 0;
                  placeholder.classList.remove('d-none');

                  updateThumbnails();
                  updateLayoutTemplates(0);
                  updateToolbar();
            }

            function draw() {
                  if (!backgroundImage) {
                        placeholder.classList.remove('d-none');
                        return;
                  };
                  placeholder.classList.add('d-none');

                  // Fit canvas to background image aspect ratio
                  const wrapperRect = canvasWrapper.getBoundingClientRect();
                  const imgAspectRatio = backgroundImage.width / backgroundImage.height;
                  const wrapperAspectRatio = wrapperRect.width / wrapperRect.height;

                  if (imgAspectRatio > wrapperAspectRatio) {
                        canvas.width = wrapperRect.width;
                        canvas.height = wrapperRect.width / imgAspectRatio;
                  } else {
                        canvas.height = wrapperRect.height;
                        canvas.width = wrapperRect.height * imgAspectRatio;
                  }

                  ctx.clearRect(0, 0, canvas.width, canvas.height);
                  ctx.drawImage(backgroundImage, 0, 0, canvas.width, canvas.height);

                  // FIX: Check the state variable to draw rainbow border
                  if (ie_isRainbowBorder && parseInt(spaceInput.value, 10) > 0) {
                        drawRainbowBorder();
                  }

                  textObjects.forEach((obj, index) => {
                        drawTextObject(obj);
                  });

                  if (selectedTextIndex > -1 && textObjects[selectedTextIndex]) {
                        drawBoundingBox(textObjects[selectedTextIndex]);
                  }
            }

            function drawTextObject(obj) {
                  const lines = obj.text.split('\n');
                  const fontStyle = obj.fontStyle || 'normal';
                  const fontWeight = obj.fontWeight || 'normal';
                  const font = `${fontStyle} ${fontWeight} ${obj.fontSize}px "${obj.font}"`;
                  ctx.font = font;

                  // Recalculate width/height for multiline text
                  let maxWidth = 0;
                  lines.forEach(line => {
                        const lineWidth = ctx.measureText(line).width;
                        if (lineWidth > maxWidth) {
                              maxWidth = lineWidth;
                        }
                  });
                  obj.width = maxWidth;
                  obj.height = lines.length * obj.fontSize * 1.2;

                  // Handle color / gradient
                  if (obj.color === 'rainbow') {
                        const gradient = ctx.createLinearGradient(obj.x, obj.y, obj.x + obj.width, obj.y);
                        gradient.addColorStop(0, "red");
                        gradient.addColorStop(1 / 6, "orange");
                        gradient.addColorStop(2 / 6, "yellow");
                        gradient.addColorStop(3 / 6, "green");
                        gradient.addColorStop(4 / 6, "blue");
                        gradient.addColorStop(5 / 6, "indigo");
                        gradient.addColorStop(1, "violet");
                        ctx.fillStyle = gradient;
                  } else {
                        ctx.fillStyle = obj.color;
                  }

                  ctx.textAlign = obj.textAlign || 'left';
                  ctx.textBaseline = 'top';

                  lines.forEach((line, i) => {
                        let drawX = obj.x;
                        if (ctx.textAlign === 'center') { drawX = obj.x + obj.width / 2; }
                        if (ctx.textAlign === 'right') { drawX = obj.x + obj.width; }
                        const drawY = obj.y + (i * obj.fontSize * 1.2);
                        ctx.fillText(line, drawX, drawY);

                        if (obj.textDecoration === 'underline') {
                              const textWidth = ctx.measureText(line).width;
                              let underlineX = obj.x;
                              if (ctx.textAlign === 'center') { underlineX = obj.x + (obj.width - textWidth) / 2; }
                              if (ctx.textAlign === 'right') { underlineX = obj.x + (obj.width - textWidth); }
                              ctx.fillRect(underlineX, drawY + obj.fontSize * 1.1, textWidth, 2);
                        }
                  });
            }

            function drawRainbowBorder() {
                  const borderThickness = parseInt(spaceInput.value, 10);
                  if (borderThickness <= 0) return;

                  ctx.save();
                  ctx.lineWidth = borderThickness;
                  const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
                  const rainbowColors = ["red", "orange", "yellow", "green", "blue", "indigo", "violet"];
                  rainbowColors.forEach((color, index) => {
                        gradient.addColorStop(index / (rainbowColors.length - 1), color);
                  });

                  ctx.strokeStyle = gradient;
                  ctx.strokeRect(borderThickness / 2, borderThickness / 2, canvas.width - borderThickness, canvas.height - borderThickness);
                  ctx.restore();
            }


            function drawBoundingBox(obj) {
                  ctx.strokeStyle = '#0d6efd';
                  ctx.lineWidth = 2;
                  ctx.setLineDash([6, 3]);
                  ctx.strokeRect(obj.x, obj.y, obj.width, obj.height);
                  ctx.setLineDash([]);

                  // Draw resize handles
                  const handles = getHandleRects(obj);
                  ctx.fillStyle = '#0d6efd';
                  for (const key in handles) {
                        const handle = handles[key];
                        ctx.fillRect(handle.x, handle.y, handle.w, handle.h);
                  }
            }

            // === Event Handlers ===
            function setupEventListeners() {
                  uploadBtn.addEventListener('click', () => uploadInput.click());
                  uploadInput.addEventListener('change', handleImageUpload);
                  resetBtn.addEventListener('click', resetEditor);
                  addTextBtn.addEventListener('click', addText);
                  saveBtn.addEventListener('click', saveImage);

                  // Collage controls
                  spaceInput.addEventListener('change', generateCollageBackground);
                  // FIX: Handle native color picker input to disable rainbow mode
                  colorInput.addEventListener('input', () => {
                        ie_isRainbowBorder = false;
                        const rainbowSwatch = imageEditorPane.querySelector('.ie-color-swatches[data-target-input="ie-color-input"] span[data-color="rainbow"].active');
                        if (rainbowSwatch) {
                              rainbowSwatch.classList.remove('active');
                        }
                        generateCollageBackground();
                  });

                  // Text Toolbar controls
                  fontSelect.addEventListener('change', (e) => updateSelectedTextProperty('font', e.target.value));
                  fontSizeInput.addEventListener('change', (e) => updateSelectedTextProperty('fontSize', parseInt(e.target.value, 10)));
                  textColorInput.addEventListener('input', (e) => updateSelectedTextProperty('color', e.target.value));

                  // FIX: Correctly handle color swatches for both border and text
                  document.querySelectorAll('.ie-color-swatches').forEach(swatchGroup => {
                        swatchGroup.addEventListener('click', (e) => {
                              const swatch = e.target.closest('span[data-color]');
                              if (swatch) {
                                    const targetInputId = swatchGroup.dataset.targetInput;
                                    const targetInput = document.getElementById(targetInputId);
                                    const color = swatch.dataset.color;

                                    if (targetInputId === 'ie-color-input') {
                                          // Handle collage background color
                                          if (color === 'rainbow') {
                                                ie_isRainbowBorder = true;
                                                // Set the color picker to black for visual feedback, as the generated background will be black
                                                targetInput.value = '#000000';
                                          } else {
                                                ie_isRainbowBorder = false;
                                                targetInput.value = color;
                                          }
                                          generateCollageBackground();
                                    } else {
                                          // Handle text color (logic is unchanged)
                                          if (color !== 'rainbow') {
                                                targetInput.value = color;
                                          }
                                          updateSelectedTextProperty('color', color);
                                    }

                                    // Update active state for swatches
                                    swatchGroup.querySelector('.active')?.classList.remove('active');
                                    swatch.classList.add('active');
                              }
                        });
                  });

                  // Text Style & Align
                  textStyleBtns.addEventListener('click', handleTextStyleClick);
                  textAlignBtns.addEventListener('click', handleTextAlignClick);


                  // Canvas interaction
                  canvas.addEventListener('mousedown', handleMouseDown);
                  canvas.addEventListener('mousemove', handleMouseMove);
                  canvas.addEventListener('mouseup', handleMouseUp);
                  canvas.addEventListener('dblclick', handleDblClick);

                  // Keyboard interaction
                  canvas.addEventListener('keydown', handleKeyDown);

                  // Thumbnail Drag and Drop
                  thumbnailsContainer.addEventListener('dragstart', handleThumbnailDragStart);
                  thumbnailsContainer.addEventListener('dragend', handleThumbnailDragEnd);
                  thumbnailsContainer.addEventListener('dragover', e => e.preventDefault());
                  thumbnailsContainer.addEventListener('drop', handleThumbnailDrop);
            }

            async function handleImageUpload(e) {
                  const files = e.target.files;
                  if (files.length === 0) return;
                  const formData = new FormData();
                  for (const file of files) { formData.append('files', file); }
                  showToast('Đang tải ảnh lên...', 'info');
                  try {
                        const response = await fetch('/image-editor/upload', { method: 'POST', body: formData });
                        const data = await response.json();
                        if (!response.ok) throw new Error(data.error || 'Lỗi không xác định');
                        ie_sessionId = data.sessionId;
                        ie_uploadedFilesInfo = data.files.map(url => ({ url: url, originalFilename: url.split('/').pop() }));
                        updateThumbnails();
                        showToast(`Đã tải lên ${ie_uploadedFilesInfo.length} ảnh.`, 'success');
                        updateLayoutTemplates(ie_uploadedFilesInfo.length);
                  } catch (error) {
                        showToast(error.message, 'error');
                        resetEditor();
                  } finally {
                        uploadInput.value = '';
                  }
            }

            async function generateCollageBackground() {
                  if (ie_uploadedFilesInfo.length === 0) return;
                  const selectedLayout = layoutContainer.querySelector('.ie-layout-box.active');
                  if (!selectedLayout) {
                        showToast('Vui lòng chọn một bố cục.', 'error');
                        return;
                  }
                  placeholder.classList.add('d-none');
                  showToast('Đang tạo ảnh nền...', 'info');

                  // FIX: Use the state variable to determine the background color for the server
                  const bgColorForServer = ie_isRainbowBorder ? '#000000' : colorInput.value;

                  const payload = {
                        sessionId: ie_sessionId,
                        images: ie_uploadedFilesInfo.map(info => info.url),
                        layout: selectedLayout.dataset.layout,
                        space: spaceInput.value,
                        color: bgColorForServer,
                  };

                  try {
                        const response = await fetch('/image-editor/create-collage', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                        const data = await response.json();
                        if (!response.ok) throw new Error(data.error || 'Lỗi không xác định');

                        const img = new Image();
                        img.crossOrigin = "anonymous"; // Important for canvas
                        img.src = data.result_url + '?t=' + new Date().getTime();
                        img.onload = () => {
                              backgroundImage = img;
                              textObjects = []; // Clear text when background changes
                              selectedTextIndex = -1;
                              updateToolbar();
                              draw();
                        };
                  } catch (error) {
                        showToast(error.message, 'error');
                        placeholder.classList.remove('d-none');
                  }
            }

            function addText() {
                  if (!backgroundImage) {
                        showToast('Vui lòng tạo ảnh ghép trước.', 'error');
                        return;
                  }
                  const newText = {
                        text: 'Văn bản mẫu',
                        x: canvas.width / 2 - 100,
                        y: canvas.height / 2 - 25,
                        font: 'Arial',
                        fontSize: 50,
                        color: '#FFFFFF',
                        width: 0,
                        height: 0,
                        fontWeight: 'normal',
                        fontStyle: 'normal',
                        textDecoration: 'none',
                        textAlign: 'left'
                  };
                  textObjects.push(newText);
                  selectedTextIndex = textObjects.length - 1;
                  updateToolbar();
                  draw();
            }

            function saveImage() {
                  if (!backgroundImage) {
                        showToast('Không có ảnh để lưu.', 'error');
                        return;
                  }
                  const previouslySelected = selectedTextIndex;
                  selectedTextIndex = -1;
                  draw();

                  const link = document.createElement('a');
                  link.download = `stool_collage_${Date.now()}.jpg`;
                  link.href = canvas.toDataURL('image/jpeg', 0.9);
                  link.click();

                  selectedTextIndex = previouslySelected;
                  if (selectedTextIndex > -1) draw();
            }

            function getMousePos(e) {
                  const rect = canvas.getBoundingClientRect();
                  return {
                        x: e.clientX - rect.left,
                        y: e.clientY - rect.top
                  };
            }

            function handleMouseDown(e) {
                  const pos = getMousePos(e);
                  let clickedOnSomething = false;

                  if (selectedTextIndex > -1 && textObjects[selectedTextIndex]) {
                        const handles = getHandleRects(textObjects[selectedTextIndex]);
                        for (const key in handles) {
                              const handle = handles[key];
                              if (pos.x >= handle.x && pos.x <= handle.x + handle.w &&
                                    pos.y >= handle.y && pos.y <= handle.y + handle.h) {
                                    isResizing = true;
                                    activeResizeHandle = key;
                                    clickedOnSomething = true;
                                    canvas.focus();
                                    break;
                              }
                        }
                  }

                  if (!isResizing) {
                        for (let i = textObjects.length - 1; i >= 0; i--) {
                              const obj = textObjects[i];
                              if (pos.x >= obj.x && pos.x <= obj.x + obj.width &&
                                    pos.y >= obj.y && pos.y <= obj.y + obj.height) {
                                    selectedTextIndex = i;
                                    isDragging = true;
                                    dragOffsetX = pos.x - obj.x;
                                    dragOffsetY = pos.y - obj.y;
                                    clickedOnSomething = true;
                                    canvas.focus();
                                    break;
                              }
                        }
                  }

                  if (!clickedOnSomething) {
                        selectedTextIndex = -1;
                  }

                  updateToolbar();
                  draw();
            }

            function handleMouseMove(e) {
                  const pos = getMousePos(e);

                  let onHandle = false;
                  if (selectedTextIndex > -1 && !isDragging) {
                        const obj = textObjects[selectedTextIndex];
                        if (obj) {
                              const handles = getHandleRects(obj);
                              for (const key in handles) {
                                    const handle = handles[key];
                                    if (pos.x >= handle.x && pos.x <= handle.x + handle.w &&
                                          pos.y >= handle.y && pos.y <= handle.y + handle.h) {
                                          canvas.style.cursor = `${key}-resize`;
                                          onHandle = true;
                                          break;
                                    }
                              }
                        }
                  }
                  if (!onHandle && !isDragging) {
                        canvas.style.cursor = 'default';
                  } else if (isDragging) {
                        canvas.style.cursor = 'move';
                  }

                  if (isDragging && selectedTextIndex > -1) {
                        const obj = textObjects[selectedTextIndex];
                        obj.x = pos.x - dragOffsetX;
                        obj.y = pos.y - dragOffsetY;
                        draw();
                  } else if (isResizing && selectedTextIndex > -1) {
                        const obj = textObjects[selectedTextIndex];
                        const oldWidth = obj.width;
                        const oldHeight = obj.height;

                        if (activeResizeHandle.includes('r')) obj.width = pos.x - obj.x;
                        if (activeResizeHandle.includes('l')) {
                              obj.width += obj.x - pos.x;
                              obj.x = pos.x;
                        }

                        if (oldWidth > 0 && obj.width > 5) { // Prevent shrinking to zero
                              const scale = obj.width / oldWidth;
                              obj.fontSize *= scale;
                        }

                        draw();
                  }
            }

            function handleMouseUp() {
                  isDragging = false;
                  isResizing = false;
                  activeResizeHandle = null;
                  canvas.style.cursor = 'default';
            }

            function handleDblClick(e) {
                  const pos = getMousePos(e);
                  selectedTextIndex = -1;
                  draw();
                  for (let i = textObjects.length - 1; i >= 0; i--) {
                        const obj = textObjects[i];
                        if (pos.x >= obj.x && pos.x <= obj.x + obj.width &&
                              pos.y >= obj.y && pos.y <= obj.y + obj.height) {
                              createEditingTextarea(obj, i);
                              return;
                        }
                  }
            }

            function handleKeyDown(e) {
                  if ((e.key === 'Delete' || e.key === 'Backspace') && selectedTextIndex > -1) {
                        if (document.activeElement.tagName.toLowerCase() !== 'textarea') {
                              e.preventDefault();
                              textObjects.splice(selectedTextIndex, 1);
                              selectedTextIndex = -1;
                              updateToolbar();
                              draw();
                        }
                  }
            }

            function createEditingTextarea(obj, index) {
                  const existingTextarea = document.querySelector('.ie-editing-textarea');
                  if (existingTextarea) existingTextarea.blur();

                  const textarea = document.createElement('textarea');
                  textarea.value = obj.text;
                  textarea.className = 'ie-editing-textarea';

                  const canvasRect = canvas.getBoundingClientRect();

                  textarea.style.left = `${canvasRect.left + obj.x}px`;
                  textarea.style.top = `${canvasRect.top + obj.y}px`;
                  textarea.style.width = `${obj.width + 40}px`;
                  textarea.style.height = `auto`;
                  textarea.style.font = `${obj.fontStyle || 'normal'} ${obj.fontWeight || 'normal'} ${obj.fontSize}px "${obj.font}"`;
                  textarea.style.color = obj.color === 'rainbow' ? '#FFFFFF' : obj.color;

                  textarea.oninput = () => {
                        textarea.style.height = 'auto';
                        textarea.style.height = `${textarea.scrollHeight}px`;
                  };

                  textarea.onblur = () => {
                        const newText = textarea.value;
                        if (newText.trim()) {
                              textObjects[index].text = newText;
                        } else {
                              textObjects.splice(index, 1);
                        }
                        selectedTextIndex = -1;
                        updateToolbar();
                        if (document.body.contains(textarea)) {
                              document.body.removeChild(textarea);
                        }
                        draw();
                  };

                  textarea.addEventListener('keydown', (e) => { e.stopPropagation(); });

                  document.body.appendChild(textarea);
                  textarea.focus();
                  textarea.select();
                  textarea.dispatchEvent(new Event('input'));
            }

            function getHandleRects(obj) {
                  return {
                        tl: { x: obj.x - handleSize / 2, y: obj.y - handleSize / 2, w: handleSize, h: handleSize },
                        tr: { x: obj.x + obj.width - handleSize / 2, y: obj.y - handleSize / 2, w: handleSize, h: handleSize },
                        bl: { x: obj.x - handleSize / 2, y: obj.y + obj.height - handleSize / 2, w: handleSize, h: handleSize },
                        br: { x: obj.x + obj.width - handleSize / 2, y: obj.y + obj.height - handleSize / 2, w: handleSize, h: handleSize }
                  };
            }

            function updateToolbar() {
                  if (selectedTextIndex > -1 && textObjects[selectedTextIndex]) {
                        textToolbar.classList.remove('d-none');
                        const obj = textObjects[selectedTextIndex];
                        fontSelect.value = obj.font;
                        fontSizeInput.value = Math.round(obj.fontSize);
                        textColorInput.value = obj.color === 'rainbow' ? '#ffffff' : obj.color;

                        textStyleBtns.querySelectorAll('button').forEach(btn => {
                              const style = btn.dataset.style;
                              const value = btn.dataset.value;
                              if (obj[style] === value) {
                                    btn.classList.add('active');
                              } else {
                                    btn.classList.remove('active');
                              }
                        });
                        textAlignBtns.querySelectorAll('button').forEach(btn => {
                              if (obj.textAlign === btn.dataset.align) {
                                    btn.classList.add('active');
                              } else {
                                    btn.classList.remove('active');
                              }
                        });

                  } else {
                        textToolbar.classList.add('d-none');
                  }
            }

            function updateSelectedTextProperty(key, value) {
                  if (selectedTextIndex > -1) {
                        const obj = textObjects[selectedTextIndex];
                        if (!obj) return;

                        if (key === 'fontWeight' || key === 'fontStyle' || key === 'textDecoration') {
                              obj[key] = obj[key] === value ? 'normal' : value;
                              if (key === 'textDecoration' && obj[key] === 'normal') obj[key] = 'none';
                        } else {
                              obj[key] = value;
                        }

                        draw();
                        updateToolbar();
                  }
            }

            function handleTextStyleClick(e) {
                  const btn = e.target.closest('button');
                  if (btn) {
                        updateSelectedTextProperty(btn.dataset.style, btn.dataset.value);
                  }
            }
            function handleTextAlignClick(e) {
                  const btn = e.target.closest('button');
                  if (btn) {
                        updateSelectedTextProperty('textAlign', btn.dataset.align);
                  }
            }

            function updateThumbnails() {
                  thumbnailsContainer.innerHTML = '';
                  if (ie_uploadedFilesInfo.length === 0) {
                        thumbnailsContainer.innerHTML = '<div class="text-muted d-flex align-items-center justify-content-center h-100 p-2 text-center small">Chưa có ảnh nào</div>';
                  } else {
                        ie_uploadedFilesInfo.forEach((info, index) => {
                              const img = document.createElement('img');
                              img.src = info.url;
                              img.draggable = true;
                              img.dataset.index = index;
                              thumbnailsContainer.appendChild(img);
                        });
                  }
                  imageCountSpan.textContent = ie_uploadedFilesInfo.length;
            }

            function updateLayoutTemplates(count) {
                  layoutContainer.innerHTML = '';
                  const layouts = layoutsByCount[count];
                  if (!layouts) {
                        layoutContainer.innerHTML = `<div class="text-warning text-center small">Không có bố cục cho ${count} ảnh.</div>`;
                        return;
                  }
                  let isFirst = true;
                  for (const layoutId in layouts) {
                        const box = document.createElement('div');
                        box.className = 'ie-layout-box';
                        box.dataset.layout = layoutId;
                        box.innerHTML = layouts[layoutId];
                        if (isFirst) { box.classList.add('active'); isFirst = false; }
                        box.addEventListener('click', (e) => {
                              layoutContainer.querySelector('.active')?.classList.remove('active');
                              e.currentTarget.classList.add('active');
                              generateCollageBackground();
                        });
                        layoutContainer.appendChild(box);
                  }
                  if (count > 0) { generateCollageBackground(); }
            }

            function populateFonts() {
                  const googleFonts = ['Lobster', 'Pacifico', 'Anton', 'Oswald', 'Roboto'];
                  const fontLink = document.createElement('link');
                  fontLink.href = `https://fonts.googleapis.com/css2?family=${googleFonts.map(f => f.replace(' ', '+')).join('&family=')}&display=swap`;
                  fontLink.rel = 'stylesheet';
                  document.head.appendChild(fontLink);

                  fontSelect.innerHTML = '';
                  fonts.forEach(font => {
                        const option = document.createElement('option');
                        option.value = font;
                        option.textContent = font;
                        option.style.fontFamily = font;
                        fontSelect.appendChild(option);
                  });
            }


            function handleThumbnailDragStart(e) {
                  if (e.target.tagName === 'IMG') {
                        ie_draggedThumbnailIndex = parseInt(e.target.dataset.index);
                        e.target.classList.add('dragging');
                  }
            }
            function handleThumbnailDragEnd(e) {
                  if (e.target.tagName === 'IMG') { e.target.classList.remove('dragging'); }
            }
            function handleThumbnailDrop(e) {
                  e.preventDefault();
                  const target = e.target.closest('img');
                  if (target && target.tagName === 'IMG') {
                        const fromIndex = ie_draggedThumbnailIndex;
                        const toIndex = parseInt(target.dataset.index);
                        if (fromIndex !== toIndex) {
                              const [movedItem] = ie_uploadedFilesInfo.splice(fromIndex, 1);
                              ie_uploadedFilesInfo.splice(toIndex, 0, movedItem);
                              updateThumbnails();
                              generateCollageBackground();
                        }
                  }
                  ie_draggedThumbnailIndex = null;
            }

            init();
      })();

      // --- Custom Context Menu Logic ---
      (function() {
        // Get menu elements
        const dashboardMenu = document.getElementById('dashboard-context-menu');
        const telegramMenu = document.getElementById('telegram-context-menu');
        const telegramPane = document.getElementById('telegram-tool-pane');
        const mainTabContent = document.getElementById('main-tab-content');

        // Helper: Hide all menus
        function hideMenus() {
          dashboardMenu.style.display = 'none';
          telegramMenu.style.display = 'none';
        }

        // Helper: Show menu at mouse position
        function showMenu(menu, x, y) {
          menu.style.display = 'block';
          // Prevent menu from going off screen
          const menuRect = menu.getBoundingClientRect();
          const winW = window.innerWidth, winH = window.innerHeight;
          if (x + menuRect.width > winW) x = winW - menuRect.width - 8;
          if (y + menuRect.height > winH) y = winH - menuRect.height - 8;
          menu.style.left = x + 'px';
          menu.style.top = y + 'px';
        }

        // Telegram tab context menu
        if (telegramPane) {
          telegramPane.addEventListener('contextmenu', function(e) {
            // Only show if right-click inside telegram tab content
            hideMenus();
            showMenu(telegramMenu, e.clientX, e.clientY);
            e.preventDefault();
          });
        }

        // Hide menus on click elsewhere or scroll
        document.addEventListener('click', hideMenus);
        document.addEventListener('scroll', hideMenus, true);
        window.addEventListener('resize', hideMenus);

        // Hide menus when switching tabs
        document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tabBtn => {
          tabBtn.addEventListener('shown.bs.tab', hideMenus);
        });

        // Prevent both menus from showing at once
        dashboardMenu.addEventListener('contextmenu', e => e.preventDefault());
        telegramMenu.addEventListener('contextmenu', e => e.preventDefault());
      })();

      // --- NOTES MANAGER SCRIPT ---
      (() => {
        const notesTab = document.getElementById('notes-tool-tab');
        if (!notesTab) return;

        // --- Element selectors ---
        const container = document.getElementById('notes-container');
        const modalEl = document.getElementById('notes-addEditModal');
        const notesModal = new bootstrap.Modal(modalEl);
        const form = document.getElementById('notes-addEditForm');
        const modalTitle = document.getElementById('notes-modalTitle');
        const editIdInput = document.getElementById('notes-editId');
        const titleInput = document.getElementById('notes-title-input');
        const contentEditor = document.getElementById('notes-content-editor');
        
        // Alarm UI Elements
        const enableAlarmCheck = document.getElementById('notes-enableAlarmCheck');
        const alarmContainer = document.getElementById('notes-alarm-container');
        const dueTimeInput = document.getElementById('notes-dueTime');
        const alarmTypeAbsoluteRadio = document.getElementById('alarmTypeAbsolute');
        const alarmTypeRelativeRadio = document.getElementById('alarmTypeRelative');
        const absolutePanel = document.getElementById('notes-alarm-absolute-panel');
        const relativePanel = document.getElementById('notes-alarm-relative-panel');

        // Notification Elements
        const notificationModalEl = document.getElementById('notes-notificationModal');
        const notificationModal = new bootstrap.Modal(notificationModalEl);
        const notificationTitle = document.getElementById('notes-notificationTitle');
        const notificationContent = document.getElementById('notes-notificationContent');
        let notificationSound = new Audio();

        // Context Menu Elements
        const contextMenu = document.getElementById('notes-context-menu');
        const contextCopy = document.getElementById('context-copy');
        const colorPalette = document.querySelector('#notes-context-menu .color-palette');

        // --- Core Functions ---
        async function fetchAndRenderNotes() {
            try {
                const response = await fetch('/notes/api/get');
                const notes = await response.json();
                container.innerHTML = '';
                if (notes.length === 0) {
                    container.innerHTML = `<div class="col-12 text-center text-muted p-5"><h6>Chưa có ghi chú nào.</h6><p>Hãy nhấn "Thêm Mới" để bắt đầu.</p></div>`;
                    return;
                }
                notes.forEach(note => container.appendChild(createNoteCard(note)));
            } catch (error) {
                container.innerHTML = `<div class="col-12 text-center text-danger p-5"><h6>Lỗi tải ghi chú.</h6><p>${error.message}</p></div>`;
            }
        }

        function createNoteCard(note) {
            const col = document.createElement('div');
            col.className = 'col-lg-4 col-md-6 d-flex note-card-enter';

            let borderColor = 'var(--bs-card-border-color)';
            let statusHTML = '<small class="text-muted">&nbsp;</small>';

            if (note.status === 'notified') {
                borderColor = '#28a745';
                statusHTML = `<small class="text-success fw-bold"><i class="bi bi-check-circle-fill"></i> Đã báo</small>`;
            } else if (note.due_time) {
                borderColor = '#ffc107';
                statusHTML = `<small class="text-warning fw-bold"><i class="bi bi-alarm-fill"></i> <span id="countdown-${note.id}" data-due-time="${note.due_time}">Đang tính...</span></small>`;
            }

            const noteTitleText = note.title_html.trim() || "Ghi chú không có tiêu đề";
            const noteBodyHtml = note.content_html.trim() || '';

            col.innerHTML = `
                <div class="card h-100 w-100" style="border-left: 4px solid ${borderColor};">
                    <div class="card-body d-flex flex-column">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <h5 class="card-title mb-0">${noteTitleText}</h5>
                            <small class="text-muted" id="note-modified-at-${note.id}"></small>
                        </div>
                        <div class="card-text text-muted flex-grow-1 card-note-body"></div>
                        <div class="d-flex justify-content-between align-items-center mt-3">
                            ${statusHTML}
                            <div>
                                <button class="btn btn-sm btn-outline-secondary" onclick="prepareEditNoteModal('${note.id}')"><i class="bi bi-pencil-fill"></i></button>
                                <button class="btn btn-sm btn-outline-danger" onclick="deleteNote('${note.id}')"><i class="bi bi-trash-fill"></i></button>
                            </div>
                        </div>
                    </div>
                </div>`;

            const noteBodyElement = col.querySelector('.card-note-body');
            if (noteBodyElement) {
                noteBodyElement.innerHTML = noteBodyHtml || '...';
            }
            const modifiedAtElement = col.querySelector(`#note-modified-at-${note.id}`);
            if (modifiedAtElement && note.modified_at) {
                const date = new Date(note.modified_at);
                const formattedDate = `Đã sửa ${date.getDate()}/${date.getMonth() + 1}/${date.getFullYear()}`;
                modifiedAtElement.textContent = formattedDate;
            }

            if (note.due_time && note.status !== 'notified') {
                setTimeout(() => updateCountdown(`countdown-${note.id}`, note.due_time), 0);
            }

            const cardElement = col.querySelector('.card');
            cardElement.addEventListener('animationend', () => {
                col.classList.remove('note-card-enter');
            }, { once: true });

            return col;
        }

        // --- START: Code mới thêm vào ---
        function updateCountdown(elementId, dueTimeString) {
            const elem = document.getElementById(elementId);
            if (!elem) return;

            const dueTime = new Date(dueTimeString).getTime();
            const now = new Date().getTime();
            const distance = dueTime - now;

            if (distance < 0) {
                elem.textContent = "Đã đến giờ!";
                // Không cần xóa interval ở đây vì server sẽ sớm cập nhật trạng thái
                return;
            }

            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            let result = "Còn ";
            if (days > 0) result += `${days} ngày `;
            if (hours > 0 || days > 0) result += `${hours} giờ `;
            if (minutes > 0 || hours > 0 || days > 0) result += `${minutes} phút `;
            result += `${seconds} giây`;

            elem.textContent = result;
        }

        // Cập nhật tất cả các bộ đếm ngược mỗi giây
        setInterval(() => {
            document.querySelectorAll('[id^="countdown-"]').forEach(span => {
                if(span.dataset.dueTime) {
                    updateCountdown(span.id, span.dataset.dueTime);
                }
            });
        }, 1000);
        // --- END: Code mới thêm vào ---

        // --- Modal and Form Logic ---
        window.prepareAddNoteModal = () => {
            form.reset();
            modalTitle.textContent = 'Thêm Ghi Chú Mới';
            editIdInput.value = '';
            titleInput.innerHTML = '';
            contentEditor.innerHTML = '';
            alarmContainer.classList.add('d-none');
            enableAlarmCheck.checked = false;
            alarmTypeAbsoluteRadio.checked = true;
            absolutePanel.classList.remove('d-none'); // Show absolute panel by default
            relativePanel.classList.add('d-none'); // Hide relative panel
        };

        window.prepareEditNoteModal = async (id) => {
            const response = await fetch('/notes/api/get');
            const notesList = await response.json();
            const note = notesList.find(n => n.id === id);

            if (!note) {
                showAlert("Không thể tìm thấy ghi chú để sửa.");
                return;
            }

            form.reset();
            modalTitle.textContent = 'Sửa Ghi Chú';
            editIdInput.value = id;
            titleInput.innerHTML = note.title_html || '';
            contentEditor.innerHTML = note.content_html || '';

            if (note.due_time && note.due_time !== 'null') {
                enableAlarmCheck.checked = true;
                alarmContainer.classList.remove('d-none');
                alarmTypeAbsoluteRadio.checked = true;
                absolutePanel.classList.remove('d-none');
                relativePanel.classList.add('d-none');
                const date = new Date(note.due_time);
                date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
                dueTimeInput.value = date.toISOString().slice(0, 16);
            } else {
                enableAlarmCheck.checked = false;
                alarmContainer.classList.add('d-none');
            }
            notesModal.show();
        };

        window.deleteNote = async (id) => {
            window.confirmDeleteAction(async () => {
                await fetch(`/notes/api/delete/${id}`, { method: 'POST' });
                fetchAndRenderNotes();
            }, 'Bạn có chắc muốn xóa ghi chú này?');
        };

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = editIdInput.value;
            const url = id ? `/notes/api/update/${id}` : '/notes/api/add';
            
            let due_time = null;
            if (enableAlarmCheck.checked) {
                if (alarmTypeAbsoluteRadio.checked) {
                    if (dueTimeInput.value) {
                        due_time = new Date(dueTimeInput.value).toISOString();
                    }
                } else {
                    const days = parseInt(document.getElementById('relative-days').value) || 0;
                    const hours = parseInt(document.getElementById('relative-hours').value) || 0;
                    const minutes = parseInt(document.getElementById('relative-minutes').value) || 0;
                    const totalMinutes = (days * 24 * 60) + (hours * 60) + minutes;
                    if (totalMinutes > 0) {
                        const now = new Date();
                        now.setMinutes(now.getMinutes() + totalMinutes);
                        due_time = now.toISOString();
                    }
                }
            }
            
            const title_html = titleInput.innerHTML.trim();
            const content_html = contentEditor.innerHTML.trim();
            if (!title_html && !content_html) {
                showAlert('Tiêu đề hoặc Nội dung không được để trống.');
                return;
            }
            const payload = {
                title_html: title_html,
                content_html: content_html,
                due_time: due_time
            };

            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                showAlert('Lỗi: ' + (await response.json()).error);
                return;
            }
            notesModal.hide();
            fetchAndRenderNotes();
        });

        // --- Event Listeners for UI ---
        notesTab.addEventListener('shown.bs.tab', fetchAndRenderNotes);

        enableAlarmCheck.addEventListener('change', function() {
            alarmContainer.classList.toggle('d-none', !this.checked);
            if (this.checked && !dueTimeInput.value) {
                const now = new Date();
                // Adjust for local timezone and set default time 5 minutes into the future
                now.setMinutes(now.getMinutes() - now.getTimezoneOffset() + 5);
                dueTimeInput.value = now.toISOString().slice(0, 16);
            }
            // Set the default view to 'Absolute Time' when enabling the alarm
            if (this.checked) {
                alarmTypeAbsoluteRadio.checked = true;
                absolutePanel.classList.remove('d-none');
                relativePanel.classList.add('d-none');
            }
        });
        
        alarmTypeAbsoluteRadio.addEventListener('change', () => {
            if (alarmTypeAbsoluteRadio.checked) {
                absolutePanel.classList.remove('d-none');
                relativePanel.classList.add('d-none');
            }
        });
        
        alarmTypeRelativeRadio.addEventListener('change', () => {
            if (alarmTypeRelativeRadio.checked) {
                absolutePanel.classList.add('d-none');
                relativePanel.classList.remove('d-none');
            }
        });
        
        // --- Notification Polling ---
        setInterval(async () => {
            try {
                const response = await fetch('/notes/api/check-notifications');
                const notification = await response.json();
                if (notification) {
                    notificationTitle.textContent = notification.title;
                    notificationContent.innerHTML = notification.notes || 'Không có nội dung chi tiết.';
                    // Use dynamic sound URL from backend
                    notificationSound.src = notification.sound_url;
                    notificationSound.play().catch(e => console.log("User interaction needed to play sound."));
                    notificationModal.show();
                    if (document.getElementById('notes-tool-pane').classList.contains('active')) {
                        fetchAndRenderNotes();
                    }
                }
            } catch (error) {
                console.error("Error polling for notifications:", error);
            }
        }, 10000); // Check every 10 seconds

        // Thay thế listener cũ bằng listener này
            titleInput.addEventListener('contextmenu', e => {
                  e.preventDefault();
                  e.stopPropagation();
                  const selection = window.getSelection();
                  // Chỉ hiển thị menu nếu có đoạn text được bôi đen
                  if (selection.toString().length > 0) {
                        // Đây là logic đúng, giống hệt với của ô Nội dung
                        contextMenu.style.top = `${e.clientY}px`;
                        contextMenu.style.left = `${e.clientX}px`;
                        contextMenu.style.display = 'block';
                  }
            });

        // --- Logic for Sub-tab State Management ---
        const mainNotesTab = document.getElementById('notes-tool-tab');
        const subTabs = document.querySelectorAll('#notes-sub-pills .nav-link');
        const defaultSubTabId = 'notes-sub-tab-notes';
        const notesMainTitle = document.getElementById('notes-main-title');
        const addNewBtn = document.getElementById('notes-add-new-btn');

        // Function to update the header and button based on the active sub-tab
        function updateNotesHeader(activeTabId) {
            if (activeTabId === 'notes-sub-tab-mxh') {
                // --- State for MXH Tab ---
                notesMainTitle.innerHTML = `<i class="bi bi-people-fill me-2"></i>Mạng Xã Hội`;
                addNewBtn.innerHTML = `<i class="bi bi-plus-lg me-1"></i> Thêm Tài Khoản MXH`;
                // Point the button to the Facebook modal
                addNewBtn.setAttribute('data-bs-target', '#fb-addAccountModal');
                addNewBtn.removeAttribute('onclick');
            } else {
                // --- Default State for Notes Tab ---
                notesMainTitle.innerHTML = `<i class="bi bi-journal-richtext me-2"></i>Ghi Chú`;
                addNewBtn.innerHTML = `<i class="bi bi-plus-lg me-1"></i> Thêm Mới`;
                // Point the button back to the Notes modal
                addNewBtn.setAttribute('data-bs-target', '#notes-addEditModal');
                addNewBtn.setAttribute('onclick', 'prepareAddNoteModal()');
            }
        }

        // Save the active sub-tab and update the header when a sub-tab is clicked
        subTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                localStorage.setItem('activeNotesSubTab', tab.id);
                updateNotesHeader(tab.id);
            });
        });

        // When the main Notes tab is shown, restore the last active sub-tab and update header
        mainNotesTab.addEventListener('shown.bs.tab', () => {
            const lastTabId = localStorage.getItem('activeNotesSubTab') || defaultSubTabId;
            const tabToActivate = document.getElementById(lastTabId);
            if (tabToActivate) {
                new bootstrap.Tab(tabToActivate).show();
                updateNotesHeader(lastTabId); // Update header based on the restored tab
            }
        });

    })();
});

(function() {
  let formToDelete = null;
  let callbackToDelete = null;
  document.addEventListener('submit', function(e) {
    const form = e.target;
    if (form.classList.contains('needs-confirm-delete')) {
      e.preventDefault();
      formToDelete = form;
      callbackToDelete = null;
      const msg = form.getAttribute('data-confirm-message') || 'Bạn có chắc muốn xóa?';
      document.getElementById('globalDeleteConfirmText').textContent = msg;
      new bootstrap.Modal(document.getElementById('globalDeleteConfirmModal')).show();
    }
  });
  window.confirmDeleteAction = function(callback, message) {
    formToDelete = null;
    callbackToDelete = callback;
    document.getElementById('globalDeleteConfirmText').textContent = message || 'Bạn có chắc muốn xóa?';
    new bootstrap.Modal(document.getElementById('globalDeleteConfirmModal')).show();
  };
  document.getElementById('globalDeleteConfirmBtn').onclick = function() {
    if (formToDelete) formToDelete.submit();
    if (callbackToDelete) callbackToDelete();
    bootstrap.Modal.getInstance(document.getElementById('globalDeleteConfirmModal')).hide();
  };
})();

function toggleDashboardSettingsModal() {
    const modalElement = document.getElementById('dashboardSettingsModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    modal.toggle();
}

const autoStartSwitch = document.getElementById('autoStartSwitch');
const dashboardSettingsModal = document.getElementById('dashboardSettingsModal');

// When the modal is shown, fetch the current settings from the backend
if (dashboardSettingsModal) {
    dashboardSettingsModal.addEventListener('show.bs.modal', async () => {
        try {
            const response = await fetch('/dashboard/api/settings');
            const settings = await response.json();
            autoStartSwitch.checked = settings.auto_start;
        } catch (error) {
            console.error("Lỗi khi tải cài đặt:", error);
        }
    });
}

// When the switch is toggled, save the new state to the backend
if (autoStartSwitch) {
    autoStartSwitch.addEventListener('change', async () => {
        try {
            const response = await fetch('/dashboard/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ auto_start: autoStartSwitch.checked })
            });
            if (response.ok) {
                showToast("Đã lưu cài đặt tự khởi động.", "success");
            } else {
                throw new Error("Lỗi server.");
            }
        } catch (error) {
            console.error("Lỗi khi lưu cài đặt:", error);
            showToast("Không thể lưu cài đặt. Vui lòng thử lại.", "error");
            // Revert the switch state on failure
            autoStartSwitch.checked = !autoStartSwitch.checked;
        }
    });
}

// === GLOBAL SEARCH SCRIPT ===
// (Remove the block that starts with // === GLOBAL SEARCH SCRIPT === and its IIFE wrapper)
// ... existing code ...
