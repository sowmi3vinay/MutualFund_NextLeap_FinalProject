import { useState } from 'react';
import FAQView from './views/FAQView.jsx';
import PulseView from './views/PulseView.jsx';
import SchedulerView from './views/SchedulerView.jsx';
import ApprovalCentre from './views/ApprovalCentre.jsx';

const views = [
  { id: 'faq', label: 'Customer', detail: 'Facts-only AI assistant', component: FAQView },
  { id: 'pulse', label: 'Product', detail: 'Weekly pulse', component: PulseView },
  { id: 'scheduler', label: 'Advisor', detail: 'Voice scheduler', component: SchedulerView },
  { id: 'approvals', label: 'Operations', detail: 'Approval centre', component: ApprovalCentre },
];

export default function App() {
  const [activeView, setActiveView] = useState('faq');
  const ActiveComponent = views.find((view) => view.id === activeView).component;

  return (
    <main className="app-shell">
      <aside className="side-rail" aria-label="Application navigation">
        <div className="brand-card">
          <div className="brand-mark">MF</div>
          <div>
            <h1>MF Ops AI</h1>
            <p>Advisor Intelligence Suite</p>
          </div>
        </div>

        <p className="nav-eyebrow">Surfaces</p>
        {views.map((view) => (
          <button
            key={view.id}
            className={activeView === view.id ? 'surface-link active' : 'surface-link'}
            onClick={() => setActiveView(view.id)}
            type="button"
          >
            <span>{view.label}</span>
            <small>{view.detail}</small>
          </button>
        ))}

        <div className="timezone-card">
          <p className="nav-eyebrow">Timezone</p>
          <strong>Asia/Kolkata (IST)</strong>
          <span>Booking slots and pulse cadence are shown in IST.</span>
        </div>
      </aside>

      <section className="workspace">
        <ActiveComponent />
      </section>
    </main>
  );
}
