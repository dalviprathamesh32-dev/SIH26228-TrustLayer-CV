import React from 'react';
import { Shield, Cpu, Database, Activity, RefreshCw } from 'lucide-react';

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
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'integrity', label: 'Integrity Analysis', icon: Cpu },
    { id: 'inference', label: 'Inference & Provenance', icon: Shield },
    { id: 'audit', label: 'Audit Ledger', icon: Database },
  ];

  return (
    <header className="border-b border-slate-800/80 bg-slate-950/90 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Left */}
        <div className="flex items-center gap-3">
          <div className="p-2 bg-cyan-950/60 border border-cyan-500/40 rounded-lg text-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.2)]">
            <Shield className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-base tracking-wider text-slate-100 uppercase">
                TrustLayer-CV
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950/80 text-cyan-400 border border-cyan-500/40 tracking-wider">
                SIH26228 | AIR-GAPPED
              </span>
            </div>
            <p className="text-[11px] font-mono text-slate-400 tracking-tight">
              Cryptographic Integrity & Provenance Defense Layer
            </p>
          </div>
        </div>

        {/* 4 Navigation Tabs - horizontally spaced with flex, gap-4 */}
        <nav className="flex items-center gap-2 sm:gap-4 bg-slate-900/80 p-1.5 rounded-xl border border-slate-800">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                  isActive
                    ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/50 shadow-[0_0_10px_rgba(6,182,212,0.15)] font-bold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Quick Demo Reset Button */}
        <button
          onClick={onResetDemo}
          disabled={resetting}
          title="Restore certified baseline state and clean ledger"
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700/80 transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${resetting ? 'animate-spin text-cyan-400' : 'text-slate-400'}`} />
          <span>{resetting ? 'RESETTING...' : 'RESET DEMO'}</span>
        </button>
      </div>
    </header>
  );
};
