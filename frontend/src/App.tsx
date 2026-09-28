import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { IntegrityAnalysis } from './pages/IntegrityAnalysis';
import { InferenceVerify } from './pages/InferenceVerify';
import { AuditReport } from './pages/AuditReport';
import { api } from './api/client';
import { CheckCircle2 } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [resetting, setResetting] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const handleResetDemo = async () => {
    try {
      setResetting(true);
      const res = await api.resetDemo();
      setToastMessage(res.message || 'Demo state restored to certified baseline.');
      setTimeout(() => setToastMessage(null), 3500);
      // Reload current tab
      window.location.reload();
    } catch (err: any) {
      alert(`Reset failed: ${err.message}`);
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-emerald-950 border border-emerald-500 text-emerald-200 px-4 py-3 rounded-xl shadow-2xl flex items-center gap-2.5 animate-bounce text-xs font-semibold">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          {toastMessage}
        </div>
      )}

      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onResetDemo={handleResetDemo}
        resetting={resetting}
      />

      {/* Main Page Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && (
          <Dashboard onNavigate={setActiveTab} onResetDemo={handleResetDemo} />
        )}
        {activeTab === 'integrity' && <IntegrityAnalysis />}
        {activeTab === 'inference' && <InferenceVerify />}
        {activeTab === 'audit' && <AuditReport />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>TrustLayer-CV &copy; 2026 | PS SIH26228 Computer Vision Integrity Assurance</span>
          <div className="flex items-center gap-3 font-mono text-[11px]">
            <span className="text-cyan-400">Ed25519 Canonical Signing</span>
            <span>&bull;</span>
            <span className="text-emerald-400">SHA-256 Hash Chaining</span>
            <span>&bull;</span>
            <span className="text-amber-400">Offline Air-Gapped Mode</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
