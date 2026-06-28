import { useEffect, useRef, useState } from 'react';
import Vapi from '@vapi-ai/web';
import { getSchedulerGreeting, sendVoiceTurn } from '../lib/api.js';

const VAPI_PUBLIC_KEY = import.meta.env.VITE_VAPI_PUBLIC_KEY;
const VAPI_ASSISTANT_ID = import.meta.env.VITE_VAPI_ASSISTANT_ID;

const fallbackGreeting = `Welcome to the Mutual Fund Support Assistant.

One of the most common support topics this week is shown after the first scheduler turn.

How can I help you today?`;

const vapiTransportInstruction = [
  'You are only the voice transport for the Mutual Fund Advisor Scheduler.',
  'Never answer the user directly.',
  'Do not answer scheduling, investment, performance, or fund-comparison questions yourself.',
  'Do not create calendar events, notes, emails, or bookings.',
  'Do not invent booking codes, appointment times, or confirmations.',
  'Stay completely silent unless the web application sends exact text to speak.',
  'Never mention waiting, checking, backend, application, or hold messages.',
  'Never add filler, paraphrases, summaries, or extra guidance.',
].join(' ');

const SCHEDULER_FILLER = 'Let me check that.';
const FILLER_DELAY_MS = 1800;

function speak(vapi, text) {
  if (typeof vapi?.say === 'function') {
    sendAssistantControl(vapi, 'unmute-assistant');
    vapi.say(text, false, true, true);
  }
}

function sendAssistantControl(vapi, control) {
  if (typeof vapi?.send !== 'function') {
    return;
  }
  vapi.send({
    type: 'control',
    control,
  });
}

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

function isPartialUserTranscript(message) {
  if (!message || message.role === 'assistant') {
    return false;
  }
  return message.type === 'transcript' && message.transcriptType === 'partial';
}

