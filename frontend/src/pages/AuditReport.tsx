import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { LedgerBlock } from '../api/client';
import {
  Database, ShieldCheck, FileText, CheckCircle2,
  XCircle, RefreshCw, AlertTriangle, ExternalLink
} from 'lucide-react';

export const AuditReport: React.FC = () => {
  const [blocks, setBlocks] = useState<LedgerBlock[]>([]);
  const [loading, setLoading] = useState(false);
  const [verifyStatus, setVerifyStatus] = useState<any>(null);
  const [tampering, setTampering] = useState(false);
  const [reportData, setReportData] = useState<any>(null);
  const [showReportModal, setShowReportModal] = useState(false);

  const loadBlocks = async () => {
    try {
      setLoading(true);
      const [blockList, vRes] = await Promise.all([
        api.getLedgerBlocks(50),
        api.verifyLedger(),
      ]);
      setBlocks(blockList);
      setVerifyStatus(vRes);
    } catch (err) {
      console.error('Failed to load ledger:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBlocks();
  }, []);

  const handleVerifyChain = async () => {
    try {
      setLoading(true);
      const res = await api.verifyLedger();
      setVerifyStatus(res);
    } catch (err: any) {
      alert(`Ledger verification failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleTamperLedger = async () => {
    try {
      setTampering(true);
      await api.simulateTamper('ledger');
      await loadBlocks();
    } catch (err: any) {
      alert(`Tamper failed: ${err.message}`);
    } finally {
      setTampering(false);
    }
  };

  const handleGenerateReport = async () => {
    try {
      const res = await api.getReport('latest', 'json');
      setReportData(res);
      setShowReportModal(true);
    } catch (err: any) {
      alert(`Report generation failed: ${err.message}`);
    }
  };

  const openHtmlReport = () => {
    api.getReport('latest', 'html');
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Tamper-Evident Audit Ledger Overview */}
      <div className="card-panel">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-cyan-400" />
              <h1 className="text-xl font-black text-white m-0 tracking-tight">
                TAMPER-EVIDENT AUDIT LEDGER
              </h1>
              <span className={`badge-pill ${
                verifyStatus?.valid ? 'badge-pass' : 'badge-fail'
              }`}>
                {verifyStatus?.valid ? 'CHAIN INTACT' : 'CHAIN BROKEN / COMPROMISED'}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Cryptographically hash-chained append-only SQLite audit blocks protected by SQLite triggers
              and Ed25519 digital signatures.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleVerifyChain}
              disabled={loading}
              className="btn-primary text-xs"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              {loading ? 'Verifying Chain...' : 'Verify Chain'}
            </button>
            <button
              onClick={handleTamperLedger}
              disabled={tampering}
              className="btn-danger text-xs"
              title="Simulates illicit SQLite block mutation"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              {tampering ? 'Tampering...' : 'Tamper Ledger'}
            </button>
            <button
              onClick={openHtmlReport}
              className="btn-secondary text-xs"
            >
              <ExternalLink className="w-3.5 h-3.5" /> Printable HTML Report
            </button>
            <button
              onClick={handleGenerateReport}
              className="btn-secondary text-xs"
            >
              <FileText className="w-3.5 h-3.5" /> View JSON Evidence
            </button>
          </div>
        </div>

        {/* Verification Status Banner */}
        {verifyStatus && (
          <div className={`mt-4 p-3 rounded-xl border flex items-center justify-between text-xs ${
            verifyStatus.valid
              ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-300'
              : 'bg-rose-950/40 border-rose-500/40 text-rose-300 glow-red'
          }`}>
            <div className="flex items-center gap-2">
              {verifyStatus.valid ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : (
                <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
              )}
              <span>
                <strong>Verification Verdict:</strong> {verifyStatus.reason}
              </span>
            </div>
            <span className="font-mono text-[11px] text-slate-400">
              Total Chained Blocks: {verifyStatus.total_blocks}
            </span>
          </div>
        )}
      </div>

      {/* Sequential Blocks Table */}
      <div className="card-panel">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <h2 className="text-sm font-bold text-white m-0">Sequential Chained Ledger Blocks</h2>
          <button onClick={loadBlocks} className="btn-secondary text-xs">
            <RefreshCw className="w-3 h-3" /> Refresh Blocks
          </button>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                <th className="p-3">Index</th>
                <th className="p-3">Event Type</th>
                <th className="p-3">Timestamp (UTC)</th>
                <th className="p-3">Payload SHA-256</th>
                <th className="p-3">Previous Block Hash</th>
                <th className="p-3">Block Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-[11px]">
              {blocks.map((blk) => {
                const isBad = verifyStatus?.first_bad_block === blk.block_index;
                return (
                  <tr
                    key={blk.block_index}
                    className={`hover:bg-slate-900/40 ${isBad ? 'bg-rose-950/40 text-rose-300' : ''}`}
                  >
                    <td className="p-3 font-bold text-slate-200">
                      #{blk.block_index}
                      {isBad && <span className="ml-2 badge-pill badge-fail text-[9px]">CORRUPTED</span>}
                    </td>
                    <td className="p-3">
                      <span className="badge-pill badge-cyan text-[10px]">{blk.event_type}</span>
                    </td>
                    <td className="p-3 text-slate-400">{blk.timestamp}</td>
                    <td className="p-3 text-slate-300 truncate max-w-[130px]" title={blk.payload_hash}>
                      {blk.payload_hash}
                    </td>
                    <td className="p-3 text-slate-400 truncate max-w-[130px]" title={blk.prev_hash}>
                      {blk.prev_hash}
                    </td>
                    <td className="p-3 font-semibold text-cyan-400 truncate max-w-[130px]" title={blk.hash}>
                      {blk.hash}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* JSON Evidence Report Modal */}
      {showReportModal && reportData && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-cyan-400" />
                <h3 className="text-base font-bold text-white m-0">
                  Assurance Evidence Report ({reportData.report_id})
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={openHtmlReport} className="btn-primary text-xs">
                  <ExternalLink className="w-3.5 h-3.5" /> Printable HTML
                </button>
                <button
                  onClick={() => setShowReportModal(false)}
                  className="btn-secondary text-xs"
                >
                  Close
                </button>
              </div>
            </div>

            <div className="p-4 overflow-y-auto font-mono text-xs bg-slate-950 text-slate-300 space-y-2">
              <pre className="whitespace-pre-wrap">
                {JSON.stringify(reportData, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
