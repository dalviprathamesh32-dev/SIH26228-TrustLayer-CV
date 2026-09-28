const BASE_URL = '/api';

export interface InferenceReceipt {
  receipt_id: string;
  input_sha256: string;
  model_sha256: string;
  config_sha256: string;
  output_sha256: string;
  timestamp: string;
  nonce: string;
  previous_receipt_hash: string;
  signature: string;
  public_key: string;
}

export interface InferenceOutput {
  class_id: number;
  class_name: string;
  confidence: number;
  probabilities: number[];
}

export interface VerifyFieldResult {
  status: 'PASS' | 'FAIL';
  expected: string;
  observed: string;
}

export interface VerifyResponse {
  overall_status: 'PASS' | 'FAIL';
  fields: Record<string, VerifyFieldResult>;
  message: string;
}

export interface LedgerBlock {
  block_index: number;
  timestamp: string;
  prev_hash: string;
  event_type: string;
  payload_hash: string;
  signature: string;
  hash: string;
}

export interface Finding {
  id: string;
  contributor_id: string;
  asset: string;
  reason: string;
  evidence: Record<string, any>;
  severity: string;
  confidence: number;
  recommended_disposition: string;
  created_at: string;
}

export interface ContributorRisk {
  contributor_id: string;
  total_samples: number;
  flag_rate: number;
  duplicate_rate: number;
  OOD_rate: number;
  risk_score: number;
}

export interface ModelAnalysis {
  model_id: string;
  sha256: string;
  digest_status: string;
  trusted_sha256: string;
  fingerprint_mismatches: number;
  fingerprint_total: number;
  trigger_probe: {
    probed_patches: number;
    clean_baseline_acc: number;
    highest_flip_rate: number;
    target_class_affinity?: string;
    suspicious: boolean;
    verdict: string;
    tested_patch_family: string;
    most_suspect_configuration?: {
      corner: string;
      pattern: string;
    };
  };
  status: 'TRUSTED' | 'REVIEW' | 'COMPROMISED';
  notes: string[];
}

export const api = {
  async getHealth() {
    const res = await fetch(`${BASE_URL}/health`);
    return res.json();
  },

  async runInference(file: File | null, imageB64: string | null, modelName = 'trusted', config?: any) {
    const formData = new FormData();
    if (file) formData.append('file', file);
    if (imageB64) formData.append('image_b64', imageB64);
    formData.append('model_name', modelName);
    if (config) formData.append('config_json', JSON.stringify(config));

    const res = await fetch(`${BASE_URL}/infer`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async verifyProvenance(payload: {
    image_b64?: string;
    model_name?: string;
    config: any;
    output: any;
    receipt: InferenceReceipt;
  }): Promise<VerifyResponse> {
    const res = await fetch(`${BASE_URL}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async simulateTamper(tamper_type: string) {
    const res = await fetch(`${BASE_URL}/demo/tamper`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tamper_type }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async resetDemo() {
    const res = await fetch(`${BASE_URL}/demo/reset`, { method: 'POST' });
    return res.json();
  },

  async getLedgerBlocks(limit = 50): Promise<LedgerBlock[]> {
    const res = await fetch(`${BASE_URL}/ledger/blocks?limit=${limit}`);
    return res.json();
  },

  async verifyLedger() {
    const res = await fetch(`${BASE_URL}/ledger/verify`);
    return res.json();
  },

  async getFindings(): Promise<Finding[]> {
    const res = await fetch(`${BASE_URL}/findings`);
    return res.json();
  },

  async getDatasetAnalysis(id: string) {
    const res = await fetch(`${BASE_URL}/datasets/${id}/analysis`);
    return res.json();
  },

  async getModelAnalysis(id: string): Promise<{ model_id: string; analysis: ModelAnalysis }> {
    const res = await fetch(`${BASE_URL}/models/${id}/analysis`);
    return res.json();
  },

  async analyzeShift(imagesB64?: string[]) {
    const res = await fetch(`${BASE_URL}/shift/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: imagesB64 ? new URLSearchParams({ images_b64: JSON.stringify(imagesB64) }) : undefined,
    });
    return res.json();
  },

  async getReport(id = 'latest', format: 'json' | 'html' = 'json') {
    if (format === 'html') {
      window.open(`${BASE_URL}/report/${id}?format=html`, '_blank');
      return null;
    }
    const res = await fetch(`${BASE_URL}/report/${id}?format=json`);
    return res.json();
  },
};
