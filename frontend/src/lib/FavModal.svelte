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
    background: rgba(0, 0, 0, 0.85);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2000;
    padding: 16px;
    font-family: var(--font-mono);
  }

  .fav-modal {
    width: 100%;
    max-width: 400px;
    max-height: 520px;
    height: 70vh;
    background: #000000;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    display: flex;
    flex-direction: column;
    overflow: hidden;
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
    color: #ffffff;
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
  }

  .close-btn:hover {
    color: #ffffff;
  }

  .fav-list {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    -webkit-overflow-scrolling: touch;
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
    background: #080808;
    overflow: hidden;
  }

  .fav-use-btn {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: none;
    color: #ffffff;
    padding: 10px 12px;
    font-family: var(--font-mono);
    font-size: 12px;
    text-align: left;
    cursor: pointer;
    overflow: hidden;
    transition: background var(--transition-fast);
  }

  .fav-use-btn:hover {
    background: #141414;
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
    background: #080808;
  }

  .fav-add-input {
    flex: 1;
    background: #000000;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 8px 12px;
    font-family: var(--font-mono);
    font-size: 12px;
    color: #ffffff;
    outline: none;
  }

  .fav-add-input:focus {
    border-color: var(--purple);
  }

  .fav-add-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    background: #141414;
    color: #ffffff;
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
    background: #202020;
    border-color: var(--text-secondary);
  }

  .fav-footer {
    padding: 16px;
    border-top: 1px solid var(--border);
    background: #000000;
  }

  .footer-close-btn {
    width: 100%;
    background: #141414;
    color: #ffffff;
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
    background: #202020;
    border-color: var(--text-secondary);
  }
</style>
