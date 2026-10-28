/** Hand-rolled SVG trend chart — zero chart dependencies, hackathon-proof. */
export default function TrendChart({ data, target }: { data: { week: string; pass_rate: number }[]; target?: number }) {
  const W = 560, H = 220, PAD = 36;
  const maxV = 80;
  const x = (i: number) => PAD + (i * (W - PAD * 2)) / (data.length - 1);
  const y = (v: number) => H - PAD - (v / maxV) * (H - PAD * 2);
  const pts = data.map((d, i) => `${x(i)},${y(d.pass_rate)}`).join(' ');
  const last = data[data.length - 1];
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ maxWidth: 620 }}>
      {/* grid */}
      {[0, 20, 40, 60, 80].map((v) => (
        <g key={v}>
          <line x1={PAD} x2={W - PAD} y1={y(v)} y2={y(v)} stroke="#e8e8e8" strokeDasharray="4 4" />
          <text x={PAD - 6} y={y(v) + 4} fontSize="10" fill="#999" textAnchor="end">{v}%</text>
        </g>
      ))}
      {target && <line x1={PAD} x2={W - PAD} y1={y(target)} y2={y(target)} stroke="#d8314d" strokeDasharray="6 4" strokeWidth="1.2" />}
      {target && <text x={W - PAD} y={y(target) - 6} fontSize="10" fill="#d8314d" textAnchor="end">目标 {target}%</text>}
      {/* area */}
      <polygon points={`${PAD},${y(0)} ${pts} ${x(data.length - 1)},${y(0)}`} fill="rgba(47,127,168,0.10)" />
      <polyline points={pts} fill="none" stroke="#2F7FA8" strokeWidth="2.5" />
      {data.map((d, i) => (
        <g key={d.week}>
          <circle cx={x(i)} cy={y(d.pass_rate)} r={i === data.length - 1 ? 5 : 3.2} fill={i === data.length - 1 ? '#d8314d' : '#2F7FA8'} />
          <text x={x(i)} y={H - 12} fontSize="10" fill="#888" textAnchor="middle">{d.week}</text>
          {(i === 0 || i === data.length - 1) && (
            <text x={x(i)} y={y(d.pass_rate) - 10} fontSize="11" fontWeight="600" fill="#444" textAnchor="middle">{d.pass_rate}%</text>
          )}
        </g>
      ))}
      {last && (
        <text x={x(data.length - 1)} y={y(last.pass_rate) + 20} fontSize="10" fill="#d8314d" textAnchor="middle">本周(实时)</text>
      )}
    </svg>
  );
}
