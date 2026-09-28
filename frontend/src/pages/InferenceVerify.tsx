import React, { useState } from 'react';
import { api } from '../api/client';
import type { InferenceReceipt, InferenceOutput, VerifyResponse } from '../api/client';
import {
  ShieldCheck, ShieldAlert, CheckCircle2, XCircle,
  Copy, Check, Upload, Zap
} from 'lucide-react';

export const InferenceVerify: React.FC = () => {
  const [selectedShape, setSelectedShape] = useState<'circle' | 'square' | 'triangle'>('circle');
  const [customFile, setCustomFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);

  const [inferring, setInferring] = useState(false);
  const [verifying, setVerifying] = useState(false);

  // Inference State
  const [inferenceOutput, setInferenceOutput] = useState<InferenceOutput | null>(null);
  const [receipt, setReceipt] = useState<InferenceReceipt | null>(null);
  const [config, setConfig] = useState<any>(null);
  const [modelName, setModelName] = useState<string>('trusted');
  const [currentImageB64, setCurrentImageB64] = useState<string | null>(null);

  // Verification State
  const [verificationResult, setVerificationResult] = useState<VerifyResponse | null>(null);
  const [tamperMessage, setTamperMessage] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Generate synthetic shape locally on canvas if no file uploaded
  const generatePresetShape = (shape: 'circle' | 'square' | 'triangle'): string => {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d')!;

    // Dark background matching dataset
    ctx.fillStyle = 'rgb(20, 24, 33)';
    ctx.fillRect(0, 0, 64, 64);

    // Foreground shape
    ctx.fillStyle = 'rgb(220, 220, 220)';
    if (shape === 'circle') {
      ctx.beginPath();
      ctx.arc(32, 32, 20, 0, Math.PI * 2);
      ctx.fill();
    } else if (shape === 'square') {
      ctx.fillRect(14, 14, 36, 36);
    } else if (shape === 'triangle') {
      ctx.beginPath();
      ctx.moveTo(32, 12);
      ctx.lineTo(12, 52);
      ctx.lineTo(52, 52);
      ctx.closePath();
      ctx.fill();
    }

    return canvas.toDataURL('image/png');
  };

  const handleRunInference = async () => {
    try {
      setInferring(true);
      setVerificationResult(null);
      setTamperMessage(null);

      let b64: string | null = null;
      let fileToSend: File | null = customFile;

      if (!fileToSend) {
        b64 = generatePresetShape(selectedShape);
        setImagePreview(b64);
        setCurrentImageB64(b64);
      }

      const res = await api.runInference(fileToSend, b64, 'trusted');
      setInferenceOutput(res.output);
      setReceipt(res.receipt);
      setConfig(res.config);
      setModelName(res.model_name);
      if (res.image_b64) {
        const fullB64 = `data:image/png;base64,${res.image_b64}`;
        setCurrentImageB64(fullB64);
        setImagePreview(fullB64);
      }
    } catch (err: any) {
      alert(`Inference failed: ${err.message}`);
    } finally {
      setInferring(false);
    }
  };

  const handleVerify = async () => {
    if (!receipt || !inferenceOutput || !config) return;
    try {
      setVerifying(true);
      const res = await api.verifyProvenance({
        image_b64: currentImageB64 || undefined,
        model_name: modelName,
        config: config,
        output: inferenceOutput,
        receipt: receipt,
      });
      setVerificationResult(res);
    } catch (err: any) {
      alert(`Verification failed: ${err.message}`);
    } finally {
      setVerifying(false);
    }
  };

  const handleTamper = async (type: string) => {
    try {
      setVerifying(true);
      const res = await api.simulateTamper(type);
      setTamperMessage(res.narrative);

      if (res.state) {
        if (res.state.image_b64) {
          const imgB64 = `data:image/png;base64,${res.state.image_b64}`;
          setCurrentImageB64(imgB64);
          setImagePreview(imgB64);
        }
        if (res.state.model_name) setModelName(res.state.model_name);
        if (res.state.config) setConfig(res.state.config);
        if (res.state.output) setInferenceOutput(res.state.output);
      }
      if (res.receipt) setReceipt(res.receipt);
      if (res.verification) setVerificationResult(res.verification);
    } catch (err: any) {
      alert(`Tamper simulation failed: ${err.message}`);
    } finally {
      setVerifying(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setCustomFile(file);
      const reader = new FileReader();
      reader.onload = (ev) => {
        setImagePreview(ev.target?.result as string);
        setCurrentImageB64(ev.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const copyReceipt = () => {
    if (!receipt) return;
    navigator.clipboard.writeText(JSON.stringify(receipt, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* 2-Column Main Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Input Selection & Sandbox Controls (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Card: Input Selection */}
          <div className="card-panel">
            <h2 className="text-base font-bold text-white mb-2">1. Image Input Selection</h2>
            <p className="text-xs text-slate-400 mb-4">
              Select a synthetic geometric shape or upload an offline sample.
            </p>

            <div className="grid grid-cols-3 gap-2 mb-4">
              {(['circle', 'square', 'triangle'] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => {
                    setSelectedShape(s);
                    setCustomFile(null);
                    const b64 = generatePresetShape(s);
                    setImagePreview(b64);
                    setCurrentImageB64(b64);
                  }}
                  className={`p-3 rounded-xl border text-xs font-semibold uppercase flex flex-col items-center gap-2 transition-all ${
                    selectedShape === s && !customFile
                      ? 'bg-cyan-500/10 border-cyan-500 text-cyan-300 shadow-sm'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span className="text-xl">
                    {s === 'circle' ? '⚪' : s === 'square' ? '⬛' : '🔺'}
                  </span>
                  {s}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3">
              <label className="btn-secondary text-xs flex-1 justify-center cursor-pointer">
                <Upload className="w-3.5 h-3.5" /> Upload Image
                <input type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />
              </label>
              {customFile && (
                <span className="text-xs text-cyan-400 truncate max-w-[120px]">
                  {customFile.name}
                </span>
              )}
            </div>

            {/* Preview Box */}
            <div className="mt-4 p-3 bg-slate-900/80 rounded-xl border border-slate-800 flex items-center justify-center">
              {imagePreview ? (
                <div className="flex items-center gap-4">
                  <img
                    src={imagePreview}
                    alt="Preview"
                    className="w-20 h-20 rounded border border-slate-700 bg-black image-render-pixelated"
                    style={{ imageRendering: 'pixelated' }}
                  />
                  <div className="text-xs text-slate-400">
                    <div>Resolution: <span className="text-slate-200 font-mono">64x64</span></div>
                    <div>Model: <span className="text-slate-200 font-mono">{modelName}</span></div>
                    <div>Status: <span className="text-emerald-400 font-mono">Ready</span></div>
                  </div>
                </div>
              ) : (
                <span className="text-xs text-slate-500 py-4">Click below to generate and run</span>
              )}
            </div>

            <button
              onClick={handleRunInference}
              disabled={inferring}
              className="btn-primary w-full mt-4 justify-center"
            >
              <Zap className="w-4 h-4" />
              {inferring ? 'Processing Offline Inference...' : 'Run Trusted Inference'}
            </button>
          </div>

          {/* Card: Tamper Simulation Sandbox */}
          {receipt && (
            <div className="card-panel border-rose-900/40 glow-red">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <h2 className="text-sm font-bold text-rose-400 flex items-center gap-2 m-0">
                  <ShieldAlert className="w-4 h-4" /> Tamper Simulation Sandbox
                </h2>
                <span className="badge-pill badge-fail text-[9px]">DETERMINISTIC FAILURES</span>
              </div>
              <p className="text-xs text-slate-400 mt-2 mb-3">
                Simulate targeted adversary manipulations. Each scenario deterministically breaks exact field bindings.
              </p>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => handleTamper('input')}
                  className="btn-danger text-xs justify-center"
                >
                  🔴 Tamper Input
                </button>
                <button
                  onClick={() => handleTamper('model')}
                  className="btn-danger text-xs justify-center"
                >
                  🔴 Replace Model
                </button>
                <button
                  onClick={() => handleTamper('output')}
                  className="btn-danger text-xs justify-center"
                >
                  🔴 Alter Output
                </button>
                <button
                  onClick={() => handleTamper('replay')}
                  className="btn-danger text-xs justify-center"
                >
                  🔴 Replay Receipt
                </button>
              </div>

              {tamperMessage && (
                <div className="mt-3 p-2.5 bg-rose-950/30 rounded border border-rose-700/50 text-[11px] text-rose-300">
                  <strong>Simulated Attack:</strong> {tamperMessage}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Receipt & Verification Results (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Card: Inference Output & Receipt */}
          {receipt && inferenceOutput && (
            <div className="card-panel">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div>
                  <h2 className="text-base font-bold text-white m-0">2. Inference Output & Provenance</h2>
                  <p className="text-xs text-slate-400">Class prediction bound cryptographically via Ed25519</p>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={copyReceipt} className="btn-secondary text-xs">
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    {copied ? 'Copied' : 'Copy JSON'}
                  </button>
                  <button onClick={handleVerify} disabled={verifying} className="btn-primary text-xs">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    {verifying ? 'Verifying...' : 'Verify Receipt'}
                  </button>
                </div>
              </div>

              {/* Predictions Display */}
              <div className="mt-4 p-3 bg-slate-900/60 rounded-xl border border-slate-800 flex items-center justify-between">
                <div>
                  <div className="text-xs text-slate-400 uppercase font-semibold">Predicted Class</div>
                  <div className="text-xl font-black text-cyan-300 uppercase mt-0.5">
                    {inferenceOutput.class_name}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-slate-400 uppercase font-semibold">Confidence</div>
                  <div className="text-xl font-black text-emerald-400 mt-0.5">
                    {(inferenceOutput.confidence * 100).toFixed(2)}%
                  </div>
                </div>
              </div>

              {/* Canonical Receipt Details */}
              <div className="mt-4 bg-slate-950 p-3 rounded-xl border border-slate-800 font-mono text-[11px] space-y-1.5 overflow-x-auto text-slate-300">
                <div className="text-cyan-400 font-bold">// Canonical Ed25519 Signed Provenance Receipt</div>
                <div><span className="text-slate-500">receipt_id:</span> <span className="text-slate-100">{receipt.receipt_id}</span></div>
                <div><span className="text-slate-500">input_sha256:</span> <span className="text-cyan-300">{receipt.input_sha256}</span></div>
                <div><span className="text-slate-500">model_sha256:</span> <span className="text-cyan-300">{receipt.model_sha256}</span></div>
                <div><span className="text-slate-500">output_sha256:</span> <span className="text-cyan-300">{receipt.output_sha256}</span></div>
                <div><span className="text-slate-500">config_sha256:</span> <span className="text-cyan-300">{receipt.config_sha256}</span></div>
                <div><span className="text-slate-500">nonce:</span> <span className="text-amber-300">{receipt.nonce}</span></div>
                <div><span className="text-slate-500">timestamp:</span> <span className="text-slate-300">{receipt.timestamp}</span></div>
                <div className="truncate"><span className="text-slate-500">signature:</span> <span className="text-purple-400">{receipt.signature}</span></div>
              </div>
            </div>
          )}

          {/* Card: Verification Results Breakdown */}
          {verificationResult && (
            <div className={`card-panel ${
              verificationResult.overall_status === 'PASS' ? 'glow-green' : 'glow-red'
            }`}>
              {/* Verdict Header */}
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${
                    verificationResult.overall_status === 'PASS' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                  }`}>
                    {verificationResult.overall_status === 'PASS' ? (
                      <CheckCircle2 className="w-5 h-5" />
                    ) : (
                      <XCircle className="w-5 h-5" />
                    )}
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white m-0">
                      Verification Result: {verificationResult.overall_status}
                    </h2>
                    <p className="text-xs text-slate-300 mt-0.5">{verificationResult.message}</p>
                  </div>
                </div>

                <span className={`badge-pill ${
                  verificationResult.overall_status === 'PASS' ? 'badge-pass' : 'badge-fail'
                }`}>
                  {verificationResult.overall_status}
                </span>
              </div>

              {/* Field-by-Field Breakdown Table */}
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                      <th className="p-2.5">Field Binding</th>
                      <th className="p-2.5">Status</th>
                      <th className="p-2.5">Expected Hash / Token</th>
                      <th className="p-2.5">Observed Runtime State</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                    {Object.entries(verificationResult.fields).map(([fieldName, res]) => {
                      const isPass = res.status === 'PASS';
                      return (
                        <tr key={fieldName} className={isPass ? 'bg-slate-900/20' : 'bg-rose-950/20'}>
                          <td className="p-2.5 font-bold text-slate-200">{fieldName}</td>
                          <td className="p-2.5">
                            <span className={`badge-pill text-[10px] ${isPass ? 'badge-pass' : 'badge-fail'}`}>
                              {res.status}
                            </span>
                          </td>
                          <td className="p-2.5 text-slate-400 truncate max-w-[160px]" title={res.expected}>
                            {res.expected}
                          </td>
                          <td className={`p-2.5 truncate max-w-[160px] font-semibold ${isPass ? 'text-slate-300' : 'text-rose-400'}`} title={res.observed}>
                            {res.observed}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!receipt && (
            <div className="card-panel flex flex-col items-center justify-center p-12 text-center text-slate-500">
              <ShieldCheck className="w-12 h-12 text-slate-700 mb-3" />
              <h3 className="text-sm font-semibold text-slate-300">No Inference Executed Yet</h3>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                Select a test shape on the left and click "Run Trusted Inference" to generate an Ed25519-signed receipt.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