function transcriptMessage(message) {
  if (message?.type === 'conversation-update') {
    return message.messages?.[message.messages.length - 1];
  }
  return message;
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

function formatCallError(error, fallback) {
  if (!error) {
    return fallback;
  }
  if (typeof error === 'string') {
    return error;
  }
  if (error.message) {
    return error.message;
  }
  if (error.error?.message) {
    return error.error.message;
  }
  if (error.error) {
    return String(error.error);
  }
  return fallback;
}

function normalizeTranscript(value) {
  return (value || '').toLowerCase().replace(/[^a-z0-9: ]+/g, ' ').replace(/\s+/g, ' ').trim();
}

function isLowSignalTranscript(value) {
  const normalized = normalizeTranscript(value);
  return ['', 'hi', 'hello', 'okay', 'ok', 'yeah', 'yes', 'uh', 'um', 'hmm'].includes(normalized);
}

function isGreetingOnlyTranscript(value) {
  const normalized = normalizeTranscript(value);
  return [
    'hello',
    'hey',
    'hi',
    'hello hey hi',
    'can you hear me',
    'are you there',
    'hey hi',
    'hi hey',
  ].includes(normalized);
}

function isClosingTranscript(value) {
  const normalized = normalizeTranscript(value);
  return [
    'thank you',
    'thanks',
    'thank you so much',
    'thanks a lot',
    'okay thank you',
    'ok thank you',
    'bye',
    'goodbye',
  ].includes(normalized);
}

function hasSupportSignal(value) {
  const normalized = normalizeTranscript(value);
  return ['exit load', 'redeem', 'redemption', 'riskometer', 'benchmark', 'expense ratio', 'fees', 'sip', 'statement']
    .some((term) => normalized.includes(term));
}

function hasSchedulingSignal(value) {
  const normalized = normalizeTranscript(value);
  return ['book', 'schedule', 'reschedule', 'appointment', 'call', 'slot', 'advisor', 'adviser']
    .some((term) => normalized.includes(term));
}

function hasTemporalSignal(value) {
  const normalized = normalizeTranscript(value);
  return [
    'today',
    'tomorrow',
    'day after tomorrow',
    'after tomorrow',
    'next few days',
    'next 3 days',
    'morning',
    'afternoon',
    'evening',
    'monday',
    'tuesday',
    'wednesday',
    'thursday',
    'friday',
    'saturday',
    'sunday',
    'am',
    'pm',
  ].some((term) => normalized.includes(term));
}

function buildSchedulerTranscript(latestTranscript, history) {
  const recentHistory = history.slice(-3);
  const latest = (latestTranscript || '').trim();
  if (!latest) {
    return latest;
  }

  const contextParts = [];
  const needsSupportContext = !hasSupportSignal(latest);
  const needsSchedulingContext = !hasSchedulingSignal(latest);
  const needsTemporalContext = !hasTemporalSignal(latest);

  if (needsSupportContext) {
    const priorSupport = [...recentHistory].reverse().find((entry) => hasSupportSignal(entry));
    if (priorSupport) {
      contextParts.push(priorSupport);
    }
  }

  if (needsSchedulingContext) {
    const priorScheduling = [...recentHistory].reverse().find((entry) => hasSchedulingSignal(entry));
    if (priorScheduling && !contextParts.includes(priorScheduling)) {
      contextParts.push(priorScheduling);
    }
  }

  if (needsTemporalContext) {
    const priorTemporal = [...recentHistory].reverse().find((entry) => hasTemporalSignal(entry));
    if (priorTemporal && !contextParts.includes(priorTemporal)) {
      contextParts.push(priorTemporal);
    }
  }

  contextParts.push(latest);
  return contextParts.join(' ');
}

export default function SchedulerView() {
  const [greeting, setGreeting] = useState(fallbackGreeting);
  const [transcript, setTranscript] = useState('');
  const [turn, setTurn] = useState(null);
  const [callStatus, setCallStatus] = useState('idle');
  const [partialTranscript, setPartialTranscript] = useState('');
  const [finalTranscripts, setFinalTranscripts] = useState([]);
  const [assistantResponse, setAssistantResponse] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const vapiRef = useRef(null);
  const lastFinalTranscriptRef = useRef('');
  const pendingSchedulerRef = useRef(false);
  const queuedTranscriptRef = useRef('');
  const processedTranscriptsRef = useRef(new Map());
  const transcriptHistoryRef = useRef([]);
  const bookingCompletedRef = useRef(false);
  const callStartedAtRef = useRef(0);
  const unmountedRef = useRef(false);
  const fillerTimeoutRef = useRef(null);

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

    unmountedRef.current = false;
    const vapi = new Vapi(VAPI_PUBLIC_KEY);
    vapiRef.current = vapi;

    async function processTranscript(finalTranscript) {
      const normalizedTranscript = normalizeTranscript(finalTranscript);
      const now = Date.now();
      const lastProcessedAt = processedTranscriptsRef.current.get(normalizedTranscript);
      if (finalTranscript === lastFinalTranscriptRef.current || (lastProcessedAt && now - lastProcessedAt < 12000)) {
        return;
      }

      if (pendingSchedulerRef.current) {
        queuedTranscriptRef.current = finalTranscript;
        return;
      }

      sendAssistantControl(vapi, 'mute-assistant');
      pendingSchedulerRef.current = true;
      processedTranscriptsRef.current.set(normalizedTranscript, now);
      lastFinalTranscriptRef.current = finalTranscript;
      setTranscript(finalTranscript);
      setPartialTranscript('');
      let nextHistory = [];
      setFinalTranscripts((currentTranscripts) => {
        nextHistory = [...currentTranscripts, finalTranscript].slice(-5);
        return nextHistory;
      });
      transcriptHistoryRef.current = nextHistory;
      setCallStatus('processing');
      setErrorMessage('');

      if (fillerTimeoutRef.current) {
        window.clearTimeout(fillerTimeoutRef.current);
      }
      fillerTimeoutRef.current = window.setTimeout(() => {
        if (!pendingSchedulerRef.current || unmountedRef.current) {
          return;
        }
        speak(vapi, SCHEDULER_FILLER);
      }, FILLER_DELAY_MS);

      try {
        const schedulerTranscript = buildSchedulerTranscript(finalTranscript, transcriptHistoryRef.current.slice(0, -1));
        const response = await sendVoiceTurn(schedulerTranscript);
        if (unmountedRef.current) {
          return;
        }
        setTurn(response);
        setAssistantResponse(response.reply);
        setCallStatus('active');
        if (response.booking_code) {
          bookingCompletedRef.current = true;
        }
        speak(vapi, response.spoken_reply || response.reply);
      } catch (error) {
        if (unmountedRef.current) {
          return;
        }
        const reply =
          error.message ||
          'The scheduler is taking too long to respond. Please repeat your preferred day and time.';
        setAssistantResponse(reply);
        setErrorMessage(reply);
        setCallStatus('error');
        speak(vapi, 'I had trouble processing that. Please repeat your preferred day and time.');
      } finally {
        if (fillerTimeoutRef.current) {
          window.clearTimeout(fillerTimeoutRef.current);
          fillerTimeoutRef.current = null;
        }
        pendingSchedulerRef.current = false;
        const queuedTranscript = queuedTranscriptRef.current;
        queuedTranscriptRef.current = '';
        if (queuedTranscript && normalizeTranscript(queuedTranscript) !== normalizedTranscript) {
          window.setTimeout(() => {
            if (!pendingSchedulerRef.current && !unmountedRef.current) {
              processTranscript(queuedTranscript);
            }
          }, 250);
        }
      }
    }

    vapi.on('call-start', () => {
      callStartedAtRef.current = Date.now();
      bookingCompletedRef.current = false;
      setCallStatus('active');
      setErrorMessage('');
      sendAssistantControl(vapi, 'mute-assistant');
      vapi.send({
        type: 'add-message',
        message: {
          role: 'system',
          content: vapiTransportInstruction,
        },
        triggerResponseEnabled: false,
      });
      speak(vapi, greeting);
    });

    vapi.on('speech-end', () => {
      sendAssistantControl(vapi, 'mute-assistant');
    });

    vapi.on('call-end', () => {
      setCallStatus('idle');
      pendingSchedulerRef.current = false;
      queuedTranscriptRef.current = '';
      if (fillerTimeoutRef.current) {
        window.clearTimeout(fillerTimeoutRef.current);
        fillerTimeoutRef.current = null;
      }
    });

    vapi.on('message', async (message) => {
      if (message?.type === 'user-interrupted') {
        sendAssistantControl(vapi, 'mute-assistant');
        return;
      }

      const spokenMessage = transcriptMessage(message);

      if (isPartialUserTranscript(spokenMessage)) {
        setPartialTranscript(transcriptText(spokenMessage));
        return;
      }

      const finalTranscript = isFinalUserTranscript(message)
        ? transcriptText(spokenMessage)
        : '';

      if (!finalTranscript || isLowSignalTranscript(finalTranscript)) {
        return;
      }

      if (Date.now() - callStartedAtRef.current < 8000 && isGreetingOnlyTranscript(finalTranscript)) {
        return;
      }

      if (bookingCompletedRef.current && isClosingTranscript(finalTranscript)) {
        setTranscript(finalTranscript);
        setAssistantResponse('Booking is already captured. You can end the call.');
        setCallStatus('active');
        return;
      }

      if (
        bookingCompletedRef.current &&
        !hasTemporalSignal(finalTranscript) &&
        !hasSchedulingSignal(finalTranscript) &&
        !hasSupportSignal(finalTranscript)
      ) {
        return;
      }

      processTranscript(finalTranscript);
    });

    vapi.on('error', (error) => {
      setCallStatus('error');
      setErrorMessage(formatCallError(error, 'Vapi call error. Check assistant configuration and microphone permissions.'));
    });

    return () => {
      unmountedRef.current = true;
      if (fillerTimeoutRef.current) {
        window.clearTimeout(fillerTimeoutRef.current);
        fillerTimeoutRef.current = null;
      }
      vapi.stop();
      vapiRef.current = null;
    };
  }, [greeting]);

  async function startCall() {
    if (!vapiRef.current || callStatus === 'active' || callStatus === 'connecting') {
      return;
    }
    setTranscript('');
    setPartialTranscript('');
    setFinalTranscripts([]);
    transcriptHistoryRef.current = [];
    bookingCompletedRef.current = false;
    callStartedAtRef.current = 0;
    setTurn(null);
    setAssistantResponse('');
    setErrorMessage('');
    lastFinalTranscriptRef.current = '';
    pendingSchedulerRef.current = false;
    queuedTranscriptRef.current = '';
    processedTranscriptsRef.current = new Map();
    setCallStatus('connecting');
    try {
      await vapiRef.current.start(VAPI_ASSISTANT_ID, {
        firstMessage: '',
        firstMessageInterruptionsEnabled: true,
        firstMessageMode: 'assistant-waits-for-user',
        startSpeakingPlan: {
          waitSeconds: 0,
        },
        stopSpeakingPlan: {
          numWords: 0,
          voiceSeconds: 0.15,
          backoffSeconds: 0.4,
          interruptionPhrases: ['stop', 'wait', 'pause', 'hold on', 'actually', 'no', 'change that'],
        },
      });
    } catch (error) {
      setCallStatus('error');
      setErrorMessage(formatCallError(error, 'Unable to start Vapi call.'));
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
          <p className="muted">Set VITE_VAPI_PUBLIC_KEY and VITE_VAPI_ASSISTANT_ID in apps/web/.env.</p>
        )}
        {errorMessage && <p className="error-text">{errorMessage}</p>}
      </section>

      <div className="grid scheduler-grid">
        <div className="result">
          <h3>Transcript</h3>
          <p>{partialTranscript || transcript || 'No transcript yet.'}</p>
          {partialTranscript && <span className="source-badge">Listening live</span>}
          {finalTranscripts.length > 0 && (
            <div className="transcript-history">
              {finalTranscripts.map((line, index) => (
                <small className="muted" key={`${line}-${index}`}>
                  {line}
                </small>
              ))}
            </div>
          )}
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
