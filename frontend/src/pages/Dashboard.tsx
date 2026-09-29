import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Finding, ContributorRisk, ModelAnalysis } from '../api/client';
import {
  ShieldCheck, ShieldAlert, AlertTriangle, Layers,
  Database, Cpu, ArrowRight, RefreshCw, CheckCircle2
} from 'lucide-react';

interface DashboardProps {
  onNavigate: (tab: string) => void;
  onResetDemo?: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [loading, setLoading] = useState(true);
  const [ledgerValid, setLedgerValid] = useState<boolean>(true);
  const [totalBlocks, setTotalBlocks] = useState<number>(0);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [contributors, setContributors] = useState<Record<string, ContributorRisk>>({});
  const [modelAnalysis, setModelAnalysis] = useState<ModelAnalysis | null>(null);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [ledgerRes, findingsRes, datasetRes, modelRes] = await Promise.all([
        api.verifyLedger(),
        api.getFindings(),
        api.getDatasetAnalysis('poisoned'),
        api.getModelAnalysis('trusted'),
      ]);

      setLedgerValid(ledgerRes.valid);
      setTotalBlocks(ledgerRes.total_blocks);
      setFindings(findingsRes);
      if (datasetRes?.analysis?.contributor_risks) {
        setContributors(datasetRes.analysis.contributor_risks);
      }
      if (modelRes?.analysis) {
        setModelAnalysis(modelRes.analysis);
      }
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Compute Overall Pipeline Status
  const isCompromised = !ledgerValid || modelAnalysis?.status === 'COMPROMISED';
  const isReview = modelAnalysis?.status === 'REVIEW' || findings.length > 0;
  const overallStatus = isCompromised ? 'COMPROMISED' : (isReview ? 'REVIEW' : 'TRUSTED');

  // Dynamic Contributor Analytics (no hardcoded fallbacks)
  const contribEntries = Object.entries(contributors);
  const maxRiskEntry = contribEntries.length > 0
    ? contribEntries.reduce((prev, curr) => curr[1].risk_score > prev[1].risk_score ? curr : prev)
    : null;
  const trustedContribCount = contribEntries.filter(([, c]) => c.risk_score <= 10).length;

