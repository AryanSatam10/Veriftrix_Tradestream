import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadInvoice, updateTransactionStatus, fetchAnalytics } from './services/api';
import {
  UploadCloud, FileText, AlertTriangle, CheckCircle2, ShieldAlert,
  Clock, FileWarning, Loader2, TrendingUp, Package, Hash, DollarSign, 
  Activity, Check, XCircle, Code, RefreshCw, X, LayoutDashboard, ScanLine, AlertOctagon, BarChart3, Fingerprint
} from 'lucide-react';
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

// ---------------------------------------------------------------------------
// Fintech Design Tokens
// ---------------------------------------------------------------------------
const RISK_BANDS = [
  { max: 0.3, label: 'LOW RISK', tone: 'success', action: 'AUTO-APPROVE' },
  { max: 0.65, label: 'ELEVATED RISK', tone: 'warning', action: 'MANUAL REVIEW' },
  { max: 1.01, label: 'CRITICAL RISK', tone: 'danger', action: 'IMMEDIATE HOLD' },
];

function getRiskBand(score) {
  return RISK_BANDS.find((b) => score <= b.max) ?? RISK_BANDS[RISK_BANDS.length - 1];
}

const toneClasses = {
  success: { text: 'text-emerald-700', bg: 'bg-emerald-50/50', border: 'border-emerald-500', bar: 'bg-emerald-500', icon: 'text-emerald-600', badge: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
  warning: { text: 'text-amber-700', bg: 'bg-amber-50/50', border: 'border-amber-500', bar: 'bg-amber-500', icon: 'text-amber-600', badge: 'bg-amber-100 text-amber-800 border-amber-200' },
  danger: { text: 'text-rose-700', bg: 'bg-rose-50/50', border: 'border-rose-500', bar: 'bg-rose-500', icon: 'text-rose-600', badge: 'bg-rose-100 text-rose-800 border-rose-200' },
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="w-8 h-8 bg-slate-900 flex items-center justify-center border border-slate-800">
        <ShieldAlert className="w-4 h-4 text-white" strokeWidth={2.5} />
      </div>
      <div className="leading-none flex flex-col justify-center">
        <div className="flex items-center gap-1.5">
          <span className="text-[17px] font-bold text-slate-900 tracking-tight">TradeStream</span>
          <span className="px-1.5 py-0.5 text-[9px] font-bold bg-blue-50 text-blue-700 border border-blue-200 uppercase tracking-widest">Enterprise</span>
        </div>
      </div>
    </div>
  );
}

