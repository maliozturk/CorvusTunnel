<script>
  import { STATE, disconnectTerminal, hapticHeavy } from './state.svelte.js';
  import { AlertTriangle } from 'lucide-svelte';

  function handleStay() {
    STATE.showExitConfirm = false;
  }

  function handleDisconnect() {
    hapticHeavy();
    STATE.showExitConfirm = false;
    disconnectTerminal(true);
    STATE.phase = 'launcher';
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') {
      handleStay();
    }
  }
</script>

{#if STATE.showExitConfirm}
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <div class="exit-overlay" onclick={handleStay} onkeydown={handleKeydown} role="dialog" aria-modal="true" aria-label="Exit confirmation" tabindex="-1">
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="exit-dialog" onclick={(e) => e.stopPropagation()} role="document">
      <div class="exit-icon">
        <AlertTriangle size={28} strokeWidth={1.5} />
      </div>
      <div class="exit-title">Active Session Running</div>
      <div class="exit-desc">
        Your {STATE.selectedAgent} session is still connected. Are you sure you want to disconnect?
      </div>
      <div class="exit-actions">
        <button class="exit-btn stay" onclick={handleStay}>
          STAY
        </button>
        <button class="exit-btn disconnect" onclick={handleDisconnect}>
          DISCONNECT
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .exit-overlay {
    position: fixed;
    inset: 0;
    background: var(--bg-modal-overlay);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 3000;
    padding: 24px;
    animation: fadeIn 200ms ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .exit-dialog {
    width: 100%;
    max-width: 320px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-lg);
    padding: 28px 24px 20px;
    text-align: center;
    box-shadow: var(--shadow-lg);
    animation: scaleIn 250ms cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  @keyframes scaleIn {
    from { opacity: 0; transform: scale(0.9); }
    to { opacity: 1; transform: scale(1); }
  }

  .exit-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 52px;
    height: 52px;
    background: rgba(245, 158, 11, 0.08);
    border: 1px solid rgba(245, 158, 11, 0.2);
    border-radius: var(--radius-md);
    color: var(--yellow);
    margin-bottom: 16px;
  }

  .exit-title {
    font-family: var(--font-sans);
    font-size: 16px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 8px;
  }

  .exit-desc {
    font-family: var(--font-sans);
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.5;
    margin-bottom: 24px;
  }

  .exit-actions {
    display: flex;
    gap: 10px;
  }

  .exit-btn {
    flex: 1;
    padding: 12px;
    border-radius: var(--radius-sm);
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .exit-btn:active {
    transform: scale(0.97);
  }

  .exit-btn.stay {
    background: var(--btn-primary-bg);
    color: var(--btn-primary-text);
    border: 1px solid var(--btn-primary-border);
  }

  .exit-btn.stay:hover {
    background: var(--btn-primary-hover);
  }

  .exit-btn.disconnect {
    background: rgba(239, 68, 68, 0.08);
    color: var(--red);
    border: 1px solid rgba(239, 68, 68, 0.25);
  }

  .exit-btn.disconnect:hover {
    background: rgba(239, 68, 68, 0.15);
  }
</style>
