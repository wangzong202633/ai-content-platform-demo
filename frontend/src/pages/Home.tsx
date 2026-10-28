import { useEffect, useState } from 'react';
import { Card, Col, Row, Segmented, Table, Tag, Button, Popconfirm, message, Space } from 'antd';
import {
  ArrowRightOutlined, CheckCircleOutlined, ExperimentOutlined, TableOutlined, ThunderboltOutlined, DashboardOutlined,
} from '@ant-design/icons';
import { api, Content } from '../api';
import { UrgentTag } from '../components/UrgentBadge';

const STATUS_COLOR: Record<string, string> = {
  draft: 'default', generating: 'processing', pending_supervisor: 'gold',
  pending_revision: 'orange', pending_boss: 'purple', confirmed: 'green', distributed: 'cyan',
};

/** F06 看板视图：按生命周期四列 */
function Kanban({ contents, nav }: { contents: Content[]; nav: (v: any, id?: number) => void }) {
  const COLS: { key: string; title: string; color: string; match: (s: string) => boolean }[] = [
    { key: 'first', title: '初审池', color: '#D9930D', match: (s) => s === 'pending_supervisor' || s === 'pending_revision' },
    { key: 'boss', title: '待老板终审', color: '#722ED1', match: (s) => s === 'pending_boss' },
    { key: 'ok', title: '已确认', color: '#2E9E5B', match: (s) => s === 'confirmed' },
    { key: 'done', title: '已分发', color: '#16838A', match: (s) => s === 'distributed' },
  ];
  return (
    <Row gutter={14}>
      {COLS.map((col) => {
        const items = contents.filter((c) => col.match(c.status));
        return (
          <Col span={6} key={col.key}>
            <div style={{ background: '#F7FAFC', border: '1px solid #E3EBF1', borderRadius: 12, padding: 10, minHeight: 260 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
                <span style={{ width: 8, height: 8, borderRadius: 99, background: col.color }} />
                <b style={{ fontSize: 13, color: '#16303F' }}>{col.title}</b>
                <span className="soft-pill" style={{ background: '#fff', color: '#7B8FA0', marginLeft: 'auto' }}>{items.length}</span>
              </div>
              {items.map((c) => (
                <Card
                  key={c.id} size="small" className="card-hover" style={{ marginBottom: 8, cursor: 'pointer', borderLeft: c.params?.is_urgent ? '3px solid #D93B2B' : undefined }}
                  onClick={() => nav('detail', c.id)}
                >
                  <div style={{ fontSize: 12.5, fontWeight: 600, color: '#16303F', marginBottom: 6, lineHeight: 1.5 }}>
                    #{c.id} {c.title.slice(0, 16)}
                  </div>
                  <Space size={4}>
                    <Tag style={{ borderRadius: 999, fontSize: 11 }}>{c.type_label}</Tag>
                    {c.version > 1 && <Tag color="red" style={{ borderRadius: 999, fontSize: 11 }}>v{c.version}</Tag>}
                    {c.params?.is_urgent && <UrgentTag />}
                    {c.status === 'pending_revision' && <Tag color="orange" style={{ borderRadius: 999, fontSize: 11 }}>待修改</Tag>}
                  </Space>
                </Card>
              ))}
              {items.length === 0 && <div style={{ color: '#A7B6C2', fontSize: 12, textAlign: 'center', padding: '28px 0' }}>暂无内容</div>}
            </div>
          </Col>
        );
      })}
    </Row>
  );
}

function StatCard({ icon, tint, value, suffix, label, delta }: any) {
  return (
    <Card className="card-hover" styles={{ body: { padding: '18px 20px' } }}>
      <div className="stat-card">
        <div className="stat-icon" style={{ background: tint.bg, color: tint.fg }}>{icon}</div>
        <div style={{ minWidth: 0 }}>
          <div className="stat-value">{value}<span style={{ fontSize: 13, fontWeight: 500, color: '#8AA0B0', marginLeft: 3 }}>{suffix}</span></div>
          <div className="stat-label">{label}</div>
          {delta && <div className="stat-delta" dangerouslySetInnerHTML={{ __html: delta }} />}
        </div>
      </div>
    </Card>
  );
}

export default function Home({ role, nav }: { role: string; nav: (v: any, id?: number) => void }) {
  const [metrics, setMetrics] = useState<any>(null);
  const [contents, setContents] = useState<Content[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [m, c] = await Promise.all([api.metrics(), api.contents()]);
      setMetrics(m); setContents(c);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const inboxStatus = role === 'boss' ? 'pending_boss' : 'pending_supervisor';
  const inboxCount = contents.filter((c) => c.status === inboxStatus).length;
  const passRate = metrics?.cards?.first_pass_rate;
  const [viewMode, setViewMode] = useState<'table' | 'kanban'>('table');

  return (
    <div>
      <Row gutter={16}>
        <Col span={6}>
          <StatCard
            icon={<CheckCircleOutlined />} tint={{ bg: '#FDEEEE', fg: '#C0392B' }}
            value={inboxCount} suffix="条"
            label={role === 'boss' ? '待我终审（老板）' : '待我初审（主管）'}
            delta={role === 'boss' ? '终审反馈将自动沉淀偏好' : '初审通过后提交老板'}
          />
        </Col>
        <Col span={6}>
          <StatCard
            icon={<ExperimentOutlined />} tint={{ bg: '#E9F2F7', fg: '#2C6E8F' }}
            value={metrics?.preference_rules?.active ?? '–'} suffix={`/ 待确认 ${metrics?.preference_rules?.pending ?? 0}`}
            label="生效偏好规则"
            delta="上限 100 条 · <b>宁精勿滥</b>"
          />
        </Col>
        <Col span={6}>
          <StatCard
            icon={<ThunderboltOutlined />} tint={{ bg: '#F0F7F0', fg: '#2E9E5B' }}
            value={metrics?.counts?.week_output ?? '–'} suffix="条"
            label="本周内容产出" delta="目标：周产出 5 → <b class='up'>15-20 条</b>"
          />
        </Col>
        <Col span={6}>
          <StatCard
            icon={<CheckCircleOutlined />} tint={{ bg: '#FBF5E8', fg: '#B98A1F' }}
            value={passRate?.value ?? '–'} suffix="%"
            label="老板一次通过率"
            delta={`基线 ${passRate?.baseline ?? 30}% → 目标 <b class="goal">${passRate?.target ?? 70}%+</b>`}
          />
        </Col>
      </Row>

      <Card
        className="fade-in"
        style={{ marginTop: 16 }}
        title={<Space><span style={{ width: 4, height: 16, background: '#2C6E8F', borderRadius: 2, display: 'inline-block' }} />项目工作台 · 2026国际化工装备展</Space>}
        extra={
          <Space>
            <Segmented
              value={viewMode} onChange={(v) => setViewMode(v as any)}
              options={[
                { label: '表格', value: 'table', icon: <TableOutlined /> },
                { label: '看板', value: 'kanban', icon: <DashboardOutlined /> },
              ]}
            />
            <Button type="primary" onClick={() => nav('generate')}>＋ 新建内容</Button>
            <Popconfirm title="重置后所有演示数据恢复初始状态，确定？" onConfirm={async () => { await api.reset(); message.success('已重置'); load(); }}>
              <Button size="small">重置演示数据</Button>
            </Popconfirm>
          </Space>
        }
      >
        {viewMode === 'kanban'
          ? <Kanban contents={contents} nav={nav} />
          : (
            <Table<Content>
          rowKey="id" size="middle" loading={loading} dataSource={contents} pagination={false}
          onRow={(r) => ({ onClick: () => nav('detail', r.id), style: { cursor: 'pointer' } })}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 56 },
            { title: '类型', dataIndex: 'type_label', width: 110, render: (t) => <Tag style={{ borderRadius: 999 }}>{t}</Tag> },
            { title: '标题', dataIndex: 'title', ellipsis: true },
            { title: '版本', dataIndex: 'version', width: 70, render: (v, r) => (<Space size={4}>{r.params?.is_urgent && <UrgentTag />}{v > 1 ? <Tag color="red" style={{ borderRadius: 999 }}>v{v}</Tag> : <span style={{ color: '#8AA0B0' }}>v{v}</span>}</Space>) },
            { title: '状态', dataIndex: 'status', width: 110, render: (s, r) => <Tag color={STATUS_COLOR[s]} style={{ borderRadius: 999 }}>{r.status_label}</Tag> },
            { title: '创建时间', dataIndex: 'created_at', width: 150, render: (t) => <span style={{ color: '#8AA0B0' }}>{t}</span> },
          ]}
            />
          )}
      </Card>

      <Row gutter={16} style={{ marginTop: 16 }}>
        {(metrics?.goals ?? []).map((g: any) => (
          <Col span={8} key={g.name}>
            <Card className="card-hover" size="small">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <b style={{ color: '#16303F' }}>{g.name}</b>
              </div>
              <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="soft-pill" style={{ background: '#F0F3F6', color: '#7B8FA0' }}>{g.from}</span>
                <ArrowRightOutlined style={{ color: '#AFC2CF', fontSize: 12 }} />
                <span className="soft-pill" style={{ background: '#E9F7EF', color: '#2E9E5B' }}>{g.to}</span>
                <span className="soft-pill" style={{ background: '#E9F2F7', color: '#2C6E8F', marginLeft: 'auto' }}>当前 {g.now}</span>
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}
