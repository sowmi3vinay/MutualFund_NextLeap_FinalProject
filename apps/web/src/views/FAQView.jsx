import { useMemo, useState } from 'react';
import { askFAQ } from '../lib/api.js';

const THREADS_KEY = 'faq_threads_v2';
const SESSION_KEY = 'faq_session_id_v2';

const suggestions = [
  'What is the exit load for HDFC ELSS Tax Saver?',
  'Why was exit load charged?',
  'Explain expense ratio in simple words',
  'What is the benchmark for HDFC Flexi Cap Fund?',
  'What about its riskometer?',
  'Which fund should I invest in for highest return?',
];

const supportedFunds = [
  { code: 'ELSS', name: 'HDFC ELSS Tax Saver', detail: 'Tax saver' },
  { code: 'FC', name: 'HDFC Flexi Cap Fund', detail: 'Equity - Flexi cap' },
  { code: 'BAF', name: 'HDFC Balanced Advantage Fund', detail: 'Hybrid allocation' },
  { code: 'MID', name: 'HDFC Mid-Cap Opportunities Fund', detail: 'Equity - Mid cap' },
];

function createLocalSessionId() {
  const existingSessionId = window.localStorage.getItem(SESSION_KEY);
  if (existingSessionId) {
    return existingSessionId;
  }
  const newSessionId = `faq-web-${Date.now().toString(36)}`;
  window.localStorage.setItem(SESSION_KEY, newSessionId);
  return newSessionId;
}

function loadThreads() {
  try {
    return JSON.parse(window.localStorage.getItem(THREADS_KEY)) || [];
  } catch {
    return [];
  }
}

function saveThreads(threads) {
  window.localStorage.setItem(THREADS_KEY, JSON.stringify(threads));
}

function createThread(initialTitle = 'New chat') {
  return {
    id: `thread-${Date.now().toString(36)}`,
    title: initialTitle,
    messages: [],
    updatedAt: new Date().toISOString(),
  };
}

function titleFromQuestion(question) {
  const trimmed = question.trim();
  if (!trimmed) {
    return 'New chat';
  }
  return trimmed.length > 48 ? `${trimmed.slice(0, 45)}...` : trimmed;
}

