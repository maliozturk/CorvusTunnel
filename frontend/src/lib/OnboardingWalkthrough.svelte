<script>
  import { STATE, completeOnboarding } from './state.svelte.js';
  import { FolderOpen, Cpu, Smartphone, ChevronRight, ChevronLeft, X } from 'lucide-svelte';
  import CorvusIcon from './CorvusIcon.svelte';

  let currentSlide = $state(0);

  const slides = [
    {
      icon: 'terminal',
      title: 'Welcome to CorvusTunnel',
      desc: 'Control your AI coding agents remotely from any device. Claude Code, Codex, and Antigravity — all from your phone.',
      highlight: 'Self-hosted tunnel — no third-party servers between you and your machine.',
    },
    {
      icon: 'folder',
      title: 'Pick a Workspace',
      desc: 'Choose the project folder where your AI agent will work. You can browse your server\'s file system or create new directories.',
      highlight: 'Tap the folder card on the launcher screen to browse.',
    },
    {
      icon: 'cpu',
      title: 'Select Your Agent',
      desc: 'Choose which AI coding agent to use. Available agents are detected automatically from your server environment.',
      highlight: 'Only agents installed on your server will be selectable.',
    },
    {
      icon: 'phone',
      title: 'Terminal Controls',
      desc: 'Use the keypad bar to send special keys (Ctrl, Esc, arrows). Swipe the keypad left/right for more keys. Two-finger swipe to scroll terminal history.',
      highlight: 'Enjoying CorvusTunnel? ⭐ Star us on GitHub to support the project!',
    },
  ];

  function nextSlide() {
    if (currentSlide < slides.length - 1) {
      currentSlide++;
    } else {
      handleFinish();
    }
  }

  function prevSlide() {
    if (currentSlide > 0) {
      currentSlide--;
    }
  }

  function handleFinish() {
    completeOnboarding();
  }

  function handleSkip() {
    completeOnboarding();
  }

  const CurrentIcon = $derived.by(() => {
    switch (slides[currentSlide].icon) {
      case 'terminal': return CorvusIcon;
      case 'folder': return FolderOpen;
      case 'cpu': return Cpu;
      case 'phone': return Smartphone;
      default: return CorvusIcon;
    }
  });
</script>

{#if STATE.showOnboarding}
  <div class="onboarding-overlay" role="dialog" aria-modal="true" aria-label="Welcome walkthrough">
    <div class="onboarding-card">
      <!-- Skip button -->
      <button class="skip-btn" onclick={handleSkip} aria-label="Skip walkthrough">
        <X size={18} />
      </button>

      <!-- Slide content -->
      <div class="slide-content">
        <div class="slide-icon-wrap">
          <CurrentIcon size={32} strokeWidth={1.5} />
        </div>
        
        <h2 class="slide-title">{slides[currentSlide].title}</h2>
        <p class="slide-desc">{slides[currentSlide].desc}</p>
        
        <div class="slide-highlight">
          {slides[currentSlide].highlight}
        </div>
      </div>

      <!-- Dots indicator -->
      <div class="slide-dots">
        {#each slides as _, i}
          <button
            class="dot"
            class:active={i === currentSlide}
            onclick={() => currentSlide = i}
            aria-label={`Go to slide ${i + 1}`}
          ></button>
        {/each}
      </div>

      <!-- Navigation -->
      <div class="slide-nav">
        {#if currentSlide > 0}
          <button class="nav-btn back" onclick={prevSlide}>
            <ChevronLeft size={14} />
            <span>BACK</span>
          </button>
        {:else}
          <div></div>
        {/if}

        <button class="nav-btn next" onclick={nextSlide}>
          <span>{currentSlide === slides.length - 1 ? 'GET STARTED' : 'NEXT'}</span>
          {#if currentSlide < slides.length - 1}
            <ChevronRight size={14} />
          {/if}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .onboarding-overlay {
    position: fixed;
    inset: 0;
    background: var(--bg-modal-overlay);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 5000;
    padding: 24px;
    animation: fadeIn 300ms ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .onboarding-card {
    width: 100%;
    max-width: 380px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-lg);
    padding: 32px 24px 24px;
    position: relative;
    box-shadow: var(--shadow-lg);
    animation: slideUp 350ms cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  @keyframes slideUp {
    from { opacity: 0; transform: translateY(20px) scale(0.95); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }

  .skip-btn {
    position: absolute;
    top: 12px;
    right: 12px;
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-sm);
    transition: all var(--transition-fast);
  }

  .skip-btn:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }

  .slide-content {
    text-align: center;
    min-height: 200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }

  .slide-icon-wrap {
    width: 64px;
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--purple-soft);
    border: 1px solid rgba(144, 96, 255, 0.15);
    border-radius: var(--radius-md);
    color: var(--purple);
    margin-bottom: 20px;
  }

  .slide-title {
    font-family: var(--font-sans);
    font-size: 20px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 12px;
    line-height: 1.2;
  }

  .slide-desc {
    font-family: var(--font-sans);
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.6;
    margin-bottom: 16px;
    max-width: 320px;
  }

  .slide-highlight {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--purple);
    background: var(--purple-soft);
    border: 1px solid rgba(144, 96, 255, 0.12);
    border-radius: var(--radius-sm);
    padding: 8px 14px;
    line-height: 1.4;
    max-width: 300px;
  }

  .slide-dots {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin: 24px 0 20px;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--bg-surface);
    border: none;
    cursor: pointer;
    padding: 0;
    transition: all var(--transition-fast);
  }

  .dot.active {
    background: var(--purple);
    width: 20px;
    border-radius: var(--radius-full);
  }

  .slide-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .nav-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 10px 16px;
    border-radius: var(--radius-sm);
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .nav-btn:active {
    transform: scale(0.97);
  }

  .nav-btn.back {
    background: none;
    border: 1px solid var(--border);
    color: var(--text-secondary);
  }

  .nav-btn.back:hover {
    border-color: var(--border-hover);
    color: var(--text-primary);
  }

  .nav-btn.next {
    background: var(--btn-primary-bg);
    color: var(--btn-primary-text);
    border: 1px solid var(--btn-primary-border);
  }

  .nav-btn.next:hover {
    background: var(--btn-primary-hover);
  }
</style>
