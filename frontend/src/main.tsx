import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#2C6E8F',
          colorInfo: '#2C6E8F',
          borderRadius: 10,
          colorBgLayout: '#F4F7FA',
          fontFamily: "'Segoe UI', 'Microsoft YaHei UI', 'Microsoft YaHei', -apple-system, sans-serif",
          colorText: '#16303F',
          colorTextSecondary: '#4A6072',
        },
        components: {
          Card: { headerFontSize: 15 },
          Table: { headerBg: '#F7FAFC' },
          Menu: { itemBorderRadius: 9, itemMarginInline: 10 },
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
);
