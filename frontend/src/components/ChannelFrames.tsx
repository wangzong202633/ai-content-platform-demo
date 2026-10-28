import { useEffect, useRef } from 'react';
import { Tag } from 'antd';

/** Canvas channel preview frames — one material, five exact channel specs. */
interface Ver { channel: string; label: string; size: string; limit: string; w: number; h: number; copy: Record<string, any> }

function draw(ctx: CanvasRenderingContext2D, v: Ver, dh: { bg?: string; accent?: string; text?: string }) {
  const { w, h } = v;
  const bg = dh.bg || '#1B2A4A', accent = dh.accent || '#C9A45C', fg = dh.text || '#F5F7FA';
  ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
  // accent top bar
  ctx.fillStyle = accent; ctx.fillRect(0, 0, w, Math.max(8, h * 0.014));
  // faint circle deco
  ctx.globalAlpha = 0.12; ctx.fillStyle = accent;
  ctx.beginPath(); ctx.arc(w * 0.86, h * 0.2, Math.min(w, h) * 0.18, 0, Math.PI * 2); ctx.fill();
  ctx.globalAlpha = 1;
  // channel label
  ctx.fillStyle = accent;
  ctx.font = `600 ${Math.round(Math.min(w, h) * 0.035) + 8}px sans-serif`;
  ctx.fillText(v.label, 36, 74);
  ctx.fillStyle = 'rgba(255,255,255,0.55)';
  ctx.font = `${Math.round(Math.min(w, h) * 0.028) + 4}px sans-serif`;
  ctx.fillText(`${v.size} · ${v.limit}`, 36, 108);
  // title with wrapping
  const title = String(v.copy.title || v.copy.headline || v.copy.hook_lines?.[0] || '');
  ctx.fillStyle = fg;
  let fs = v.channel === 'channels' ? 64 : Math.round(w * 0.038) + 10;
  ctx.font = `700 ${fs}px sans-serif`;
  const wrap = (text: string, x: number, y: number, maxW: number, lh: number, maxLines = 3) => {
    let line = '', yy = y;
    for (const ch of text) {
      if (ctx.measureText(line + ch).width > maxW) { ctx.fillText(line, x, yy); yy += lh; line = ch; if (yy > y + lh * (maxLines - 1)) break; }
      else line += ch;
    }
    if (line) ctx.fillText(line, x, yy);
    return yy;
  };
  let lastY = wrap(title, 36, h * 0.42, w - 72, fs * 1.35);
  // snippet
  const snippet = String(v.copy.digest || v.copy.sub || v.copy.post || v.copy.text || v.copy.hook_lines?.slice(1, 3).join(' / ') || '').replace(/\n/g, ' ').slice(0, 90);
  ctx.fillStyle = 'rgba(255,255,255,0.75)';
  ctx.font = `${Math.round(Math.min(w, h) * 0.03) + 2}px sans-serif`;
  wrap(snippet, 36, lastY + fs * 1.7, w - 72, fs * 1.0, 3);
  // tags for xhs
  if (v.channel === 'xhs' && v.copy.tags) {
    ctx.fillStyle = accent;
    ctx.font = '500 26px sans-serif';
    ctx.fillText(v.copy.tags.join('  '), 36, h - 40);
  }
}

export default function ChannelFrames({ versions, designHint }: { versions: Ver[]; designHint: any }) {
  const refs = useRef<(HTMLCanvasElement | null)[]>([]);
  useEffect(() => {
    versions.forEach((v, i) => {
      const cv = refs.current[i]; if (!cv) return;
      cv.width = v.w; cv.height = v.h;
      const ctx = cv.getContext('2d')!;
      ctx.clearRect(0, 0, v.w, v.h);
      draw(ctx, v, designHint || {});
    });
  }, [versions, designHint]);
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(262px, 1fr))', gap: 16 }}>
      {versions.map((v, i) => (
        <div key={v.channel} className="channel-cell">
          <canvas
            ref={(el) => { refs.current[i] = el; }}
            style={{ boxShadow: '0 3px 12px rgba(16,42,67,.14)', aspectRatio: `${v.w} / ${v.h}` }}
          />
          <div style={{ marginTop: 8, display: 'flex', gap: 6, alignItems: 'center' }}>
            <Tag color="blue" style={{ borderRadius: 999, marginInlineEnd: 0 }}>{v.label}</Tag>
            <span style={{ fontSize: 11.5, color: '#8AA0B0', fontFamily: 'Consolas, monospace' }}>{v.size}</span>
          </div>
          <div style={{ fontSize: 12, color: '#666', marginTop: 4, whiteSpace: 'pre-wrap', maxHeight: 84, overflow: 'hidden', lineHeight: 1.6 }}>
            {v.copy.digest || v.copy.headline || v.copy.hook_lines?.join(' / ') || v.copy.text?.slice(0, 80) || v.copy.post?.slice(0, 120)}
          </div>
        </div>
      ))}
    </div>
  );
}
