import { useEffect, useRef, useState } from 'react';
import Vapi from '@vapi-ai/web';
import { getSchedulerGreeting, sendVoiceTurn } from '../lib/api.js';

const VAPI_PUBLIC_KEY = import.meta.env.VITE_VAPI_PUBLIC_KEY;
const VAPI_ASSISTANT_ID = import.meta.env.VITE_VAPI_ASSISTANT_ID;

const fallbackGreeting = `Welcome to the Mutual Fund Support Assistant.

One of the most common support topics this week is shown after the first scheduler turn.

How can I help you today?`;

function transcriptText(message) {
  return (
    message?.transcript ||
    message?.text ||
    message?.message?.content ||
    message?.content ||
    ''
  ).trim();
}

function isFinalUserTranscript(message) {
  if (!message || message.role === 'assistant') {
    return false;
  }
  if (message.type === 'transcript' && message.transcriptType === 'final') {
    return true;
  }
  if (message.type === 'conversation-update') {
    const lastMessage = message.messages?.[message.messages.length - 1];
    return lastMessage?.role === 'user' && Boolean(transcriptText(lastMessage));
  }
  return false;
}

function callStatusLabel(status) {
  if (!VAPI_PUBLIC_KEY || !VAPI_ASSISTANT_ID) {
    return 'Add Vapi environment variables to enable live voice calls.';
  }
  if (status === 'connecting') {
    return 'Connecting to Vapi...';
  }
  if (status === 'active') {
    return 'Call active. Speak your scheduling request.';
  }
  if (status === 'processing') {
    return 'Scheduler is processing the latest transcript...';
  }
  if (status === 'error') {
    return 'Call issue. Check Vapi configuration and browser microphone permissions.';
  }
  return 'Ready to start a Vapi call.';
}

export default function SchedulerView() {
  const [greeting, setGreeting] = useState(fallbackGreeting);
  const [transcript, setTranscript] = useState('');
  const [turn, setTurn] = useState(null);
  const [callStatus, setCallStatus] = useState('idle');
  const [assistantResponse, setAssistantResponse] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const vapiRef = useRef(null);
  const lastFinalTranscriptRef = useRef('');

  useEffect(() => {
    getSchedulerGreeting()
      .then((payload) => {
        if (payload.greeting) {
          setGreeting(payload.greeting);
        }
      })
      .catch(() => {
        setGreeting(fallbackGreeting);
      });
  }, []);

  useEffect(() => {
    if (!VAPI_PUBLIC_KEY || !VAPI_ASSISTANT_ID) {
      return undefined;
    }

    const vapi = new Vapi(VAPI_PUBLIC_KEY);
    vapiRef.current = vapi;

    vapi.on('call-start', () => {
      setCallStatus('active');
      setErrorMessage('');
      if (typeof vapi.say === 'function') {
        vapi.say(greeting, false);
      }
    });

    vapi.on('call-end', () => {
      setCallStatus('idle');
    });

    vapi.on('message', async (message) => {
      const finalTranscript = isFinalUserTranscript(message)
        ? transcriptText(message.type === 'conversation-update' ? message.messages?.[message.messages.length - 1] : message)
        : '';

      if (!finalTranscript || finalTranscript === lastFinalTranscriptRef.current) {
        return;
      }

      lastFinalTranscriptRef.current = finalTranscript;
      setTranscript(finalTranscript);
      setCallStatus('processing');
      setErrorMessage('');

      try {
        const response = await sendVoiceTurn(finalTranscript);
        setTurn(response);
        setAssistantResponse(response.reply);
        setCallStatus('active');
        if (typeof vapi.say === 'function') {
          vapi.say(response.reply, false);
        }
      } catch (error) {
        const reply = error.message || 'Scheduler request failed.';
        setAssistantResponse(reply);
        setErrorMessage(reply);
        setCallStatus('error');
        if (typeof vapi.say === 'function') {
          vapi.say('I could not reach the scheduler service. Please try again.', false);
        }
      }
    });

    vapi.on('error', (error) => {
      setCallStatus('error');
      setErrorMessage(error?.message || 'Vapi call error.');
    });

    return () => {
      vapi.stop();
      vapiRef.current = null;
    };
  }, [greeting]);

  async function startCall() {
    if (!vapiRef.current || callStatus === 'active' || callStatus === 'connecting') {
      return;
    }
    setTranscript('');
    setTurn(null);
    setAssistantResponse('');
    setErrorMessage('');
    lastFinalTranscriptRef.current = '';
    setCallStatus('connecting');
    try {
      await vapiRef.current.start(VAPI_ASSISTANT_ID);
    } catch (error) {
      setCallStatus('error');
      setErrorMessage(error?.message || 'Unable to start Vapi call.');
    }
  }

  function endCall() {
    if (!vapiRef.current) {
      return;
    }
    vapiRef.current.stop();
    setCallStatus('idle');
  }

  const vapiConfigured = Boolean(VAPI_PUBLIC_KEY && VAPI_ASSISTANT_ID);
  const callActive = ['connecting', 'active', 'processing'].includes(callStatus);

  return (
    <div className="panel scheduler-panel">
      <div className="scheduler-header">
        <div>
          <p className="eyebrow">Advisor voice flow</p>
          <h2>Voice Scheduler</h2>
        </div>
        <span className={`status-pill ${callActive ? 'active' : ''}`}>{callStatusLabel(callStatus)}</span>
      </div>

      <div className="result">
        <h3>Greeting</h3>
        {(turn?.greeting || greeting).split('\n').map((line, index) => (
          <p key={`${line}-${index}`}>{line}</p>
        ))}
      </div>

      <section className="voice-console" aria-label="Vapi call controls">
        <div className="actions">
          <button
            className="primary-button"
            type="button"
            onClick={startCall}
            disabled={!vapiConfigured || callActive}
          >
            Start Call
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={endCall}
            disabled={!vapiConfigured || !callActive}
          >
            End Call
          </button>
        </div>
        {!vapiConfigured && (
          <p className="muted">Set VITE_VAPI_PUBLIC_KEY and VITE_VAPI_ASSISTANT_ID in apps/web/.env.local.</p>
        )}
        {errorMessage && <p className="error-text">{errorMessage}</p>}
      </section>

      <div className="grid scheduler-grid">
        <div className="result">
          <h3>Transcript</h3>
          <p>{transcript || 'No transcript yet.'}</p>
        </div>
        <div className="result">
          <h3>Assistant Response</h3>
          <p>{assistantResponse || 'The scheduler response will appear after the user speaks.'}</p>
        </div>
        <div className="result">
          <h3>Booking Code</h3>
          <p>{turn?.booking_code || 'Not generated'}</p>
        </div>
      </div>

      {turn && (
        <div className="result">
          <h3>Scheduler Result</h3>
          <p>Detected intent: {turn.intent}</p>
          <p>Advisor slot: {turn.slot || 'No slot selected'}</p>
          <p>Pending MCP actions: {turn.pending_actions_created ? 'Created' : 'Not created'}</p>
        </div>
      )}
    </div>
  );
}
