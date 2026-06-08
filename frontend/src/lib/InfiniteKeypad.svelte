<script>
  import { STATE, hapticTap } from './state.svelte.js';
  
  const { onSend } = $props();

  // Define the key sequence for the infinite carousel
  const keys = [
    { label: 'PASTE', seq: null, type: 'paste' },
    { label: 'CTRL', seq: null, type: 'ctrl' },
    { label: 'ESC', seq: '\x1b', type: 'key' },
    { label: 'TAB', seq: '\t', type: 'key' },
    { label: '▲', seq: '\x1b[A', type: 'arrow' },
    { label: '▼', seq: '\x1b[B', type: 'arrow' },
    { label: '⇧▲', seq: '\x1b[1;2A', type: 'arrow' },
    { label: '⇧▼', seq: '\x1b[1;2B', type: 'arrow' },
    { label: '◀', seq: '\x1b[D', type: 'arrow' },
    { label: '▶', seq: '\x1b[C', type: 'arrow' },
    { label: '⏎', seq: '\r', type: 'enter' },
    { label: 'HOME', seq: '\x1b[H', type: 'key' },
    { label: 'END', seq: '\x1b[F', type: 'key' },
    { label: 'PGUP', seq: '\x1b[5~', type: 'key' },
    { label: 'PGDN', seq: '\x1b[6~', type: 'key' },
    { label: 'DEL', seq: '\x1b[3~', type: 'key' },
  ];

  // Triple the keys for infinite scroll illusion
  const tripleKeys = [...keys, ...keys, ...keys];

  let ctrlActive = $state(false);
  let scrollContainer = $state(null);
  let isResetting = false;

  async function handleKeyTap(key) {
    hapticTap();
    
    if (key.type === 'paste') {
      try {
        const text = await navigator.clipboard.readText();
        if (text && onSend) {
          onSend(text);
        }
      } catch (e) {
        console.warn('Clipboard read failed:', e);
        alert('Could not access clipboard automatically. Please focus the input area and use your keyboard to paste.');
      }
      return;
    }

    if (key.type === 'ctrl') {
      ctrlActive = !ctrlActive;
      return;
    }

    let seq = key.seq;
    
    // If ctrl is active, modify the sequence
    if (ctrlActive && seq && seq.length === 1) {
      const code = seq.toUpperCase().charCodeAt(0);
      if (code >= 64 && code <= 95) {
        seq = String.fromCharCode(code - 64);
      }
      ctrlActive = false;
    }

    if (seq && onSend) {
      onSend(seq);
    }
  }

  // Handle infinite scroll wrapping
  function handleScroll() {
    if (!scrollContainer || isResetting) return;
    
    const el = scrollContainer;
    const singleWidth = el.scrollWidth / 3;
    
    if (el.scrollLeft <= 2) {
      isResetting = true;
      el.scrollLeft = singleWidth + 2;
      requestAnimationFrame(() => { isResetting = false; });
    } else if (el.scrollLeft >= singleWidth * 2 - 2) {
      isResetting = true;
      el.scrollLeft = singleWidth - 2;
      requestAnimationFrame(() => { isResetting = false; });
    }
  }

  // Center on mount
  import { onMount } from 'svelte';
  onMount(() => {
    if (scrollContainer) {
      const singleWidth = scrollContainer.scrollWidth / 3;
      scrollContainer.scrollLeft = singleWidth;
    }
  });
</script>

<div class="keypad-carousel">
  <div 
    class="keypad-scroll" 
    bind:this={scrollContainer}
    onscroll={handleScroll}
  >
    {#each tripleKeys as key, i}
      <button
        class="kp-btn"
        class:ctrl={key.type === 'ctrl'}
        class:ctrl-active={key.type === 'ctrl' && ctrlActive}
        class:arrow={key.type === 'arrow'}
        class:enter={key.type === 'enter'}
        class:paste={key.type === 'paste'}
        onclick={() => handleKeyTap(key)}
      >
        {key.label}
      </button>
    {/each}
  </div>
</div>

<style>
  .keypad-carousel {
    flex-shrink: 0;
    border-top: 1px solid var(--border);
    background: var(--bg-primary);
    padding: 6px 0;
    padding-bottom: calc(6px + var(--safe-bottom));
  }

  .keypad-scroll {
    display: flex;
    gap: 6px;
    overflow-x: auto;
    padding: 0 12px;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
    scroll-behavior: auto;
  }

  .keypad-scroll::-webkit-scrollbar {
    display: none;
  }

  .kp-btn {
    flex-shrink: 0;
    min-width: var(--touch-min);
    height: var(--touch-min);
    background: var(--bg-card);
    color: var(--text-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0 12px;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    user-select: none;
    -webkit-user-select: none;
    touch-action: manipulation;
    transition: all var(--transition-fast);
  }

  .kp-btn:active {
    background: var(--bg-elevated);
    transform: scale(0.93);
  }

  .kp-btn.ctrl {
    color: var(--text-secondary);
    min-width: 52px;
  }

  .kp-btn.ctrl-active {
    background: var(--purple-soft);
    border-color: var(--purple);
    color: var(--purple);
    box-shadow: var(--shadow-glow);
  }

  .kp-btn.arrow {
    font-size: 14px;
    min-width: 40px;
    color: var(--text-muted);
  }

  .kp-btn.arrow:active {
    color: var(--text-primary);
  }

  .kp-btn.enter {
    color: var(--green);
    font-size: 16px;
    min-width: 48px;
  }

  .kp-btn.paste {
    color: var(--purple);
    border-color: rgba(144, 96, 255, 0.4);
    background: rgba(144, 96, 255, 0.05);
    min-width: 58px;
  }

  .kp-btn.paste:active {
    background: rgba(144, 96, 255, 0.15);
  }
</style>
