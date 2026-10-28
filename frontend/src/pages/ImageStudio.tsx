import { useState } from 'react';
import { Button, Card, Col, Input, Row, Select, Space, Tag, Typography, message } from 'antd';
import { PictureOutlined, RedoOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { api } from '../api';

/** AI 生图工作台 / 试验台 —— 当场生图主舞台 */
const SPECS = [
  { value: 'wechat', label: '公众号头图 900×383', spec: { label: '公众号头图', w: 900, h: 383 } },
  { value: 'xhs', label: '小红书方图 1080×1080', spec: { label: '小红书封面', w: 1080, h: 1080 } },
  { value: 'channels', label: '视频号竖版 1080×1920', spec: { label: '视频号封面', w: 1080, h: 1920 } },
  { value: 'linkedin', label: 'LinkedIn 1200×628', spec: { label: 'LinkedIn封面', w: 1200, h: 628 } },
];

export default function ImageStudio() {
  const [prompt, setPrompt] = useState('浅色系工业风背景，洁净空气主题，大量留白');
  const [title, setTitle] = useState('X系列分子筛 · 现场首展');
  const [subtitle, setSubtitle] = useState('Lower Energy, Higher Purity · 展位 E3-36');
  const [cta, setCta] = useState('Book a Meeting');
  const [specKey, setSpecKey] = useState('wechat');
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    try {
      const spec = SPECS.find((s) => s.value === specKey)!.spec;
      const r = await api.generateImage({
        prompt, spec, title, subtitle, cta, compose: true,
        design_hint: { bg: '#EAF3F8', accent: '#2F7FA8', text: '#1F3340' },
      });
      setResult(r);
    } catch (e: any) { message.error(e?.body?.detail || '生成失败'); }
    finally { setBusy(false); }
  };

  return (
    <Row gutter={16}>
      <Col span={9}>
        <Card title="① 描述与文案（文字由排版层渲染，AI 只画背景）" size="small">
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Typography.Text strong>画面描述（给 AI 的提示词）</Typography.Text>
              <Input.TextArea rows={3} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
            </div>
            <div><Typography.Text strong>标题（程序化排版）</Typography.Text><Input value={title} onChange={(e) => setTitle(e.target.value)} /></div>
            <div><Typography.Text strong>副标题</Typography.Text><Input value={subtitle} onChange={(e) => setSubtitle(e.target.value)} /></div>
            <div><Typography.Text strong>CTA</Typography.Text><Input value={cta} onChange={(e) => setCta(e.target.value)} /></div>
            <div>
              <Typography.Text strong>目标规格</Typography.Text>
              <Select style={{ width: '100%' }} value={specKey} onChange={setSpecKey} options={SPECS} />
            </div>
            <Button type="primary" size="large" icon={<ThunderboltOutlined />} loading={busy} onClick={run}>
              当场生成
            </Button>
          </Space>
        </Card>
      </Col>
      <Col span={15}>
        <Card
          title={<Space><PictureOutlined /> ② 生成结果</Space>}
          extra={result && (
            <Space>
              <Tag color={result.mode === 'live' ? 'green' : 'orange'}>
                {result.mode === 'live' ? `⚡ 实时生图 · ${result.provider}` : '模板合成（未配置生图 API，兜底通道）'}
              </Tag>
              <Tag>{result.latency_ms}ms</Tag>
              <Button size="small" icon={<RedoOutlined />} onClick={run} loading={busy}>重抽一张</Button>
            </Space>
          )}
        >
          {result ? (
            <div style={{ textAlign: 'center' }}>
              <img
                src={result.url}
                style={{ maxWidth: '100%', maxHeight: 560, borderRadius: 12, boxShadow: '0 6px 22px rgba(16,42,67,.16)' }}
              />
              <div style={{ marginTop: 10 }}>
                <Button type="primary" href={result.url} target="_blank" download>下载成品图</Button>
                <Typography.Text type="secondary" style={{ marginLeft: 12, fontSize: 12 }}>
                  AI 画背景 + 代码排文字：文字 100% 准确、规格 100% 精确、配色 100% 服从品牌偏好
                </Typography.Text>
              </div>
            </div>
          ) : (
            <div style={{ color: '#999', textAlign: 'center', padding: 80 }}>
              输入描述点「当场生成」——配置生图 API Key 后为真实文生图（30-60 秒），
              未配置时走模板合成兜底。
            </div>
          )}
        </Card>
      </Col>
    </Row>
  );
}
