import { useCallback, useEffect, useState } from 'react';
import { Button, Card, Checkbox, Col, Input, message, Modal, Popconfirm, Row, Space, Spin, Tag, Typography } from 'antd';
import { AppstoreOutlined, EditOutlined, RocketOutlined, ScissorOutlined, SendOutlined, TeamOutlined } from '@ant-design/icons';
import { api, Content } from '../api';
import ContentPreview from '../components/ContentPreview';
import ChannelFrames from '../components/ChannelFrames';
import { UrgentBanner, UrgentCountdown, UrgentTag } from '../components/UrgentBadge';

export default function ContentDetail({
  id, role, nav, setRegenBase,
}: { id: number | null; role: string; nav: (v: any, id?: number) => void; setRegenBase: (c: Content | null) => void }) {
  const [c, setC] = useState<Content | null>(null);
  const [adapting, setAdapting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editCta, setEditCta] = useState('');
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => { if (id) setC(await api.content(id)); }, [id]);
  useEffect(() => { load(); }, [load]);

  if (!id) return <Card><Spin /></Card>;
  if (!c) return <Card><Spin tip="加载中…" /></Card>;

  const lineage = c.lineage?.filter((x) => x.id !== c.id || true) || [];
  const versions = c.lineage && c.lineage.length > 1 ? c.lineage : [c];
  const oldRules = versions.length > 1 ? (versions[0].applied_rules || c.applied_rules || []).map((r) => r.id) : [];
  const newRules = (c.applied_rules || []).filter((r) => !oldRules.includes(r.id));

  const openEdit = () => {
    setEditTitle(c.body?.title || c.title || '');
    setEditBody(c.body?.body || '');
    setEditCta(c.body?.cta || '');
    setEditing(true);
  };
  const saveEdit = async () => {
    setSaving(true);
    try {
      const patch: any = { title: editTitle, body: editBody, cta: editCta };
      if (c.type === 'article' && c.body?.summary) patch.summary = c.body.summary;
      await api.editContent(c.id, patch);
      message.success('人工调教已保存（content_edit 埋点已记录，AI采用率口径会体现人工参与）');
      setEditing(false);
      setC(await api.content(c.id));
    } catch (e: any) { message.error(e?.body?.detail || '保存失败'); }
    finally { setSaving(false); }
  };

  const doAdapt = async () => {
    setAdapting(true);
    try {
      const r = await api.adapt(c.id);
      message.success(`已适配 ${r.versions.length} 个渠道（硬适配：图像规格；软适配：文案风格）`);
      setC(await api.content(c.id));
    } catch (e: any) { message.error(e?.body?.detail || '适配失败'); }
    finally { setAdapting(false); }
  };

  const distribute = async () => {
    try {
      const r = await api.distribute(c.id);
      message.success(`已分发至 ${r.channels.length} 个渠道 🎉`);
      setC(await api.content(c.id));
    } catch (e: any) { message.error(e?.body?.detail || '操作失败'); }
  };

  return (
    <div>
      {c.params?.is_urgent && <UrgentBanner deadline={c.params?.urgent_deadline} />}
      <Card
        title={<Space>
          <span>#{c.id} {c.title}</span>
          {c.params?.is_urgent && <UrgentTag />}
          <Tag color={c.status === 'pending_boss' ? 'purple' : c.status === 'confirmed' ? 'green' : c.status === 'distributed' ? 'cyan' : 'gold'}>{c.status_label}</Tag>
          <Tag>{c.type_label}</Tag>
          {c.version > 1 && <Tag color="red">v{c.version}</Tag>}
          {c.generation_meta?.has_manual_edit && <Tag color="blue" style={{ borderRadius: 999 }}>✍️ 人工已调教</Tag>}
        </Space>}
        extra={
          <Space>
            {role === 'supervisor' && c.status === 'pending_revision' && (
              <Button type="primary" icon={<ScissorOutlined />} onClick={() => { setRegenBase(c); nav('generate'); }}>
                按最新偏好重新生成
              </Button>
            )}
            {role === 'supervisor' && !['generating', 'distributed'].includes(c.status) && (
              <Button icon={<EditOutlined />} onClick={openEdit}>人工调教</Button>
            )}
            {role === 'supervisor' && c.status === 'confirmed' && (
              <Popconfirm title="分发至全部已适配渠道？" onConfirm={distribute}>
                <Button type="primary" icon={<RocketOutlined />}>分发</Button>
              </Popconfirm>
            )}
          </Space>
        }
      >
        {/* version compare — the money shot */}
        {versions.length > 1 ? (
          <div className="money-shot">
            <Typography.Title level={5} style={{ marginTop: 0 }}>
              版本对比：v1（退回） vs v2（偏好注入后重新生成）
            </Typography.Title>
            {newRules.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <Typography.Text type="secondary">v2 新增注入的偏好规则：</Typography.Text>
                {newRules.map((r) => (
                  <Tag key={r.id} color="volcano" style={{ borderRadius: 999 }}>{r.code} {r.category}｜{r.rule_text.slice(0, 18)}</Tag>
                ))}
              </div>
            )}
            <Row gutter={24} style={{ position: 'relative' }}>
              <div className="vs-badge">VS</div>
              {versions.map((v) => (
                <Col span={12} key={v.id}>
                  <div style={{ marginBottom: 6 }}>
                    <Tag color={v.id === c.id ? 'red' : 'default'} style={{ borderRadius: 999 }}>v{v.version}{v.id === c.id ? ' · 当前' : ' · 已被退回'}</Tag>
                  </div>
                  <ContentPreview content={v} small />
                </Col>
              ))}
            </Row>
          </div>
        ) : (
          <ContentPreview content={c} />
        )}

        {(c.generation_meta?.injected_rules?.length ?? 0) > 0 && (
          <div style={{ marginTop: 10 }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              生成元数据：{c.generation_meta.prompt_version} · 注入规则 {c.generation_meta.injected_rules.join('/')} ·
              耗时 {c.generation_meta.latency_ms}ms · {c.generation_meta.mode} 模式（可观测性：每次生成都可追溯）
            </Typography.Text>
          </div>
        )}
      </Card>

      <Card
        style={{ marginTop: 16 }}
        title={<Space><AppstoreOutlined /> 多渠道适配预览（一份素材 × 5 渠道）</Space>}
        extra={role === 'supervisor' && <Button loading={adapting} onClick={doAdapt}>{c.channel_versions?.length ? '重新适配' : '一键适配 5 渠道'}</Button>}
      >
        {c.channel_versions?.length ? (
          <ChannelFrames
            versions={c.channel_versions.map((v: any) => ({
              channel: v.channel, label: v.spec.label, size: v.spec.size,
              limit: v.spec.limit, w: v.spec.w, h: v.spec.h, copy: v.copy,
            }))}
            designHint={c.design_hint}
          />
        ) : (
          <div style={{ color: '#999', textAlign: 'center', padding: 32 }}>
            尚未适配渠道 —— 点击右上角「一键适配 5 渠道」，2 小时的活 3 分钟干完。
          </div>
        )}
      </Card>

      <PackageSection contentId={c.id} />

      <Modal
        open={editing} title={`人工调教 #${c.id}（基于 AI 初稿修改，content_edit 埋点）`} okText="保存调教"
        confirmLoading={saving} onOk={saveEdit} onCancel={() => setEditing(false)} width={680}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Typography.Text strong>标题</Typography.Text>
            <Input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
          </div>
          <div>
            <Typography.Text strong>正文</Typography.Text>
            <Input.TextArea rows={8} value={editBody} onChange={(e) => setEditBody(e.target.value)} />
          </div>
          <div>
            <Typography.Text strong>行动号召（CTA）</Typography.Text>
            <Input value={editCta} onChange={(e) => setEditCta(e.target.value)} />
          </div>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            PRD 4.2「内容专员基于 AI 初稿进行人工加工」—— 保存后内容标记为「✍️ 人工已调教」，并计入 content_edit 埋点（AI采用率 = 初稿未被大改的比例）。
          </Typography.Text>
        </Space>
      </Modal>
    </div>
  );
}

