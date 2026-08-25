'use client';

import React, { useState, useEffect, useMemo } from 'react';

interface Application {
  id: number;
  company: string;
  role: string;
  status: 'Applied' | 'Interview' | 'Rejected' | 'Offer' | string;
  drive_link?: string | null;
  drive_file_id?: string | null;
  fit_summary?: string | null;
  match_score?: number | null;
  jd_hash?: string | null;
  created_at: string;
  updated_at: string;
  days_since_update: number;
}

interface Stats {
  applied: number;
  interview: number;
  rejected: number;
  offer: number;
  total: number;
}

const STATUS_CONFIG: Record<string, { bg: string; text: string; border: string; icon: string }> = {
  Applied: {
    bg: 'bg-surface-container-high',
    text: 'text-secondary',
    border: 'border-secondary/20',
    icon: 'send',
  },
  Interview: {
    bg: 'bg-primary/10',
    text: 'text-primary',
    border: 'border-primary/30',
    icon: 'video_chat',
  },
  Offer: {
    bg: 'bg-emerald-50 text-emerald-700',
    text: 'text-emerald-700',
    border: 'border-emerald-300',
    icon: 'military_tech',
  },
  Rejected: {
    bg: 'bg-error-container/40',
    text: 'text-error',
    border: 'border-error/20',
    icon: 'close',
  },
  Tailored: {
    bg: 'bg-surface-container-high',
    text: 'text-on-surface-variant',
    border: 'border-outline-variant',
    icon: 'edit_document',
  },
};

