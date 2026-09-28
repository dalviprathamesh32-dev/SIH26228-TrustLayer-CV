import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Finding, ContributorRisk, ModelAnalysis } from '../api/client';
import {
  Cpu, Layers, Filter
} from 'lucide-react';

export const IntegrityAnalysis: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'data' | 'model'>('data');
  const [selectedDataset, setSelectedDataset] = useState<string>('poisoned');
  const [selectedModel, setSelectedModel] = useState<string>('trusted');

  const [, setLoading] = useState(false);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [contributors, setContributors] = useState<Record<string, ContributorRisk>>({});
  const [modelAnalysis, setModelAnalysis] = useState<ModelAnalysis | null>(null);

  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');

  const loadDatasetData = async (dsId: string) => {
    try {
      setLoading(true);
      const res = await api.getDatasetAnalysis(dsId);
      if (res?.analysis) {
        setFindings(res.analysis.findings || []);
        setContributors(res.analysis.contributor_risks || {});
      }
    } catch (err) {
      console.error('Error loading dataset analysis:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadModelData = async (mId: string) => {
    try {
      setLoading(true);
      const res = await api.getModelAnalysis(mId);
      if (res?.analysis) {
        setModelAnalysis(res.analysis);
      }
    } catch (err) {
      console.error('Error loading model analysis:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDatasetData(selectedDataset);
    loadModelData(selectedModel);
  }, []);

  const handleDatasetChange = (ds: string) => {
    setSelectedDataset(ds);
    loadDatasetData(ds);
  };

  const handleModelChange = (m: string) => {
    setSelectedModel(m);
    loadModelData(m);
  };

  const filteredFindings = findings.filter((f) => {
    if (filterSeverity === 'ALL') return true;
    return f.severity === filterSeverity;
  });

  return (
    <div className="space-y-6">
      {/* Subtab Navigation */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveSubTab('data')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              activeSubTab === 'data'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Layers className="w-4 h-4" /> Data Integrity & Contributors (Module 1)
          </button>
          <button
            onClick={() => setActiveSubTab('model')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              activeSubTab === 'model'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Cpu className="w-4 h-4" /> Model Integrity & Backdoor Probes (Module 2)
          </button>
        </div>

        {/* Dataset / Model Selector */}
        <div className="flex items-center gap-2">
          {activeSubTab === 'data' ? (
            <div className="flex items-center gap-2 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
              <span className="text-slate-400">Dataset Preset:</span>
              <select
                value={selectedDataset}
                onChange={(e) => handleDatasetChange(e.target.value)}
                className="bg-transparent text-slate-200 font-semibold focus:outline-none"
              >
                <option value="poisoned" className="bg-slate-900">Poisoned (Mallory Injected)</option>
                <option value="clean" className="bg-slate-900">Clean (Alice & Bob)</option>
                <option value="trigger_patched" className="bg-slate-900">Trigger-Patched (Sybil)</option>
              </select>
            </div>
          ) : (
            <div className="flex items-center gap-2 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
              <span className="text-slate-400">Inspect Model:</span>
              <select
                value={selectedModel}
                onChange={(e) => handleModelChange(e.target.value)}
                className="bg-transparent text-slate-200 font-semibold focus:outline-none"
              >
                <option value="trusted" className="bg-slate-900">trusted_model.onnx</option>
                <option value="backdoored" className="bg-slate-900">backdoored_model.onnx</option>
                <option value="substituted" className="bg-slate-900">substituted_model.onnx</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* SUBTAB 1: DATA INTEGRITY */}
      {activeSubTab === 'data' && (
        <div className="space-y-6">
          {/* Contributor Aggregation Cards */}
          <div>
            <h2 className="text-base font-bold text-slate-200 mb-3">Contributor Scoring Aggregation</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(contributors).map(([cid, data]) => {
                const isHigh = data.risk_score > 25;
                return (
                  <div key={cid} className={`card-panel ${isHigh ? 'glow-red' : ''}`}>
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-sm text-slate-200">{cid}</span>
                      <span className={`badge-pill text-[10px] ${isHigh ? 'badge-fail' : 'badge-pass'}`}>
                        {isHigh ? 'HIGH RISK' : 'CERTIFIED'}
                      </span>
                    </div>

                    <div className="mt-3 flex items-baseline gap-2">
                      <span className="text-3xl font-black text-white">{data.risk_score}</span>
                      <span className="text-xs text-slate-400">/ 100 Risk Score</span>
                    </div>

                    <div className="w-full bg-slate-800 h-2 rounded-full mt-3 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${isHigh ? 'bg-rose-500' : 'bg-emerald-500'}`}
                        style={{ width: `${Math.max(5, data.risk_score)}%` }}
                      />
                    </div>

                    <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-slate-800 text-[11px] text-slate-400">
                      <div>
                        <div className="text-slate-500">Mislabeled</div>
                        <div className="font-semibold text-slate-200">{(data.flag_rate * 100).toFixed(0)}%</div>
                      </div>
                      <div>
                        <div className="text-slate-500">Duplicates</div>
                        <div className="font-semibold text-slate-200">{(data.duplicate_rate * 100).toFixed(0)}%</div>
                      </div>
                      <div>
                        <div className="text-slate-500">OOD Items</div>
                        <div className="font-semibold text-slate-200">{(data.OOD_rate * 100).toFixed(0)}%</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Evidence Findings Table */}
          <div className="card-panel">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
              <div>
                <h2 className="text-base font-bold text-white m-0">
                  Data Integrity Findings ({filteredFindings.length})
                </h2>
                <p className="text-xs text-slate-400">
                  Identified via k-NN majority consensus, perceptual dHash clustering, and manifold distance.
                </p>
              </div>

              {/* Filter */}
              <div className="flex items-center gap-2 text-xs">
                <Filter className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-slate-400">Severity:</span>
                <select
                  value={filterSeverity}
                  onChange={(e) => setFilterSeverity(e.target.value)}
                  className="bg-slate-900 border border-slate-800 text-slate-200 px-2 py-1 rounded"
                >
                  <option value="ALL">All Severities</option>
                  <option value="HIGH">High Severity</option>
                  <option value="MEDIUM">Medium Severity</option>
                </select>
              </div>
            </div>

            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                    <th className="p-3">Asset</th>
                    <th className="p-3">Contributor</th>
                    <th className="p-3">Integrity Violation</th>
                    <th className="p-3">Severity</th>
                    <th className="p-3">Confidence</th>
                    <th className="p-3">Recommended Disposition</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredFindings.map((f) => {
                    const isHigh = f.severity === 'HIGH';
                    return (
                      <tr key={f.id} className="hover:bg-slate-900/40">
                        <td className="p-3 font-mono text-cyan-400 font-semibold">{f.asset}</td>
                        <td className="p-3 text-slate-300 font-semibold">{f.contributor_id}</td>
                        <td className="p-3 text-slate-300 max-w-xs">{f.reason}</td>
                        <td className="p-3">
                          <span className={`badge-pill text-[10px] ${isHigh ? 'badge-fail' : 'badge-amber'}`}>
                            {f.severity}
                          </span>
                        </td>
                        <td className="p-3 font-mono text-slate-200">{(f.confidence * 100).toFixed(0)}%</td>
                        <td className="p-3">
                          <code className="text-[11px] bg-slate-900 px-2 py-0.5 rounded text-amber-300 border border-slate-800">
                            {f.recommended_disposition}
                          </code>
                        </td>
                      </tr>
                    );
                  })}
                  {filteredFindings.length === 0 && (
                    <tr>
                      <td colSpan={6} className="text-center p-6 text-slate-500">
                        No findings detected under selected filter. Baseline clean.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SUBTAB 2: MODEL INTEGRITY */}
      {activeSubTab === 'model' && modelAnalysis && (
        <div className="space-y-6">
          {/* Model Status Header */}
          <div className="card-panel">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <span className="font-bold text-lg text-white">Inspected Artifact:</span>
                  <code className="text-sm text-cyan-400 font-mono bg-cyan-950/40 px-2.5 py-1 rounded border border-cyan-800/40">
                    {modelAnalysis.model_id}
                  </code>
                  <span className={`badge-pill ${
                    modelAnalysis.status === 'TRUSTED' ? 'badge-pass' : modelAnalysis.status === 'REVIEW' ? 'badge-amber' : 'badge-fail'
                  }`}>
                    {modelAnalysis.status}
                  </span>
                </div>
                <div className="mt-2 text-xs font-mono text-slate-400 flex items-center gap-2">
                  <span>SHA-256 Digest:</span>
                  <span className="text-slate-200">{modelAnalysis.sha256}</span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="text-right">
                  <div className="text-xs text-slate-400 uppercase font-semibold">Registry Match</div>
                  <div className={`font-mono text-xs font-bold ${
                    modelAnalysis.digest_status === 'MATCH_TRUSTED' ? 'text-emerald-400' : 'text-rose-400'
                  }`}>
                    {modelAnalysis.digest_status}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 2-Column Split: Fingerprint & Trigger Probe */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 1. Behavioural Fingerprinting */}
            <div className="card-panel">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <h3 className="text-sm font-bold text-white m-0">1. Behavioural Fingerprint Test</h3>
                <span className="text-xs font-mono text-slate-400">20 Fixed Reference Images</span>
              </div>

              <div className="mt-4 p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-300">Fingerprint Mismatches:</span>
                  <span className={`text-sm font-mono font-bold ${
                    modelAnalysis.fingerprint_mismatches === 0 ? 'text-emerald-400' : 'text-rose-400'
                  }`}>
                    {modelAnalysis.fingerprint_mismatches} / {modelAnalysis.fingerprint_total}
                  </span>
                </div>

                <div className="w-full bg-slate-800 h-2 rounded-full mt-3 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      modelAnalysis.fingerprint_mismatches === 0 ? 'bg-emerald-500' : 'bg-rose-500'
                    }`}
                    style={{
                      width: `${Math.max(5, ((modelAnalysis.fingerprint_total - modelAnalysis.fingerprint_mismatches) / modelAnalysis.fingerprint_total) * 100)}%`,
                    }}
                  />
                </div>
                <p className="text-[11px] text-slate-400 mt-2">
                  {modelAnalysis.fingerprint_mismatches === 0
                    ? '100% behavioural prediction parity observed against trusted baseline.'
                    : 'Prediction divergence detected across canonical shape manifolds.'}
                </p>
              </div>

              <div className="mt-4 space-y-2 text-xs">
                {modelAnalysis.notes.map((note, idx) => (
                  <div key={idx} className="p-2.5 bg-slate-900/40 rounded border border-slate-800 text-slate-300">
                    &bull; {note}
                  </div>
                ))}
              </div>
            </div>

            {/* 2. Backdoor Trigger Probe */}
            <div className="card-panel">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <h3 className="text-sm font-bold text-white m-0">2. Tested-Family Trigger Probe</h3>
                <span className="badge-pill badge-cyan text-[10px]">4 Corners x 3 Patterns</span>
              </div>

              <div className="mt-4 space-y-3">
                <div className={`p-4 rounded-xl border ${
                  modelAnalysis.trigger_probe.suspicious
                    ? 'bg-rose-950/20 border-rose-500/40 glow-red'
                    : 'bg-emerald-950/20 border-emerald-500/40 glow-green'
                }`}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-300">Probe Verdict:</span>
                    <span className={`badge-pill text-[10px] ${
                      modelAnalysis.trigger_probe.suspicious ? 'badge-fail' : 'badge-pass'
                    }`}>
                      {modelAnalysis.trigger_probe.suspicious ? 'VULNERABILITY DETECTED' : 'CLEAR'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-200 font-semibold mt-2">
                    {modelAnalysis.trigger_probe.verdict}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                    <span className="text-slate-500">Highest Flip Rate</span>
                    <div className="text-lg font-bold text-white mt-1">
                      {(modelAnalysis.trigger_probe.highest_flip_rate * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                    <span className="text-slate-500">Target Affinity</span>
                    <div className="text-lg font-bold text-cyan-400 mt-1 uppercase">
                      {modelAnalysis.trigger_probe.target_class_affinity || 'None'}
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-slate-900/40 rounded-lg border border-slate-800 text-[11px] text-slate-400">
                  <strong>Tested Family:</strong> {modelAnalysis.trigger_probe.tested_patch_family} (Tested across 50 clean probe samples).
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
