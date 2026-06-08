<script>
  import { STATE } from './state.svelte.js';
  import { api } from './api.js';
  import { X, Folder, ChevronUp, Plus, AlertCircle } from 'lucide-svelte';

  let currentPath = $state('');
  let parentPath = $state(null);
  let directories = $state([]);
  let loading = $state(false);
  let error = $state('');
  
  let newFolderName = $state('');
  let createError = $state('');
  let creating = $state(false);

  // Initialize browser
  $effect(() => {
    if (STATE.showFolderModal) {
      newFolderName = '';
      createError = '';
      error = '';
      loadFolder(STATE.currentFolder || null);
    }
  });

  async function loadFolder(path) {
    loading = true;
    error = '';
    createError = '';
    
    try {
      const url = path ? `/api/browse?path=${encodeURIComponent(path)}` : '/api/browse';
      const r = await api(url);
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        throw new Error(e.detail || 'Failed to list folders');
      }
      
      const data = await r.json();
      currentPath = data.current;
      parentPath = data.parent;
      directories = data.directories || [];
    } catch (err) {
      error = err.message || 'Error loading directory';
      currentPath = 'Error';
    } finally {
      loading = false;
    }
  }

  function handleClose() {
    STATE.showFolderModal = false;
  }

  function selectFolder() {
    if (currentPath && currentPath !== 'Projects') {
      STATE.currentFolder = currentPath;
      localStorage.setItem('corvus_workdir', currentPath);
    }
    handleClose();
  }

  async function createFolder() {
    const name = newFolderName.trim();
    createError = '';
    
    if (!name) {
      createError = 'Folder name is required';
      return;
    }
    
    if (!currentPath || currentPath === 'Projects') {
      createError = 'Navigate into a base directory first';
      return;
    }
    
    creating = true;
    try {
      const r = await api('/api/browse/mkdir', {
        method: 'POST',
        body: JSON.stringify({ parent: currentPath, name }),
      });
      
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        throw new Error(e.detail || 'Failed to create folder');
      }
      
      newFolderName = '';
      loadFolder(currentPath);
    } catch (err) {
      createError = err.message;
    } finally {
      creating = false;
    }
  }
</script>

{#if STATE.showFolderModal}
  <div class="folder-modal-overlay">
    <div class="folder-modal">
      <div class="folder-header">
        <span class="folder-title">WORKSPACE_BROWSER</span>
        <button class="close-btn" onclick={handleClose} aria-label="Close modal">
          <X size={18} />
        </button>
      </div>

      <div class="folder-path">{loading ? 'Loading...' : currentPath || '/'}</div>

      <!-- Create Folder Row -->
      {#if currentPath && currentPath !== 'Projects' && !loading}
        <div class="folder-create-row">
          <input
            type="text"
            class="folder-create-input"
            placeholder="New folder name..."
            bind:value={newFolderName}
            disabled={creating}
            spellcheck="false"
          />
          <button class="folder-create-btn" onclick={createFolder} disabled={creating}>
            <Plus size={16} />
            <span>CREATE</span>
          </button>
        </div>
        {#if createError}
          <div class="folder-error-text">
            <AlertCircle size={12} />
            <span>{createError}</span>
          </div>
        {/if}
      {/if}

      <!-- Directory List -->
      <div class="folder-list">
        {#if loading}
          <div class="folder-status-msg">Reading disk...</div>
        {:else if error}
          <div class="folder-status-msg error">{error}</div>
        {:else}
          <!-- Go Up Option -->
          {#if parentPath !== null && parentPath !== undefined}
            <button class="folder-item up-dir" onclick={() => loadFolder(parentPath)}>
              <ChevronUp size={16} />
              <span class="folder-name">.. (Go Up)</span>
            </button>
          {/if}

          <!-- Empty Directory -->
          {#if directories.length === 0}
            <div class="folder-empty">
              {currentPath === 'Projects' ? 'No directories mapped in ALLOWED_DIRS' : 'Empty folder'}
            </div>
          {/if}

          <!-- Directories -->
          {#each directories as dir}
            <button class="folder-item" onclick={() => loadFolder(dir.path)}>
              <Folder size={16} />
              <span class="folder-name">{dir.name}</span>
            </button>
          {/each}
        {/if}
      </div>

      <div class="folder-footer">
        {#if currentPath && currentPath !== 'Projects' && !loading && !error}
          <button class="select-btn" onclick={selectFolder}>
            SELECT_THIS_FOLDER
          </button>
        {:else}
          <button class="select-btn cancel" onclick={handleClose}>
            CANCEL
          </button>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .folder-modal-overlay {
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

  .folder-modal {
    width: 100%;
    max-width: 420px;
    height: 80vh;
    max-height: 580px;
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

  .folder-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px;
    border-bottom: 1px solid var(--border);
  }

  .folder-title {
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

  .folder-path {
    padding: 12px 16px;
    font-size: 11px;
    color: var(--text-secondary);
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--border);
    word-break: break-all;
  }

  .folder-create-row {
    display: flex;
    padding: 12px 16px 4px 16px;
    gap: 8px;
  }

  .folder-create-input {
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

  .folder-create-input:focus {
    border-color: var(--purple);
  }

  .folder-create-input::placeholder {
    color: var(--text-muted);
  }

  .folder-create-btn {
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

  .folder-create-btn:hover {
    background: var(--bg-surface);
    border-color: var(--border-hover);
  }

  .folder-error-text {
    display: flex;
    align-items: center;
    gap: 4px;
    color: var(--red);
    font-size: 11px;
    padding: 2px 16px 0 16px;
  }

  .folder-list {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    -webkit-overflow-scrolling: touch;
    overscroll-behavior-y: contain;
  }

  .folder-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    background: none;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    padding: 10px 12px;
    color: var(--text-secondary);
    text-align: left;
    font-family: var(--font-mono);
    font-size: 13px;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .folder-item:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
    border-color: var(--border);
  }

  .folder-item:active {
    background: var(--bg-elevated);
  }

  .folder-item.up-dir {
    color: var(--purple);
  }

  .folder-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .folder-empty {
    font-size: 12px;
    color: var(--text-muted);
    text-align: center;
    padding: 32px 0;
  }

  .folder-status-msg {
    font-size: 12px;
    color: var(--text-secondary);
    text-align: center;
    padding: 24px 0;
  }

  .folder-status-msg.error {
    color: var(--red);
  }

  .folder-footer {
    padding: 16px;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: flex-end;
  }

  .select-btn {
    width: 100%;
    background: var(--btn-primary-bg);
    color: var(--btn-primary-text);
    border: 1px solid var(--btn-primary-border);
    border-radius: var(--radius-sm);
    padding: 12px;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    letter-spacing: 1px;
    transition: all var(--transition-fast);
  }

  .select-btn:hover {
    background: var(--btn-primary-hover);
  }

  .select-btn:active {
    transform: scale(0.98);
  }

  .select-btn.cancel {
    background: var(--bg-elevated);
    border-color: var(--border);
    color: var(--text-primary);
  }

  .select-btn.cancel:hover {
    background: var(--bg-surface);
  }
</style>
