import { Tag } from 'antd';
import type { Content, DesignHint } from '../api';

/** Content preview — palette comes from AI design_hint. The visual carrier of
 *  the preference flywheel: v1 deep navy vs v2 light mist is instantly visible. */
export default function ContentPreview({ content, small }: { content: Content; small?: boolean }) {
  const d: DesignHint = content.design_hint || {};
  const b = content.body || {};
  const intl = String(b.title || '').includes('Connect') || String(b.body || '').includes('Lower');
  const isLight = (d.bg || '').toUpperCase() >= '#E0';
  return (
    <div className="preview-card">
      <div
        className="preview-frame"
        style={{
          background: d.bg || '#f5f5f5',
          color: d.text || '#333',
          borderLeft: `6px solid ${d.accent || '#888'}`,
          padding: small ? '18px 22px' : '28px 32px',
          minHeight: small ? 150 : 240,
        }}
      >
        {intl && <div className="kicker">GLOBAL BRAND VOICE</div>}
        {!intl && <div className="kicker" style={{ opacity: 0.5 }}>{isLight ? 'LIGHT EDIT' : 'CORPORATE FORMAL'}</div>}
        <div style={{ fontSize: small ? 15 : 21, fontWeight: 700, lineHeight: 1.4, marginBottom: 12, letterSpacing: .3 }}>
          {b.title || content.title}
        </div>
        <div style={{ whiteSpace: 'pre-wrap', fontSize: small ? 12 : 14, lineHeight: 1.9, opacity: 0.94 }}>
          {(b.summary ? `${b.summary}\n\n` : '') + (b.body || '')}
        </div>
        {b.cta && (
          <span
            style={{
              display: 'inline-block', marginTop: 16, padding: '6px 18px',
              background: d.accent, color: '#fff', borderRadius: 999, fontSize: small ? 11 : 13,
              letterSpacing: .5, boxShadow: '0 2px 8px rgba(0,0,0,.15)',
            }}
          >
            {b.cta}
          </span>
        )}
      </div>
      <div className="preview-meta">
        <span className="soft-pill" style={{ background: '#F0F3F6', color: '#4A6072' }}>{d.layout_note || '设计建议'}</span>
        <span className="soft-pill" style={{ background: '#E9F2F7', color: '#2C6E8F' }}>bg {d.bg}</span>
        <span className="soft-pill" style={{ background: '#E9F2F7', color: '#2C6E8F' }}>accent {d.accent}</span>
      </div>
    </div>
  );
}
