import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css'; // если у вас есть стили

const container = document.getElementById('root');
const root = ReactDOM.createRoot(container);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
