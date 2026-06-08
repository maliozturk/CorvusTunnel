<script>
  import { STATE, manualReconnect } from './state.svelte.js';
  import { Wifi, WifiOff, Loader } from 'lucide-svelte';
</script>

{#if STATE.wsStatus !== 'connected'}
  <div
    class="status-bar"
    class:connecting={STATE.wsStatus === 'connecting'}
    class:disconnected={STATE.wsStatus === 'disconnected' || STATE.wsStatus === 'exited'}
    role="status"
    aria-live="polite"
  >
    {#if STATE.wsStatus === 'connecting'}
      <Loader size={12} class="spin-anim" />
      <span>RECONNECTING{STATE.reconnectAttempt > 0 ? ` (${STATE.reconnectAttempt}/${STATE.maxReconnect})` : ''}...</span>
    {:else if STATE.wsStatus === 'exited'}
      <WifiOff size={12} />
      <span>SESSION ENDED</span>
    {:else}
      <WifiOff size={12} />
      <span>DISCONNECTED</span>
      <button class="reconnect-btn" onclick={manualReconnect}>
        TAP TO RECONNECT
      </button>
    {/if}
  </div>
{:else}
  <div class="status-bar online" role="status" aria-live="polite">
    <span class="status-dot"></span>
    <span>CONNECTED</span>
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
