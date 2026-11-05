import { useState, useEffect, useCallback, useRef } from 'react';
import { ClusterDetail, EvaluationResult, GraphData, TimelineBucket, TopicInfo } from './types';
import NetworkGraphCanvas from './components/NetworkGraphCanvas';
import ClusterInspector from './components/ClusterInspector';
import EvaluationLabView from './components/EvaluationLabView';
import EthicsAndDocsView from './components/EthicsAndDocsView';

// ── Config ──
const API_BASE = '';
const POLL_INTERVAL = 15000;

// ── Helpers ──
function riskBadge(band: string) {
  const c: Record<string, string> = { critical: 'bg-red-600', high: 'bg-orange-500', medium: 'bg-yellow-500', low: 'bg-green-600' };
  return <span className={`text-xs font-bold px-2 py-0.5 rounded-full text-white ${c[band] || 'bg-gray-500'}`}>{band.toUpperCase()}</span>;
}

function scoreGradient(s: number) {
  if (s >= 80) return 'from-red-600 to-red-400';
  if (s >= 50) return 'from-orange-500 to-yellow-400';
  return 'from-green-500 to-green-400';
}

function sparkline(data: number[], w = 80, h = 24) {
  if (!data.length) return null;
  const max = Math.max(...data, 1);
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - (v / max) * h}`).join(' ');
  return <svg width={w} height={h} className="inline-block"><polyline points={pts} fill="none" stroke="#60a5fa" strokeWidth="1.5" /></svg>;
}

type View = 'dashboard' | 'evaluation' | 'ethics';

export default function App() {
  // ── State ──
  const [view, setView] = useState<View>('dashboard');
  const [topics, setTopics] = useState<TopicInfo[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<number | null>(null);
  const [clusters, setClusters] = useState<ClusterDetail[]>([]);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [timeline, setTimeline] = useState<TimelineBucket[]>([]);
  const [evalResult, setEvalResult] = useState<EvaluationResult | null>(null);
  const [newKeyword, setNewKeyword] = useState('');
  const [trackingStatus, setTrackingStatus] = useState('');
  const [inspectedCluster, setInspectedCluster] = useState<ClusterDetail | null>(null);
  const [revealHandles, setRevealHandles] = useState(false);
  const [health, setHealth] = useState<any>(null);
  const pollRef = useRef<number>();

  // ── Fetch helpers ──
  const fetchTopics = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/api/topics`);
      const d = await r.json();
      setTopics(d.topics || []);
      if (d.topics?.length && selectedTopic === null) setSelectedTopic(d.topics[0].id);
    } catch { /* silent */ }
  }, [selectedTopic]);

  const fetchAnalysis = useCallback(async (topicId: number) => {
    try {
      const [cRes, gRes, tRes] = await Promise.all([
        fetch(`${API_BASE}/api/clusters?topicId=${topicId}`),
        fetch(`${API_BASE}/api/graph?topicId=${topicId}`),
        fetch(`${API_BASE}/api/timeline?topicId=${topicId}`)
      ]);
      const cData = await cRes.json();
      const gData = await gRes.json();
      const tData = await tRes.json();
      setClusters(cData.clusters || []);
      setGraphData(gData);
      setTimeline(tData.timeline || []);
    } catch { /* silent */ }
  }, []);

  const fetchHealth = useCallback(async () => {
    try { setHealth(await (await fetch(`${API_BASE}/health`)).json()); } catch { /* silent */ }
  }, []);

  const fetchEval = useCallback(async () => {
    try { setEvalResult(await (await fetch(`${API_BASE}/api/evaluation/latest`)).json()); } catch { /* silent */ }
  }, []);

  // ── Effects ──
  useEffect(() => { fetchTopics(); fetchHealth(); }, []);

  useEffect(() => {
    if (selectedTopic !== null) fetchAnalysis(selectedTopic);
  }, [selectedTopic, fetchAnalysis]);

  useEffect(() => {
    if (view === 'evaluation') fetchEval();
  }, [view, fetchEval]);

  useEffect(() => {
    pollRef.current = window.setInterval(() => {
      fetchTopics();
      if (selectedTopic !== null) fetchAnalysis(selectedTopic);
      fetchHealth();
    }, POLL_INTERVAL);
    return () => clearInterval(pollRef.current);
  }, [selectedTopic, fetchTopics, fetchAnalysis, fetchHealth]);

  // ── Handlers ──
  const startTracking = async () => {
    if (!newKeyword.trim()) return;
    setTrackingStatus('Creating topic...');
    try {
      const r = await fetch(`${API_BASE}/api/topics`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword: newKeyword.trim() })
      });
      const d = await r.json();
      const created = d.topic || d;
      setTrackingStatus(`Tracking "${created.keyword}" (topic #${created.id})`);
      setNewKeyword('');
      await fetchTopics();
      setSelectedTopic(created.id);
    } catch { setTrackingStatus('Error creating topic'); }
  };

  const runEval = async () => {
    setTrackingStatus('Running evaluation...');
    try {
      const r = await fetch(`${API_BASE}/api/evaluation/run`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ organicCount: 500 }) });
      setEvalResult(await r.json());
      setTrackingStatus('Evaluation complete');
    } catch { setTrackingStatus('Evaluation failed'); }
  };

  const currentTopicObj = topics.find(t => t.id === selectedTopic);
  const isDemoTopic = currentTopicObj?.source === 'demo' || currentTopicObj?.id === 1;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* ── NAV ── */}
      <nav className="bg-gray-900/80 backdrop-blur border-b border-gray-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center font-bold text-sm">CW</div>
            <span className="font-semibold text-lg">CoordWatch</span>
            <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full font-mono">FASTAPI</span>
          </div>
          <div className="flex items-center gap-2">
            {(['dashboard', 'evaluation', 'ethics'] as View[]).map(v => (
              <button key={v} onClick={() => setView(v)}
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${view === v ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'}`}>
                {v === 'dashboard' ? '📊 Dashboard' : v === 'evaluation' ? '🔬 Evaluation Lab' : '📋 Ethics & Docs'}
              </button>
            ))}
            <button
              onClick={() => setRevealHandles(!revealHandles)}
              className="ml-2 px-2.5 py-1 text-xs font-mono rounded-lg border border-gray-700 bg-gray-850 hover:bg-gray-800 text-gray-300 hover:text-white transition-colors"
              title="Toggle between deterministic privacy aliases (A-xxxx) and raw Bluesky handles per Phase 9 Ethics Policy"
            >
              {revealHandles ? '👁️ Handles' : '🔒 Privacy Aliases'}
            </button>
            {health && (
              <div className="flex items-center gap-1.5 ml-3 text-xs">
                <div className={`w-2 h-2 rounded-full ${health.jetstream?.connected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
                <span className="text-gray-400">{health.jetstream?.connected ? 'JETSTREAM LIVE' : 'OFFLINE'}</span>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* A5: Visible banner distinguishing synthetic demonstration data from live monitored topics */}
      {view === 'dashboard' && isDemoTopic && (
        <div className="bg-amber-950/80 border-b border-amber-600/50 px-4 py-2 text-center text-xs text-amber-200 flex items-center justify-center gap-2">
          <span className="font-bold uppercase tracking-wider bg-amber-600/40 px-2 py-0.5 rounded text-amber-100">SIMULATED DEMO DATA</span>
          <span>This topic contains synthetic demonstration data for methodology illustration. These are not real accounts or actual accusations.</span>
        </div>
      )}

      {/* ── MAIN CONTENT ── */}
      {view === 'evaluation' ? <EvaluationLabView result={evalResult} onRun={runEval} /> :
       view === 'ethics' ? <EthicsAndDocsView /> :
      (
        <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
          {/* ── Topic Tracking Bar ── */}
          <section className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <div className="flex items-center gap-3 mb-3">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Track New Topic</h2>
              {trackingStatus && <span className="text-xs text-blue-400">{trackingStatus}</span>}
            </div>
            <div className="flex gap-2">
              <input value={newKeyword} onChange={e => setNewKeyword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && startTracking()}
                className="flex-1 bg-gray-800 rounded-lg px-4 py-2 text-sm border border-gray-700 focus:border-blue-500 focus:outline-none"
                placeholder="Enter keyword or hashtag to monitor via live Bluesky Jetstream..." />
              <button onClick={startTracking}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium transition-colors">
                🔍 Start Tracking
              </button>
            </div>
          </section>

          {/* ── Topic Tabs ── */}
          {topics.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              {topics.map(t => (
                <button key={t.id} onClick={() => setSelectedTopic(t.id)}
                  className={`px-4 py-2 rounded-lg text-sm transition-all flex items-center gap-2 ${selectedTopic === t.id
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>
                  <span className="font-medium">{t.keyword}</span>
                  {t.source === 'demo' && (
                    <span className="text-[10px] bg-amber-500/30 text-amber-300 px-1.5 py-0.2 rounded font-semibold uppercase">Demo</span>
                  )}
                  <span className="text-xs opacity-70">{t.postCount} posts · {t.clusterCount} clusters</span>
                </button>
              ))}
            </div>
          )}

          {/* ── Summary Cards ── */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <div className="text-xs text-gray-500 uppercase mb-1">Posts Collected</div>
              <div className="text-2xl font-bold">{currentTopicObj?.postCount || 0}</div>
            </div>
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <div className="text-xs text-gray-500 uppercase mb-1">Unique Accounts</div>
              <div className="text-2xl font-bold">{currentTopicObj?.accountCount || 0}</div>
            </div>
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <div className="text-xs text-gray-500 uppercase mb-1">Clusters Found</div>
              <div className="text-2xl font-bold">{clusters.length}</div>
            </div>
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <div className="text-xs text-gray-500 uppercase mb-1">High Risk (Score ≥ 50)</div>
              <div className="text-2xl font-bold text-red-400">{clusters.filter(c => (c.score || c.coordinationScore || 0) >= 50).length}</div>
            </div>
          </div>

          {/* ── Network Graph ── */}
          <section className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Coordination Network Graph</h2>
            {graphData && graphData.nodes?.length > 0 ? (
              <NetworkGraphCanvas
                graphData={graphData}
                selectedClusterId={inspectedCluster?.id || null}
                revealHandles={revealHandles}
                onSelectCluster={(cid) => {
                  if (cid) {
                    const cl = clusters.find(c => c.id === cid);
                    if (cl) setInspectedCluster(cl);
                  } else {
                    setInspectedCluster(null);
                  }
                }}
                onNodeClick={(nodeId) => {
                  const cl = clusters.find(c => c.members?.some(m => m.did === nodeId) || c.memberDids?.includes(nodeId));
                  if (cl) setInspectedCluster(cl);
                }}
              />
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-600">
                <p>No coordination graph data yet. Track a topic and wait for analysis.</p>
              </div>
            )}
          </section>

          {/* ── Timeline ── */}
          {timeline.length > 0 && (
            <section className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Activity Timeline</h2>
              <div className="flex items-end gap-1 h-32">
                {timeline.map((b, i) => {
                  const maxCount = Math.max(...timeline.map(t => t.total), 1);
                  const h = (b.total / maxCount) * 100;
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1">
                      <div className="w-full flex flex-col justify-end" style={{ height: '100px' }}>
                        <div className="w-full bg-blue-500/30 rounded-t" style={{ height: `${h}%` }}>
                          {b.flagged > 0 && (
                            <div className="w-full bg-red-500/50 rounded-t" style={{ height: `${(b.flagged / b.total) * 100}%` }} />
                          )}
                        </div>
                      </div>
                      <span className="text-[10px] text-gray-600 truncate w-full text-center">{b.label}</span>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* ── Clusters Table ── */}
          <section className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <div className="p-4 border-b border-gray-800">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Detected Clusters</h2>
            </div>
            {clusters.length === 0 ? (
              <div className="p-8 text-center text-gray-600">No clusters detected yet.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-500 uppercase border-b border-gray-800">
                      <th className="px-4 py-3">Cluster</th>
                      <th className="px-4 py-3">Score</th>
                      <th className="px-4 py-3">Risk</th>
                      <th className="px-4 py-3">Members</th>
                      <th className="px-4 py-3">Signals</th>
                      <th className="px-4 py-3">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {clusters.map(cl => {
                      const score = cl.score ?? cl.coordinationScore ?? 0;
                      const band = cl.riskBand || (score >= 80 ? 'critical' : score >= 60 ? 'high' : score >= 40 ? 'medium' : 'low');
                      const memCount = cl.size ?? cl.memberCount ?? cl.members?.length ?? 0;
                      return (
                        <tr key={cl.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                          <td className="px-4 py-3">
                            <div className="font-medium text-white">{cl.id}</div>
                            {cl.examplePosts?.[0] && (
                              <div className="text-xs text-gray-400 mt-0.5 truncate max-w-md">"{cl.examplePosts[0].text}"</div>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <div className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-gradient-to-r ${scoreGradient(score)} text-white`}>
                              {score}
                            </div>
                          </td>
                          <td className="px-4 py-3">{riskBadge(band)}</td>
                          <td className="px-4 py-3 text-gray-300">{memCount} accounts</td>
                          <td className="px-4 py-3">
                            <div className="flex gap-1 flex-wrap">
                              {cl.signals && Object.entries(cl.signals).map(([k, v]) => (
                                (v as number) > 0.1 && <span key={k} className="text-xs bg-gray-800 px-1.5 py-0.5 rounded text-gray-300">{k}: {(v as number).toFixed(2)}</span>
                              ))}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <button onClick={() => setInspectedCluster(cl)}
                              className="text-xs bg-blue-600/20 text-blue-400 px-2 py-1 rounded hover:bg-blue-600/30 transition-colors">
                              Inspect →
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </main>
      )}

      {/* ── Cluster Inspector Modal Overlay ── */}
      {inspectedCluster && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 md:p-6"
          onClick={() => setInspectedCluster(null)}
        >
          <div
            className="bg-[#0E121B] border border-slate-800 rounded-xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <ClusterInspector
              cluster={inspectedCluster}
              clusters={clusters}
              revealHandles={revealHandles}
              onToggleRevealHandles={() => setRevealHandles(!revealHandles)}
              onSelectCluster={(cid) => {
                const cl = clusters.find((c) => c.id === cid);
                if (cl) setInspectedCluster(cl);
              }}
              onBack={() => setInspectedCluster(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
