import { useEffect, useState } from 'react';
import { Badge, Button, Card, Col, Input, Modal, Row, Select, Space, Tag, Typography, message } from 'antd';
import { PlusOutlined, TeamOutlined } from '@ant-design/icons';
import { api } from '../api';

const PLATFORM_META: Record<string, { icon: string; color: string }> = {
  wechat_mp_personal: { icon: '💼', color: 'green' },
  channels: { icon: '📹', color: 'blue' },
  xhs: { icon: '📕', color: 'magenta' },
  douyin: { icon: '🎵', color: 'geekblue' },
  wechat_mp: { icon: '🏢', color: 'cyan' },
};

export default function Accounts() {
  const [rows, setRows] = useState<any[]>([]);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState<any>({ platform: 'xhs', persona_key: 'engineer' });
  const [connectFor, setConnectFor] = useState<any>(null);
  const [appid, setAppid] = useState('');
  const [secret, setSecret] = useState('');
  const [webhook, setWebhook] = useState('');
  const [connecting, setConnecting] = useState(false);

  const load = () => api.accounts().then(setRows);
  useEffect(() => { load(); }, []);

  const doConnect = async () => {
    setConnecting(true);
    try {
      const body: any = {};
      if (connectFor.platform === 'wechat_mp_personal' || connectFor.platform === 'wechat_mp') {
        if (!appid || !secret) { message.warning('请填写 AppID 和 AppSecret'); setConnecting(false); return; }
        body.appid = appid; body.secret = secret;
      } else {
        if (!webhook) { message.warning('请填写 Webhook 地址'); setConnecting(false); return; }
        body.webhook_url = webhook;
      }
      const r = await api.connectAccount(connectFor.id, body);
      message.success(r.message || '接入成功');
      setConnectFor(null); setAppid(''); setSecret(''); setWebhook('');
      load();
    } catch (e: any) { message.error(e?.body?.detail || '接入失败'); }
    finally { setConnecting(false); }
  };

  const isWx = connectFor && ['wechat_mp_personal', 'wechat_mp'].includes(connectFor.platform);

  const total = rows.reduce((s, r) => s + r.followers, 0);
  const published = rows.reduce((s, r) => s + r.published, 0);

  const save = async () => {
    if (!form.name) { message.warning('请填写账号名称'); return; }
    try {
      await api.createAccount({ ...form, persona: form.persona || '个人号内容人设' });
      message.success('账号已加入矩阵');
      setAdding(false); load();
    } catch (e: any) { message.error(e?.body?.detail || '失败'); }
  };

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}><Card><div className="stat-card"><div className="stat-icon" style={{ background: '#E9F2F7', color: '#2C6E8F' }}><TeamOutlined /></div><div><div className="stat-value">{rows.length}</div><div className="stat-label">已接入自媒体账号（个人号 + 官号）</div></div></div></Card></Col>
        <Col span={8}><Card><div className="stat-card"><div className="stat-icon" style={{ background: '#F0F7F0', color: '#2E9E5B' }}><TeamOutlined /></div><div><div className="stat-value">{(total / 1000).toFixed(1)}k</div><div className="stat-label">矩阵粉丝合计（触达基本盘）</div></div></div></Card></Col>
        <Col span={8}><Card><div className="stat-card"><div className="stat-icon" style={{ background: '#FBF5E8', color: '#B98A1F' }}><TeamOutlined /></div><div><div className="stat-value">{published}</div><div className="stat-label">个人号已发布内容包数</div></div></div></Card></Col>
      </Row>

      <Card
        title={<Space><span style={{ width: 4, height: 16, background: '#2C6E8F', borderRadius: 2, display: 'inline-block' }} />自媒体账号矩阵</Space>}
        extra={
          <Space>
            <Tag color="orange">V1.0 合规策略：内容包 + 复制即发（平台无个人号发布 API）</Tag>
            <Button icon={<PlusOutlined />} onClick={() => setAdding(true)}>接入账号</Button>
          </Space>
        }
      >
        <Row gutter={[16, 16]}>
          {rows.map((a) => {
            const meta = PLATFORM_META[a.platform] || { icon: '📱', color: 'default' };
            return (
              <Col span={6} key={a.id}>
                <Card className="card-hover" size="small">
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <div style={{ width: 44, height: 44, borderRadius: 12, background: '#F0F5F9', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22 }}>{meta.icon}</div>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ fontWeight: 700, color: '#16303F', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{a.name}</div>
                      <Space size={4} style={{ marginTop: 2 }}>
                        <Tag color={meta.color} style={{ borderRadius: 999 }}>{a.platform_label}</Tag>
                        <Badge status="success" text={<span style={{ fontSize: 11, color: '#8AA0B0' }}>已授权</span>} />
                      </Space>
                    </div>
                  </div>
                  <div style={{ marginTop: 10, fontSize: 12, color: '#4A6072', lineHeight: 1.7, minHeight: 40 }}>{a.persona}</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, fontSize: 12, color: '#8AA0B0' }}>
                    <span>粉丝 {a.followers.toLocaleString()}</span>
                    <span>内容包 {a.packages} · 已发 {a.published}</span>
                  </div>
                  <div style={{ marginTop: 10, borderTop: '1px dashed #E3EBF1', paddingTop: 10, display: 'flex', gap: 8 }}>
                    {a.auth_status === 'connected'
                      ? <>
                          <Tag color="green" style={{ borderRadius: 999 }}>已连接真实通道</Tag>
                          <Button size="small" onClick={async () => { await api.disconnectAccount(a.id); message.info('已断开'); load(); }}>断开</Button>
                        </>
                      : <Button size="small" type="primary" ghost onClick={() => setConnectFor(a)}>接入真实通道</Button>}
                  </div>
                </Card>
              </Col>
            );
          })}
        </Row>
        <Typography.Paragraph type="secondary" style={{ marginTop: 14, fontSize: 12 }}>
          生成入口：任意内容详情页 →「个人号内容包」→ 勾选账号一键生成人设化文案 + 平台规格封面。
        </Typography.Paragraph>
      </Card>

      <Modal open={adding} title="接入自媒体账号" okText="加入矩阵" onOk={save} onCancel={() => setAdding(false)}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div><Typography.Text strong>账号名称</Typography.Text><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="如：李工·设备日记" /></div>
          <div>
            <Typography.Text strong>平台</Typography.Text>
            <Select style={{ width: '100%' }} value={form.platform} onChange={(v) => setForm({ ...form, platform: v })}
              options={[
                { value: 'xhs', label: '小红书' }, { value: 'channels', label: '视频号' },
                { value: 'wechat_mp_personal', label: '个人公众号' }, { value: 'douyin', label: '抖音' },
              ]} />
          </div>
          <div>
            <Typography.Text strong>人设类型</Typography.Text>
            <Select style={{ width: '100%' }} value={form.persona_key} onChange={(v) => setForm({ ...form, persona_key: v })}
              options={[
                { value: 'engineer', label: '一线工程师（实干·现场感）' },
                { value: 'boss', label: '企业掌舵人（国际视野）' },
                { value: 'marketing', label: '营销人（干货·方法论）' },
              ]} />
          </div>
          <div><Typography.Text strong>人设描述</Typography.Text><Input value={form.persona} onChange={(e) => setForm({ ...form, persona: e.target.value })} placeholder="留空则按人设类型自动生成" /></div>
        </Space>
      </Modal>

      <Modal
        open={!!connectFor} title={`接入真实通道 · ${connectFor?.name ?? ''}`}
        okText={connecting ? '验证中…' : '验证并接入'} confirmLoading={connecting}
        onOk={doConnect} onCancel={() => setConnectFor(null)}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {isWx ? (
            <>
              <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
                使用<b>微信公众号官方 API</b>（个人订阅号可用）：验证后将 access_token →
                上传封面素材 → 在公众号后台<b>真实创建图文草稿</b>，运营者在草稿箱一键发布。
                <br />凭据获取：mp.weixin.qq.com → 设置与开发 → 基本配置 → 开发者ID(AppID)/开发者密码(AppSecret)。
              </Typography.Paragraph>
              <div><Typography.Text strong>AppID</Typography.Text><Input value={appid} onChange={(e) => setAppid(e.target.value)} placeholder="wx开头" /></div>
              <div><Typography.Text strong>AppSecret</Typography.Text><Input.Password value={secret} onChange={(e) => setSecret(e.target.value)} /></div>
              <Typography.Text type="warning" style={{ fontSize: 12 }}>
                ⚠️ 若提示 IP 不在白名单：请在公众号后台「基本配置-IP白名单」加入本机公网 IP 后重试。
              </Typography.Text>
            </>
          ) : (
            <>
              <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
                该平台无对个人开放的内容发布 API（合规边界见设计文档 §9）。通过
                <b> Webhook 通道</b>真实投递内容包：适用于企业微信/钉钉/飞书群机器人、
                或你自建的中转服务（如有平台企业 API 资质可在此对接）。
              </Typography.Paragraph>
              <div><Typography.Text strong>Webhook 地址</Typography.Text><Input value={webhook} onChange={(e) => setWebhook(e.target.value)} placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=…" /></div>
            </>
          )}
        </Space>
      </Modal>
    </div>
  );
}
