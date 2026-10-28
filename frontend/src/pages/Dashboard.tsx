import { useEffect, useState } from 'react';
import { Card, Col, Row, Table, Tag, Typography } from 'antd';
import { AimOutlined, ClockCircleOutlined, LikeOutlined, AppstoreOutlined } from '@ant-design/icons';
import { api } from '../api';
import TrendChart from '../components/TrendChart';

const CARDS = [
  { key: 'first_pass_rate', label: '老板一次审核通过率', icon: <AimOutlined />, tint: { bg: '#FBF5E8', fg: '#B98A1F' }, sub: (c: any) => `基线 ${c.baseline}% → 目标 ${c.target}%+（样本 n=${c.sample}）`, good: (v: number, c: any) => v >= c.baseline },
  { key: 'avg_review_rounds', label: '平均审核轮次', icon: <ClockCircleOutlined />, tint: { bg: '#E9F2F7', fg: '#2C6E8F' }, sub: (c: any) => `基线 ${c.baseline} 轮 · 偏好生效后逐周下降`, good: () => true },
  { key: 'ai_adoption_rate', label: 'AI 初稿采用率', icon: <LikeOutlined />, tint: { bg: '#F0F7F0', fg: '#2E9E5B' }, sub: (c: any) => c.note, good: () => true },
  { key: 'adapt_success_rate', label: '多渠道适配成功率', icon: <AppstoreOutlined />, tint: { bg: '#FDF0F4', fg: '#B04A6E' }, sub: (c: any) => `样本 ${c.sample} 个渠道版本`, good: () => true },
];

export default function Dashboard() {
  const [m, setM] = useState<any>(null);
  useEffect(() => { api.metrics().then(setM); }, []);
  if (!m) return null;
  const c = m.cards;
  return (
    <div>
      <Row gutter={16}>
        {CARDS.map((cfg) => {
          const card = c[cfg.key];
          const good = cfg.good(card.value, card);
          return (
            <Col span={6} key={cfg.key}>
              <Card className="card-hover" styles={{ body: { padding: '18px 20px' } }}>
                <div className="stat-card">
                  <div className="stat-icon" style={{ background: cfg.tint.bg, color: cfg.tint.fg }}>{cfg.icon}</div>
                  <div style={{ minWidth: 0 }}>
                    <div className="stat-value" style={{ color: good ? '#16303F' : '#C0392B' }}>
                      {card.value}<span style={{ fontSize: 13, fontWeight: 500, color: '#8AA0B0', marginLeft: 3 }}>{card.unit || (cfg.key === 'avg_review_rounds' ? '轮' : '%')}</span>
                    </div>
                    <div className="stat-label">{cfg.label}</div>
                    <div className="stat-delta">{cfg.sub(card)}</div>
                  </div>
                </div>
              </Card>
            </Col>
          );
        })}
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={14}>
          <Card title="一次通过率趋势（含种子历史 + 本周实时）" size="small">
            <TrendChart data={m.trend} target={c.first_pass_rate.target} />
          </Card>
        </Col>
        <Col span={10}>
          <Card title="业务目标对齐" size="small">
            <Table
              size="small" pagination={false} dataSource={m.goals} rowKey="name"
              columns={[
                { title: '目标', dataIndex: 'name' },
                { title: '基线', dataIndex: 'from', render: (v) => <Tag>{v}</Tag> },
                { title: '目标', dataIndex: 'to', render: (v) => <Tag color="green">{v}</Tag> },
                { title: '当前', dataIndex: 'now', render: (v) => <Tag color="blue">{v}</Tag> },
              ]}
            />
            <Card size="small" style={{ marginTop: 12, background: '#f0f7fb' }}>
              <Typography.Text>
                偏好知识库：<b>{m.preference_rules.active}</b> 条生效 / {m.preference_rules.pending} 条待确认
                （V1.0 上限 100 条，宁精勿滥）
              </Typography.Text>
              {m.personal_reach && m.personal_reach.accounts > 0 && (
                <div style={{ marginTop: 6 }}>
                  <Typography.Text>
                    📣 个人自媒体矩阵：<b>{m.personal_reach.accounts}</b> 个账号 ·
                    内容包 <b>{m.personal_reach.packages}</b> 份 · 已发布 <b>{m.personal_reach.published}</b> 份 ·
                    回执触达 <b>{m.personal_reach.reach.toLocaleString()}</b>
                  </Typography.Text>
                </div>
              )}
              {m.urgent && m.urgent.total > 0 && (
                <div style={{ marginTop: 6 }}>
                  <Typography.Text>
                    🚨 急单响应（F11）：<b>{m.urgent.done}</b> / {m.urgent.total} 单已交付 ·
                    端到端 SLA &lt; {m.urgent.sla_hours} 小时（当日交付）
                  </Typography.Text>
                </div>
              )}
            </Card>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
