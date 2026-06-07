<script>
  import { STATE, connectTerminal } from './state.svelte.js';
  import { FolderOpen, Settings, Play, CheckSquare, Square, AlertTriangle, ShieldCheck } from 'lucide-svelte';

  // Extract directory name for friendly display
  const folderName = $derived.by(() => {
    const path = STATE.currentFolder;
    if (!path) return 'No folder selected';
    return path.split('\\').pop() || path.split('/').pop() || path;
  });

  // Calculate connection button eligibility
  const selectedAgentInfo = $derived(
    STATE.agents.find(a => a.name === STATE.selectedAgent)
  );
  
  const isAgentAvailable = $derived(
    selectedAgentInfo ? selectedAgentInfo.available : false
  );

  const canConnect = $derived(
    isAgentAvailable && STATE.currentFolder !== '' && STATE.currentFolder !== 'Projects'
  );

  function selectAgent(agent) {
    if (!agent.available) return;
    STATE.selectedAgent = agent.name;
    localStorage.setItem('corvus_agent', agent.name);
  }

  function handleConnectClick() {
    if (!canConnect) return;
    STATE.phase = 'terminal';
    connectTerminal();
  }

  function toggleAutoApprove() {
    STATE.autoApprove = !STATE.autoApprove;
  }
</script>

