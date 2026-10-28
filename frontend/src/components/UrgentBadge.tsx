import { Tag } from 'antd';
import { useEffect, useState } from 'react';

/** F11 急单徽章 + SLA 倒计时（PRD：急单端到端交付 < 4 小时，当日交付） */
export function UrgentTag() {
  return <Tag color="red" style={{ borderRadius: 999, fontWeight: 600 }}>🚨 急单</Tag>;
}

function fmt(ms: number) {
  if (ms <= 0) return '已超时';
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(h)}:${p(m)}:${p(sec)}`;
}

export function UrgentCountdown({ deadline, showLabel }: { deadline?: string; showLabel?: boolean }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  if (!deadline) return null;
  const remain = new Date(deadline.replace(' ', 'T')).getTime() - now;
  return (
    <span style={{
      fontFamily: 'Consolas, monospace', fontSize: 13, fontWeight: 700,
      color: remain > 0 ? '#C0392B' : '#999',
    }}>
      {showLabel !== false && <span style={{ fontFamily: 'inherit', fontWeight: 500, marginRight: 6 }}>SLA 倒计时</span>}
      {fmt(remain)}
    </span>
  );
}

/** 急单横幅（生成页/审核页顶部） */
export function UrgentBanner({ deadline }: { deadline?: string }) {
  if (!deadline) return null;
  return (
    <div style={{
      background: 'linear-gradient(90deg, #FDF2F0, #FBEAE7)', border: '1px solid #F2C4BC',
      borderRadius: 10, padding: '10px 16px', marginBottom: 14,
      display: 'flex', alignItems: 'center', gap: 12,
    }}>
      <UrgentTag />
      <span style={{ color: '#8A3B2E', fontSize: 13 }}>急单快速通道：AI 优先处理，目标当日交付（端到端 &lt; 4 小时）</span>
      <span style={{ marginLeft: 'auto' }}><UrgentCountdown deadline={deadline} /></span>
    </div>
  );
}
