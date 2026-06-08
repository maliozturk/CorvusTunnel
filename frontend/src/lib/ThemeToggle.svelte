<script>
  import { STATE, toggleTheme, hapticTap } from './state.svelte.js';
  import { Sun, Moon } from 'lucide-svelte';

  function handleToggle() {
    hapticTap();
    toggleTheme();
  }
</script>

<button
  class="theme-toggle"
  onclick={handleToggle}
  title={STATE.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
  aria-label={STATE.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
>
  <div class="toggle-track" class:light={STATE.theme === 'light'}>
    <div class="toggle-thumb" class:light={STATE.theme === 'light'}>
      {#if STATE.theme === 'dark'}
        <Moon size={12} strokeWidth={2.5} />
      {:else}
        <Sun size={12} strokeWidth={2.5} />
      {/if}
    </div>
  </div>
</button>

<style>
  .theme-toggle {
    background: none;
    border: none;
    cursor: pointer;
    padding: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .toggle-track {
    width: 36px;
    height: 20px;
    background: var(--bg-elevated);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-full);
    position: relative;
    transition: background var(--transition-smooth), border-color var(--transition-smooth);
  }

  .toggle-track.light {
    background: var(--purple-soft);
    border-color: var(--purple);
  }

  .toggle-thumb {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 14px;
    height: 14px;
    background: var(--purple);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ffffff;
    transition: transform var(--transition-spring);
  }

  .toggle-thumb.light {
    transform: translateX(16px);
    background: var(--purple);
    color: #ffffff;
  }
</style>