<div class="launcher-screen">
  <div class="launcher-container">
    
    <!-- Workspace Folder Card -->
    <div class="section-title">WORKSPACE_DIRECTORY</div>
    <button class="folder-card" onclick={() => STATE.showFolderModal = true}>
      <div class="folder-icon-wrap">
        <FolderOpen size={20} />
      </div>
      <div class="folder-info">
        <div class="folder-display-name" class:empty={!STATE.currentFolder}>
          {folderName}
        </div>
        <div class="folder-full-path">
          {STATE.currentFolder || 'Tap to browse directories'}
        </div>
      </div>
    </button>

    <!-- Agent Selector -->
    <div class="section-title">ACTIVE_AI_AGENT</div>
    <div class="agent-grid">
      {#if STATE.agents.length === 0}
        <div class="agents-loading">Checking system path...</div>
      {:else}
        {#each STATE.agents as agent}
          <button
            class="agent-card"
            class:selected={STATE.selectedAgent === agent.name}
            disabled={!agent.available}
            onclick={() => selectAgent(agent)}
          >
            <span class="agent-title">{agent.name.toUpperCase()}</span>
            <span class="agent-path" title={agent.path}>
              {agent.available ? 'AVAILABLE' : 'NOT_INSTALLED'}
            </span>
          </button>
        {/each}
      {/if}
    </div>

    <!-- Security & Flags -->
    <div class="section-title">SESSION_FLAGS</div>
    <div class="flags-card">
      <button class="flag-row" onclick={toggleAutoApprove}>
        <div class="flag-checkbox">
          {#if STATE.autoApprove}
            <CheckSquare size={16} class="checked-icon" />
          {:else}
            <Square size={16} class="unchecked-icon" />
          {/if}
        </div>
        <div class="flag-info">
          <div class="flag-label">AUTO_APPROVE_MODE</div>
          <div class="flag-desc">Skip manual confirmations for agent tool calls.</div>
        </div>
      </button>
    </div>

    <!-- Connection Launcher Button -->
    <div class="action-wrap">
      <button
        class="connect-launch-btn"
        disabled={!canConnect}
        onclick={handleConnectClick}
      >
        <Play size={16} fill="currentColor" />
        <span>CONNECT_TO_{STATE.selectedAgent.toUpperCase()}</span>
      </button>

      <!-- Connection Hints -->
      {#if STATE.agents.length > 0}
        {#if !isAgentAvailable}
          <div class="connect-hint error">
            <AlertTriangle size={12} />
            <span>Agent '{STATE.selectedAgent}' is not installed in the container environment.</span>
          </div>
        {:else if !STATE.currentFolder || STATE.currentFolder === 'Projects'}
          <div class="connect-hint">
            <span>Choose a project workspace folder to start coding.</span>
          </div>
        {/if}
      {/if}
    </div>

  </div>
</div>

<style>
  .launcher-screen {
    flex: 1;
    overflow-y: auto;
    padding: 24px 16px;
    background: #000000;
    display: flex;
    justify-content: center;
    -webkit-overflow-scrolling: touch;
  }

  .launcher-container {
    width: 100%;
    max-width: 440px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .section-title {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-muted);
    font-weight: 700;
    letter-spacing: 1.5px;
    margin-bottom: 2px;
  }

  /* Folder Card */
  .folder-card {
    display: flex;
    align-items: center;
    width: 100%;
    background: #080808;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 14px 16px;
    cursor: pointer;
    text-align: left;
    transition: all var(--transition-fast);
  }

  .folder-card:hover {
    background: #0c0c0c;
    border-color: var(--text-secondary);
  }

  .folder-icon-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--purple);
    margin-right: 14px;
    flex-shrink: 0;
  }

  .folder-info {
    flex: 1;
    min-width: 0;
  }

  .folder-display-name {
    font-family: var(--font-sans);
    font-size: 14px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.2;
  }

  .folder-display-name.empty {
    color: var(--text-secondary);
  }

  .folder-full-path {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-muted);
    margin-top: 4px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Agent Grid */
  .agent-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }

  .agents-loading {
    grid-column: span 3;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-muted);
    text-align: center;
    padding: 16px 0;
  }

  .agent-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    background: #080808;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 12px 6px;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .agent-card:hover:not(:disabled) {
    background: #0c0c0c;
    border-color: var(--text-secondary);
  }

  .agent-card.selected {
    border-color: var(--purple);
    background: rgba(144, 96, 255, 0.05);
  }

  .agent-card:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .agent-title {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    color: #ffffff;
  }

  .agent-card:disabled .agent-title {
    color: var(--text-muted);
  }

  .agent-card.selected .agent-title {
    color: var(--purple);
  }

  .agent-path {
    font-family: var(--font-mono);
    font-size: 9px;
    color: var(--text-muted);
    margin-top: 4px;
  }

  /* Flags */
  .flags-card {
    background: #080808;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    overflow: hidden;
  }

  .flag-row {
    display: flex;
    width: 100%;
    align-items: flex-start;
    background: none;
    border: none;
    padding: 14px 16px;
    cursor: pointer;
    text-align: left;
    transition: background var(--transition-fast);
  }

  .flag-row:hover {
    background: #0c0c0c;
  }

  .flag-checkbox {
    margin-right: 12px;
    margin-top: 2px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .flag-row:hover .flag-checkbox {
    color: var(--text-secondary);
  }

  :global(.checked-icon) {
    color: var(--purple);
  }

  .flag-info {
    flex: 1;
  }

  .flag-label {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    color: #ffffff;
  }

  .flag-desc {
    font-family: var(--font-sans);
    font-size: 11px;
    color: var(--text-secondary);
    margin-top: 3px;
    line-height: 1.3;
  }

  /* Launch button */
  .action-wrap {
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .connect-launch-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    background: #ffffff;
    color: #000000;
    border: 1px solid #ffffff;
    border-radius: var(--radius-sm);
    padding: 14px;
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: all var(--transition-fast);
    letter-spacing: 1px;
  }

  .connect-launch-btn:hover:not(:disabled) {
    background: #e6e6e6;
    border-color: #e6e6e6;
  }

  .connect-launch-btn:active:not(:disabled) {
    transform: scale(0.98);
  }

  .connect-launch-btn:disabled {
    background: #080808;
    border-color: var(--border);
    color: var(--text-muted);
    cursor: not-allowed;
  }

  .connect-hint {
    font-family: var(--font-sans);
    font-size: 11px;
    color: var(--text-secondary);
    text-align: center;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 4px 0;
  }

  .connect-hint.error {
    color: var(--red);
  }
</style>
