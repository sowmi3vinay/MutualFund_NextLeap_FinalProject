import { useEffect, useState } from 'react';
import { approveAction, getPendingApprovals, rejectAction } from '../lib/api.js';

export default function ApprovalCentre() {
  const [approvals, setApprovals] = useState([]);
  const [status, setStatus] = useState('loading');

  function refreshApprovals() {
    setStatus('loading');
    getPendingApprovals()
      .then((data) => {
        setApprovals(data.actions || []);
        setStatus('idle');
      })
      .catch(() => setStatus('error'));
  }

  useEffect(() => {
    refreshApprovals();
  }, []);

  async function handleDecision(approvalId, decision) {
    setStatus('loading');
    try {
      const updatedAction =
        decision === 'approve' ? await approveAction(approvalId) : await rejectAction(approvalId);
      setApprovals((currentApprovals) =>
        currentApprovals.map((approval) =>
          approval.approval_id === approvalId ? updatedAction : approval
        )
      );
      setStatus('idle');
    } catch {
      setStatus('error');
    }
  }

  function formatDetails(details) {
    if (!details) {
      return 'No details provided';
    }
    return Object.entries(details)
      .map(([key, value]) => `${key}: ${value}`)
      .join(', ');
  }

  return (
    <div className="panel">
      <h2>Approval Centre</h2>
      <p className="muted">MCP actions wait here until a human approves or rejects them.</p>

      {status === 'loading' && <p>Loading approvals...</p>}
      {status === 'error' && <p>Could not load approvals.</p>}

      <div className="grid">
        {approvals.map((approval) => (
          <div className="item" key={approval.approval_id}>
            <h3>{approval.action_type || approval.type}</h3>
            <p>Status: {approval.status}</p>
            <p>Booking code: {approval.booking_code}</p>
            <p>Action details: {approval.summary}</p>
            <p className="muted">{formatDetails(approval.details)}</p>
            {approval.execution_result && <p>Tool result: {approval.execution_result}</p>}
            <div className="actions">
              <button
                className="primary-button"
                type="button"
                disabled={approval.status !== 'pending'}
                onClick={() => handleDecision(approval.approval_id, 'approve')}
              >
                Approve
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={approval.status !== 'pending'}
                onClick={() => handleDecision(approval.approval_id, 'reject')}
              >
                Reject
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