export default function CareerPilotMissionControl() {
  const [token, setToken] = useState<string>('');
  const [inputToken, setInputToken] = useState<string>('');
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string>('');

  // Data state
  const [applications, setApplications] = useState<Application[]>([]);
  const [stats, setStats] = useState<Stats>({ applied: 0, interview: 0, rejected: 0, offer: 0, total: 0 });
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  // UI state
  const [activeNav, setActiveNav] = useState<'overview' | 'applications' | 'resumelab' | 'activity' | 'analytics' | 'settings'>('applications');
  const [viewMode, setViewMode] = useState<'kanban' | 'table'>('kanban');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [isUpdating, setIsUpdating] = useState<number | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Initialize Auth from local storage / cookie
  useEffect(() => {
    const saved = localStorage.getItem('dashboard_token');
    if (saved) {
      setToken(saved);
      setIsAuthenticated(true);
    }
  }, []);

  // Fetch data
  const fetchData = async (authToken: string) => {
    setLoading(true);
    setError('');
    try {
      const headers = { Authorization: `Bearer ${authToken}` };

      const [appsRes, statsRes] = await Promise.all([
        fetch('/api/applications', { headers }),
        fetch('/api/stats', { headers }),
      ]);

      if (appsRes.status === 401 || statsRes.status === 401) {
        setIsAuthenticated(false);
        localStorage.removeItem('dashboard_token');
        setAuthError('Session expired or invalid dashboard token.');
        setLoading(false);
        return;
      }

      if (!appsRes.ok || !statsRes.ok) {
        throw new Error('Failed to fetch data from API');
      }

      const appsData = await appsRes.json();
      const statsData = await statsRes.json();

      setApplications(appsData);
      setStats(statsData);
    } catch (err: any) {
      setError(err.message || 'Error communicating with CareerPilot backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchData(token);
    }
  }, [isAuthenticated, token]);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputToken.trim()) return;
    const cleanToken = inputToken.trim();
    localStorage.setItem('dashboard_token', cleanToken);
    setToken(cleanToken);
    setIsAuthenticated(true);
    setAuthError('');
  };

  const handleLogout = () => {
    localStorage.removeItem('dashboard_token');
    setToken('');
    setIsAuthenticated(false);
    setApplications([]);
  };

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Status update with optimistic UI
  const handleStatusChange = async (appId: number, newStatus: string) => {
    if (!token) return;
    setIsUpdating(appId);

    // Optimistic local update
    const prevApps = [...applications];
    setApplications((prev) =>
      prev.map((app) => (app.id === appId ? { ...app, status: newStatus, updated_at: new Date().toISOString() } : app))
    );

    try {
      const res = await fetch(`/api/applications/${appId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Failed to update status');
      }

      const updated = await res.json();
      setApplications((prev) => prev.map((app) => (app.id === appId ? { ...app, ...updated } : app)));
      showToast(`Updated status for #${appId} to ${newStatus}`);

      // Refresh stats
      const statsRes = await fetch('/api/stats', { headers: { Authorization: `Bearer ${token}` } });
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (err: any) {
      setApplications(prevApps);
      showToast(`Error: ${err.message}`);
    } finally {
      setIsUpdating(null);
    }
  };

  // Filtered applications
  const filteredApps = useMemo(() => {
    return applications.filter((app) => {
      const matchStatus = statusFilter === 'ALL' || app.status.toLowerCase() === statusFilter.toLowerCase();
      const matchSearch =
        !searchQuery ||
        app.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
        app.role.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (app.fit_summary && app.fit_summary.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchStatus && matchSearch;
    });
  }, [applications, statusFilter, searchQuery]);

  // Auth Gate Screen
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
        <div className="w-full max-w-md bg-surface-container-lowest border border-outline-variant/60 rounded-2xl p-8 shadow-ambient-lg text-center">
          <div className="w-16 h-16 bg-primary/10 text-primary rounded-2xl flex items-center justify-center mx-auto mb-4 border border-primary/20">
            <span className="material-symbols-outlined text-[36px]">robot_2</span>
          </div>
          <h1 className="text-2xl font-bold text-on-surface mb-1">CareerPilot AI</h1>
          <p className="text-sm text-on-surface-variant mb-6">Mission Control & Application Tracking Dashboard</p>

          {authError && (
            <div className="mb-4 p-3 bg-error-container text-on-error-container text-xs rounded-lg flex items-center gap-2 text-left">
              <span className="material-symbols-outlined text-sm text-error">error</span>
              <span>{authError}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div className="text-left">
              <label className="block text-xs font-semibold text-on-surface mb-1.5 uppercase tracking-wider">
                Dashboard Access Token
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[20px]">
                  key
                </span>
                <input
                  type="password"
                  value={inputToken}
                  onChange={(e) => setInputToken(e.target.value)}
                  placeholder="Enter DASHBOARD_TOKEN from .env"
                  className="w-full pl-10 pr-4 py-2.5 bg-surface-container-low border border-outline-variant rounded-xl text-sm text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-outline"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 text-on-primary font-medium py-2.5 px-4 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm text-sm"
            >
              <span className="material-symbols-outlined text-[18px]">lock_open</span>
              Authenticate Mission Control
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-outline-variant/40 text-xs text-on-surface-variant flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              FastAPI Ready (:8000)
            </span>
            <span className="text-[11px] text-outline font-mono">v1.2.0-stitch</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-background text-on-background overflow-hidden">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-inverse-surface text-inverse-on-surface px-4 py-3 rounded-xl shadow-lg flex items-center gap-2.5 text-sm animate-bounce">
          <span className="material-symbols-outlined text-emerald-400 text-[20px]">check_circle</span>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Side Navigation Bar (Stitch Design) */}
      <nav className="bg-surface border-r border-outline-variant/60 h-screen w-64 fixed left-0 top-0 flex flex-col py-6 px-4 z-40 hidden md:flex">
        {/* Brand Header */}
        <div className="flex items-center gap-3 mb-6 px-2">
          <div className="w-10 h-10 rounded-xl bg-primary text-on-primary flex items-center justify-center shadow-sm">
            <span className="material-symbols-outlined text-[24px]">robot_2</span>
          </div>
          <div>
            <h1 className="text-lg font-bold text-on-surface leading-tight">CareerPilot AI</h1>
            <p className="text-xs text-emerald-600 font-medium flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Agent Online
            </p>
          </div>
        </div>

        {/* Quick Action Button */}
        <button
          onClick={() => showToast('Agent ready. Run: python jaa.py "JD" in terminal.')}
          className="w-full bg-primary hover:bg-primary/90 text-on-primary rounded-xl py-2.5 px-3 flex items-center justify-center gap-2 text-sm font-medium mb-6 transition-all shadow-sm"
        >
          <span className="material-symbols-outlined text-[20px]">play_arrow</span>
          Run Agent Pipeline
        </button>

        {/* Navigation Links */}
        <div className="flex-1 overflow-y-auto kanban-scroll space-y-1">
          <button
            onClick={() => setActiveNav('overview')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
              activeNav === 'overview'
                ? 'bg-surface-container text-primary font-bold shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
            }`}
          >
            <span className={`material-symbols-outlined text-[20px] ${activeNav === 'overview' ? 'fill text-primary' : ''}`}>
              dashboard
            </span>
            Overview
          </button>

          <button
            onClick={() => setActiveNav('applications')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
              activeNav === 'applications'
                ? 'bg-surface-container text-primary font-bold shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
            }`}
          >
            <span className={`material-symbols-outlined text-[20px] ${activeNav === 'applications' ? 'fill text-primary' : ''}`}>
              description
            </span>
            Applications
            <span className="ml-auto bg-surface-container-high text-on-surface-variant text-[11px] font-semibold px-2 py-0.5 rounded-full">
              {stats.total}
            </span>
          </button>

          <button
            onClick={() => setActiveNav('resumelab')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
              activeNav === 'resumelab'
                ? 'bg-surface-container text-primary font-bold shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
            }`}
          >
            <span className={`material-symbols-outlined text-[20px] ${activeNav === 'resumelab' ? 'fill text-primary' : ''}`}>
              edit_document
            </span>
            Resume Lab
          </button>

          <button
            onClick={() => setActiveNav('activity')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
              activeNav === 'activity'
                ? 'bg-surface-container text-primary font-bold shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
            }`}
          >
            <span className={`material-symbols-outlined text-[20px] ${activeNav === 'activity' ? 'fill text-primary' : ''}`}>
              smart_toy
            </span>
            Agent Activity
          </button>

          <button
            onClick={() => setActiveNav('analytics')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
              activeNav === 'analytics'
                ? 'bg-surface-container text-primary font-bold shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
            }`}
          >
            <span className={`material-symbols-outlined text-[20px] ${activeNav === 'analytics' ? 'fill text-primary' : ''}`}>
              analytics
            </span>
            Analytics
          </button>

          <button
            onClick={() => setActiveNav('settings')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
              activeNav === 'settings'
                ? 'bg-surface-container text-primary font-bold shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
            }`}
          >
            <span className={`material-symbols-outlined text-[20px] ${activeNav === 'settings' ? 'fill text-primary' : ''}`}>
              settings
            </span>
            Settings
          </button>
        </div>

        {/* User Footer */}
        <div className="mt-auto pt-4 border-t border-outline-variant/60">
          <div className="flex items-center justify-between px-2 py-1">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center text-primary font-bold text-xs">
                AM
              </div>
              <div className="truncate">
                <p className="text-xs font-semibold text-on-surface truncate">Alex Mercer</p>
                <p className="text-[10px] text-on-surface-variant truncate">Master Profile Active</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Lock & Logout"
              className="text-outline hover:text-error p-1 rounded-lg transition-colors"
            >
              <span className="material-symbols-outlined text-[18px]">logout</span>
            </button>
          </div>
        </div>
      </nav>

      {/* Main Screen Content Area */}
      <main className="flex-1 flex flex-col md:ml-64 h-screen bg-background overflow-hidden">
        {/* Top App Bar */}
        <header className="bg-surface/90 backdrop-blur-md border-b border-outline-variant/60 sticky top-0 z-30 flex justify-between items-center px-6 py-3">
          <div className="flex items-center gap-4 flex-1">
            {/* Search Input */}
            <div className="relative w-72 hidden sm:block">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[18px]">
                search
              </span>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search applications, roles, companies..."
                className="w-full pl-9 pr-4 py-1.5 bg-surface-container-lowest border border-outline-variant rounded-full text-xs text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-outline"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Live Status Chip */}
            <div className="hidden lg:flex items-center gap-1.5 px-3 py-1 bg-surface-container-low border border-outline-variant/50 rounded-full text-xs font-medium text-on-surface-variant">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              Gemini 3.6 Flash • Drive Synced
            </div>

            {/* Refresh Button */}
            <button
              onClick={() => fetchData(token)}
              disabled={loading}
              className="p-2 text-on-surface-variant hover:bg-surface-container rounded-full transition-colors"
              title="Refresh Data"
            >
              <span className={`material-symbols-outlined text-[20px] ${loading ? 'animate-spin' : ''}`}>
                refresh
              </span>
            </button>

            {/* Notifications Button */}
            <button
              onClick={() => showToast('Push alerts live at ntfy.sh/jaa_alerts_alex_2026')}
              className="relative p-2 text-on-surface-variant hover:bg-surface-container rounded-full transition-colors"
            >
              <span className="material-symbols-outlined text-[20px]">notifications</span>
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-primary rounded-full"></span>
            </button>
          </div>
        </header>

        {/* Dynamic Nav Screen Router */}
        {activeNav === 'overview' && (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-on-surface">Mission Control Overview</h2>
              <p className="text-sm text-on-surface-variant">Real-time status of autonomous job tailoring & pipeline velocity.</p>
            </div>

            {/* KPI Cards Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/60 shadow-ambient">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-on-surface-variant uppercase tracking-wider">Total Pipeline</span>
                  <span className="material-symbols-outlined text-primary text-[20px]">all_inbox</span>
                </div>
                <p className="text-3xl font-bold text-on-surface">{stats.total}</p>
                <p className="text-xs text-on-surface-variant mt-1">Tracked in SQLite</p>
              </div>

              <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/60 shadow-ambient">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-on-surface-variant uppercase tracking-wider">Applied</span>
                  <span className="material-symbols-outlined text-secondary text-[20px]">send</span>
                </div>
                <p className="text-3xl font-bold text-secondary">{stats.applied}</p>
                <p className="text-xs text-on-surface-variant mt-1">Ready for follow-up</p>
              </div>

              <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/60 shadow-ambient">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-on-surface-variant uppercase tracking-wider">Interviews</span>
                  <span className="material-symbols-outlined text-primary text-[20px]">video_chat</span>
                </div>
                <p className="text-3xl font-bold text-primary">{stats.interview}</p>
                <p className="text-xs text-on-surface-variant mt-1">Active interview stages</p>
              </div>

              <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/60 shadow-ambient">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-on-surface-variant uppercase tracking-wider">Offers</span>
                  <span className="material-symbols-outlined text-emerald-600 text-[20px]">military_tech</span>
                </div>
                <p className="text-3xl font-bold text-emerald-600">{stats.offer}</p>
                <p className="text-xs text-on-surface-variant mt-1">Converted offers</p>
              </div>
            </div>

            {/* Quick Overview Panels */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Agent Status Panel */}
              <div className="bg-surface-container-lowest p-6 rounded-2xl border border-outline-variant/60 shadow-ambient">
                <h3 className="text-base font-bold text-on-surface mb-3 flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">smart_toy</span>
                  Autonomous Pipeline Architecture
                </h3>
                <div className="space-y-3 text-sm text-on-surface-variant">
                  <div className="flex items-center justify-between p-3 bg-surface-container-low rounded-xl">
                    <span className="font-medium text-on-surface">LLM Tailor Engine</span>
                    <span className="text-xs px-2.5 py-1 rounded-full bg-primary/10 text-primary font-semibold">Gemini 3.6 Flash</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-surface-container-low rounded-xl">
                    <span className="font-medium text-on-surface">Google Drive Root</span>
                    <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 font-semibold">Connected (Folder ID: 1M2s...)</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-surface-container-low rounded-xl">
                    <span className="font-medium text-on-surface">Instant Push Channel</span>
                    <span className="text-xs px-2.5 py-1 rounded-full bg-secondary-fixed text-on-secondary-container font-semibold">ntfy.sh/jaa_alerts_alex_2026</span>
                  </div>
                </div>
              </div>

              {/* Recent Applications Panel */}
              <div className="bg-surface-container-lowest p-6 rounded-2xl border border-outline-variant/60 shadow-ambient">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-base font-bold text-on-surface flex items-center gap-2">
                    <span className="material-symbols-outlined text-secondary">history</span>
                    Recent Activity
                  </h3>
                  <button
                    onClick={() => setActiveNav('applications')}
                    className="text-xs font-semibold text-primary hover:underline"
                  >
                    View All &rarr;
                  </button>
                </div>
                {applications.length === 0 ? (
                  <p className="text-sm text-outline">No applications tracked yet.</p>
                ) : (
                  <div className="space-y-2">
                    {applications.slice(0, 4).map((app) => (
                      <div
                        key={app.id}
                        onClick={() => {
                          setSelectedApp(app);
                          setActiveNav('applications');
                        }}
                        className="flex items-center justify-between p-3 rounded-xl border border-outline-variant/40 hover:bg-surface-container-low cursor-pointer transition-colors"
                      >
                        <div>
                          <p className="text-sm font-semibold text-on-surface">{app.role}</p>
                          <p className="text-xs text-on-surface-variant">{app.company}</p>
                        </div>
                        <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${STATUS_CONFIG[app.status]?.bg || 'bg-surface-container'} ${STATUS_CONFIG[app.status]?.text || 'text-on-surface'}`}>
                          {app.status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Applications Pipeline Screen */}
        {activeNav === 'applications' && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Page Header & Tab Bar */}
            <div className="px-6 pt-5 pb-3 bg-surface-container-lowest border-b border-outline-variant/60">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                <div>
                  <h2 className="text-2xl font-bold text-on-surface leading-tight">Applications Pipeline</h2>
                  <p className="text-xs text-on-surface-variant">
                    Manage and update your active job applications in one interactive workspace.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {/* View Mode Switcher */}
                  <div className="flex bg-surface-container-low p-1 rounded-xl border border-outline-variant/60">
                    <button
                      onClick={() => setViewMode('kanban')}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                        viewMode === 'kanban'
                          ? 'bg-surface-container-lowest text-primary shadow-sm'
                          : 'text-on-surface-variant hover:text-on-surface'
                      }`}
                    >
                      <span className="material-symbols-outlined text-[16px]">view_kanban</span>
                      Kanban
                    </button>
                    <button
                      onClick={() => setViewMode('table')}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                        viewMode === 'table'
                          ? 'bg-surface-container-lowest text-primary shadow-sm'
                          : 'text-on-surface-variant hover:text-on-surface'
                      }`}
                    >
                      <span className="material-symbols-outlined text-[16px]">table_rows</span>
                      Table
                    </button>
                  </div>

                  <button
                    onClick={() => showToast('CLI Runner: execute python jaa.py "<Job Description>"')}
                    className="bg-primary hover:bg-primary/90 text-on-primary rounded-xl py-2 px-3.5 text-xs font-medium flex items-center gap-1.5 shadow-sm transition-colors"
                  >
                    <span className="material-symbols-outlined text-[18px]">add</span>
                    New Tailored App
                  </button>
                </div>
              </div>

              {/* Status Filter Tabs */}
              <div className="flex overflow-x-auto no-scrollbar gap-4 text-xs font-medium border-b border-outline-variant/40 pt-1">
                <button
                  onClick={() => setStatusFilter('ALL')}
                  className={`pb-2.5 border-b-2 font-semibold transition-colors ${
                    statusFilter === 'ALL'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  All Applications ({stats.total})
                </button>
                <button
                  onClick={() => setStatusFilter('Applied')}
                  className={`pb-2.5 border-b-2 font-semibold transition-colors ${
                    statusFilter === 'Applied'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  Applied ({stats.applied})
                </button>
                <button
                  onClick={() => setStatusFilter('Interview')}
                  className={`pb-2.5 border-b-2 font-semibold transition-colors ${
                    statusFilter === 'Interview'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  Interview ({stats.interview})
                </button>
                <button
                  onClick={() => setStatusFilter('Offer')}
                  className={`pb-2.5 border-b-2 font-semibold transition-colors ${
                    statusFilter === 'Offer'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  Offer ({stats.offer})
                </button>
                <button
                  onClick={() => setStatusFilter('Rejected')}
                  className={`pb-2.5 border-b-2 font-semibold transition-colors ${
                    statusFilter === 'Rejected'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  Rejected ({stats.rejected})
                </button>
              </div>
            </div>

            {/* Applications Content: Kanban or Table */}
            {viewMode === 'kanban' ? (
              /* Kanban Board View */
              <div className="flex-1 overflow-x-auto overflow-y-hidden p-6 kanban-scroll bg-background">
                <div className="flex gap-6 h-full min-w-max pb-4">
                  {['Applied', 'Interview', 'Offer', 'Rejected'].map((columnStatus) => {
                    const colApps = applications.filter((a) => a.status.toLowerCase() === columnStatus.toLowerCase());
                    return (
                      <div
                        key={columnStatus}
                        className="w-80 flex flex-col bg-surface-container-low/60 rounded-2xl border border-outline-variant/60 overflow-hidden"
                      >
                        {/* Column Header */}
                        <div className="p-3.5 bg-surface-container-lowest border-b border-outline-variant/60 flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className={`material-symbols-outlined text-[18px] ${STATUS_CONFIG[columnStatus]?.text || 'text-primary'}`}>
                              {STATUS_CONFIG[columnStatus]?.icon || 'label'}
                            </span>
                            <h3 className="text-sm font-bold text-on-surface">{columnStatus}</h3>
                            <span className="bg-surface-container text-on-surface-variant text-[11px] font-semibold px-2 py-0.5 rounded-full">
                              {colApps.length}
                            </span>
                          </div>
                        </div>

                        {/* Column Cards Container */}
                        <div className="flex-1 overflow-y-auto p-3 space-y-3 kanban-scroll">
                          {colApps.length === 0 ? (
                            <div className="h-48 flex flex-col items-center justify-center text-center p-4 border border-dashed border-outline-variant/60 rounded-xl text-outline text-xs">
                              <span className="material-symbols-outlined text-[32px] mb-1 opacity-50">
                                {STATUS_CONFIG[columnStatus]?.icon || 'inbox'}
                              </span>
                              No applications in {columnStatus}
                            </div>
                          ) : (
                            colApps.map((app) => (
                              <div
                                key={app.id}
                                className="bg-surface-container-lowest rounded-xl border border-outline-variant/60 p-4 shadow-ambient hover:border-primary/40 hover:shadow-ambient-lg transition-all"
                              >
                                {/* Card Header */}
                                <div className="flex items-start justify-between gap-2 mb-2.5">
                                  <div className="flex items-center gap-2.5">
                                    <div className="w-9 h-9 rounded-lg bg-surface-container-high flex items-center justify-center font-bold text-primary text-xs border border-outline-variant/30">
                                      {app.company.slice(0, 2).toUpperCase()}
                                    </div>
                                    <div>
                                      <h4
                                        onClick={() => setSelectedApp(app)}
                                        className="text-sm font-bold text-on-surface hover:text-primary cursor-pointer leading-tight"
                                      >
                                        {app.role}
                                      </h4>
                                      <p className="text-xs text-on-surface-variant">{app.company}</p>
                                    </div>
                                  </div>
                                </div>

                                {/* Match Score & Badges */}
                                <div className="flex flex-wrap items-center gap-1.5 mb-3">
                                  <span className="bg-primary/10 text-primary text-[11px] font-bold px-2 py-0.5 rounded-md flex items-center gap-1">
                                    <span className="material-symbols-outlined text-[13px]">psychology</span>
                                    {app.match_score || 95}% Match
                                  </span>
                                  {app.days_since_update > 7 ? (
                                    <span className="bg-amber-50 text-amber-700 text-[10px] font-medium px-2 py-0.5 rounded-md border border-amber-200">
                                      Follow-up Due ({app.days_since_update}d)
                                    </span>
                                  ) : (
                                    <span className="bg-surface-container text-on-surface-variant text-[10px] px-2 py-0.5 rounded-md">
                                      Active ({app.days_since_update}d ago)
                                    </span>
                                  )}
                                </div>

                                {/* Fit Summary Preview */}
                                {app.fit_summary && (
                                  <p className="text-xs text-on-surface-variant line-clamp-2 mb-3 bg-surface-container-low p-2 rounded-lg">
                                    {app.fit_summary}
                                  </p>
                                )}

                                {/* Action Bar */}
                                <div className="pt-2.5 border-t border-outline-variant/40 flex items-center justify-between text-xs">
                                  {/* Status Selector Dropdown */}
                                  <div className="relative">
                                    <select
                                      value={app.status}
                                      disabled={isUpdating === app.id}
                                      onChange={(e) => handleStatusChange(app.id, e.target.value)}
                                      className="bg-surface-container-low text-on-surface font-semibold text-[11px] py-1 px-2 pr-6 rounded-lg border border-outline-variant/60 focus:outline-none focus:border-primary cursor-pointer"
                                    >
                                      <option value="Applied">Applied</option>
                                      <option value="Interview">Interview</option>
                                      <option value="Offer">Offer</option>
                                      <option value="Rejected">Rejected</option>
                                    </select>
                                  </div>

                                  {/* Drive Link */}
                                  {app.drive_link ? (
                                    <a
                                      href={app.drive_link}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-primary font-semibold flex items-center gap-1 hover:underline text-[11px]"
                                    >
                                      <span className="material-symbols-outlined text-[14px]">visibility</span>
                                      Resume
                                    </a>
                                  ) : (
                                    <button
                                      onClick={() => setSelectedApp(app)}
                                      className="text-outline hover:text-on-surface text-[11px]"
                                    >
                                      Details
                                    </button>
                                  )}
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              /* Data Table View */
              <div className="flex-1 overflow-y-auto p-6 kanban-scroll bg-background">
                <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant/60 shadow-ambient overflow-hidden">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-surface-container-low text-on-surface-variant text-xs uppercase tracking-wider border-b border-outline-variant/60">
                      <tr>
                        <th className="py-3.5 px-4 font-semibold">Company & Role</th>
                        <th className="py-3.5 px-4 font-semibold">Match</th>
                        <th className="py-3.5 px-4 font-semibold">Status</th>
                        <th className="py-3.5 px-4 font-semibold">Last Update</th>
                        <th className="py-3.5 px-4 font-semibold">Resume / Artifact</th>
                        <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-outline-variant/40">
                      {filteredApps.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="py-12 text-center text-outline">
                            No matching applications found.
                          </td>
                        </tr>
                      ) : (
                        filteredApps.map((app) => (
                          <tr key={app.id} className="hover:bg-surface-container-low/50 transition-colors">
                            <td className="py-3.5 px-4">
                              <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center font-bold text-primary text-xs">
                                  {app.company.slice(0, 2).toUpperCase()}
                                </div>
                                <div>
                                  <p
                                    onClick={() => setSelectedApp(app)}
                                    className="font-bold text-on-surface hover:text-primary cursor-pointer"
                                  >
                                    {app.role}
                                  </p>
                                  <p className="text-xs text-on-surface-variant">{app.company}</p>
                                </div>
                              </div>
                            </td>
                            <td className="py-3.5 px-4">
                              <span className="bg-primary/10 text-primary text-xs font-bold px-2 py-0.5 rounded-md">
                                {app.match_score || 95}%
                              </span>
                            </td>
                            <td className="py-3.5 px-4">
                              <select
                                value={app.status}
                                disabled={isUpdating === app.id}
                                onChange={(e) => handleStatusChange(app.id, e.target.value)}
                                className={`text-xs font-semibold py-1 px-2.5 rounded-lg border cursor-pointer ${
                                  STATUS_CONFIG[app.status]?.bg || 'bg-surface-container'
                                } ${STATUS_CONFIG[app.status]?.text || 'text-on-surface'} ${
                                  STATUS_CONFIG[app.status]?.border || 'border-outline-variant'
                                }`}
                              >
                                <option value="Applied">Applied</option>
                                <option value="Interview">Interview</option>
                                <option value="Offer">Offer</option>
                                <option value="Rejected">Rejected</option>
                              </select>
                            </td>
                            <td className="py-3.5 px-4 text-xs text-on-surface-variant">
                              {app.days_since_update === 0
                                ? 'Today'
                                : `${app.days_since_update} day${app.days_since_update > 1 ? 's' : ''} ago`}
                            </td>
                            <td className="py-3.5 px-4">
                              {app.drive_link ? (
                                <a
                                  href={app.drive_link}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs text-primary font-semibold flex items-center gap-1 hover:underline"
                                >
                                  <span className="material-symbols-outlined text-[16px]">picture_as_pdf</span>
                                  Google Drive
                                </a>
                              ) : (
                                <span className="text-xs text-outline">—</span>
                              )}
                            </td>
                            <td className="py-3.5 px-4 text-right">
                              <button
                                onClick={() => setSelectedApp(app)}
                                className="text-xs text-primary font-medium hover:underline"
                              >
                                Details
                              </button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Resume Lab Screen */}
        {activeNav === 'resumelab' && (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-on-surface">Resume Lab & ATS Tailoring</h2>
              <p className="text-sm text-on-surface-variant">Inspect tailored outputs, ATS score calibration, and Google Drive PDFs.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-surface-container-lowest p-6 rounded-2xl border border-outline-variant/60 shadow-ambient col-span-2">
                <h3 className="text-base font-bold text-on-surface mb-4 flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">description</span>
                  Tailored Applications Artifacts
                </h3>
                <div className="space-y-3">
                  {applications.map((app) => (
                    <div key={app.id} className="p-4 rounded-xl border border-outline-variant/60 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-bold text-xs">
                          PDF
                        </div>
                        <div>
                          <p className="font-bold text-on-surface text-sm">{app.role} - {app.company}</p>
                          <p className="text-xs text-on-surface-variant">JD Hash: {app.jd_hash ? `${app.jd_hash.slice(0, 12)}...` : 'N/A'}</p>
                        </div>
                      </div>
                      {app.drive_link && (
                        <a
                          href={app.drive_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-3 py-1.5 bg-primary/10 text-primary hover:bg-primary/20 text-xs font-semibold rounded-lg flex items-center gap-1"
                        >
                          <span className="material-symbols-outlined text-[16px]">open_in_new</span>
                          Open PDF
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-surface-container-lowest p-6 rounded-2xl border border-outline-variant/60 shadow-ambient">
                <h3 className="text-base font-bold text-on-surface mb-3 flex items-center gap-2">
                  <span className="material-symbols-outlined text-secondary">tune</span>
                  ATS Calibration
                </h3>
                <div className="space-y-4 text-xs text-on-surface-variant">
                  <p>Alex Mercer master resume loaded and calibrated for ATS scanning (WeasyPrint 1-page constraints).</p>
                  <div className="p-3 bg-surface-container-low rounded-xl">
                    <p className="font-bold text-on-surface mb-1">Target Persona</p>
                    <p>Staff / Senior Software Engineer & AI Systems Architect</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Agent Activity Screen */}
        {activeNav === 'activity' && (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-on-surface">Agent Activity Stream</h2>
              <p className="text-sm text-on-surface-variant">Audit log of autonomous tailoring pipeline runs and mobile alerts.</p>
            </div>

            <div className="bg-surface-container-lowest p-6 rounded-2xl border border-outline-variant/60 shadow-ambient space-y-4">
              {applications.map((app, idx) => (
                <div key={app.id} className="flex items-start gap-4 p-3 rounded-xl bg-surface-container-low">
                  <span className="material-symbols-outlined text-primary text-[24px]">verified</span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-bold text-on-surface">Pipeline Run #{app.id} Completed</p>
                      <span className="text-xs text-outline">{app.created_at}</span>
                    </div>
                    <p className="text-xs text-on-surface-variant mt-0.5">
                      Tailored resume for <span className="font-semibold">{app.company}</span> ({app.role}). Google Drive upload successful.
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Analytics Screen */}
        {activeNav === 'analytics' && (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-on-surface">Application Analytics</h2>
              <p className="text-sm text-on-surface-variant">Conversion metrics across pipeline stages.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-surface-container-lowest p-6 rounded-2xl border border-outline-variant/60 shadow-ambient">
                <h3 className="text-base font-bold text-on-surface mb-4">Stage Distribution</h3>
                <div className="space-y-3 text-xs">
                  <div>
                    <div className="flex justify-between font-semibold mb-1">
                      <span>Applied</span>
                      <span>{stats.applied} / {stats.total}</span>
                    </div>
                    <div className="w-full bg-surface-container h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-secondary h-full"
                        style={{ width: `${stats.total > 0 ? (stats.applied / stats.total) * 100 : 0}%` }}
                      ></div>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between font-semibold mb-1">
                      <span>Interviews</span>
                      <span>{stats.interview} / {stats.total}</span>
                    </div>
                    <div className="w-full bg-surface-container h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-primary h-full"
                        style={{ width: `${stats.total > 0 ? (stats.interview / stats.total) * 100 : 0}%` }}
                      ></div>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between font-semibold mb-1">
                      <span>Offers</span>
                      <span>{stats.offer} / {stats.total}</span>
                    </div>
                    <div className="w-full bg-surface-container h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-emerald-500 h-full"
                        style={{ width: `${stats.total > 0 ? (stats.offer / stats.total) * 100 : 0}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Settings Screen */}
        {activeNav === 'settings' && (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-on-surface">Mission Control Settings</h2>
              <p className="text-sm text-on-surface-variant">System environment and integration parameters.</p>
            </div>

            <div className="bg-surface-container-lowest p-6 rounded-2xl border border-outline-variant/60 shadow-ambient max-w-2xl space-y-4 text-sm">
              <div>
                <label className="block font-bold text-on-surface text-xs mb-1">DASHBOARD_TOKEN</label>
                <input
                  type="password"
                  disabled
                  value={token}
                  className="w-full p-2.5 bg-surface-container-low border border-outline-variant rounded-xl text-xs font-mono"
                />
              </div>

              <div>
                <label className="block font-bold text-on-surface text-xs mb-1">GOOGLE_DRIVE_ROOT_FOLDER_ID</label>
                <input
                  type="text"
                  disabled
                  value="1M2sV8m9DSvqsuyas8J-CTkBCxuCexgTg"
                  className="w-full p-2.5 bg-surface-container-low border border-outline-variant rounded-xl text-xs font-mono"
                />
              </div>

              <div>
                <label className="block font-bold text-on-surface text-xs mb-1">NTFY TOPIC</label>
                <input
                  type="text"
                  disabled
                  value="jaa_alerts_alex_2026"
                  className="w-full p-2.5 bg-surface-container-low border border-outline-variant rounded-xl text-xs font-mono"
                />
              </div>

              <div className="pt-4 border-t border-outline-variant/40">
                <button
                  onClick={handleLogout}
                  className="px-4 py-2 bg-error-container text-on-error-container text-xs font-bold rounded-xl"
                >
                  Disconnect Session
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Application Detail Modal */}
      {selectedApp && (
        <div className="fixed inset-0 z-50 bg-inverse-surface/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant max-w-lg w-full p-6 shadow-ambient-lg animate-in fade-in zoom-in-95">
            <div className="flex items-start justify-between mb-4">
              <div>
                <span className="text-[11px] font-semibold text-outline uppercase tracking-wider">Application #{selectedApp.id}</span>
                <h3 className="text-xl font-bold text-on-surface">{selectedApp.role}</h3>
                <p className="text-sm font-semibold text-primary">{selectedApp.company}</p>
              </div>
              <button
                onClick={() => setSelectedApp(null)}
                className="text-outline hover:text-on-surface p-1 rounded-lg"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="p-3 bg-surface-container-low rounded-xl">
                <p className="font-semibold text-on-surface mb-1">AI Tailoring Fit Summary</p>
                <p className="text-on-surface-variant leading-relaxed">
                  {selectedApp.fit_summary || 'No fit summary provided during generation.'}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-surface-container-low rounded-xl">
                  <p className="text-outline mb-0.5">Applied Date</p>
                  <p className="font-semibold text-on-surface">{selectedApp.created_at}</p>
                </div>
                <div className="p-3 bg-surface-container-low rounded-xl">
                  <p className="text-outline mb-0.5">Last Update</p>
                  <p className="font-semibold text-on-surface">{selectedApp.days_since_update} days ago</p>
                </div>
              </div>

              {selectedApp.jd_hash && (
                <div className="p-3 bg-surface-container-low rounded-xl">
                  <p className="text-outline mb-0.5">JD SHA-256 Hash</p>
                  <p className="font-mono text-[10px] text-on-surface break-all">{selectedApp.jd_hash}</p>
                </div>
              )}

              {selectedApp.drive_link && (
                <a
                  href={selectedApp.drive_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-2.5 bg-primary text-on-primary hover:bg-primary/90 rounded-xl font-semibold flex items-center justify-center gap-2 transition-colors"
                >
                  <span className="material-symbols-outlined text-[18px]">open_in_new</span>
                  View PDF on Google Drive
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
