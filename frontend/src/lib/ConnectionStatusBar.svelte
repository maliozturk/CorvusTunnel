<script>
  import { STATE, manualReconnect } from './state.svelte.js';
  import { WifiOff, Loader } from 'lucide-svelte';

  let status = $derived(
    STATE.wsStatus === 'exited' ? 'exited'
    : STATE.reconnecting || STATE.wsStatus === 'connecting' ? 'reconnecting'
    : STATE.connected ? 'connected'
    : 'disconnected'
  );
</script>

{#if status === 'connected'}
  <div class="status-bar online" role="status" aria-live="polite"
       title="This device stays connected while corvustunnel is running. If it drops, it reconnects automatically — or reopen this page.">
    <span class="status-dot"></span>
    <span>CONNECTED</span>
  </div>
{:else if status === 'reconnecting'}
  <div class="status-bar connecting" role="status" aria-live="polite">
    <Loader size={12} class="spin-anim" />
    <span>RECONNECTING{STATE.reconnectAttempt > 0 ? ` (${STATE.reconnectAttempt}/${STATE.maxReconnect})` : ''}...</span>
  </div>
{:else if status === 'exited'}
  <div class="status-bar disconnected" role="status" aria-live="polite">
    <WifiOff size={12} />
    <span>SESSION ENDED</span>
    <button class="reconnect-btn" onclick={manualReconnect}>RECONNECT</button>
  </div>
{:else}
  <div class="status-bar disconnected" role="status" aria-live="polite">
    <WifiOff size={12} />
    <span>DISCONNECTED</span>
    <button class="reconnect-btn" onclick={manualReconnect}>RECONNECT</button>
  </div>
{/if}

<style>
  .status-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 5px 12px;
    font-family: var(--font-mono);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
    flex-shrink: 0;
    transition: background var(--transition-fast), color var(--transition-fast);
  }

  .status-bar.online {
    background: rgba(16, 185, 129, 0.06);
    color: var(--green);
    border-bottom: 1px solid rgba(16, 185, 129, 0.15);
  }

  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--green);
    animation: pulse-dot 2s ease-in-out infinite;
  }

  @keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .status-bar.connecting {
    background: rgba(245, 158, 11, 0.06);
    color: var(--yellow);
    border-bottom: 1px solid rgba(245, 158, 11, 0.15);
  }

  .status-bar.disconnected {
    background: rgba(239, 68, 68, 0.06);
    color: var(--red);
    border-bottom: 1px solid rgba(239, 68, 68, 0.15);
  }

  :global(.spin-anim) {
    animation: spin 1.5s linear infinite;
  }

  @keyframes spin {
    100% { transform: rotate(360deg); }
  }

  .reconnect-btn {
    background: rgba(239, 68, 68, 0.1);
    color: var(--red);
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: var(--radius-full);
    padding: 2px 8px;
    font-family: var(--font-mono);
    font-size: 8px;
    font-weight: 700;
    cursor: pointer;
    transition: all var(--transition-fast);
    margin-left: 4px;
  }

  .reconnect-btn:hover {
    background: rgba(239, 68, 68, 0.2);
  }

  .reconnect-btn:active {
    transform: scale(0.95);
  }
</style>
