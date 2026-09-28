import React from 'react';
import { ShieldCheck, Database, Cpu, Activity, RefreshCw } from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onResetDemo: () => void;
  resetting: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  onResetDemo,
  resetting,
}) => {
  const tabs = [
    { id: 'dashboard', label: '1. Dashboard', icon: Activity },
    { id: 'integrity', label: '2. Integrity Analysis', icon: Cpu },
    { id: 'inference', label: '3. Inference + Verify', icon: ShieldCheck },
    { id: 'audit', label: '4. Audit + Report', icon: Database },
  ];

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo & Subtitle */}
        <div className="flex items-center gap-3">
          <div className="p-2 bg-cyan-950/80 border border-cyan-500/30 rounded-lg text-cyan-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-slate-100 tracking-tight">TrustLayer-CV</span>
              <span className="badge-pill badge-cyan text-[10px]">SIH26228</span>
              <span className="badge-pill badge-pass text-[10px]">OFFLINE AIR-GAPPED</span>
            </div>
            <p className="text-xs text-slate-400">Computer Vision Provenance & Integrity Assurance</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="flex items-center gap-1 bg-slate-900/60 p-1 rounded-xl border border-slate-800">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>

        {/* Reset Demo Button */}
        <button
          onClick={onResetDemo}
          disabled={resetting}
          title="Restore certified baseline state and clean ledger"
          className="btn-secondary text-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${resetting ? 'animate-spin text-cyan-400' : ''}`} />
          {resetting ? 'Resetting Demo...' : 'Reset Demo State'}
        </button>
      </div>
    </header>
  );
};