function StatusPill() {
  return (
    <div className="flex items-center gap-2 px-2.5 py-1 bg-slate-50 border border-slate-200 shadow-sm">
      <span className="relative flex h-1.5 w-1.5">
        <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60 animate-ping" />
        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500" />
      </span>
      <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">System Operational</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Application
// ---------------------------------------------------------------------------

function App() {
  const [activeTab, setActiveTab] = useState('ingestion');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [fileName, setFileName] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [resolvedState, setResolvedState] = useState(null);
  const [showJson, setShowJson] = useState(false);

  const [dashboardData, setDashboardData] = useState({
    kpis: { total_volume: 0, processed_count: 0, intervention_rate: 0 },
    chart_data: [],
    recent_transactions: []
  });
  const [chartsLoading, setChartsLoading] = useState(false);

  useEffect(() => {
    if (activeTab === 'analytics') {
      setChartsLoading(true);
      fetchAnalytics().then(data => {
        if (data && !data.error) {
          setDashboardData(data);
        }
        setChartsLoading(false);
      });
    }
  }, [activeTab, resolvedState]); 

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setFileName(file.name);
    setLoading(true);
    setError(null);
    setResult(null);
    setResolvedState(null);

    try {
      const data = await uploadInvoice(file);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'application/pdf': ['.pdf'] }, multiple: false, disabled: loading || resolvedState !== null
  });

  const handleDecision = async (decision) => {
    setActionLoading(decision);
    try {
      await updateTransactionStatus(result.transaction_id, decision);
      setResolvedState(decision);
    } catch (err) {
      console.error("Failed to update status", err);
    } finally {
      setActionLoading(null);
    }
  };

  const resetDashboard = () => {
    setResult(null);
    setFileName(null);
    setResolvedState(null);
    setError(null);
  };

  const handleExportCSV = () => {
    if (!dashboardData || !dashboardData.recent_transactions || dashboardData.recent_transactions.length === 0) return;
    const headers = ["Transaction ID", "Timestamp", "Value (USD)", "Risk Score", "Status"];
    const csvRows = [headers.join(",")];
    dashboardData.recent_transactions.forEach(txn => {
      const row = [
        txn.transaction_id,
        new Date(txn.created_at).toISOString(),
        txn.amount,
        txn.risk_score,
        txn.is_anomalous ? "REVIEW_REQUIRED" : "AUTO_CLEARED"
      ];
      csvRows.push(row.join(","));
    });
    const csvString = csvRows.join("\n");
    const blob = new Blob([csvString], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `TradeStream_Audit_Ledger_${new Date().getTime()}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const timestamp = new Date().toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

  return (
    <div className="min-h-screen bg-[#F4F4F5] text-slate-900 font-sans antialiased selection:bg-slate-200 relative">
      
      {/* Dev Console Modal */}
      {showJson && result && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="bg-[#1E1E1E] border border-slate-700 w-full max-w-3xl shadow-2xl overflow-hidden shadow-black/50 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-[#252526]">
              <div className="flex items-center gap-2">
                <Code className="w-4 h-4 text-slate-400" />
                <h3 className="text-slate-300 font-mono text-[11px] uppercase tracking-widest">Transaction Payload</h3>
              </div>
              <button onClick={() => setShowJson(false)} className="text-slate-400 hover:text-white"><X className="w-4 h-4" /></button>
            </div>
            <div className="p-5 overflow-y-auto max-h-[60vh] bg-[#1E1E1E]">
              <pre className="text-[#9CDCFE] font-mono text-[12px] leading-relaxed">{JSON.stringify(result, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}

      {/* Institutional Header */}
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
        <div className="max-w-[1400px] mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-10 h-full">
            <Logo />
            
            {/* Fintech Segmented Nav */}
            <nav className="hidden md:flex items-center gap-6 h-full">
              <button 
                onClick={() => setActiveTab('ingestion')} 
                className={`flex items-center gap-2 h-full text-[13px] font-semibold transition-all border-b-2 ${activeTab === 'ingestion' ? 'border-slate-900 text-slate-900' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
              >
                <ScanLine className="w-4 h-4" /> Scanner Hub
              </button>
              <button 
                onClick={() => setActiveTab('analytics')} 
                className={`flex items-center gap-2 h-full text-[13px] font-semibold transition-all border-b-2 ${activeTab === 'analytics' ? 'border-slate-900 text-slate-900' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
              >
                <LayoutDashboard className="w-4 h-4" /> Global Analytics
              </button>
            </nav>
          </div>
          <StatusPill />
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto px-6 py-8">
        
        {/* =========================================================================
            VIEW 1: INGESTION HUB
            ========================================================================= */}
        {activeTab === 'ingestion' && (
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 animate-in fade-in duration-300">
            
            {/* Left Column */}
            <div className="xl:col-span-4 flex flex-col gap-6">
              <div>
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">Compliance Scanner</h1>
                <p className="text-[13px] text-slate-500 mt-1">Upload trade finance documents for TBML and risk screening.</p>
              </div>

              <div className="bg-white border border-slate-200 shadow-sm p-1">
                <div 
                  {...getRootProps()} 
                  className={`relative border border-dashed transition-all cursor-pointer overflow-hidden bg-slate-50/50 hover:bg-slate-50 ${isDragActive ? 'border-slate-900 bg-slate-100' : 'border-slate-300'} ${(loading || resolvedState) ? 'opacity-50 cursor-not-allowed pointer-events-none' : ''}`}
                >
                  <input {...getInputProps()} />
                  <div className="flex flex-col items-center justify-center py-14 px-6 text-center">
                    <div className="w-10 h-10 bg-white border border-slate-200 shadow-sm flex items-center justify-center mb-4">
                      <UploadCloud className={`w-5 h-5 ${isDragActive ? 'text-slate-900' : 'text-slate-400'}`} />
                    </div>
                    {isDragActive ? (
                      <p className="text-[13px] font-bold text-slate-900 tracking-wide">Awaiting drop...</p>
                    ) : (
                      <>
                        <p className="text-[13px] font-bold text-slate-700">Select document to process</p>
                        <p className="text-[12px] text-slate-500 mt-1">PDF format only. Max 10MB.</p>
                      </>
                    )}
                  </div>
                </div>

                {fileName && (
                  <div className="flex items-center justify-between m-4 p-3 bg-slate-50 border border-slate-200">
                    <div className="flex items-center gap-3 overflow-hidden">
                      <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                      <span className="text-[12px] font-semibold text-slate-700 truncate">{fileName}</span>
                    </div>
                    {!loading && !error && <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />}
                  </div>
                )}
                {error && (
                  <div className="flex items-start gap-3 m-4 p-3 bg-rose-50 border-l-2 border-rose-500">
                    <FileWarning className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-[12px] font-bold text-rose-900 uppercase tracking-wider">Processing Error</p>
                      <p className="text-[12px] text-rose-700 mt-1 font-mono">{error}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Right Column */}
            <div className="xl:col-span-8 flex flex-col">
              <div className="bg-white border border-slate-200 shadow-sm flex flex-col flex-1 relative min-h-[500px]">
                
                {/* Overlay */}
                {resolvedState && (
                  <div className="absolute inset-0 bg-white/90 backdrop-blur-sm z-20 flex flex-col items-center justify-center animate-in fade-in duration-300">
                    <div className="w-12 h-12 bg-emerald-50 border border-emerald-200 flex items-center justify-center mb-4">
                      <CheckCircle2 className="w-6 h-6 text-emerald-600" />
                    </div>
                    <h3 className="text-lg font-bold text-slate-900 tracking-tight mb-1">Transaction Logged</h3>
                    <p className="text-slate-500 text-[13px] mb-6">Status permanently updated to <span className="font-bold text-slate-900">{resolvedState}</span>.</p>
                    <button onClick={resetDashboard} className="flex items-center gap-2 px-5 py-2 bg-slate-900 text-white text-[13px] font-semibold hover:bg-slate-800 transition-colors shadow-sm focus:ring-2 focus:ring-slate-900 focus:ring-offset-2">
                      <RefreshCw className="w-3.5 h-3.5" /> Process Next Record
                    </button>
                  </div>
                )}

                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50/50">
                  <h2 className="text-[13px] font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                    <Activity className="w-4 h-4 text-slate-400" /> Analysis Report
                  </h2>
                  {result && (
                    <div className="flex items-center gap-4">
                      <span className="text-[11px] font-mono text-slate-500 bg-white px-2 py-1 border border-slate-200">{result.transaction_id}</span>
                      <span className="text-[11px] text-slate-400 flex items-center gap-1 font-medium"><Clock className="w-3 h-3" /> {timestamp}</span>
                    </div>
                  )}
                </div>

                <div className="flex-1 p-6 bg-slate-50/30">
                  {!result && !loading && (
                    <div className="flex flex-col items-center justify-center h-full py-24 text-center">
                      <Fingerprint className="w-8 h-8 text-slate-300 mb-4" strokeWidth={1} />
                      <p className="text-[14px] font-medium text-slate-900">Awaiting Telemetry</p>
                      <p className="text-[13px] text-slate-500 mt-1">System is standing by for document ingestion.</p>
                    </div>
                  )}
                  
                  {loading && (
                     <div className="flex flex-col items-center justify-center h-full py-20">
                     <Loader2 className="w-6 h-6 text-slate-800 animate-spin mb-4" />
                     <p className="text-[13px] text-slate-600 font-medium">Executing GenAI & ML Pipeline...</p>
                   </div>
                  )}

                  {result && (
                    <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 max-w-3xl mx-auto">
                      
                      {/* Institutional Risk Card */}
                      {(() => {
                        const band = getRiskBand(result.risk_score);
                        const tone = toneClasses[band.tone];
                        return (
                          <div className={`mb-6 bg-white border border-l-4 ${tone.border} p-5 shadow-sm`}>
                            <div className="flex justify-between items-start mb-4">
                              <div>
                                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Isolation Forest Verdict</p>
                                <div className="flex items-center gap-2">
                                  {band.tone === 'success' ? <CheckCircle2 className={`w-4 h-4 ${tone.icon}`} /> : <AlertTriangle className={`w-4 h-4 ${tone.icon}`} />}
                                  <h3 className={`text-[15px] font-bold tracking-wide ${tone.text}`}>{band.label}</h3>
                                </div>
                              </div>
                              <div className="text-right">
                                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Confidence Score</p>
                                <p className={`text-3xl font-black tabular-nums tracking-tighter ${tone.text}`}>{result.risk_score.toFixed(2)}</p>
                              </div>
                            </div>
                            
                            {/* Fintech specific segmented bar */}
                            <div className="relative h-1.5 w-full bg-slate-100 flex overflow-hidden">
                              <div className="h-full bg-emerald-500" style={{ width: '30%' }}></div>
                              <div className="h-full bg-amber-400" style={{ width: '35%' }}></div>
                              <div className="h-full bg-rose-500" style={{ width: '35%' }}></div>
                              <div className="absolute top-0 bottom-0 w-0.5 bg-slate-900 shadow-sm transition-all duration-1000" style={{ left: `${Math.min(Math.round(result.risk_score * 100), 100)}%` }}></div>
                            </div>
                          </div>
                        );
                      })()}
                      
                      {/* XAI X-Ray Block (Compliance Look) */}
                      {result.is_anomalous && result.risk_drivers && result.risk_drivers.length > 0 && (
                        <div className="mb-6 bg-white border border-rose-200 border-l-4 border-l-rose-500 shadow-sm">
                          <div className="px-4 py-2 border-b border-rose-100 bg-rose-50/30 flex items-center gap-2">
                            <AlertOctagon className="w-3.5 h-3.5 text-rose-600" />
                            <h3 className="text-[11px] font-bold text-rose-800 uppercase tracking-widest">Key Risk Drivers</h3>
                          </div>
                          <div className="p-4 space-y-2">
                            {result.risk_drivers.map((driver, idx) => (
                              <div key={idx} className="flex items-start gap-2.5">
                                <span className="text-rose-500 text-[10px] mt-0.5">■</span>
                                <p className="text-[12px] text-slate-700 font-medium leading-relaxed">{driver}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Structured Telemetry Grid */}
                      <div className="bg-white border border-slate-200 shadow-sm">
                        <div className="px-4 py-3 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center">
                          <h3 className="text-[11px] font-bold text-slate-700 uppercase tracking-widest">Extracted Telemetry</h3>
                          <div className="flex items-center gap-1.5 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 text-[9px] text-emerald-700 font-bold uppercase tracking-widest">
                            <Check className="w-3 h-3" /> GenAI Verified
                          </div>
                        </div>
                        <div className="grid grid-cols-2 divide-x divide-y divide-slate-100">
                          <div className="p-4">
                            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Invoice Ref</p>
                            <p className="text-[13px] font-mono font-medium text-slate-900">{result.extracted_data.invoice_number}</p>
                          </div>
                          <div className="p-4">
                            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Settlement Value</p>
                            <p className="text-[16px] font-bold tabular-nums tracking-tight text-slate-900">${result.extracted_data.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
                          </div>
                          <div className="p-4 col-span-2">
                            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Commodity Description</p>
                            <p className="text-[13px] font-medium text-slate-800">{result.extracted_data.goods_description}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Footer Controls */}
                {result && (
                  <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
                    <button onClick={() => setShowJson(true)} className="flex items-center gap-1.5 text-[12px] font-bold uppercase tracking-wider text-slate-500 hover:text-slate-900 transition-colors">
                      <Code className="w-3.5 h-3.5" /> Dev Logs
                    </button>
                    <div className="flex gap-3">
                      <button onClick={() => handleDecision('REJECTED')} disabled={actionLoading !== null} className="flex items-center gap-1.5 px-5 py-2 bg-white border border-slate-300 text-[12px] font-bold uppercase tracking-wider text-slate-700 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-200 transition-all shadow-sm active:scale-95 disabled:opacity-50">
                        {actionLoading === 'REJECTED' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-3.5 h-3.5" />} Reject
                      </button>
                      <button onClick={() => handleDecision('CLEARED')} disabled={actionLoading !== null} className="flex items-center gap-1.5 px-5 py-2 bg-slate-900 text-white text-[12px] font-bold uppercase tracking-wider hover:bg-slate-800 transition-all shadow-sm active:scale-95 disabled:opacity-50">
                        {actionLoading === 'CLEARED' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />} Clear
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* =========================================================================
            VIEW 2: GLOBAL ANALYTICS DASHBOARD
            ========================================================================= */}
        {activeTab === 'analytics' && (
          <div className="animate-in fade-in duration-300">
            {chartsLoading ? (
               <div className="flex flex-col items-center justify-center h-64">
                 <Loader2 className="w-6 h-6 text-slate-900 animate-spin mb-4" />
                 <p className="text-[13px] text-slate-600 font-medium">Syncing persistent ledger...</p>
               </div>
            ) : (
              <>
                <div className="mb-8 flex justify-between items-end">
                  <div>
                    <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Macro Telemetry</h1>
                    <p className="text-[13px] text-slate-500 mt-1">Live aggregation of Trade Volume & Machine Learning Interventions.</p>
                  </div>
                  <button onClick={handleExportCSV} className="text-[12px] font-bold uppercase tracking-wider bg-white border border-slate-300 px-4 py-2 shadow-sm text-slate-700 hover:bg-slate-50 active:scale-95 transition-all">
                    Export .CSV
                  </button>
                </div>

                {/* KPI Row */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                  <div className="bg-white border border-slate-200 p-6 shadow-sm border-t-2 border-t-blue-500">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">Total Monitored Vol</h3>
                      <BarChart3 className="w-4 h-4 text-blue-500" />
                    </div>
                    <p className="text-3xl font-black tabular-nums tracking-tighter text-slate-900">
                      ${dashboardData.kpis.total_volume >= 1000000 
                        ? (dashboardData.kpis.total_volume / 1000000).toFixed(2) + 'M' 
                        : dashboardData.kpis.total_volume.toLocaleString()}
                    </p>
                    <p className="text-[12px] text-slate-500 font-medium mt-2">Cumulative USD processed</p>
                  </div>

                  <div className="bg-white border border-slate-200 p-6 shadow-sm border-t-2 border-t-slate-800">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">Processed TXNs</h3>
                      <FileText className="w-4 h-4 text-slate-800" />
                    </div>
                    <p className="text-3xl font-black tabular-nums tracking-tighter text-slate-900">{dashboardData.kpis.processed_count.toLocaleString()}</p>
                    <p className="text-[12px] text-slate-500 font-medium mt-2">Total records analyzed</p>
                  </div>

                  <div className={`bg-white border p-6 shadow-sm border-t-2 ${dashboardData.kpis.intervention_rate > 5 ? 'border-rose-200 border-t-rose-500' : 'border-slate-200 border-t-amber-500'}`}>
                    <div className="flex items-center justify-between mb-4">
                      <h3 className={`text-[11px] font-bold uppercase tracking-widest ${dashboardData.kpis.intervention_rate > 5 ? 'text-rose-600' : 'text-slate-600'}`}>ML Intervention Rate</h3>
                      <AlertOctagon className={`w-4 h-4 ${dashboardData.kpis.intervention_rate > 5 ? 'text-rose-500' : 'text-amber-500'}`} />
                    </div>
                    <p className="text-3xl font-black tabular-nums tracking-tighter text-slate-900">{dashboardData.kpis.intervention_rate}%</p>
                    <p className="text-[12px] text-slate-500 font-medium mt-2">Records flagged for review</p>
                  </div>
                </div>

                {dashboardData.chart_data.length === 0 ? (
                  <div className="bg-white border border-slate-200 p-12 text-center shadow-sm">
                    <p className="text-[13px] text-slate-500 font-medium">No transaction data available yet. Process an invoice to generate charts.</p>
                  </div>
                ) : (
                  <>
                    {/* Charts */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                      <div className="bg-white border border-slate-200 p-6 shadow-sm">
                        <h3 className="text-[11px] font-bold text-slate-700 uppercase tracking-widest mb-6">Isolation Forest Risk Trajectory</h3>
                        <div className="h-[280px] w-full">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={dashboardData.chart_data} margin={{ top: 5, right: 10, bottom: 5, left: -20 }}>
                              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 11}} dy={10} />
                              <YAxis axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 11}} />
                              <Tooltip contentStyle={{ borderRadius: '0px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }} labelStyle={{ fontWeight: 'bold', color: '#0f172a' }} />
                              <Line type="monotone" dataKey="riskScore" name="Avg Risk Score" stroke="#0f172a" strokeWidth={2} dot={{r: 3, fill: '#0f172a', strokeWidth: 0}} activeDot={{r: 5}} />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      </div>

                      <div className="bg-white border border-slate-200 p-6 shadow-sm">
                        <h3 className="text-[11px] font-bold text-slate-700 uppercase tracking-widest mb-6">Trade Volume (USD)</h3>
                        <div className="h-[280px] w-full">
                          <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={dashboardData.chart_data} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
                              <defs>
                                <linearGradient id="colorVol" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                                </linearGradient>
                              </defs>
                              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 11}} dy={10} />
                              <YAxis axisLine={false} tickLine={false} tickFormatter={(val) => val >= 1000000 ? `$${(val / 1000000).toFixed(1)}M` : `$${val.toLocaleString()}`} tick={{fill: '#94a3b8', fontSize: 11}} />
                              <Tooltip formatter={(value) => [`$${value.toLocaleString()}`, 'Volume']} contentStyle={{ borderRadius: '0px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }} />
                              <Area type="monotone" dataKey="volume" stroke="#3b82f6" fillOpacity={1} fill="url(#colorVol)" strokeWidth={2} />
                            </AreaChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                    </div>
                    
                    {/* Financial Ledger Table */}
                    <div className="bg-white border border-slate-200 shadow-sm overflow-hidden">
                      <div className="px-5 py-4 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center">
                        <h3 className="text-[11px] font-bold text-slate-700 uppercase tracking-widest">Master Audit Ledger</h3>
                        <div className="flex items-center gap-1.5 bg-white border border-slate-200 px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest text-slate-500 shadow-sm">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Live Sync
                        </div>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                          <thead>
                            <tr className="bg-white border-b border-slate-200 text-[10px] uppercase tracking-widest text-slate-500 font-bold">
                              <th className="px-5 py-3 whitespace-nowrap">Transaction ID</th>
                              <th className="px-5 py-3 whitespace-nowrap">Timestamp</th>
                              <th className="px-5 py-3 text-right whitespace-nowrap">Value (USD)</th>
                              <th className="px-5 py-3 text-right whitespace-nowrap">ML Risk Score</th>
                              <th className="px-5 py-3 text-center whitespace-nowrap">System Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {dashboardData.recent_transactions?.map((txn, idx) => (
                              <tr key={idx} className="hover:bg-slate-50 transition-colors group">
                                <td className="px-5 py-3.5 font-mono text-[12px] font-medium text-slate-900 whitespace-nowrap">{txn.transaction_id}</td>
                                <td className="px-5 py-3.5 text-[12px] text-slate-500 whitespace-nowrap">
                                   {new Date(txn.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                </td>
                                <td className="px-5 py-3.5 text-[13px] font-semibold tabular-nums text-right text-slate-900 whitespace-nowrap">
                                   ${txn.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                                </td>
                                <td className="px-5 py-3.5 text-right whitespace-nowrap">
                                   <span className={`text-[12px] font-bold tabular-nums ${txn.risk_score > 0.65 ? 'text-rose-600' : 'text-emerald-600'}`}>
                                     {txn.risk_score.toFixed(2)}
                                   </span>
                                </td>
                                <td className="px-5 py-3.5 flex justify-center whitespace-nowrap">
                                   <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 border text-[10px] font-bold uppercase tracking-widest ${txn.is_anomalous ? 'bg-rose-50 text-rose-700 border-rose-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'}`}>
                                     {txn.is_anomalous ? 'Review Required' : 'Auto-Cleared'}
                                   </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;