import { useEffect, useState } from 'react';
import {
  Button, Card, Col, Input, Row, Space, Steps, Switch, Tag, Typography, message, Spin,
} from 'antd';
import { ExperimentOutlined, SendOutlined, AppstoreOutlined, ReloadOutlined } from '@ant-design/icons';
import { api, generateSSE, Content, GenMeta, Rule } from '../api';
import ContentPreview from '../components/ContentPreview';
import { UrgentBanner } from '../components/UrgentBadge';

const TYPES = [
  { key: 'invitation', label: '展会邀请函', desc: '标题 + 正文 + CTA + 设计建议（演示主推）' },
  { key: 'article', label: '公众号文章', desc: '主标题 + 摘要 + 正文 + 配图建议' },
];

/** F01 选题策划（Demo 预置版）：点击直接带入生成向导 */
const TOPIC_CARDS = [
  {
    tag: '展会邀请函', title: 'ChemEquip 2026 观众邀请', angle: '以「与世界共享洁净分离」切入，突出 E3-36 现场体验',
    payload: { type: 'invitation', topic: '展会邀请函', event_name: '2026国际化工装备展', sellpoints: '空分能耗优化、天然气深度脱水' },
  },
  {
    tag: '公众号文章', title: 'X 系列降本三问', angle: '从采购视角自问自答：能耗账怎么算、周期怎么延、数据怎么说',
    payload: { type: 'article', topic: 'X系列分子筛降本解读', event_name: '新品内容运营', sellpoints: '空分能耗优化、更换周期延长、年运行8000小时测算' },
  },
  {
    tag: '公众号文章', title: '天然气脱水选型指南', angle: '露点 / 床层高度 / 再生窗口三个参数的组合决策',
    payload: { type: 'article', topic: '天然气深度脱水选型指南', event_name: '技术科普内容', sellpoints: '天然气深度脱水、选型参数解读' },
  },
];

