<script>
  import { STATE, claimAndBoot } from './state.svelte.js';
  import { Terminal } from 'lucide-svelte';

  let tokenValue = $state('');
  let loading = $state(false);

  async function handleAuth() {
    const token = tokenValue.trim();
    if (!token) {
      STATE.error = 'Please enter a valid token.';
      return;
    }
    
    loading = true;
    STATE.error = '';
    try {
      await claimAndBoot(token);
    } catch (e) {
      STATE.error = e.message || 'Authentication failed.';
    } finally {
      loading = false;
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') {
      handleAuth();
    }
  }
</script>

<div class="auth-screen">
  <div class="auth-card">
    <div class="auth-logo">
      <div class="auth-logo-icon">
        <Terminal size={32} strokeWidth={1.5} />
      </div>
      <div class="auth-title">CORVUS_TUNNEL</div>
      <div class="auth-subtitle">Secure Agent Gateway</div>
    </div>
    
    <div class="auth-field">
      <label for="tokenInput" class="auth-label">Access Token</label>
      <input
        type="password"
        id="tokenInput"
        class="auth-input"
        placeholder="Paste boot token..."
        bind:value={tokenValue}
        onkeydown={handleKeyDown}
        disabled={loading}
        autocomplete="off"
        spellcheck="false"
      />
    </div>
    
    <button class="auth-btn" onclick={handleAuth} disabled={loading}>
      {loading ? 'AUTHENTICATING...' : 'CONNECT_SESSION'}
    </button>
    
    {#if STATE.error}
      <div class="auth-error">{STATE.error}</div>
    {/if}
  </div>
</div>

<style>
  .auth-screen {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #000000;
    z-index: 1000;
    padding: 24px;
    font-family: var(--font-mono);
  }

  .auth-card {
    width: 100%;
    max-width: 360px;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 32px 24px;
    background: #000000;
    text-align: center;
  }

  .auth-logo {
    margin-bottom: 28px;
  }

  .auth-logo-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border: 1px solid var(--border);
    color: var(--purple);
    border-radius: var(--radius-sm);
    margin-bottom: 16px;
  }

  .auth-title {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 2px;
    color: #ffffff;
  }

  .auth-subtitle {
    font-size: 11px;
    color: var(--text-secondary);
    margin-top: 4px;
    letter-spacing: 1px;
  }

  .auth-field {
    text-align: left;
    margin-bottom: 20px;
  }

  .auth-label {
    display: block;
    font-size: 10px;
    color: var(--text-secondary);
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  .auth-input {
    width: 100%;
    background: #080808;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 12px 14px;
    color: #ffffff;
    font-family: var(--font-mono);
    font-size: 13px;
    outline: none;
    transition: border-color var(--transition-fast);
  }

  .auth-input:focus {
    border-color: var(--purple);
  }

  .auth-btn {
    width: 100%;
    background: #ffffff;
    color: #000000;
    border: 1px solid #ffffff;
    border-radius: var(--radius-sm);
    padding: 12px;
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: all var(--transition-fast);
    letter-spacing: 1px;
  }

  .auth-btn:hover:not(:disabled) {
    background: #e6e6e6;
    border-color: #e6e6e6;
  }

  .auth-btn:active:not(:disabled) {
    transform: scale(0.98);
  }

  .auth-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .auth-error {
    margin-top: 16px;
    font-size: 12px;
    color: var(--red);
    padding: 10px;
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: var(--radius-sm);
    background: rgba(239, 68, 68, 0.05);
    word-break: break-word;
  }
</style>
