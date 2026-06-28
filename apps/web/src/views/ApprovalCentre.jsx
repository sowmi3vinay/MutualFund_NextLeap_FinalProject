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
    const displayKeys = ['assigned_advisor', 'customer_topic', 'slot', 'intent', 'transcript_summary', 'purpose', 'auto_send'];
    return displayKeys
      .filter((key) => details[key] !== undefined && details[key] !== null && details[key] !== '')
      .map((key) => `${key.replaceAll('_', ' ')}: ${details[key]}`)
      .join(', ');
  }

  function sortedActions(actions) {
    const statusRank = {
      pending: 0,
      approved: 1,
      completed: 2,
      failed: 3,
      rejected: 4,
    };
    return [...actions].sort((left, right) => {
      const leftRank = statusRank[left.status] ?? 5;
      const rightRank = statusRank[right.status] ?? 5;
      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }
      return right.approval_id.localeCompare(left.approval_id);
    });
  }

  const pendingApprovals = sortedActions(approvals.filter((approval) => approval.status === 'pending'));
  const recentApprovals = sortedActions(approvals.filter((approval) => approval.status !== 'pending')).slice(0, 6);

  function renderApproval(approval) {
    const isPending = approval.status === 'pending';
    return (
      <div className="item approval-card" key={approval.approval_id}>
        <div className="approval-card-header">
          <h3>{approval.action_type || approval.type}</h3>
          <span className={`approval-status ${approval.status}`}>{approval.status}</span>
        </div>
        <p>Booking code: {approval.booking_code || 'Not available'}</p>
        <p>Assigned advisor: {approval.assigned_advisor || approval.details?.assigned_advisor || 'Not assigned'}</p>
        <p>Action details: {approval.summary}</p>
        <p className="muted">{formatDetails(approval.details)}</p>
        {approval.execution_result && <p>Tool result: {approval.execution_result}</p>}
        {approval.tool_result?.calendar_link && (
          <a className="calendar-link" href={approval.tool_result.calendar_link} target="_blank" rel="noreferrer">
            Open calendar event
          </a>
        )}
        {isPending && (
          <div className="actions">
            <button
              className="primary-button"
              type="button"
              onClick={() => handleDecision(approval.approval_id, 'approve')}
            >
              Approve
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => handleDecision(approval.approval_id, 'reject')}
            >
              Reject
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="panel">
      <h2>Approval Centre</h2>
      <p className="muted">MCP actions wait here until a human approves or rejects them.</p>

      {status === 'loading' && <p>Loading approvals...</p>}
      {status === 'error' && <p>Could not load approvals.</p>}

      {status === 'idle' && pendingApprovals.length === 0 && (
        <div className="empty-state">
          <h3>No pending approvals</h3>
          <p className="muted">New scheduler bookings will create Calendar, Notes, and Email Draft actions here.</p>
        </div>
      )}

      {pendingApprovals.length > 0 && (
        <>
          <h3 className="section-label">Pending actions</h3>
          <div className="grid">{pendingApprovals.map(renderApproval)}</div>
        </>
      )}

      {recentApprovals.length > 0 && (
        <>
          <h3 className="section-label">Recent decisions</h3>
          <div className="grid">{recentApprovals.map(renderApproval)}</div>
        </>
      )}
    </div>
  );
}