export default function Generate({
  nav, base,
}: { nav: (v: any, id?: number) => void; base?: Content | null }) {
  const [step, setStep] = useState(base ? 1 : 0);
  const [type, setType] = useState<string>(base?.type || 'invitation');
  const [topic, setTopic] = useState(base?.params?.['主题'] || '');
  const [eventName, setEventName] = useState(base?.params?.['展会/场景'] || '2026国际化工装备展');
  const [sellpoints, setSellpoints] = useState(base?.params?.['核心卖点'] || '');
  const [isUrgent, setIsUrgent] = useState(false);
  const [rules, setRules] = useState<Rule[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [text, setText] = useState('');
  const [meta, setMeta] = useState<GenMeta | null>(null);
  const [result, setResult] = useState<Content | null>(null);

  useEffect(() => { api.preferences('active').then(setRules); }, []);

  const start = async () => {
    setStep(2); setStreaming(true); setText(''); setResult(null); setMeta(null);
    try {
      const payload: any = { type, topic, event_name: eventName, sellpoints, is_urgent: isUrgent };
      if (base) payload.base_content_id = base.id;
      const done = await generateSSE(
        payload,
        (m) => { setMeta(m); message.info(`已注入 ${m.used_preferences.length} 条老板偏好规则（${m.mode === 'scripted' ? '离线剧本' : m.mode === 'cache' ? '缓存命中' : '实时大模型'}）`); },
        (t) => setText((prev) => prev + t),
      );
      setResult(done);
    } catch (e: any) {
      message.error(`生成失败：${e?.body?.detail || e.message}`);
      setStep(1);
    } finally { setStreaming(false); }
  };

  return (
    <div>
      <Steps
        current={step} size="small" style={{ marginBottom: 20, maxWidth: 720 }}
        items={[{ title: '选择类型' }, { title: '关键信息' }, { title: 'AI 生成' }]}
      />

      {base && (
        <Card size="small" style={{ marginBottom: 16, background: '#fffbe6' }}>
          基于 <b>#{base.id} {base.title}</b>（v{base.version}）重新生成 → 新版本 <Tag color="red">v{base.version + 1}</Tag>
          ，将按<b>最新生效的偏好规则</b>重新拼装 Prompt。
        </Card>
      )}

      {step === 0 && (
        <Space direction="vertical" size={18} style={{ width: '100%' }}>
          <Card size="small" title="🧭 AI 选题建议（F01 · 预置选题，点击直接开始）">
            <Row gutter={14}>
              {TOPIC_CARDS.map((t) => (
                <Col span={8} key={t.title}>
                  <Card
                    className="type-card card-hover" size="small"
                    style={{ textAlign: 'left', padding: '16px 16px !important', minHeight: 132 }}
                    onClick={() => {
                      setType(t.payload.type); setTopic(t.payload.topic);
                      setEventName(t.payload.event_name); setSellpoints(t.payload.sellpoints);
                      setStep(1);
                    }}
                  >
                    <div style={{ position: 'relative', zIndex: 1 }}>
                      <Tag color="geekblue" style={{ borderRadius: 999 }}>{t.tag}</Tag>
                      <div style={{ fontWeight: 700, fontSize: 15, margin: '8px 0 6px', color: '#16303F' }}>{t.title}</div>
                      <div style={{ fontSize: 12, color: '#7B8FA0', lineHeight: 1.7 }}>{t.angle}</div>
                    </div>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
          <Card size="small" title="或自定义内容类型">
            <Row gutter={16}>
              {TYPES.map((t) => (
                <Col span={10} key={t.key}>
                  <Card className="type-card card-hover" onClick={() => { setType(t.key); setStep(1); }}>
                    <Typography.Title level={4}>{t.label}</Typography.Title>
                    <Typography.Text type="secondary">{t.desc}</Typography.Text>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        </Space>
      )}

      {step === 1 && (
        <Card title="第二步 · 关键信息" style={{ maxWidth: 720 }} extra={<Button onClick={() => setStep(0)}>返回</Button>}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <Typography.Text strong>主题</Typography.Text>
              <Input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="如：展会邀请函 / 产品降本解读" />
            </div>
            <div>
              <Typography.Text strong>展会 / 场景</Typography.Text>
              <Input value={eventName} onChange={(e) => setEventName(e.target.value)} />
            </div>
            <div>
              <Typography.Text strong>核心卖点</Typography.Text>
              <Input.TextArea rows={2} value={sellpoints} onChange={(e) => setSellpoints(e.target.value)}
                placeholder="空分能耗优化、天然气深度脱水（可留空用默认）" />
            </div>
            <Card size="small" style={{ background: '#f0f7fb' }} title={<Space><ExperimentOutlined /> 将注入的老板偏好规则（{rules.length} 条生效）</Space>}>
              {rules.map((r) => (
                <Tag key={r.id} color={r.category === '色彩' ? 'magenta' : r.category === '风格' ? 'geekblue' : 'green'}>
                  {r.code} {r.category}｜{r.rule_text.slice(0, 16)}
                </Tag>
              ))}
            </Card>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', border: isUrgent ? '1px solid #F2C4BC' : '1px dashed #E3EBF1', borderRadius: 10, background: isUrgent ? '#FDF6F5' : '#fff' }}>
              <Switch checked={isUrgent} onChange={setIsUrgent} />
              <Typography.Text strong={isUrgent} type={isUrgent ? 'danger' : undefined}>
                🚨 急单快速通道（F11）
              </Typography.Text>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                AI 优先处理 · SLA 倒计时 4 小时 · 目标当日交付
              </Typography.Text>
            </div>
            <Button type="primary" size="large" icon={<AppstoreOutlined />} onClick={start} loading={streaming}>
              {isUrgent ? '🚨 急单优先生成' : '开始 AI 生成'}
            </Button>
          </Space>
        </Card>
      )}

      {step === 2 && (
        <Row gutter={16}>
          <Col span={12}>
            {meta?.is_urgent && <UrgentBanner deadline={meta.urgent_deadline} />}
            <Card title="AI 实时生成（Prompt 四层拼装：角色→偏好注入→任务→示例）" size="small">
              {meta && (
                <div style={{ marginBottom: 8 }}>
                  {meta.used_preferences.map((p) => (
                    <Tag key={p.code} color="blue">{p.code} {p.rule_text.slice(0, 12)}</Tag>
                  ))}
                </div>
              )}
              <div
                className={streaming ? 'stream-caret' : ''}
                style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', lineHeight: 1.9, minHeight: 320, maxHeight: 460, overflow: 'auto' }}
              >
                {text}
                {streaming && <span style={{ opacity: 0 }}>.</span>}
              </div>
            </Card>
          </Col>
          <Col span={12}>
            <Card title="生成结果预览" size="small" extra={result?.generation_meta && (
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                {result.generation_meta.prompt_version} · {result.generation_meta.latency_ms}ms · {result.generation_meta.mode}
              </Typography.Text>
            )}>
              {result ? (
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  <ContentPreview content={result} />
                  <Space>
                    <Button type="primary" icon={<SendOutlined />} onClick={() => { message.success('已进入待初审，请到审核中心'); nav('review'); }}>
                      提交审核流程
                    </Button>
                    <Button onClick={() => nav('detail', result.id)}>查看详情 / 渠道适配</Button>
                    <Button icon={<ReloadOutlined />} onClick={start} disabled={streaming}>重新生成</Button>
                  </Space>
                </Space>
              ) : (
                <div style={{ color: '#999', padding: 40, textAlign: 'center' }}>等待生成完成…</div>
              )}
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
}
