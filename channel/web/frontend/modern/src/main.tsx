import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import '@ant-design/x-markdown/dist/x-markdown.css';
import './styles.css';
import './styles/console.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
