const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

async function request(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;
  const retryCount = options.retryCount ?? 2;
  const timeoutMs = options.timeoutMs ?? 15000;
  const timeoutMessage = options.timeoutMessage;
  let lastError;

  for (let attempt = 0; attempt <= retryCount; attempt += 1) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {}),
        },
        signal: controller.signal,
        ...options,
      });
      window.clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }

      return response.json();
    } catch (error) {
      window.clearTimeout(timeoutId);
      lastError = error;
      const canRetry = error instanceof TypeError || error.name === 'AbortError';
      if (!canRetry || attempt === retryCount) {
        break;
      }
      await delay(350 * (attempt + 1));
    }
  }

  if (lastError instanceof TypeError) {
    throw new Error(`Could not reach the API at ${API_BASE_URL}. Check that the backend is running.`);
  }

  if (lastError?.name === 'AbortError') {
    throw new Error(timeoutMessage || 'The request took too long. Please try again.');
  }

  throw lastError;
}

export function askFAQ(question, sessionId, threadId = 'default') {
  return request('/faq/ask', {
    method: 'POST',
    body: JSON.stringify({
      question,
      session_id: sessionId,
      thread_id: threadId,
    }),
    retryCount: 0,
    timeoutMs: 30000,
    timeoutMessage: 'The FAQ request took too long. Please try again in a moment.',
  });
}

export function generatePulse() {
  return request('/pulse/generate', {
    method: 'POST',
    body: JSON.stringify({
      reviews_csv_path: 'data/reviews/sample_reviews.csv',
      week_start: '2026-06-01',
      week_end: '2026-06-07',
      refresh_vectors: false,
    }),
    retryCount: 0,
    timeoutMs: 45000,
  });
}

export function sendVoiceTurn(transcript) {
  return request('/scheduler/voice-turn', {
    method: 'POST',
    body: JSON.stringify({ transcript }),
    retryCount: 0,
    timeoutMs: 12000,
    timeoutMessage: 'The scheduler took too long to respond. Please try again.',
  });
}

export function getSchedulerGreeting() {
  return request('/scheduler/greeting');
}

export function getPendingApprovals() {
  return request('/approvals/pending');
}

export function approveAction(approvalId) {
  return request(`/approvals/${approvalId}/approve`, {
    method: 'POST',
  });
}

export function rejectAction(approvalId) {
  return request(`/approvals/${approvalId}/reject`, {
    method: 'POST',
  });
}
