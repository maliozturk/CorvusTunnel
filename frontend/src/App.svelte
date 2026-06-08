<script>
  import { onMount } from 'svelte';
  import { STATE, claimAndBoot, bootApp, handleLogout } from './lib/state.svelte.js';
  import { api } from './lib/api.js';
  import AuthScreen from './lib/AuthScreen.svelte';
  import LauncherScreen from './lib/LauncherScreen.svelte';
  import TerminalScreen from './lib/TerminalScreen.svelte';
  import FolderModal from './lib/FolderModal.svelte';
  import FavModal from './lib/FavModal.svelte';
  import HistoryPanel from './lib/HistoryPanel.svelte';
  import OnboardingWalkthrough from './lib/OnboardingWalkthrough.svelte';
  import ExitConfirmDialog from './lib/ExitConfirmDialog.svelte';
  import CorvusIcon from './lib/CorvusIcon.svelte';
  import ThemeToggle from './lib/ThemeToggle.svelte';
  import { Bell, X } from 'lucide-svelte';

  onMount(async () => {
    // 1. Check url hash for token (direct/LAN mode)
    const hash = window.location.hash;
    let hashToken = null;
    if (hash && hash.length > 1) {
      const params = new URLSearchParams(hash.substring(1));
      hashToken = params.get('token');
    }
    
    // 2. Fallback: check window._corvusAutoToken (set by relay HTML rewriter)
    if (!hashToken && window._corvusAutoToken) {
      hashToken = window._corvusAutoToken;
      delete window._corvusAutoToken;
    }
    
    if (hashToken) {
      // Clear hash from URL immediately for security
      window.history.replaceState(null, '', window.location.pathname);
      localStorage.removeItem('corvus_token');
      STATE.token = '';
      await claimAndBoot(hashToken);
    } else if (STATE.token) {
      // We have a stored token, let's verify it with the server
      try {
        const resp = await fetch('/api/browse', {
          headers: { 'Authorization': 'Bearer ' + STATE.token },
        });
        if (resp.ok) {
          bootApp();
        } else {
          handleLogout();
        }
      } catch (e) {
        // network issue, keep token but proceed to launcher
        bootApp();
      }
    }

    // 3. Check for local browser notification permissions request
    checkNotificationStatus();
    
    // 4. Register service worker for PWA caching
    registerServiceWorker();

    // 5. Setup beforeunload handler for exit prevention
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  });

  // ── beforeunload handler ──────────────────────────────────────
  function handleBeforeUnload(e) {
    if (STATE.phase === 'terminal' && STATE.wsStatus === 'connected') {
      e.preventDefault();
      e.returnValue = 'You have an active terminal session. Are you sure you want to leave?';
      return e.returnValue;
    }
  }

  function checkNotificationStatus() {
    if (!('Notification' in window)) return;
    if (Notification.permission === 'default' && !localStorage.getItem('corvus_notif_dismissed')) {
      STATE.showNotifBanner = true;
    }
  }

  function enableNotifications() {
    Notification.requestPermission().then((perm) => {
      STATE.showNotifBanner = false;
      if (perm === 'granted') {
        localStorage.setItem('corvus_notif_enabled', 'true');
        new Notification('CorvusTunnel', {
          body: 'Notifications active! Get notified when coding agents finish execution.',
          icon: '/static/icons/icon-192.png'
        });
      }
    });
  }

  function dismissNotifBanner() {
    STATE.showNotifBanner = false;
    localStorage.setItem('corvus_notif_dismissed', 'true');
  }

  function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/static/sw.js')
        .then(() => console.log('[PWA] Service worker registered'))
        .catch((err) => console.warn('[PWA] Service worker registration failed:', err));
    }
  }
</script>

<main class="app-layout">
  
  {#if !STATE.token}
    <AuthScreen />
  {:else}
    <!-- Top banner asking for notification access -->
    {#if STATE.showNotifBanner}
      <div class="notification-request-banner">
        <div class="banner-left">
          <Bell size={14} color="var(--purple)" style="flex-shrink: 0;" />
          <span>Enable push notifications to alert you when your agent completes jobs.</span>
        </div>
        <div class="banner-right">
          <button class="banner-btn" onclick={enableNotifications}>ENABLE</button>
          <button class="banner-close" onclick={dismissNotifBanner} aria-label="Dismiss banner">
            <X size={14} />
          </button>
        </div>
      </div>
    {/if}

    <!-- Screen Phase selection -->
    {#if STATE.phase === 'launcher'}
      <div class="dashboard-header">
        <div class="header-logo"><CorvusIcon size={18} /> CORVUS_TUNNEL</div>
        <div class="header-actions">
          <button class="header-logs-btn" onclick={() => STATE.showHistoryPanel = true} title="Logs History">
            VIEW_HISTORY
          </button>
          <ThemeToggle />
        </div>
      </div>
      <LauncherScreen />
    {:else}
      <TerminalScreen />
    {/if}

    <!-- Global Modals & Overlays -->
    <FolderModal />
    <FavModal />
    <HistoryPanel />
    <ExitConfirmDialog />
    <OnboardingWalkthrough />
  {/if}

</main>

<style>
  .app-layout {
    display: flex;
    flex-direction: column;
    height: 100vh;
    height: 100dvh;
    overflow: hidden;
    background: var(--bg-primary);
    color: var(--text-primary);
    transition: background var(--transition-smooth), color var(--transition-smooth);
  }

  .notification-request-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
    padding: 10px 14px;
    z-index: 500;
    font-family: var(--font-sans);
    font-size: 11px;
    flex-shrink: 0;
    animation: slideDown 300ms ease-out;
  }

  @keyframes slideDown {
    from { opacity: 0; transform: translateY(-100%); }
    to { opacity: 1; transform: translateY(0); }
  }

  .banner-left {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-secondary);
    min-width: 0;
  }

  .banner-left span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .banner-right {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }

  .banner-btn {
    background: var(--btn-primary-bg);
    color: var(--btn-primary-text);
    border: none;
    border-radius: var(--radius-sm);
    padding: 4px 10px;
    font-family: var(--font-mono);
    font-size: 9px;
    font-weight: 700;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .banner-btn:hover {
    background: var(--btn-primary-hover);
  }

  .banner-btn:active {
    transform: scale(0.95);
  }

  .banner-close {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 2px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-xs);
    transition: all var(--transition-fast);
  }

  .banner-close:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }

  .dashboard-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 16px;
    padding-top: calc(18px + var(--safe-top));
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    font-family: var(--font-mono);
    transition: background var(--transition-smooth);
  }

  .header-logo {
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: var(--text-primary);
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .header-logs-btn {
    background: none;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
    padding: 6px 12px;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .header-logs-btn:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
    border-color: var(--border-hover);
  }

  .header-logs-btn:active {
    transform: scale(0.97);
  }
</style>
