<script>
  let prompt = '';
  let pending = false;
  let status = 'Ready';
  let attachInput;

  let messages = [
    {
      role: 'assistant',
      content:
        'Sydney is online. Local model active. Weaviate memory connected.'
    }
  ];

  async function sendPrompt() {
    const text = prompt.trim();
    if (!text || pending) return;

    prompt = '';
    pending = true;
    status = 'Generating';
    messages = [...messages, { role: 'user', content: text }];

    try {
      const response = await fetch('/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: text })
      });
      const data = await response.json();
      const content = response.ok ? data.response : `Error: ${data.error ?? 'Unknown error'}`;
      messages = [...messages, { role: 'assistant', content }];
      status = response.ok ? 'Ready' : 'Error';
    } catch (error) {
      const content = `Error: ${error.message}`;
      messages = [...messages, { role: 'assistant', content }];
      status = 'Offline';
    } finally {
      pending = false;
    }
  }

  async function saveMessage(index) {
    const assistantMessage = messages[index];
    const previousUser = [...messages.slice(0, index)].reverse().find((message) => message.role === 'user');
    if (!assistantMessage || assistantMessage.role !== 'assistant') {
      return;
    }
    status = 'Saving';
    const response = await fetch('/memory/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: previousUser?.content ?? '',
        response: assistantMessage.content,
        kind: 'workflow'
      })
    });
    status = response.ok ? 'Saved to memory' : 'Save failed';
  }

  async function uploadFile(file) {
    if (!file) return;

    status = `Uploading ${file.name}`;
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch('/memory/upload', {
      method: 'POST',
      body: formData
    });
    const data = await response.json();
    status = response.ok
      ? `Uploaded ${data.chunks} chunk${data.chunks === 1 ? '' : 's'}`
      : `Upload failed: ${data.error ?? 'unknown error'}`;
  }

  function onComposerKeydown(event) {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      sendPrompt();
    }
  }
</script>

<svelte:head>
  <title>Sydney Console</title>
</svelte:head>

<div class="app-shell">
  <aside class="sidebar">
    <div class="sidebar-top">
      <div class="brand-lockup">
        <div class="sidebar-label">Ethical Hacking Project</div>
      </div>
    </div>

    <div class="sidebar-meta">
      <div class="meta-card">
        <div class="meta-row">
          <span>Backend</span>
          <code>On</code>
        </div>
        <div class="meta-row">
          <span>Model</span>
          <code>Local</code>
        </div>
        <div class="meta-row">
          <span>Port</span>
          <code>5000</code>
        </div>
      </div>
    </div>
  </aside>

  <main class="main-panel">
    <header class="topbar">
      <div>
        <div class="topbar-label">Local Security Assistant</div>
        <div class="topbar-title">Conversation</div>
      </div>

      <div class="topbar-actions">
        <input
          bind:this={attachInput}
          type="file"
          accept=".txt,.md,.log,.json,.csv"
          hidden
          on:change={(event) => uploadFile(event.currentTarget.files?.[0])}
        />
        <div class="status-pill {pending ? 'busy' : ''}">
          <span class="status-dot"></span>
          <span>{status}</span>
        </div>
      </div>
    </header>

    <section class="chat-panel">
      <div class="messages">
        {#each messages as message, index}
          <article class="message {message.role}">
            <div class="message-avatar">
              {message.role === 'assistant' ? 'S' : 'Y'}
            </div>
            <div class="message-content">
              <div class="message-head">
                <div class="message-role">
                  {message.role === 'assistant' ? 'Sydney' : 'You'}
                </div>
                {#if message.role === 'assistant'}
                  <button
                    class="more-button"
                    title="Save this response to memory"
                    on:click={() => saveMessage(index)}
                  >
                    <span></span><span></span><span></span>
                  </button>
                {/if}
              </div>
              <div class="message-body">{message.content}</div>
            </div>
          </article>
        {/each}
      </div>

      <div class="composer-wrap">
        <div class="composer">
          <textarea
            bind:value={prompt}
            rows="2"
            placeholder="Message Sydney..."
            on:keydown={onComposerKeydown}
          ></textarea>

          <div class="composer-footer">
            <div class="composer-hint">Press Ctrl+Enter to send</div>
            <div class="composer-actions">
              <button class="icon-button small" title="Upload file to memory" on:click={() => attachInput.click()}>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 5v14M5 12h14" />
                </svg>
              </button>
              <button class="send-button small" on:click={sendPrompt} disabled={pending}>
                <span>Send</span>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M5 12h12M13 4l8 8-8 8" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  </main>
</div>
