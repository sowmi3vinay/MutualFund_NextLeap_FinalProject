import { useState } from 'react';
import { generatePulse } from '../lib/api.js';

export default function PulseView() {
  const [pulse, setPulse] = useState(null);
  const [status, setStatus] = useState('idle');

  async function handleGenerate() {
    setStatus('loading');
    try {
      setPulse(await generatePulse());
      setStatus('idle');
    } catch (error) {
      setPulse({ top_theme: 'Error', weekly_pulse: error.message, actions: [] });
      setStatus('error');
    }
  }

  return (
    <div className="panel">
      <h2>Weekly Product Pulse</h2>
      <p className="muted">Generate a product pulse and fee explainer from review data.</p>
      <button className="primary-button" type="button" onClick={handleGenerate}>
        {status === 'loading' ? 'Generating...' : 'Generate Pulse'}
      </button>

      {pulse && (
        <div className="result">
          <h3>{pulse.top_theme}</h3>
          <p>{pulse.weekly_pulse}</p>
          <h3>Action Ideas</h3>
          {pulse.actions?.map((action) => (
            <p key={action}>{action}</p>
          ))}
        </div>
      )}
    </div>
  );
}
