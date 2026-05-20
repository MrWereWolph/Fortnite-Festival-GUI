import { useState } from "react";
import "./App.css";

import JamSearchPage from "./pages/JamSearchPage";
import MainSearchPage from "./pages/MainSearchPage";
import ExportPage from "./pages/ExportPage";
import SettingsPage from "./pages/SettingsPage";

const TABS = [
  {
    id: "jam",
    title: "Jam Search",
    subtitle: "BPM, key, mode, Camelot",
  },
  {
    id: "main",
    title: "Main Search",
    subtitle: "Length and difficulties",
  },
  {
    id: "export",
    title: "Export",
    subtitle: "CSV, JSON, database",
  },
  {
    id: "settings",
    title: "Settings",
    subtitle: "Local preferences",
  },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("jam");

  function renderActiveTab() {
    if (activeTab === "jam") return <JamSearchPage />;
    if (activeTab === "main") return <MainSearchPage />;
    if (activeTab === "export") return <ExportPage />;
    if (activeTab === "settings") return <SettingsPage />;
    return <JamSearchPage />;
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-title">FNFest GUI5</div>
          <div className="brand-sub muted">Fortnite Festival Tools</div>
        </div>

        <nav className="nav">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`nav-item ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="nav-title">{tab.title}</span>
              <span className="nav-sub">{tab.subtitle}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer muted">
          <span>Supabase</span>
          <span className="dot">•</span>
          <span>Vercel</span>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <span className="status-pill">GUI5 Web Prototype</span>
          <span className="spacer" />
          <span className="status-pill">Catalog Online</span>
        </header>

        <div className="content">
          {renderActiveTab()}
        </div>
      </main>
    </div>
  );
}