/** 个人自媒体内容包：同一内容 × 账号人设 = 多副面孔 */
function PackageSection({ contentId }: { contentId: number }) {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [items, setItems] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [receiptFor, setReceiptFor] = useState<any>(null);
  const [link, setLink] = useState('');

  const load = useCallback(async () => {
    setAccounts(await api.accounts());
    setItems(await api.listPackages(contentId));
  }, [contentId]);
  useEffect(() => { load(); }, [load]);

  const run = async () => {
    if (!selected.length) { message.warning('请先勾选目标账号'); return; }
    setBusy(true);
    try {
      const r = await api.buildPackage(contentId, selected);
      message.success(`已为 ${r.items.length} 个账号生成人设化内容包（封面：${r.image_mode === 'live' ? 'AI 生图' : '模板合成'}）`);
      setItems(await api.listPackages(contentId));
    } catch (e: any) { message.error(e?.body?.detail || '生成失败'); }
    finally { setBusy(false); }
  };

  const copy = async (text: string) => {
    try { await navigator.clipboard.writeText(text); message.success('文案已复制，去平台粘贴即发 ✅'); }
    catch { message.warning('复制失败，请手动选择文本'); }
  };

  const saveReceipt = async () => {
    try {
      await api.receipt(receiptFor.id, { link, note: '' });
      message.success('发布回执已登记，计入个人号触达');
      setReceiptFor(null); setLink('');
      load();
    } catch (e: any) { message.error('登记失败'); }
  };

  const realPublish = async (p: any) => {
    try {
      const r = await api.publishPackage(p.id);
      message.success(r.detail || '已发布');
      load();
    } catch (e: any) { message.error(e?.body?.detail || '发布失败'); }
  };

  return (
    <Card
      style={{ marginTop: 16 }}
      title={<Space><TeamOutlined /> 个人自媒体内容包（同一内容 · 多副面孔）</Space>}
      extra={
        <Space>
          {accounts.map((a) => (
            <Checkbox
              key={a.id} checked={selected.includes(a.id)}
              onChange={(e) => setSelected(e.target.checked ? [...selected, a.id] : selected.filter((x) => x !== a.id))}
            >
              {a.name}
            </Checkbox>
          ))}
          <Button type="primary" icon={<SendOutlined />} loading={busy} onClick={run}>生成内容包</Button>
        </Space>
      }
    >
      {items.length ? (
        <Row gutter={[16, 16]}>
          {items.map((p) => (
            <Col span={12} key={p.id}>
              <Card size="small" className="card-hover" style={p.status === 'published' ? { borderColor: '#B7E4C7' } : undefined}>
                <div style={{ display: 'flex', gap: 12 }}>
                  <img src={p.image_url} style={{ width: 150, height: 100, objectFit: 'cover', borderRadius: 8, flex: 'none' }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Space size={6}>
                      <Tag color="geekblue" style={{ borderRadius: 999 }}>{p.platform_label}</Tag>
                      <Typography.Text strong style={{ fontSize: 13 }}>{p.account_name}</Typography.Text>
                      {p.status === 'published' && <Tag color="green" style={{ borderRadius: 999 }}>已发布</Tag>}
                    </Space>
                    <div style={{ fontSize: 12.5, color: '#4A6072', marginTop: 6, whiteSpace: 'pre-wrap', lineHeight: 1.7, maxHeight: 100, overflow: 'hidden' }}>
                      {p.copy_text}
                    </div>
                  </div>
                </div>
                <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  {(p.tags || []).map((t: string) => <Tag key={t} style={{ borderRadius: 999, fontSize: 11 }}>{t}</Tag>)}
                  <Typography.Text type="secondary" style={{ fontSize: 11 }}>{p.suggest_time}</Typography.Text>
                  <span style={{ marginLeft: 'auto' }}>
                    <Space>
                      <Button size="small" onClick={() => copy(p.copy_text)}>复制文案</Button>
                      <Button size="small" href={p.image_url} target="_blank" download>下载封面</Button>
                      {p.auth_status === 'connected' && p.status !== 'published' && (
                        <Popconfirm title="真实发布：公众号将创建草稿 / Webhook 将实际投递，确定？" onConfirm={() => realPublish(p)}>
                          <Button size="small" type="primary">🚀 真实发布</Button>
                        </Popconfirm>
                      )}
                      {p.status !== 'published'
                        ? <Button size="small" type="primary" ghost onClick={() => setReceiptFor(p)}>登记回执</Button>
                        : <Tag color="green" style={{ borderRadius: 999 }}>✓</Tag>}
                    </Space>
                  </span>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      ) : (
        <div style={{ color: '#999', textAlign: 'center', padding: 32 }}>
          勾选右上角账号 → 生成人设化内容包：每号一副面孔（工程师口吻 / 掌舵人视角），文案+封面+标签+建议发布时间，复制即发。
        </div>
      )}

      <Modal open={!!receiptFor} title="登记发布回执" okText="登记" onOk={saveReceipt} onCancel={() => setReceiptFor(null)}>
        <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
          粘贴已发布内容链接（或留空手动备注），回执计入个人号触达统计。
        </Typography.Paragraph>
        <Input value={link} onChange={(e) => setLink(e.target.value)} placeholder="https://www.xiaohongshu.com/..." />
      </Modal>
    </Card>
  );
}
