import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { applyConsoleThemeToCssVars } from './app/theme';
import '@ant-design/x-markdown/dist/x-markdown.css';
import './styles.css';

applyConsoleThemeToCssVars();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