  return (
    <div className="space-y-6">
      {/* Top Banner: Pipeline Verdict */}
      <div className={`p-6 rounded-2xl border transition-all ${
        overallStatus === 'TRUSTED'
          ? 'bg-emerald-950/30 border-emerald-500/40 glow-green'
          : overallStatus === 'REVIEW'
          ? 'bg-amber-950/30 border-amber-500/40 glow-amber'
          : 'bg-rose-950/30 border-rose-500/40 glow-red'
      }`}>
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className={`p-3.5 rounded-xl ${
              overallStatus === 'TRUSTED'
                ? 'bg-emerald-500/20 text-emerald-400'
                : overallStatus === 'REVIEW'
                ? 'bg-amber-500/20 text-amber-400'
                : 'bg-rose-500/20 text-rose-400'
            }`}>
              {overallStatus === 'TRUSTED' ? (
                <ShieldCheck className="w-8 h-8" />
              ) : overallStatus === 'REVIEW' ? (
                <AlertTriangle className="w-8 h-8" />
              ) : (
                <ShieldAlert className="w-8 h-8" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-black tracking-tight text-white m-0">
                  PIPELINE ASSURANCE VERDICT: {overallStatus}
                </h1>
                <span className={`badge-pill ${
                  overallStatus === 'TRUSTED' ? 'badge-pass' : overallStatus === 'REVIEW' ? 'badge-amber' : 'badge-fail'
                }`}>
                  {overallStatus}
                </span>
              </div>
              <p className="text-sm text-slate-300 mt-1">
                {overallStatus === 'TRUSTED'
                  ? 'All cryptographic signatures, model hashes, and audit ledger blocks are verified and intact.'
                  : overallStatus === 'REVIEW'
                  ? 'Data anomalies or multi-contributor risks flagged for human reviewer inspection.'
                  : 'CRITICAL: Cryptographic tampering detected in ledger or compromised model binary identified!'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button onClick={fetchDashboardData} className="btn-secondary text-xs">
              <RefreshCw className="w-3.5 h-3.5" /> Refresh State
            </button>
            <button onClick={() => onNavigate('inference')} className="btn-primary text-xs">
              Inference Sandbox <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* 4 Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. Tamper-Evident Ledger */}
        <div className="card-panel cursor-pointer hover:border-cyan-500/40" onClick={() => onNavigate('audit')}>
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
            <span>AUDIT LEDGER</span>
            <Database className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black text-white">{totalBlocks}</span>
            <span className="text-xs text-slate-400">Blocks Chained</span>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
            <span className="text-slate-400">Chain Integrity</span>
            <span className={`badge-pill ${ledgerValid ? 'badge-pass' : 'badge-fail'}`}>
              {ledgerValid ? 'VALID & LINKED' : 'BROKEN / TAMPERED'}
            </span>
          </div>
        </div>

        {/* 2. Model Integrity */}
        <div className="card-panel cursor-pointer hover:border-cyan-500/40" onClick={() => onNavigate('integrity')}>
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
            <span>MODEL REGISTRY</span>
            <Cpu className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-black text-white">
              {modelAnalysis?.status || 'TRUSTED'}
            </span>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
            <span className="text-slate-400">Fingerprint Drift</span>
            <span className="text-emerald-400 font-bold">
              {modelAnalysis?.fingerprint_mismatches || 0} / 20 Mismatches
            </span>
          </div>
        </div>

        {/* 3. Findings Count */}
        <div className="card-panel cursor-pointer hover:border-cyan-500/40" onClick={() => onNavigate('integrity')}>
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
            <span>DATA FINDINGS</span>
            <Layers className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black text-white">{findings.length}</span>
            <span className="text-xs text-slate-400">Flagged Anomalies</span>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
            <span className="text-slate-400">Review Queue</span>
            <span className="badge-pill badge-amber">{findings.length} Requires Review</span>
          </div>
        </div>

        {/* 4. Contributor Risk Summary */}
        <div className="card-panel cursor-pointer hover:border-cyan-500/40" onClick={() => onNavigate('integrity')}>
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
            <span>CONTRIBUTOR RISK</span>
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            {loading ? (
              <span className="text-2xl font-black text-slate-400">Scanning...</span>
            ) : maxRiskEntry ? (
              <>
                <span className={`text-2xl font-black ${maxRiskEntry[1].risk_score > 25 ? 'text-rose-400' : 'text-emerald-400'}`}>
                  {maxRiskEntry[1].risk_score.toFixed(1)}%
                </span>
                <span className="text-xs text-slate-400">
                  Max Risk ({maxRiskEntry[0].replace('contributor_', '').toUpperCase()})
                </span>
              </>
            ) : (
              <span className="text-2xl font-black text-slate-400">Scanning...</span>
            )}
          </div>
          <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
            <span className="text-slate-400">Trusted Contribs</span>
            {loading ? (
              <span className="text-xs font-mono text-slate-500">Scanning...</span>
            ) : contribEntries.length > 0 ? (
              <span className="badge-pill badge-pass">
                {trustedContribCount} / {contribEntries.length} Verified (&le;10%)
              </span>
            ) : (
              <span className="badge-pill badge-pass">Scanning...</span>
            )}
          </div>
        </div>
      </div>

      {/* Contributor Risk & System Core Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Contributor Risk Table */}
        <div className="card-panel">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h2 className="text-base font-bold text-white m-0">Multi-Contributor Reputation</h2>
            <button onClick={() => onNavigate('integrity')} className="text-cyan-400 text-xs hover:underline">
              Inspect Data Integrity &rarr;
            </button>
          </div>

          <div className="mt-4 space-y-4">
            {Object.entries(contributors).map(([cid, data]) => {
              const isHigh = data.risk_score > 25;
              return (
                <div key={cid} className="p-3 bg-slate-900/60 rounded-xl border border-slate-800">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-200 text-sm">{cid}</span>
                      <span className={`badge-pill text-[10px] ${isHigh ? 'badge-fail' : 'badge-pass'}`}>
                        {isHigh ? 'SUSPECT / UNTRUSTED' : 'TRUSTED CONTRIBUTOR'}
                      </span>
                    </div>
                    <span className="text-xs font-mono font-bold text-slate-300">
                      Score: {data.risk_score} / 100
                    </span>
                  </div>

                  {/* Risk Progress Bar */}
                  <div className="w-full bg-slate-800 h-2 rounded-full mt-2.5 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        isHigh ? 'bg-gradient-to-r from-amber-500 to-rose-500' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.max(5, data.risk_score)}%` }}
                    />
                  </div>

                  <div className="grid grid-cols-3 gap-2 mt-2 text-[11px] text-slate-400">
                    <div>Mislabeled: <span className="text-slate-200 font-mono">{(data.flag_rate * 100).toFixed(0)}%</span></div>
                    <div>Duplicates: <span className="text-slate-200 font-mono">{(data.duplicate_rate * 100).toFixed(0)}%</span></div>
                    <div>OOD Items: <span className="text-slate-200 font-mono">{(data.OOD_rate * 100).toFixed(0)}%</span></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Cryptographic Architecture Card */}
        <div className="card-panel">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h2 className="text-base font-bold text-white m-0">Cryptographic Provenance Flow</h2>
            <span className="badge-pill badge-cyan text-[10px]">Ed25519 + SHA-256</span>
          </div>

          <div className="mt-4 space-y-3 text-xs">
            <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800 flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0" />
              <div>
                <strong className="text-slate-200">1. Input Hashing:</strong> SHA-256 computed on raw input image bytes, binding canonical pixels to the receipt.
              </div>
            </div>

            <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800 flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0" />
              <div>
                <strong className="text-slate-200">2. Model Binding:</strong> SHA-256 of candidate ONNX binary matched against registered trusted model digest.
              </div>
            </div>

            <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800 flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0" />
              <div>
                <strong className="text-slate-200">3. Deterministic Canonicalization:</strong> Deterministic Canonical JSON (RFC 8785 Principles) serializer ensures identical hash across operating systems.
              </div>
            </div>

            <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800 flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0" />
              <div>
                <strong className="text-slate-200">4. Ed25519 Signing:</strong> Asymmetric digital signature created once inside air-gapped secrets store.
              </div>
            </div>

            <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800 flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0" />
              <div>
                <strong className="text-slate-200">5. Nonce Replay & Audit Ledger:</strong> SQLite state store blocks duplicate replayed nonces; blocks chained via SHA-256.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
