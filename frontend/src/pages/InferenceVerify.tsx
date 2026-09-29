import React, { useState, useRef } from 'react';
import { api } from '../api/client';
import type { InferenceReceipt, InferenceOutput, VerifyResponse } from '../api/client';
import {
  ShieldCheck, ShieldAlert, CheckCircle2, XCircle,
  Copy, Check, Upload, Zap, AlertTriangle,
  FileImage, Lock, CornerDownRight
} from 'lucide-react';

export const InferenceVerify: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [inferring, setInferring] = useState<boolean>(false);
  const [verifying, setVerifying] = useState<boolean>(false);

  // Inference State
  const [inferenceOutput, setInferenceOutput] = useState<InferenceOutput | null>(null);
  const [receipt, setReceipt] = useState<InferenceReceipt | null>(null);
  const [config, setConfig] = useState<any>(null);
  const [modelName, setModelName] = useState<string>('trusted');
  const [currentImageB64, setCurrentImageB64] = useState<string | null>(null);

  // Threat Sandbox & Verification State
  const [tamperNarrative, setTamperNarrative] = useState<string | null>(null);
  const [tamperedType, setTamperedType] = useState<string | null>(null);
  const [verificationResult, setVerificationResult] = useState<VerifyResponse | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  // File selection handlers
  const handleFileChange = (file: File) => {
    setSelectedFile(file);
    setVerificationResult(null);
    setTamperNarrative(null);
    setTamperedType(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string;
      setImagePreview(dataUrl);
      setCurrentImageB64(dataUrl);
    };
    reader.readAsDataURL(file);
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  // Helper to generate a synthetic sample for quick 1-click test
  const loadPresetSample = (shape: 'circle' | 'square' | 'triangle') => {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d')!;

    // Background
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

    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `sample_${shape}.png`, { type: 'image/png' });
        handleFileChange(file);
      }
    }, 'image/png');
  };

  // Execute Secure Inference
  const handleExecuteInference = async () => {
    if (!selectedFile && !currentImageB64) {
      alert('Please upload an image or select a quick test sample first.');
      return;
    }

    try {
      setInferring(true);
      setVerificationResult(null);
      setTamperNarrative(null);
      setTamperedType(null);

      const res = await api.runInference(selectedFile, selectedFile ? null : currentImageB64, 'trusted');
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
      alert(`Inference execution failed: ${err.message}`);
    } finally {
      setInferring(false);
    }
  };

  // Red-Team Threat Sandbox Handlers
  const handleTamper = async (type: 'input' | 'model' | 'output' | 'replay') => {
    try {
      setVerifying(true);
      const res = await api.simulateTamper(type);
      setTamperNarrative(res.narrative);
      setTamperedType(type);

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

  // Verify Cryptographic Provenance
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

  const copyReceipt = () => {
    if (!receipt) return;
    navigator.clipboard.writeText(JSON.stringify(receipt, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Format verification field display list
  const getVerificationRows = () => {
    if (!verificationResult) return [];
    const fields = verificationResult.fields;

    return [
      { key: 'INPUT_HASH', label: 'INPUT_HASH', data: fields['INPUT_HASH'] },
      { key: 'MODEL_HASH', label: 'MODEL_HASH', data: fields['MODEL_HASH'] },
      { key: 'CONFIG_HASH', label: 'CONFIG_HASH', data: fields['CONFIG_HASH'] },
      { key: 'OUTPUT_HASH', label: 'OUTPUT_HASH', data: fields['OUTPUT_HASH'] },
      { key: 'SIGNATURE', label: 'SIGNATURE (Ed25519)', data: fields['SIGNATURE'] },
      { key: 'NONCE', label: 'NONCE FRESHNESS', data: fields['NONCE'] },
      { key: 'TIMESTAMP', label: 'TIMESTAMP FORMAT', data: fields['TIMESTAMP'] },
      { key: 'PREVIOUS_RECEIPT', label: 'CHAIN HASH BINDING', data: fields['PREVIOUS_RECEIPT'] },
    ].filter((item) => item.data);
  };

  return (
    <div className="space-y-6">
      {/* Page Title & Military Portal Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-cyan-400" />
            <h1 className="text-xl font-black text-white uppercase tracking-wider m-0">
              Inference Provenance & Tamper Assurance
            </h1>
          </div>
          <p className="text-xs font-mono text-slate-400 mt-1">
            Zero-Trust Pipeline: Upload image &rarr; Run Certified ONNX Inference &rarr; Sign Receipt &rarr; Verify Cryptographic Bindings
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-300">
            Engine: <strong className="text-cyan-400">ONNX Runtime</strong>
          </span>
          <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-300">
            Signer: <strong className="text-purple-400">Ed25519-SHA256</strong>
          </span>
        </div>
      </div>

      {/* Grid: Left Column (Image Upload & Controls) & Right Column (Output, Receipt, Threat Sandbox & Verification) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* =========================================================================
            LEFT COLUMN (5 Cols): REAL DRAG-AND-DROP FILE UPLOAD
            ========================================================================= */}
        <div className="lg:col-span-5 space-y-6">
          <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-white uppercase tracking-wide flex items-center gap-2 m-0">
                <FileImage className="w-4 h-4 text-cyan-400" />
                Image Upload & Input Intake
              </h2>
              <span className="text-[10px] font-mono text-slate-500 uppercase">Input Node</span>
            </div>

            {/* Prominent Drag & Drop Zone */}
            <div
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`p-6 border-2 border-dashed rounded-xl cursor-pointer transition-all flex flex-col items-center justify-center text-center ${
                isDragging
                  ? 'border-cyan-400 bg-cyan-950/30 shadow-[0_0_20px_rgba(6,182,212,0.25)]'
                  : imagePreview
                  ? 'border-slate-700 bg-slate-950/60 hover:border-slate-600'
                  : 'border-slate-700/80 bg-slate-950/40 hover:border-cyan-500/60 hover:bg-slate-900/60'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".png,.jpg,.jpeg,image/*"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileChange(e.target.files[0]);
                  }
                }}
                className="hidden"
              />

              {imagePreview ? (
                <div className="space-y-3 flex flex-col items-center">
                  <div className="relative group">
                    <img
                      src={imagePreview}
                      alt="Uploaded Preview"
                      className="w-32 h-32 object-contain rounded-lg border-2 border-slate-700 bg-black shadow-inner"
                      style={{ imageRendering: 'pixelated' }}
                    />
                    <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 rounded-lg flex items-center justify-center text-xs font-mono text-cyan-300 transition-opacity">
                      Click to Change
                    </div>
                  </div>
                  <div className="text-center font-mono text-xs">
                    <div className="text-slate-200 font-semibold truncate max-w-[240px]">
                      {selectedFile ? selectedFile.name : 'Generated Sample'}
                    </div>
                    <div className="text-slate-500 text-[11px] mt-0.5">
                      {selectedFile ? `${(selectedFile.size / 1024).toFixed(1)} KB` : '64x64 RGBA Canvas'} &bull; Auto-scaled to 64x64
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-3 py-4">
                  <div className="p-4 bg-slate-900 rounded-full border border-slate-800 inline-block text-cyan-400 mx-auto shadow-sm">
                    <Upload className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-200">
                      Drag & Drop ANY image here (.png, .jpg, .jpeg)
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Upload images drawn in Paint, downloaded photos, or synthetic shapes
                    </p>
                  </div>
                  <span className="inline-block px-3 py-1 bg-slate-900 hover:bg-slate-800 text-cyan-400 text-xs font-mono rounded-lg border border-slate-700">
                    Browse Local File
                  </span>
                </div>
              )}
            </div>

            {/* Quick Demo Sample Pills */}
            <div className="pt-2 border-t border-slate-800/80">
              <div className="text-[11px] font-mono text-slate-400 mb-2">
                Or Load Pre-Baked Test Shapes:
              </div>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => loadPresetSample('circle')}
                  className="px-2.5 py-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-mono flex items-center justify-center gap-1.5 transition-colors"
                >
                  <span>⚪</span> Circle
                </button>
                <button
                  type="button"
                  onClick={() => loadPresetSample('square')}
                  className="px-2.5 py-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-mono flex items-center justify-center gap-1.5 transition-colors"
                >
                  <span>⬛</span> Square
                </button>
                <button
                  type="button"
                  onClick={() => loadPresetSample('triangle')}
                  className="px-2.5 py-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-mono flex items-center justify-center gap-1.5 transition-colors"
                >
                  <span>🔺</span> Triangle
                </button>
              </div>
            </div>

            {/* Main Action Button: Execute Secure Inference */}
            <button
              onClick={handleExecuteInference}
              disabled={inferring || (!selectedFile && !currentImageB64)}
              className="w-full py-3 px-4 rounded-xl font-bold font-mono text-sm tracking-wide uppercase transition-all flex items-center justify-center gap-2 text-white bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 border border-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.3)] disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Zap className={`w-4 h-4 ${inferring ? 'animate-spin' : ''}`} />
              {inferring ? 'Computing & Signing Provenance...' : '[ Execute Secure Inference ]'}
            </button>
          </div>
        </div>

        {/* =========================================================================
            RIGHT COLUMN (7 Cols): INFERENCE OUTPUT, RECEIPT, THREAT SANDBOX & VERIFY
            ========================================================================= */}
        <div className="lg:col-span-7 space-y-6">
          {receipt && inferenceOutput ? (
            <>
              {/* Output Prediction Card */}
              <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-500/30">
                      <CheckCircle2 className="w-4 h-4" />
                    </span>
                    <h2 className="text-sm font-bold text-white uppercase tracking-wider m-0">
                      Certified Inference Output
                    </h2>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-800 uppercase">
                    Model: {modelName}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="text-[11px] font-mono text-slate-400 uppercase">Predicted Shape</span>
                    <div className="text-2xl font-black text-cyan-300 uppercase tracking-wide mt-1">
                      {inferenceOutput.class_name}
                    </div>
                    <span className="text-[11px] font-mono text-slate-500">
                      Class ID: #{inferenceOutput.class_id}
                    </span>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="text-[11px] font-mono text-slate-400 uppercase">Inference Confidence</span>
                    <div className="text-2xl font-black text-emerald-400 font-mono tracking-tight mt-1">
                      {(inferenceOutput.confidence * 100).toFixed(2)}%
                    </div>
                    <span className="text-[11px] font-mono text-slate-500">
                      Normalized Softmax
                    </span>
                  </div>
                </div>

                {/* Softmax Probabilities Bar */}
                <div className="space-y-1.5 pt-1">
                  <div className="flex justify-between text-[11px] font-mono text-slate-400">
                    <span>Circle: {(inferenceOutput.probabilities[0] * 100).toFixed(1)}%</span>
                    <span>Square: {(inferenceOutput.probabilities[1] * 100).toFixed(1)}%</span>
                    <span>Triangle: {(inferenceOutput.probabilities[2] * 100).toFixed(1)}%</span>
                  </div>
                  <div className="h-2 w-full bg-slate-950 rounded-full overflow-hidden flex border border-slate-800">
                    <div
                      className="bg-cyan-500 transition-all duration-500"
                      style={{ width: `${inferenceOutput.probabilities[0] * 100}%` }}
                    />
                    <div
                      className="bg-purple-500 transition-all duration-500"
                      style={{ width: `${inferenceOutput.probabilities[1] * 100}%` }}
                    />
                    <div
                      className="bg-emerald-500 transition-all duration-500"
                      style={{ width: `${inferenceOutput.probabilities[2] * 100}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Cryptographic Ed25519 Signed Receipt Card */}
              <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-3">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <Lock className="w-4 h-4 text-purple-400" />
                    <h2 className="text-sm font-bold text-white uppercase tracking-wider m-0">
                      Ed25519 Canonical Provenance Receipt
                    </h2>
                  </div>
                  <button
                    onClick={copyReceipt}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-950 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700 text-xs font-mono transition-colors"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy JSON'}</span>
                  </button>
                </div>

                {/* Canonical Receipt Details Block */}
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300 space-y-1.5 overflow-x-auto shadow-inner">
                  <div className="text-slate-500 text-[10px]">// Deterministic Canonical JSON (RFC 8785 Principles) Digested & Signed</div>
                  <div className="flex items-start gap-2">
                    <span className="text-slate-500 w-28 shrink-0">receipt_id:</span>
                    <span className="text-slate-200 font-semibold">{receipt.receipt_id}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-slate-500 w-28 shrink-0">input_sha256:</span>
                    <span className="text-cyan-400 break-all">{receipt.input_sha256}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-slate-500 w-28 shrink-0">model_sha256:</span>
                    <span className="text-cyan-400 break-all">{receipt.model_sha256}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-slate-500 w-28 shrink-0">output_sha256:</span>
                    <span className="text-cyan-400 break-all">{receipt.output_sha256}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-slate-500 w-28 shrink-0">config_sha256:</span>
                    <span className="text-cyan-400 break-all">{receipt.config_sha256}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-slate-500 w-28 shrink-0">nonce:</span>
                    <span className="text-amber-400">{receipt.nonce}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-slate-500 w-28 shrink-0">timestamp:</span>
                    <span className="text-slate-300">{receipt.timestamp}</span>
                  </div>
                  <div className="flex items-start gap-2 pt-1 border-t border-slate-900">
                    <span className="text-purple-400 w-28 shrink-0">signature:</span>
                    <span className="text-purple-300 break-all">{receipt.signature}</span>
                  </div>
                </div>
              </div>

              {/* Red-Team Threat Sandbox Card */}
              <div className="p-5 rounded-xl bg-slate-900/90 border border-rose-900/60 shadow-xl space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="w-5 h-5 text-rose-400" />
                    <h2 className="text-sm font-black text-rose-300 uppercase tracking-wider m-0">
                      Adversarial Threat Sandbox (Simulation)
                    </h2>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-950/90 text-rose-400 border border-rose-800/80 uppercase font-bold">
                    Inject Faults
                  </span>
                </div>

                <p className="text-xs text-slate-400 leading-relaxed">
                  Trigger deterministic adversary simulations to alter individual pipeline parameters post-signing, then verify cryptographic isolation:
                </p>

                {/* 4 Threat Buttons */}
                <div className="grid grid-cols-2 gap-2.5">
                  <button
                    onClick={() => handleTamper('input')}
                    disabled={verifying}
                    className="p-2.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 hover:border-rose-600 text-rose-300 text-xs font-mono font-bold flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
                  >
                    <span>🔴</span> [ Tamper Input Image ]
                  </button>

                  <button
                    onClick={() => handleTamper('model')}
                    disabled={verifying}
                    className="p-2.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 hover:border-rose-600 text-rose-300 text-xs font-mono font-bold flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
                  >
                    <span>🔴</span> [ Swap Substituted Model ]
                  </button>

                  <button
                    onClick={() => handleTamper('output')}
                    disabled={verifying}
                    className="p-2.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 hover:border-rose-600 text-rose-300 text-xs font-mono font-bold flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
                  >
                    <span>🔴</span> [ Alter Output Logits ]
                  </button>

                  <button
                    onClick={() => handleTamper('replay')}
                    disabled={verifying}
                    className="p-2.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 hover:border-rose-600 text-rose-300 text-xs font-mono font-bold flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
                  >
                    <span>🔴</span> [ Replay Expired Nonce ]
                  </button>
                </div>

                {tamperNarrative && (
                  <div className="p-3 bg-rose-950/50 rounded-lg border border-rose-600/60 text-xs font-mono text-rose-200 flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <strong className="text-white uppercase">Simulated Mutation ({tamperedType}):</strong>{' '}
                      {tamperNarrative}
                    </div>
                  </div>
                )}

                {/* Large Verify Provenance Button */}
                <button
                  onClick={handleVerify}
                  disabled={verifying}
                  className="w-full py-3.5 px-4 rounded-xl font-bold font-mono text-sm tracking-wider uppercase transition-all flex items-center justify-center gap-2 text-white bg-slate-950 hover:bg-slate-900 border-2 border-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.25)] hover:shadow-[0_0_20px_rgba(6,182,212,0.4)]"
                >
                  <ShieldCheck className={`w-5 h-5 text-cyan-400 ${verifying ? 'animate-pulse' : ''}`} />
                  {verifying ? 'Executing Cryptographic Field Checks...' : '[ Verify Cryptographic Provenance ]'}
                </button>
              </div>

              {/* Verification Results Table */}
              {verificationResult && (
                <div
                  className={`p-5 rounded-xl border shadow-2xl space-y-4 transition-all ${
                    verificationResult.overall_status === 'PASS'
                      ? 'bg-emerald-950/30 border-emerald-500/60 shadow-[0_0_25px_rgba(16,185,129,0.2)]'
                      : 'bg-rose-950/30 border-rose-500/60 shadow-[0_0_25px_rgba(244,63,94,0.25)]'
                  }`}
                >
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center gap-2.5">
                      {verificationResult.overall_status === 'PASS' ? (
                        <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                      ) : (
                        <XCircle className="w-6 h-6 text-rose-500" />
                      )}
                      <div>
                        <h2 className="text-base font-black text-white uppercase tracking-wider m-0">
                          Provenance Verdict: {verificationResult.overall_status}
                        </h2>
                        <p className="text-xs text-slate-300 font-mono mt-0.5">
                          {verificationResult.message}
                        </p>
                      </div>
                    </div>

                    <span
                      className={`px-3 py-1 rounded-full text-xs font-mono font-bold tracking-widest uppercase ${
                        verificationResult.overall_status === 'PASS'
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/60'
                          : 'bg-rose-950 text-rose-300 border border-rose-500/60'
                      }`}
                    >
                      {verificationResult.overall_status}
                    </span>
                  </div>

                  {/* Clean Field-by-Field Verification Table */}
                  <div className="overflow-x-auto rounded-lg border border-slate-800">
                    <table className="w-full text-left font-mono text-xs">
                      <thead>
                        <tr className="bg-slate-950/90 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                          <th className="p-3">Field Binding</th>
                          <th className="p-3">Verdict</th>
                          <th className="p-3">Expected Certificate Value</th>
                          <th className="p-3">Observed Pipeline State</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 bg-slate-950/40 text-[11px]">
                        {getVerificationRows().map((row) => {
                          const isPass = row.data.status === 'PASS';
                          return (
                            <tr key={row.key} className={isPass ? 'hover:bg-slate-900/30' : 'bg-rose-950/20'}>
                              <td className="p-3 font-bold text-slate-200 flex items-center gap-1.5">
                                <CornerDownRight className="w-3 h-3 text-slate-500" />
                                {row.label}
                              </td>
                              <td className="p-3">
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                    isPass
                                      ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/40'
                                      : 'bg-rose-950/80 text-rose-400 border border-rose-500/50'
                                  }`}
                                >
                                  {row.data.status}
                                </span>
                              </td>
                              <td
                                className="p-3 text-slate-400 truncate max-w-[150px]"
                                title={row.data.expected}
                              >
                                {row.data.expected}
                              </td>
                              <td
                                className={`p-3 truncate max-w-[150px] font-semibold ${
                                  isPass ? 'text-slate-300' : 'text-rose-400 font-bold'
                                }`}
                                title={row.data.observed}
                              >
                                {row.data.observed}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          ) : (
            /* Empty State Placeholder */
            <div className="p-12 rounded-xl bg-slate-900/50 border border-slate-800/80 flex flex-col items-center justify-center text-center space-y-3">
              <div className="p-4 bg-slate-950 rounded-2xl border border-slate-800 text-slate-600">
                <ShieldCheck className="w-10 h-10" />
              </div>
              <h3 className="text-base font-bold text-slate-300 uppercase tracking-wide">
                Awaiting Execution
              </h3>
              <p className="text-xs font-mono text-slate-500 max-w-sm">
                Drop any image or choose a demo shape on the left, then click{' '}
                <strong className="text-cyan-400">[ Execute Secure Inference ]</strong> to produce and sign a canonical receipt.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
