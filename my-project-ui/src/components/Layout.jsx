// src/components/Layout.jsx
import React from 'react';
import { Link, Outlet } from 'react-router-dom';

function Layout() {
  return (
    <div>
      <header>
        <nav>
          <ul style={{ listStyle: "none", display: "flex", gap: "1rem" }}>
            <li><Link to="/">Dashboard</Link></li>
            <li><Link to="/orders">Заказы</Link></li>
            <li><Link to="/distribution-rules">Правила распределения</Link></li>
            <li><Link to="/logists">Логисты</Link></li>
            <li><Link to="/platforms">Площадки</Link></li>
          </ul>
        </nav>
      </header>
      <hr />
      <main>
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;
