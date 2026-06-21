const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json();
}

export function askFAQ(question, sessionId, threadId = 'default') {
  return request('/faq/ask', {
    method: 'POST',
    body: JSON.stringify({
      question,
      session_id: sessionId,
      thread_id: threadId,
    }),
  });
}

export function generatePulse() {
  return request('/pulse/generate', {
    method: 'POST',
    body: JSON.stringify({
      reviews_csv_path: 'data/reviews/sample_reviews.csv',
      week_start: '2026-06-01',
      week_end: '2026-06-07',
    }),
  });
}

export function sendVoiceTurn(transcript) {
  return request('/scheduler/voice-turn', {
    method: 'POST',
    body: JSON.stringify({ transcript }),
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
