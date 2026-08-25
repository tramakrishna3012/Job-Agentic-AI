"use client";

import React, { useEffect, useState, useMemo } from "react";
import {
  Briefcase,
  Calendar,
  CheckCircle2,
  Clock,
  ExternalLink,
  Filter,
  Flame,
  Key,
  Layers,
  Lock,
  LogOut,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  X,
  AlertCircle,
  FileText
} from "lucide-react";

interface ApplicationSummary {
  id: number;
  company: string;
  role: string;
  date_applied: string;
  status: string;
  match_score?: number;
  drive_link?: string;
  days_since_update: number;
}

interface ApplicationDetail extends ApplicationSummary {
  jd_hash?: string;
  fit_summary?: string;
}

interface Stats {
  applied: number;
  interview: number;
  rejected: number;
  offer: number;
  total: number;
}

const STATUS_OPTIONS = ["Applied", "Interview", "Offer", "Rejected"];

export default function DashboardPage() {
  // Auth state
  const [token, setToken] = useState<string>("");
  const [inputToken, setInputToken] = useState<string>("");
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string>("");
  const [isVerifying, setIsVerifying] = useState<boolean>(true);

  // Data state
  const [applications, setApplications] = useState<ApplicationSummary[]>([]);
  const [stats, setStats] = useState<Stats>({
    applied: 0,
    interview: 0,
    rejected: 0,
    offer: 0,
    total: 0,
  });
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>("");

  // Filters & Search
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Selected Detail Modal
  const [selectedApp, setSelectedApp] = useState<ApplicationDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);

  // Updating row ID tracker
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  // Check saved token on mount
  useEffect(() => {
    const saved = localStorage.getItem("jaa_dashboard_token");
    if (saved) {
      setToken(saved);
      verifyAndLoad(saved);
    } else {
      setIsVerifying(false);
    }
  }, []);

  const getHeaders = (authToken: string) => {
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken.trim()}`,
    };
  };

  const verifyAndLoad = async (tokenToUse: string) => {
    setIsLoading(true);
    setAuthError("");
    setErrorMsg("");

    try {
      // Test auth with /api/stats
      const statsRes = await fetch("/api/stats", {
        headers: getHeaders(tokenToUse),
      });

      if (statsRes.status === 401) {
        setIsAuthenticated(false);
        setAuthError("Invalid dashboard token. Please verify your DASHBOARD_TOKEN from .env.");
        localStorage.removeItem("jaa_dashboard_token");
        setIsVerifying(false);
        setIsLoading(false);
        return;
      }

      if (!statsRes.ok) {
        throw new Error(`API error: ${statsRes.statusText}`);
      }

      const statsData = await statsRes.json();
      setStats(statsData);

      // Fetch applications list
      const appsRes = await fetch("/api/applications", {
        headers: getHeaders(tokenToUse),
      });
      if (appsRes.ok) {
        const appsData = await appsRes.json();
        setApplications(appsData);
      }

      // Save token
      localStorage.setItem("jaa_dashboard_token", tokenToUse);
      setToken(tokenToUse);
      setIsAuthenticated(true);
    } catch (err: any) {
      console.error("Dashboard error:", err);
      setErrorMsg(err.message || "Failed to load dashboard data. Ensure FastAPI backend is running.");
    } finally {
      setIsVerifying(false);
      setIsLoading(false);
    }
  };

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputToken.trim()) {
      setAuthError("Please enter your DASHBOARD_TOKEN.");
      return;
    }
    verifyAndLoad(inputToken.trim());
  };

  const handleLogout = () => {
    localStorage.removeItem("jaa_dashboard_token");
    setToken("");
    setIsAuthenticated(false);
    setInputToken("");
  };

  const refreshData = async () => {
    if (!token) return;
    await verifyAndLoad(token);
  };

  // Status PATCH handler
  const handleStatusChange = async (appId: number, newStatus: string) => {
    setUpdatingId(appId);
    // Optimistic UI update
    const previousApps = [...applications];
    setApplications((prev) =>
      prev.map((app) => (app.id === appId ? { ...app, status: newStatus, days_since_update: 0 } : app))
    );

    try {
      const res = await fetch(`/api/applications/${appId}`, {
        method: "PATCH",
        headers: getHeaders(token),
        body: JSON.stringify({ status: newStatus }),
      });

      if (!res.ok) {
        throw new Error("Failed to update status.");
      }

      // Refresh stats quietly
      const statsRes = await fetch("/api/stats", { headers: getHeaders(token) });
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (err: any) {
      // Revert on error
      setApplications(previousApps);
      alert(`Error updating status: ${err.message}`);
    } finally {
      setUpdatingId(null);
    }
  };

  // Fetch application detail
  const handleOpenDetail = async (appId: number) => {
    setLoadingDetail(true);
    try {
      const res = await fetch(`/api/applications/${appId}`, {
        headers: getHeaders(token),
      });
      if (res.ok) {
        const detail = await res.json();
        setSelectedApp(detail);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingDetail(false);
    }
  };

  // Filter & search applications
  const filteredApplications = useMemo(() => {
    return applications.filter((app) => {
      const matchesStatus =
        statusFilter === "ALL" || app.status.toLowerCase() === statusFilter.toLowerCase();
      const matchesSearch =
        !searchQuery ||
        app.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
        app.role.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesStatus && matchesSearch;
    });
  }, [applications, statusFilter, searchQuery]);

  const getStatusBadgeClass = (status: string) => {
    switch (status.toLowerCase()) {
      case "offer":
        return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
      case "interview":
        return "bg-purple-500/15 text-purple-400 border-purple-500/30";
      case "rejected":
        return "bg-rose-500/15 text-rose-400 border-rose-500/30";
      case "applied":
      case "tailored":
      default:
        return "bg-sky-500/15 text-sky-400 border-sky-500/30";
    }
  };

  const getScoreColor = (score?: number) => {
    if (!score) return "text-slate-400";
    if (score >= 90) return "text-emerald-400 font-semibold";
    if (score >= 80) return "text-cyan-400";
    if (score >= 70) return "text-amber-400";
    return "text-rose-400";
  };

  const formatDate = (isoStr: string) => {
    try {
      const date = new Date(isoStr);
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return isoStr;
    }
  };

  // ----------------------------------------------------------------------------
  // Render: Token Gate Screen
  // ----------------------------------------------------------------------------
  if (isVerifying) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#090d16] text-slate-300">
        <div className="flex items-center gap-3">
          <RefreshCw className="h-6 w-6 animate-spin text-cyan-400" />
          <span className="text-sm font-medium">Verifying authorization token...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#090d16] px-4">
        <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/90 p-8 shadow-2xl backdrop-blur-xl">
          <div className="mb-6 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-cyan-500/10 text-cyan-400 ring-1 ring-cyan-500/30">
              <Lock className="h-7 w-7" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">JAA Studio</h1>
            <p className="mt-1 text-sm text-slate-400">
              Enter your <code className="rounded bg-slate-800 px-1.5 py-0.5 text-cyan-300">DASHBOARD_TOKEN</code> to unlock the application tracker.
            </p>
          </div>

          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                Dashboard Token
              </label>
              <div className="relative mt-1.5">
                <Key className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input
                  type="password"
                  placeholder="Enter DASHBOARD_TOKEN from .env"
                  value={inputToken}
                  onChange={(e) => setInputToken(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950/80 py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                  autoFocus
                />
              </div>
            </div>

            {authError && (
              <div className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-400">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-500/20 transition-all hover:brightness-110 disabled:opacity-50"
            >
              {isLoading ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <ShieldCheck className="h-4 w-4" />
                  <span>Authenticate Dashboard</span>
                </>
              )}
            </button>
          </form>

          <div className="mt-6 border-t border-slate-800 pt-4 text-center text-xs text-slate-500">
            Phase 1 Single-Process Architecture • Secure Bearer Guard
          </div>
        </div>
      </div>
    );
  }

  // ----------------------------------------------------------------------------
  // Render: Main Dashboard Screen
  // ----------------------------------------------------------------------------
  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100">
      {/* Top Navbar */}
      <header className="sticky top-0 z-30 border-b border-slate-800 bg-[#090d16]/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 text-white shadow-md shadow-cyan-500/20">
              <Briefcase className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold tracking-tight text-white sm:text-lg">
                  JAA Application Tracker
                </h1>
                <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-[11px] font-medium text-cyan-400">
                  Phase 1
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Connected to SQLite <code className="text-slate-300">jaa.db</code>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <span className="hidden items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs text-slate-400 sm:inline-flex">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              Live DB Sync
            </span>

            <button
              onClick={refreshData}
              disabled={isLoading}
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:bg-slate-700 disabled:opacity-50"
              title="Refresh applications"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>

            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs font-medium text-rose-400 transition hover:bg-rose-500/20"
              title="Sign out of dashboard"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Lock</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {/* Placeholder Tag / Stitch Reconcile Notice */}
        <div className="mb-6 flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-3 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-cyan-400 shrink-0" />
            <span>
              <strong>Phase 1 Default UI</strong> — Fully functional against <code className="text-slate-300">/api/*</code> contract. Ready to swap in Stitch theme whenever exported.
            </span>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5 sm:gap-4">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-medium uppercase tracking-wider">Total</span>
              <Layers className="h-4 w-4 text-slate-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-white">{stats.total}</div>
          </div>

          <div className="rounded-xl border border-sky-500/20 bg-sky-950/20 p-4 backdrop-blur-sm">
            <div className="flex items-center justify-between text-sky-400">
              <span className="text-xs font-medium uppercase tracking-wider">Applied</span>
              <Briefcase className="h-4 w-4 text-sky-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-sky-300">{stats.applied}</div>
          </div>

          <div className="rounded-xl border border-purple-500/20 bg-purple-950/20 p-4 backdrop-blur-sm">
            <div className="flex items-center justify-between text-purple-400">
              <span className="text-xs font-medium uppercase tracking-wider">Interview</span>
              <TrendingUp className="h-4 w-4 text-purple-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-purple-300">{stats.interview}</div>
          </div>

          <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-4 backdrop-blur-sm">
            <div className="flex items-center justify-between text-emerald-400">
              <span className="text-xs font-medium uppercase tracking-wider">Offers</span>
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-emerald-300">{stats.offer}</div>
          </div>

          <div className="col-span-2 sm:col-span-1 rounded-xl border border-rose-500/20 bg-rose-950/20 p-4 backdrop-blur-sm">
            <div className="flex items-center justify-between text-rose-400">
              <span className="text-xs font-medium uppercase tracking-wider">Rejected</span>
              <X className="h-4 w-4 text-rose-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-rose-300">{stats.rejected}</div>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          {/* Status Tabs */}
          <div className="flex flex-wrap gap-1.5 rounded-xl border border-slate-800 bg-slate-900/80 p-1">
            {["ALL", "Applied", "Interview", "Offer", "Rejected"].map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  statusFilter === s
                    ? "bg-cyan-500 text-white shadow-md shadow-cyan-500/20"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Search Input */}
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search company or role..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl border border-slate-800 bg-slate-900/90 py-1.5 pl-9 pr-3 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
            />
          </div>
        </div>

        {/* Applications Table Card */}
        <div className="mt-4 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 shadow-xl backdrop-blur-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-900/90 uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="px-4 py-3.5 font-semibold">Company & Role</th>
                  <th className="px-4 py-3.5 font-semibold">Date Applied</th>
                  <th className="px-4 py-3.5 font-semibold">Status</th>
                  <th className="px-4 py-3.5 font-semibold">Match Score</th>
                  <th className="px-4 py-3.5 font-semibold">Follow-Up</th>
                  <th className="px-4 py-3.5 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium text-slate-300">
                {filteredApplications.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                      <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-slate-800 text-slate-400">
                        <Briefcase className="h-5 w-5" />
                      </div>
                      No applications found matching your criteria.
                    </td>
                  </tr>
                ) : (
                  filteredApplications.map((app) => (
                    <tr
                      key={app.id}
                      className="group transition hover:bg-slate-800/30"
                    >
                      {/* Company & Role */}
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-3">
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-800 font-bold text-cyan-400 ring-1 ring-slate-700">
                            {app.company.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div className="font-semibold text-white group-hover:text-cyan-300">
                              {app.company}
                            </div>
                            <div className="text-[11px] text-slate-400">{app.role}</div>
                          </div>
                        </div>
                      </td>

                      {/* Date Applied */}
                      <td className="px-4 py-3.5 text-slate-400">
                        <div className="flex items-center gap-1.5">
                          <Calendar className="h-3.5 w-3.5 text-slate-500" />
                          <span>{formatDate(app.date_applied)}</span>
                        </div>
                      </td>

                      {/* Status Dropdown */}
                      <td className="px-4 py-3.5">
                        <div className="relative inline-block">
                          <select
                            value={app.status}
                            disabled={updatingId === app.id}
                            onChange={(e) => handleStatusChange(app.id, e.target.value)}
                            className={`rounded-lg border px-2.5 py-1 text-xs font-semibold outline-none transition cursor-pointer appearance-none pr-6 ${getStatusBadgeClass(
                              app.status
                            )} bg-opacity-20`}
                          >
                            {STATUS_OPTIONS.map((opt) => (
                              <option key={opt} value={opt} className="bg-slate-900 text-slate-200">
                                {opt}
                              </option>
                            ))}
                          </select>
                          {updatingId === app.id ? (
                            <RefreshCw className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 animate-spin text-slate-400" />
                          ) : (
                            <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-slate-400">
                              ▼
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Match Score */}
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-1.5">
                          <Flame className={`h-3.5 w-3.5 ${getScoreColor(app.match_score)}`} />
                          <span className={`text-xs ${getScoreColor(app.match_score)}`}>
                            {app.match_score ? `${app.match_score}/100` : "N/A"}
                          </span>
                        </div>
                      </td>

                      {/* Follow-up Days */}
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-1.5">
                          <Clock className="h-3.5 w-3.5 text-slate-500" />
                          {app.days_since_update > 7 ? (
                            <span className="rounded bg-rose-500/10 px-1.5 py-0.5 text-[11px] font-semibold text-rose-400 ring-1 ring-rose-500/20" title="More than 7 days since last update">
                              {app.days_since_update}d ago (Due)
                            </span>
                          ) : (
                            <span className="text-slate-400">
                              {app.days_since_update === 0 ? "Today" : `${app.days_since_update}d ago`}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {app.drive_link && (
                            <a
                              href={app.drive_link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-[11px] font-medium text-cyan-300 transition hover:bg-slate-700 hover:text-cyan-200"
                              title="Open Tailored PDF in Google Drive"
                            >
                              <FileText className="h-3 w-3" />
                              <span>Resume</span>
                              <ExternalLink className="h-2.5 w-2.5 opacity-70" />
                            </a>
                          )}

                          <button
                            onClick={() => handleOpenDetail(app.id)}
                            className="rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-[11px] font-medium text-slate-300 transition hover:bg-slate-700 hover:text-white"
                          >
                            Details
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* Application Detail Modal */}
      {selectedApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-base font-bold text-white">{selectedApp.company}</h3>
                <p className="text-xs text-slate-400">{selectedApp.role}</p>
              </div>
              <button
                onClick={() => setSelectedApp(null)}
                className="rounded-lg p-1 text-slate-400 transition hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mt-4 space-y-4 text-xs">
              <div>
                <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px]">
                  AI Fit Summary
                </span>
                <p className="mt-1 rounded-xl border border-slate-800 bg-slate-950 p-3 text-slate-200 leading-relaxed">
                  {selectedApp.fit_summary || "No fit summary recorded for this application."}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                  <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px]">
                    Match Score
                  </span>
                  <div className={`mt-1 text-base font-bold ${getScoreColor(selectedApp.match_score)}`}>
                    {selectedApp.match_score ? `${selectedApp.match_score}/100` : "N/A"}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                  <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px]">
                    Status
                  </span>
                  <div className="mt-1">
                    <span className={`inline-block rounded-md border px-2 py-0.5 font-bold ${getStatusBadgeClass(selectedApp.status)}`}>
                      {selectedApp.status}
                    </span>
                  </div>
                </div>
              </div>

              {selectedApp.jd_hash && (
                <div>
                  <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px]">
                    Job Description SHA-256 Hash
                  </span>
                  <p className="mt-1 truncate rounded-lg bg-slate-950 px-2 py-1 font-mono text-[10px] text-slate-400">
                    {selectedApp.jd_hash}
                  </p>
                </div>
              )}

              {selectedApp.drive_link && (
                <div className="pt-2">
                  <a
                    href={selectedApp.drive_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-500 py-2 text-xs font-semibold text-white shadow-lg shadow-cyan-500/20 transition hover:bg-cyan-400"
                  >
                    <FileText className="h-4 w-4" />
                    <span>Open Tailored PDF in Google Drive</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
