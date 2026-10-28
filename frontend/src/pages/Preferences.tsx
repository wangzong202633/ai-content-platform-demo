import { useCallback, useEffect, useState } from 'react';
import { Button, Card, Col, Empty, message, Modal, Popconfirm, Progress, Row, Space, Tabs, Tag, Typography } from 'antd';
import { CheckOutlined, CloseOutlined, EditOutlined, ExperimentOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { api, Rule } from '../api';

const CAT_COLOR: Record<string, string> = {
  '色彩': 'magenta', '风格': 'geekblue', '排版': 'gold', '内容': 'green', '标杆': 'purple',
};

function RuleCard({ rule, onChanged, onEdit }: { rule: Rule; onChanged: () => void; onEdit: (r: Rule) => void }) {
  const confirm = async () => {
    try { await api.confirmPref(rule.id); message.success(`规则 ${rule.code} 已生效，将注入后续所有生成`); onChanged(); }
    catch (e: any) { message.error(e?.body?.detail || '操作失败'); }
  };
  const reject = async () => {
    try { await api.rejectPref(rule.id); message.info(`已否决 ${rule.code}（AI 误读由人工拦截）`); onChanged(); }
    catch (e: any) { message.error(e?.body?.detail || '操作失败'); }
  };
  return (
    <Card size="small" style={{ marginBottom: 10, borderLeft: `4px solid ${rule.status === 'active' ? '#52c41a' : '#faad14'}` }}>
      <Space wrap>
        <Tag color={CAT_COLOR[rule.category] || 'default'}>{rule.code} · {rule.category}</Tag>
        <Typography.Text strong>{rule.rule_text}</Typography.Text>
        {rule.status === 'pending' && <Tag color="orange">待确认</Tag>}
        {rule.status === 'active' && <Tag color="green">生效中</Tag>}
        {rule.status === 'disabled' && <Tag>已停用</Tag>}
      </Space>
      <Row style={{ marginTop: 8 }} gutter={12} align="middle">
        <Col flex="160px"><Progress percent={Math.round(rule.confidence * 100)} size="small" status={rule.confidence >= 0.9 ? 'active' : 'normal'} /></Col>
        <Col flex="auto">
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {rule.source_note}{rule.evidence ? ` · 证据：“${rule.evidence.slice(0, 20)}”` : ''}
          </Typography.Text>
        </Col>
        {rule.status !== 'disabled' && (
          <Col>
            <Button size="small" icon={<EditOutlined />} onClick={() => onEdit(rule)} style={{ marginRight: 6 }}>编辑</Button>
          </Col>
        )}
        {rule.status === 'pending' && (
          <Col>
            <Space>
              <Button size="small" type="primary" icon={<CheckOutlined />} onClick={confirm}>确认生效</Button>
              <Popconfirm title="否决后该规则不会影响生成，确定？" onConfirm={reject}>
                <Button size="small" danger icon={<CloseOutlined />}>否决</Button>
              </Popconfirm>
            </Space>
          </Col>
        )}
      </Row>
    </Card>
  );
}

export default function Preferences() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [testText, setTestText] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<any[] | null>(null);
  const [editing, setEditing] = useState<Rule | null>(null);
  const [editText, setEditText] = useState('');
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => { api.preferences().then(setRules); }, []);
  useEffect(() => { load(); }, [load]);

  const saveEdit = async () => {
    if (!editText.trim()) { message.warning('规则文本不能为空'); return; }
    setSaving(true);
    try {
      await api.editPref(editing!.id, editText);
      message.success(`规则 ${editing!.code} 已修正（AI 误读由人工兜底）`);
      setEditing(null);
      load();
    } catch (e: any) { message.error(e?.body?.detail || '保存失败'); }
    finally { setSaving(false); }
  };

  const pending = rules.filter((r) => r.status === 'pending');
  const active = rules.filter((r) => r.status === 'active');
  const disabled = rules.filter((r) => r.status === 'disabled');

  const tryExtract = async () => {
    if (!testText.trim()) { message.warning('请输入一段反馈'); return; }
    setTesting(true); setTestResult(null);
    try {
      const r = await api.extractPrefs(testText);
      setTestResult(r.rules);
      message.success(`提取到 ${r.signals.length} 条信号，已转为待确认规则`);
      load();
    } catch (e: any) { message.error(e?.body?.detail || '提取失败'); }
    finally { setTesting(false); }
  };

  return (
    <Row gutter={16}>
      <Col span={16}>
        <Tabs
          items={[
            {
              key: 'pending',
              label: `待主管确认（${pending.length}）`,
              children: pending.length
                ? pending.map((r) => <RuleCard key={r.id} rule={r} onChanged={load} onEdit={(rr) => { setEditing(rr); setEditText(rr.rule_text); }} />)
                : <Empty description="暂无待确认信号（老板退回内容后将自动出现）" />,
            },
            {
              key: 'active',
              label: `已生效（${active.length}）`,
              children: active.length
                ? active.map((r) => <RuleCard key={r.id} rule={r} onChanged={load} onEdit={(rr) => { setEditing(rr); setEditText(rr.rule_text); }} />)
                : <Empty />,
            },
            {
              key: 'disabled',
              label: `已停用（${disabled.length}）`,
              children: disabled.length ? disabled.map((r) => <RuleCard key={r.id} rule={r} onChanged={load} onEdit={(rr) => { setEditing(rr); setEditText(rr.rule_text); }} />) : <Empty description="暂无" />,
            },
          ]}
        />
      </Col>
      <Col span={8}>
        <Card size="small" title={<Space><ThunderboltOutlined /> 偏好提取试验台</Space>}>
          <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
            输入任意一句“老板口吻”的反馈，看偏好引擎能提取出什么（试试：排版太挤，重点不突出）。
          </Typography.Paragraph>
          <textarea
            rows={3} value={testText} onChange={(e) => setTestText(e.target.value)}
            style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid #d9d9d9' }}
          />
          <Button type="primary" block style={{ marginTop: 8 }} loading={testing} icon={<ExperimentOutlined />} onClick={tryExtract}>
            提取偏好信号
          </Button>
          {testResult && (
            <div style={{ marginTop: 10 }}>
              {testResult.map(({ rule, created }: any) => (
                <div key={rule.id} style={{ marginBottom: 6 }}>
                  <Tag color={CAT_COLOR[rule.category]}>{rule.code} {rule.category}</Tag>
                  {rule.rule_text}
                  <Tag style={{ marginLeft: 6 }} color={created ? 'volcano' : 'cyan'}>{created ? '新提取' : '关联已有'}</Tag>
                </div>
              ))}
            </div>
          )}
        </Card>
        <Card size="small" style={{ marginTop: 12 }} title="偏好飞轮机制">
          <Typography.Paragraph style={{ fontSize: 12 }} type="secondary">
            老板审核反馈 → <b>自动提取信号</b>（结构化+置信度）→ 主管确认生效 → 注入后续生成 Prompt。
            <br />信号不直接生效 —— 主管确认是精度兜底，避免 AI 误读老板意图；<b>提取有偏差时可手动「编辑」修正</b>。
            <br />当前规则数：{rules.length} / 100（V1.0 上限）。
          </Typography.Paragraph>
        </Card>
      </Col>

      <Modal
        open={!!editing} title={`编辑规则 ${editing?.code ?? ''}（人工兜底）`} okText="保存"
        confirmLoading={saving} onOk={saveEdit} onCancel={() => setEditing(null)}
      >
        <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
          将规则文本改写为可执行的表述（如“主色调采用浅色系”而非“颜色好看点”），保存后立即影响后续生成。
        </Typography.Paragraph>
        <textarea
          rows={3} value={editText} onChange={(e) => setEditText(e.target.value)}
          style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid #d9d9d9' }}
        />
      </Modal>
    </Row>
  );
}
