import { useCallback, useEffect, useState } from 'react';
import {
  Badge, Button, Card, Col, Empty, List, message, Modal, Popconfirm, Row, Space, Tag, Typography,
} from 'antd';
import { AuditOutlined, CheckOutlined, CloseOutlined, RocketOutlined, ScissorOutlined } from '@ant-design/icons';
import { api, Content } from '../api';
import ContentPreview from '../components/ContentPreview';
import { UrgentBanner, UrgentCountdown } from '../components/UrgentBadge';

const PRESETS = [
  '颜色太深，整体不够国际化，看着不像一家面向全球市场的企业。',
  '标题不够大气，核心卖点不突出。',
  '排版太挤，重点信息被淹没了。',
];

export default function ReviewCenter({
  role, setRole, nav, setRegenBase,
}: {
  role: string; setRole: (r: 'supervisor' | 'boss') => void;
  nav: (v: any, id?: number) => void; setRegenBase: (c: Content | null) => void;
}) {
  const [contents, setContents] = useState<Content[]>([]);
  const [active, setActive] = useState<Content | null>(null);
  const [feedback, setFeedback] = useState('');
  const [signals, setSignals] = useState<any[] | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const all = await api.contents();
    const mine = all.filter((c) =>
      role === 'boss'
        ? c.status === 'pending_boss'
        : ['pending_supervisor', 'pending_revision', 'confirmed'].includes(c.status));
    setContents(mine);
    setActive((prev) => (prev && mine.some((m) => m.id === prev.id) ? mine.find((m) => m.id === prev.id)! : mine[0] || null));
  }, [role]);
  useEffect(() => { load(); }, [load]);

  const reviews = active?.reviews || [];
  const detail = active;

  const refreshDetail = async (id: number) => {
    try { setActive(await api.content(id)); } catch { /* deleted lineage row */ }
    load();
  };

  const approve = async () => {
    setBusy(true);
    try {
      const r = await api.review(active!.id, { role, action: 'approve' });
      message.success(role === 'boss' ? '终审通过，内容已确认 ✅' : '初审通过，已提交老板终审');
      setActive(r.content);
      load();
    } catch (e: any) { message.error(e?.body?.detail || '操作失败'); } finally { setBusy(false); }
  };

  const reject = async () => {
    if (!feedback.trim()) { message.warning('请填写退回意见（老板的反馈将自动提取偏好信号）'); return; }
    setBusy(true);
    try {
      const r = await api.review(active!.id, { role, action: 'reject', feedback_text: feedback });
      if (r.extracted?.length) setSignals(r.extracted);
      else message.success('已退回');
      setActive(r.content); load();
    } catch (e: any) { message.error(e?.body?.detail || '操作失败'); } finally { setBusy(false); }
  };

  const distribute = async () => {
    setBusy(true);
    try {
      const r = await api.distribute(active!.id);
      message.success(`已分发至 ${r.channels.length} 个渠道 🎉`);
      setActive(r.content); load();
    } catch (e: any) { message.error(e?.body?.detail || '操作失败'); } finally { setBusy(false); }
  };

  const wrongRole =
    detail && ((role === 'boss' && detail.status === 'pending_supervisor') ||
               (role === 'supervisor' && detail.status === 'pending_boss'));

  return (
    <Row gutter={16}>
      <Col span={8}>
        <Card
          size="small" title={<Space><AuditOutlined /> {role === 'boss' ? '待老板终审' : '我的待办'}</Space>}
          extra={<Badge count={contents.length} color="#d8314d" />}
        >
          <List
            size="small" dataSource={contents} locale={{ emptyText: <Empty description="暂无待办，去生成一条内容吧" /> }}
            renderItem={(c) => (
              <List.Item
                style={{ cursor: 'pointer', background: active?.id === c.id ? '#e6f4ff' : undefined, borderRadius: 6, padding: '8px 10px' }}
                onClick={async () => { setActive(c); setFeedback(''); try { setActive(await api.content(c.id)); } catch { /* noop */ } }}
              >
                <List.Item.Meta
                  title={<Space>#{c.id} {c.title.slice(0, 18)} {c.version > 1 && <Tag color="red">v{c.version}</Tag>}</Space>}
                  description={<Tag>{c.status_label}</Tag>}
                />
              </List.Item>
            )}
          />
        </Card>
      </Col>

      <Col span={16}>
        {detail ? (
          <Card
            title={`#${detail.id} ${detail.title}`}
            extra={<Space>
              <Tag color={detail.status === 'pending_boss' ? 'purple' : 'gold'}>{detail.status_label}</Tag>
              <Button size="small" onClick={() => nav('detail', detail.id)}>详情/对比</Button>
            </Space>}
          >
            {wrongRole && (
              <Card size="small" style={{ marginBottom: 12, background: '#fff7e6' }}>
                当前内容处于「{detail.status_label}」，需要
                <Button type="link" size="small" onClick={() => setRole(detail.status === 'pending_boss' ? 'boss' : 'supervisor')}>
                  切换到{detail.status === 'pending_boss' ? '老板' : '主管'}视角
                </Button>
                操作。
              </Card>
            )}
            {detail.params?.is_urgent && <div style={{ marginBottom: 12 }}><UrgentBanner deadline={detail.params?.urgent_deadline} /></div>}
      <ContentPreview content={detail} />

            {detail.applied_rules && detail.applied_rules.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <Typography.Text type="secondary">本次生成注入的偏好规则：</Typography.Text>
                {detail.applied_rules.map((r) => <Tag key={r.id} color="blue">{r.code}</Tag>)}
              </div>
            )}

            {reviews.length > 0 && (
              <Card size="small" style={{ marginTop: 14 }} title="审核记录">
                {reviews.map((r: any) => (
                  <div key={r.id} style={{ marginBottom: 6 }}>
                    <Tag color={r.reviewer_role === 'boss' ? 'purple' : 'blue'}>{r.reviewer_role === 'boss' ? '老板' : '主管'}</Tag>
                    <Tag color={r.action === 'approve' ? 'green' : 'red'}>{r.action === 'approve' ? '通过' : '退回'}</Tag>
                    <Typography.Text type="secondary">第 {r.round} 轮 · {r.created_at}</Typography.Text>
                    {r.feedback_text && <div style={{ paddingLeft: 8, color: '#666' }}>“{r.feedback_text}”</div>}
                  </div>
                ))}
              </Card>
            )}

            {/* ── actions by status ── */}
            {(detail.status === 'pending_supervisor' || detail.status === 'pending_boss') && !wrongRole && (
              <Card size="small" style={{ marginTop: 14 }} title={role === 'boss' ? '老板终审（反馈将自动沉淀为偏好信号）' : '主管初审'}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space wrap>
                    {PRESETS.map((p) => (
                      <Tag.CheckableTag key={p} checked={feedback === p} onChange={() => setFeedback(feedback === p ? '' : p)}>
                        {p.slice(0, 12)}…
                      </Tag.CheckableTag>
                    ))}
                  </Space>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>点选快捷评语或自行输入（推荐演示话术：“颜色太深，整体不够国际化…”）</Typography.Text>
                  <Typography.Paragraph style={{ marginBottom: 4 }}>
                    <textarea
                      rows={3} value={feedback} onChange={(e) => setFeedback(e.target.value)}
                      style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid #d9d9d9' }}
                      placeholder="退回修改时必填；通过时可留空"
                    />
                  </Typography.Paragraph>
                  <Space>
                    <Button type="primary" icon={<CheckOutlined />} loading={busy} onClick={approve}>
                      {role === 'boss' ? '终审通过' : '初审通过'}
                    </Button>
                    <Button danger icon={<CloseOutlined />} loading={busy} onClick={reject}>退回修改</Button>
                  </Space>
                </Space>
              </Card>
            )}

            {detail.status === 'pending_revision' && role === 'supervisor' && (
              <Card size="small" style={{ marginTop: 14, background: '#fff2f0' }} title="退回修改（偏好信号已提取，确认后重新生成）">
                <Space>
                  <Button type="primary" icon={<ScissorOutlined />}
                    onClick={() => { setRegenBase(detail); nav('generate'); }}>
                    按最新偏好重新生成（v{detail.version} → v{detail.version + 1}）
                  </Button>
                  <Button onClick={() => nav('prefs')}>先去偏好中心确认信号</Button>
                </Space>
              </Card>
            )}

            {detail.status === 'confirmed' && role === 'supervisor' && (
              <Card size="small" style={{ marginTop: 14, background: '#f6ffed' }} title="老板已确认，可分发">
                <Space>
                  <Popconfirm title="分发至全部已适配渠道？" onConfirm={distribute}>
                    <Button type="primary" icon={<RocketOutlined />} loading={busy}>分发至渠道</Button>
                  </Popconfirm>
                  <Button onClick={() => nav('detail', detail.id)}>先看渠道适配预览</Button>
                </Space>
              </Card>
            )}
          </Card>
        ) : (
          <Card><Empty description="选择左侧内容进行审核" /></Card>
        )}
      </Col>

      {/* boss reject → extracted preference signals */}
      <Modal
        open={!!signals} title="🧠 偏好信号自动提取完成" footer={null} width={640}
        onCancel={() => { setSignals(null); setFeedback(''); }}
      >
        <Typography.Paragraph type="secondary">
          老板的退回反馈已由偏好引擎解析为以下规则（<b>未经主管确认不会生效</b> —— 精度兜底机制）：
        </Typography.Paragraph>
        {signals?.map(({ rule, created }: any) => (
          <Card size="small" key={rule.id} style={{ marginBottom: 8 }}>
            <Space wrap>
              <Tag color="red">{rule.code}</Tag>
              <Tag color="geekblue">{rule.category}</Tag>
              <Typography.Text strong>{rule.rule_text}</Typography.Text>
              <Tag color="orange">置信度 {(rule.confidence * 100).toFixed(0)}%</Tag>
              <Tag color={created ? 'volcano' : 'cyan'}>{created ? '新提取' : '关联已有待确认规则'}</Tag>
            </Space>
            {rule.evidence && <div style={{ marginTop: 6, color: '#888' }}>原文证据：“{rule.evidence}”</div>}
          </Card>
        ))}
        <Space style={{ marginTop: 12 }}>
          <Button type="primary" onClick={() => { setSignals(null); setFeedback(''); setRole('supervisor'); nav('prefs'); }}>
            切换到主管视角 · 去偏好中心确认生效
          </Button>
          <Button onClick={() => { setSignals(null); setFeedback(''); }}>稍后处理</Button>
        </Space>
      </Modal>
    </Row>
  );
}
