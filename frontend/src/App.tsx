import { useEffect, useState } from 'react';
import { Layout, Menu, Segmented, Tag } from 'antd';
import {
  AuditOutlined, DashboardOutlined, ExperimentOutlined, HomeOutlined, PictureOutlined, TeamOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import { api, Content } from './api';
import Home from './pages/Home';
import Generate from './pages/Generate';
import ReviewCenter from './pages/ReviewCenter';
import Preferences from './pages/Preferences';
import Dashboard from './pages/Dashboard';
import ContentDetail from './pages/ContentDetail';
import Accounts from './pages/Accounts';
import ImageStudio from './pages/ImageStudio';

const { Header, Sider, Content: AntContent } = Layout;

export default function App() {
  const [view, setView] = useState<string>('home');
  const [role, setRole] = useState<'supervisor' | 'boss'>('supervisor');
  const [detailId, setDetailId] = useState<number | null>(null);
  const [regenBase, setRegenBase] = useState<Content | null>(null);
  const [mode, setMode] = useState<string>('');

  useEffect(() => { api.health().then((h) => setMode(h.mode === 'offline' ? '离线剧本' : '实时大模型')).catch(() => setMode('后端未启动')); }, []);

  const nav = (v: string, id?: number) => {
    setView(v);
    if (id) setDetailId(id);
    if (v !== 'generate') setRegenBase(null);
  };

  const MENU = [
    { key: 'home', icon: <HomeOutlined />, label: '工作台' },
    { key: 'generate', icon: <ThunderboltOutlined />, label: '内容生成' },
    { key: 'studio', icon: <PictureOutlined />, label: 'AI 生图' },
    { key: 'review', icon: <AuditOutlined />, label: '审核中心' },
    { key: 'prefs', icon: <ExperimentOutlined />, label: '偏好中心' },
    { key: 'accounts', icon: <TeamOutlined />, label: '账号矩阵' },
    { key: 'dashboard', icon: <DashboardOutlined />, label: '数据看板' },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header className="app-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 13 }}>
          <div className="app-logo">🚀</div>
          <div className="app-title-wrap">
            <h1 className="app-title">企业AI营销内容智能管理平台</h1>
            <div className="app-subtitle">AI MARKETING CONTENT PLATFORM</div>
          </div>
          <Tag
            color={mode === '离线剧本' ? 'gold' : 'green'}
            style={{ marginLeft: 10, background: 'rgba(255,255,255,.14)', color: '#fff', borderColor: 'rgba(255,255,255,.25)' }}
          >
            {mode === '离线剧本' ? '离线剧本 · 永不翻车' : mode}
          </Tag>
        </div>
        <div className="role-pill">
          <Segmented
            value={role}
            onChange={(v) => setRole(v as any)}
            options={[
              { label: '👩‍💼 主管视角', value: 'supervisor' },
              { label: '👨‍✈️ 老板视角', value: 'boss' },
            ]}
          />
        </div>
      </Header>
      <Layout>
        <Sider width={192} className="app-sider" theme="light">
          <div className="sider-caption">WORKSPACE</div>
          <Menu mode="inline" selectedKeys={[view]} items={MENU} onClick={({ key }) => nav(key as string)} style={{ borderInlineEnd: 'none', paddingTop: 2 }} />
          <div className="sider-foot" style={{ position: 'absolute', bottom: 18, left: 0, right: 0 }}>
            <div style={{ borderTop: '1px solid var(--line)', paddingTop: 10, marginLeft: 22, marginRight: 22 }}>
              Demo V1.0 · 2026-10-27<br />偏好即审美 · 浅色 · 留白 · 国际化
            </div>
          </div>
        </Sider>
        <AntContent style={{ padding: 22, background: '#F4F7FA', overflow: 'auto', height: 'calc(100vh - 64px)' }}>
          <div key={view + (detailId ?? '')} className="fade-in">
            {view === 'home' && <Home role={role} nav={nav} />}
            {view === 'generate' && <Generate nav={nav} base={regenBase} />}
            {view === 'review' && <ReviewCenter role={role} setRole={setRole} nav={nav} setRegenBase={setRegenBase} />}
            {view === 'prefs' && <Preferences />}
            {view === 'accounts' && <Accounts />}
            {view === 'studio' && <ImageStudio />}
            {view === 'dashboard' && <Dashboard />}
            {view === 'detail' && <ContentDetail id={detailId} role={role} nav={nav} setRegenBase={setRegenBase} />}
          </div>
        </AntContent>
      </Layout>
    </Layout>
  );
}