export default function FAQView() {
  const [sessionId] = useState(createLocalSessionId);
  const [threads, setThreads] = useState(() => {
    const savedThreads = loadThreads();
    return savedThreads.length ? savedThreads : [createThread()];
  });
  const [activeThreadId, setActiveThreadId] = useState(() => threads[0]?.id);
  const [question, setQuestion] = useState('');
  const [loadingThreadId, setLoadingThreadId] = useState(null);

  const activeThread = useMemo(
    () => threads.find((thread) => thread.id === activeThreadId) || threads[0],
    [threads, activeThreadId]
  );

  function persistThreads(nextThreads) {
    setThreads(nextThreads);
    saveThreads(nextThreads);
  }

  function updateThread(threadId, updater) {
    setThreads((currentThreads) => {
      const nextThreads = currentThreads.map((thread) =>
        thread.id === threadId
          ? { ...updater(thread), updatedAt: new Date().toISOString() }
          : thread
      );
      saveThreads(nextThreads);
      return nextThreads;
    });
  }

  function startNewThread() {
    const thread = createThread();
    const nextThreads = [thread, ...threads];
    persistThreads(nextThreads);
    setActiveThreadId(thread.id);
    setQuestion('');
  }

  function chooseThread(threadId) {
    setActiveThreadId(threadId);
    setQuestion('');
  }

  async function submitQuestion(prompt = question) {
    const text = prompt.trim();
    const currentThreadId = activeThread?.id || activeThreadId;
    if (!text || loadingThreadId === currentThreadId) {
      return;
    }

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      text,
    };
    updateThread(currentThreadId, (thread) => ({
      ...thread,
      title: thread.messages.length ? thread.title : titleFromQuestion(text),
      messages: [...thread.messages, userMessage],
    }));

    setQuestion('');
    setLoadingThreadId(currentThreadId);
    try {
      const response = await askFAQ(text, sessionId, currentThreadId);
      const assistantMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        text: response.answer,
        citations: response.citations || [],
        sourceBadge: response.source_badge,
        originalQuestion: text,
        rewrittenQuestion: response.rewritten_question,
        memory: response.memory,
      };
      updateThread(currentThreadId, (thread) => ({
        ...thread,
        messages: [...thread.messages, assistantMessage],
      }));
    } catch (error) {
      updateThread(currentThreadId, (thread) => ({
        ...thread,
        messages: [
          ...thread.messages,
          {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            text: error.message,
            citations: [],
            sourceBadge: 'Connection issue',
          },
        ],
      }));
    } finally {
      setLoadingThreadId((currentLoadingThreadId) =>
        currentLoadingThreadId === currentThreadId ? null : currentLoadingThreadId
      );
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    submitQuestion();
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submitQuestion();
    }
  }

  return (
    <div className="faq-surface">
      <section className="fund-strip" aria-label="Supported mutual funds">
        <div>
          <p className="eyebrow">Supported corpus</p>
          <h2>Explore supported mutual funds</h2>
          <p className="muted">Official HDFC, AMFI, SEBI, Kuvera, and generated fee-explainer sources.</p>
        </div>
        <div className="fund-row">
          {supportedFunds.map((fund) => (
            <button
              className="fund-chip"
              key={fund.code}
              type="button"
              onClick={() => setQuestion(`What is the exit load for ${fund.name}?`)}
            >
              <span>{fund.code}</span>
              <strong>{fund.name}</strong>
              <small>{fund.detail}</small>
            </button>
          ))}
        </div>
      </section>

      <section className="chat-shell">
        <aside className="chat-history">
          <div className="chat-history-header">
            <div>
              <p className="eyebrow">Chat history</p>
              <p className="muted">Browser session threads</p>
            </div>
            <button className="icon-button" type="button" onClick={startNewThread} aria-label="New chat">
              +
            </button>
          </div>
          {threads.map((thread) => (
            <button
              className={thread.id === activeThread?.id ? 'thread-link active' : 'thread-link'}
              key={thread.id}
              type="button"
              onClick={() => chooseThread(thread.id)}
            >
              <span>{thread.title}</span>
              <small>{thread.messages.length} messages</small>
            </button>
          ))}
        </aside>

        <section className="conversation-panel">
          <div className="conversation-header">
            <div>
              <p className="eyebrow">Conversation</p>
              <h2>{activeThread?.title || 'New chat'}</h2>
            </div>
            <button className="secondary-button" type="button" onClick={startNewThread}>
              New chat
            </button>
          </div>

          <div className="suggestion-row">
            {suggestions.map((suggestion) => (
              <button
                className="suggestion-chip"
                key={suggestion}
                type="button"
                onClick={() => submitQuestion(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>

          <div className="message-list">
            {activeThread?.messages.length ? (
              activeThread.messages.map((message) => (
                <article className={`message ${message.role}`} key={message.id}>
                  <p>{message.text}</p>
                  {message.sourceBadge && <span className="source-badge">{message.sourceBadge}</span>}
                  {message.memory && (
                    <span className="memory-badge">
                      {message.memory.last_scheme || 'No scheme'} {message.memory.last_topic ? `- ${message.memory.last_topic}` : ''}
                    </span>
                  )}
                  {message.rewrittenQuestion && message.rewrittenQuestion !== message.originalQuestion && (
                    <small className="muted">Contextual query: {message.rewrittenQuestion}</small>
                  )}
                  {message.citations?.length > 0 && (
                    <div className="citation-list">
                      {message.citations.map((citation) =>
                        citation.url ? (
                          <a href={citation.url} key={citation.url} target="_blank" rel="noreferrer">
                            {citation.title}
                          </a>
                        ) : (
                          <span key={citation.source_id || citation.title}>
                            {citation.title} · internal generated source
                          </span>
                        )
                      )}
                    </div>
                  )}
                </article>
              ))
            ) : (
              <div className="empty-chat">Start with a suggestion above or type a question below.</div>
            )}
            {loadingThreadId === activeThread?.id && <div className="message assistant">Retrieving grounded sources...</div>}
          </div>

          <form className="chat-composer" onSubmit={handleSubmit}>
            <textarea
              aria-label="Ask a facts-only mutual fund question"
              placeholder="Ask about exit load, fees, benchmarks, riskometer, or statements..."
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={handleKeyDown}
            />
            <div className="composer-footer">
              <span>Facts-only RAG - citations required - session memory on</span>
              <button className="send-button" type="submit" disabled={loadingThreadId === activeThread?.id}>
                Send
              </button>
            </div>
          </form>
        </section>
      </section>
    </div>
  );
}
