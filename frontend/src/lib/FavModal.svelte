<script>
  import { STATE, addFavorite, removeFavorite } from './state.svelte.js';
  import { X, Trash2, Plus, CornerDownLeft } from 'lucide-svelte';

  let inputCmd = $state('');

  function handleClose() {
    STATE.showFavModal = false;
  }

  function handleAdd() {
    const cmd = inputCmd.trim();
    if (cmd) {
      addFavorite(cmd);
      inputCmd = '';
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') {
      handleAdd();
    }
  }

  function useFavorite(cmd) {
    if (STATE.term && STATE.ws && STATE.ws.readyState === 1) {
      STATE.ws.send(JSON.stringify({ type: 'input', data: cmd + '\r' }));
      handleClose();
    }
  }
</script>

{#if STATE.showFavModal}
  <div class="fav-modal-overlay">
    <div class="fav-modal">
      <div class="fav-header">
        <span class="fav-title">SAVED_COMMANDS</span>
        <button class="close-btn" onclick={handleClose} aria-label="Close modal">
          <X size={18} />
        </button>
      </div>

      <div class="fav-list">
        {#if STATE.favorites.length === 0}
          <div class="fav-empty">
            No saved commands. Enter a command below to save it.
          </div>
        {:else}
          {#each STATE.favorites as fav}
            <div class="fav-item">
              <button class="fav-use-btn" onclick={() => useFavorite(fav)} title="Run command">
                <CornerDownLeft size={14} class="use-icon" />
                <span class="fav-text">{fav}</span>
              </button>
              <button class="fav-delete-btn" onclick={() => removeFavorite(fav)} title="Delete shortcut">
                <Trash2 size={14} />
              </button>
            </div>
          {/each}
        {/if}
      </div>

      <div class="fav-add-row">
        <input
          type="text"
          class="fav-add-input"
          placeholder="Type a command to save..."
          bind:value={inputCmd}
          onkeydown={handleKeyDown}
          spellcheck="false"
        />
        <button class="fav-add-btn" onclick={handleAdd} aria-label="Add favorite">
          <Plus size={16} />
          <span>SAVE</span>
        </button>
      </div>

      <div class="fav-footer">
        <button class="footer-close-btn" onclick={handleClose}>
          CLOSE
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .fav-modal-overlay {
    position: fixed;
    inset: 0;
    background: var(--bg-modal-overlay);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2000;
    padding: 16px;
    font-family: var(--font-mono);
    animation: fadeIn 200ms ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .fav-modal {
    width: 100%;
    max-width: 400px;
    max-height: 520px;
    height: 70vh;
    background: var(--bg-secondary);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-lg);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-shadow: var(--shadow-lg);
    animation: scaleIn 250ms cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  @keyframes scaleIn {
    from { opacity: 0; transform: scale(0.95); }
    to { opacity: 1; transform: scale(1); }
  }

  .fav-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px;
    border-bottom: 1px solid var(--border);
  }

  .fav-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
    color: var(--text-primary);
  }

  .close-btn {
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color var(--transition-fast);
    border-radius: var(--radius-xs);
  }

  .close-btn:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }

  .fav-list {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    -webkit-overflow-scrolling: touch;
    overscroll-behavior-y: contain;
  }

  .fav-empty {
    font-size: 12px;
    color: var(--text-muted);
    text-align: center;
    padding: 32px 0;
    line-height: 1.5;
  }

  .fav-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--bg-card);
    overflow: hidden;
  }

  .fav-use-btn {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: none;
    color: var(--text-primary);
    padding: 10px 12px;
    font-family: var(--font-mono);
    font-size: 12px;
    text-align: left;
    cursor: pointer;
    overflow: hidden;
    transition: background var(--transition-fast);
  }

  .fav-use-btn:hover {
    background: var(--bg-hover);
  }

  :global(.use-icon) {
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .fav-use-btn:hover :global(.use-icon) {
    color: var(--purple);
  }

  .fav-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .fav-delete-btn {
    background: none;
    border: none;
    border-left: 1px solid var(--border);
    color: var(--text-muted);
    padding: 10px 14px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all var(--transition-fast);
  }

  .fav-delete-btn:hover {
    color: var(--red);
    background: rgba(239, 68, 68, 0.05);
  }

  .fav-add-row {
    display: flex;
    padding: 12px 16px;
    border-top: 1px solid var(--border);
    gap: 8px;
    background: var(--bg-tertiary);
  }

  .fav-add-input {
    flex: 1;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 8px 12px;
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--text-primary);
    outline: none;
    transition: border-color var(--transition-fast);
  }

  .fav-add-input:focus {
    border-color: var(--purple);
  }

  .fav-add-input::placeholder {
    color: var(--text-muted);
  }

  .fav-add-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    background: var(--bg-elevated);
    color: var(--text-primary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 8px 14px;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .fav-add-btn:hover {
    background: var(--bg-surface);
    border-color: var(--border-hover);
  }

  .fav-footer {
    padding: 16px;
    border-top: 1px solid var(--border);
  }

  .footer-close-btn {
    width: 100%;
    background: var(--bg-elevated);
    color: var(--text-primary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 12px;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    letter-spacing: 1px;
    transition: all var(--transition-fast);
  }

  .footer-close-btn:hover {
    background: var(--bg-surface);
    border-color: var(--border-hover);
  }

  .footer-close-btn:active {
    transform: scale(0.98);
  }
</style>
