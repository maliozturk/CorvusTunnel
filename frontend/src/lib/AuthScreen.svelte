<script>
  import { STATE, claimAndBoot } from './state.svelte.js';
  import { Loader } from 'lucide-svelte';
  import ThemeToggle from './ThemeToggle.svelte';
  import CorvusIcon from './CorvusIcon.svelte';

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
  <!-- Theme toggle in corner -->
  <div class="auth-theme-toggle">
    <ThemeToggle />
  </div>

  <div class="auth-card">
    <!-- Logo & Branding -->
    <div class="auth-logo">
      <div class="auth-logo-icon">
        <CorvusIcon size={28} />
      </div>
      <div class="auth-title">CORVUS_TUNNEL</div>
      <div class="auth-subtitle">Secure Agent Gateway</div>
    </div>
    
    <!-- Token Input -->
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
    
    <!-- Connect Button -->
    <button class="auth-btn" onclick={handleAuth} disabled={loading}>
      {#if loading}
        <Loader size={14} class="spin-anim" />
        <span>AUTHENTICATING...</span>
      {:else}
        <span>CONNECT_SESSION</span>
      {/if}
    </button>
    
    <!-- Error display -->
    {#if STATE.error}
      <div class="auth-error">{STATE.error}</div>
    {/if}

    <!-- Version info -->
    <div class="auth-footer">
      Self-hosted · Direct connection to your server
    </div>
  </div>
</div>

<style>
  .auth-screen {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-primary);
    z-index: 1000;
    padding: 24px;
    font-family: var(--font-mono);
    animation: fadeIn 400ms ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .auth-theme-toggle {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 1001;
  }

  .auth-card {
    width: 100%;
    max-width: 360px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-lg);
    padding: 36px 28px 28px;
    background: var(--bg-secondary);
    text-align: center;
    box-shadow: var(--shadow-lg);
    animation: slideUp 500ms cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  @keyframes slideUp {
    from { opacity: 0; transform: translateY(16px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .auth-logo {
    margin-bottom: 32px;
  }

  .auth-logo-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 56px;
    background: var(--purple-soft);
    border: 1px solid rgba(144, 96, 255, 0.15);
    color: var(--purple);
    border-radius: var(--radius-md);
    margin-bottom: 16px;
    box-shadow: var(--shadow-glow);
  }

  .auth-title {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 2px;
    color: var(--text-primary);
  }

  .auth-subtitle {
    font-size: 11px;
    color: var(--text-secondary);
    margin-top: 6px;
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
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 14px 16px;
    color: var(--text-primary);
    font-family: var(--font-mono);
    font-size: 13px;
    outline: none;
    transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  }

  .auth-input:focus {
    border-color: var(--purple);
    box-shadow: 0 0 0 3px var(--purple-soft);
  }

  .auth-input::placeholder {
    color: var(--text-muted);
  }

  .auth-btn {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    background: var(--btn-primary-bg);
    color: var(--btn-primary-text);
    border: 1px solid var(--btn-primary-border);
    border-radius: var(--radius-sm);
    padding: 14px;
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: all var(--transition-fast);
    letter-spacing: 1px;
  }

  .auth-btn:hover:not(:disabled) {
    background: var(--btn-primary-hover);
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
    padding: 10px 14px;
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: var(--radius-sm);
    background: rgba(239, 68, 68, 0.05);
    word-break: break-word;
    text-align: left;
    line-height: 1.4;
  }

  .auth-footer {
    margin-top: 24px;
    font-size: 10px;
    color: var(--text-dim);
    letter-spacing: 0.5px;
  }
</style>
