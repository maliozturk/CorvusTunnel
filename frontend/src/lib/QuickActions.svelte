<script>
  import { hapticTap } from './state.svelte.js';

  const { onSend } = $props();

  const actions = [
    { label: '⌃C', cmd: '\x03', title: 'Interrupt (Ctrl+C)', cls: 'danger' },
    { label: '/model', cmd: '/model\r\n', title: 'Change model', cls: '' },
    { label: '/usage', cmd: '/usage\r\n', title: 'Show usage stats', cls: '' },
    { label: '/clear', cmd: '/clear\r\n', title: 'Clear screen', cls: '' },
  ];

  function handleAction(action) {
    hapticTap();
    if (onSend) {
      onSend(action.cmd);
    }
  }
</script>

<div class="quick-actions">
  {#each actions as action}
    <button
      class="qa-btn"
      class:danger={action.cls === 'danger'}
      onclick={() => handleAction(action)}
      title={action.title}
    >
      {action.label}
    </button>
  {/each}
</div>

<style>
  .quick-actions {
    display: flex;
    gap: 6px;
    padding: 4px 12px;
    flex-shrink: 0;
    border-top: 1px solid var(--border);
    background: var(--bg-primary);
    overflow-x: auto;
    scrollbar-width: none;
  }

  .quick-actions::-webkit-scrollbar {
    display: none;
  }

  .qa-btn {
    flex-shrink: 0;
    background: var(--bg-card);
    color: var(--text-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-full);
    padding: 5px 12px;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    cursor: pointer;
    transition: all var(--transition-fast);
    user-select: none;
    -webkit-user-select: none;
    touch-action: manipulation;
  }

  .qa-btn:hover {
    color: var(--text-primary);
    border-color: var(--border-hover);
    background: var(--bg-hover);
  }

  .qa-btn:active {
    transform: scale(0.93);
  }

  .qa-btn.danger {
    color: var(--red);
    border-color: rgba(239, 68, 68, 0.2);
    background: rgba(239, 68, 68, 0.04);
  }

  .qa-btn.danger:hover {
    border-color: rgba(239, 68, 68, 0.4);
    background: rgba(239, 68, 68, 0.08);
  }
</style>
