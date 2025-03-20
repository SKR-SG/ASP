// src/App.js
import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Orders from "./pages/Orders";
import DistributionRules from "./pages/DistributionRules";
import Logists from "./pages/Logists";
import Platforms from "./pages/Platforms";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="orders" element={<Orders />} />
          <Route path="distribution-rules" element={<DistributionRules />} />
          <Route path="logists" element={<Logists />} />
          <Route path="platforms" element={<Platforms />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
