// API helpers + SSE client
export interface Rule { id: number; code: string; category: string; rule_text: string; confidence: number; status: string; source_note: string; evidence: string; created_at: string }
export interface DesignHint { bg?: string; accent?: string; text?: string; layout_note?: string }
export interface Content {
  id: number; project_id: number; type: string; type_label: string; title: string;
  body: Record<string, any>; design_hint: DesignHint; status: string; status_label: string;
  version: number; params: Record<string, any>; used_preference_ids: number[];
  generation_meta: Record<string, any>; created_at: string;
  channel_versions?: any[]; reviews?: any[]; applied_rules?: Rule[]; lineage?: Content[];
}

const j = async (url: string, opts?: RequestInit) => {
  const r = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...opts });
  if (!r.ok) throw Object.assign(new Error('api error'), { status: r.status, body: await r.json().catch(() => ({})) });
  return r.json();
};

export const api = {
  health: () => j('/api/health'),
  metrics: () => j('/api/metrics'),
  preferences: (status?: string) => j(`/api/preferences${status ? `?status=${status}` : ''}`),
  projects: () => j('/api/projects'),
  contents: (status?: string) => j(`/api/contents${status ? `?status=${status}` : ''}`),
  content: (id: number) => j(`/api/contents/${id}`),
  review: (id: number, body: { role: string; action: string; feedback_text?: string }) =>
    j(`/api/contents/${id}/review`, { method: 'POST', body: JSON.stringify(body) }),
  adapt: (id: number) => j(`/api/contents/${id}/adapt`, { method: 'POST', body: '{}' }),
  editContent: (id: number, patch: { title?: string; body?: string; summary?: string; cta?: string }) =>
    j(`/api/contents/${id}`, { method: 'PUT', body: JSON.stringify(patch) }),
  distribute: (id: number) => j(`/api/contents/${id}/distribute`, { method: 'POST' }),
  confirmPref: (id: number) => j(`/api/preferences/${id}/confirm`, { method: 'POST' }),
  rejectPref: (id: number) => j(`/api/preferences/${id}`, { method: 'DELETE' }),
  editPref: (id: number, rule_text: string) =>
    j(`/api/preferences/${id}`, { method: 'PATCH', body: JSON.stringify({ rule_text }) }),
  extractPrefs: (feedback_text: string, content_id?: number) =>
    j('/api/preferences/extract', { method: 'POST', body: JSON.stringify({ feedback_text, content_id }) }),
  reset: () => j('/api/demo/reset', { method: 'POST' }),
  // ── personal media + AI image ──
  accounts: () => j('/api/accounts'),
  createAccount: (body: Record<string, any>) => j('/api/accounts', { method: 'POST', body: JSON.stringify(body) }),
  buildPackage: (contentId: number, account_ids: number[]) =>
    j(`/api/contents/${contentId}/package`, { method: 'POST', body: JSON.stringify({ account_ids }) }),
  listPackages: (contentId: number) => j(`/api/contents/${contentId}/packages`),
  receipt: (packageId: number, body: { link?: string; note?: string; reach?: number }) =>
    j(`/api/packages/${packageId}/receipt`, { method: 'POST', body: JSON.stringify(body) }),
  generateImage: (body: Record<string, any>) =>
    j('/api/images/generate', { method: 'POST', body: JSON.stringify(body) }),
  connectAccount: (id: number, body: { appid?: string; secret?: string; webhook_url?: string }) =>
    j(`/api/accounts/${id}/connect`, { method: 'POST', body: JSON.stringify(body) }),
  disconnectAccount: (id: number) => j(`/api/accounts/${id}/disconnect`, { method: 'POST' }),
  publishPackage: (packageId: number) => j(`/api/packages/${packageId}/publish`, { method: 'POST' }),
};

export interface GenMeta { content_id: number; version: number; mode: string; model: string; is_urgent?: boolean; urgent_deadline?: string; used_preferences: { id: number; code: string; category: string; rule_text: string }[] }

export async function generateSSE(
  payload: Record<string, any>,
  onMeta: (m: GenMeta) => void,
  onToken: (t: string) => void,
): Promise<Content> {
  const res = await fetch('/api/contents/generate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  let done: Content | null = null;
  for (;;) {
    const { value, done: fin } = await reader.read();
    if (fin) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const block = buf.slice(0, idx); buf = buf.slice(idx + 2);
      let ev = '', data = '';
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) ev = line.slice(7);
        else if (line.startsWith('data: ')) data += line.slice(6);
      }
      if (!ev) continue;
      const obj = JSON.parse(data);
      if (ev === 'meta') onMeta(obj);
      else if (ev === 'token') onToken(obj.text);
      else if (ev === 'done') done = obj.content;
    }
  }
  return done!;
}
