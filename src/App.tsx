import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, MotionConfig, useScroll, useTransform } from 'motion/react';
import {
  ArrowUpRight,
  Clock3,
  Eye,
  EyeOff,
  Fingerprint,
  Link2,
  Radio,
  Search,
  Shield,
  Type,
} from 'lucide-react';
import { ClusterDetail, EvaluationResult, GraphData, TimelineBucket, TopicInfo, clusterClassLabel } from './types';
import NetworkGraphCanvas from './components/NetworkGraphCanvas';
import ClusterInspector from './components/ClusterInspector';
import EvaluationLabView from './components/EvaluationLabView';
import EthicsAndDocsView from './components/EthicsAndDocsView';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';
const POLL_INTERVAL = 15000;

async function fetchJson(url: string): Promise<any> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${response.status} from ${url}`);
  }
  return response.json();
}

function riskBadge(band: string) {
  const c: Record<string, string> = {
    critical: 'bg-[#E07A62] text-[#FFFAF6]',
    high: 'bg-[#E8B86D] text-[#1A120E]',
    medium: 'bg-[#E8D7B0] text-[#1A120E]',
    low: 'bg-[#B7D4C4] text-[#1A120E]',
  };
  return (
    <span className={`text-[10px] font-semibold tracking-[0.14em] px-2 py-0.5 rounded-full ${c[band] || 'bg-white/10 text-[#F6F1E8]'}`}>
      {band.toUpperCase()}
    </span>
  );
}

function sourceChip(source?: string) {
  if (source === 'demo' || source === 'synthetic') return <span className="chip chip-demo">Demo</span>;
  if (source === 'recorded') return <span className="chip chip-recorded">Recorded</span>;
  return <span className="chip chip-live">Live</span>;
}

function compact(n: number) {
  return new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(n);
}

type View = 'dashboard' | 'evaluation' | 'ethics';

const NAV: { id: View; label: string }[] = [
  { id: 'dashboard', label: 'Monitor' },
  { id: 'evaluation', label: 'Laboratory' },
  { id: 'ethics', label: 'Method' },
];

const SIGNALS = [
  { icon: Type, title: 'Text', copy: 'Shared wording, links removed' },
  { icon: Clock3, title: 'Timing', copy: 'Posts landing in one burst' },
  { icon: Fingerprint, title: 'Age', copy: 'Accounts born together' },
  { icon: Link2, title: 'Links', copy: 'One URL, tracking removed' },
  { icon: Shield, title: 'Aliases', copy: 'Handles stay hidden' },
];

export default function App() {
  const [view, setView] = useState<View>('dashboard');
  const [topics, setTopics] = useState<TopicInfo[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<number | null>(null);
  const [clusters, setClusters] = useState<ClusterDetail[]>([]);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [timeline, setTimeline] = useState<TimelineBucket[]>([]);
  const [topicPosts, setTopicPosts] = useState<any[]>([]);
  const [evalResult, setEvalResult] = useState<EvaluationResult | null>(null);
  const [newKeyword, setNewKeyword] = useState('');
  const [trackingStatus, setTrackingStatus] = useState('');
  const [inspectedCluster, setInspectedCluster] = useState<ClusterDetail | null>(null);
  const [revealHandles, setRevealHandles] = useState(false);
  const [health, setHealth] = useState<any>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [evalRunning, setEvalRunning] = useState(false);
  const [sampleIdx, setSampleIdx] = useState(0);
  const pollRef = useRef<number | undefined>(undefined);
  const keywordRef = useRef<HTMLInputElement | null>(null);

  const { scrollY, scrollYProgress } = useScroll();
  const glowY = useTransform(scrollY, [0, 800], [0, 120]);
  const heroY = useTransform(scrollY, [0, 640], [0, -72]);
  const heroOpacity = useTransform(scrollY, [0, 520], [1, 0.2]);
  const cardY = useTransform(scrollY, [0, 640], [0, -28]);

  const fetchTopics = useCallback(async () => {
    try {
      const d = await fetchJson(`${API_BASE}/api/topics`);
      setTopics(d.topics || []);
      if (d.topics?.length && selectedTopic === null) setSelectedTopic(d.topics[0].id);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof Error ? `Could not load topics. ${err.message}` : 'Could not load topics.');
    }
  }, [selectedTopic]);

  const fetchAnalysis = useCallback(async (topicId: number) => {
    try {
      const [cData, gData, tData, pData] = await Promise.all([
        fetchJson(`${API_BASE}/api/clusters?topicId=${topicId}`),
        fetchJson(`${API_BASE}/api/graph?topicId=${topicId}`),
        fetchJson(`${API_BASE}/api/timeline?topicId=${topicId}`),
        fetchJson(`${API_BASE}/api/topics/${topicId}/posts`).catch(() => ({ posts: [] })),
      ]);
      setClusters(cData.clusters || []);
      setGraphData(gData);
      setTimeline(tData.timeline || []);
      setTopicPosts(pData.posts || []);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof Error ? `Could not load this topic. ${err.message}` : 'Could not load this topic.');
    }
  }, []);

  const fetchHealth = useCallback(async () => {
    try {
      setHealth(await fetchJson(`${API_BASE}/health`));
    } catch (err) {
      setHealth(null);
      setLoadError(err instanceof Error ? `Could not reach the API. ${err.message}` : 'Could not reach the API.');
    }
  }, []);

  const fetchEval = useCallback(async () => {
    try {
      setEvalResult(await fetchJson(`${API_BASE}/api/evaluation/latest`));
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof Error ? `Could not load the evaluation. ${err.message}` : 'Could not load the evaluation.');
    }
  }, []);

  useEffect(() => { fetchTopics(); fetchHealth(); }, []);

  useEffect(() => {
    if (selectedTopic !== null) fetchAnalysis(selectedTopic);
  }, [selectedTopic, fetchAnalysis]);

  useEffect(() => {
    if (view === 'evaluation') fetchEval();
    if (view !== 'dashboard') window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [view, fetchEval]);

  useEffect(() => {
    pollRef.current = window.setInterval(() => {
      fetchTopics();
      if (selectedTopic !== null) fetchAnalysis(selectedTopic);
      fetchHealth();
    }, POLL_INTERVAL);
    return () => clearInterval(pollRef.current);
  }, [selectedTopic, fetchTopics, fetchAnalysis, fetchHealth]);

  const samples: any[] = health?.jetstream?.recentLiveSample || [];
  useEffect(() => {
    if (samples.length < 2) return;
    const id = window.setInterval(() => {
      setSampleIdx((i) => (i + 1) % samples.length);
    }, 4200);
    return () => clearInterval(id);
  }, [samples.length]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setInspectedCluster(null);
      const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement;
      if (e.key === '/' && !typing) {
        e.preventDefault();
        setView('dashboard');
        requestAnimationFrame(() => keywordRef.current?.focus());
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

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

  const runEval = async (organicCount = 80) => {
    setEvalRunning(true);
    setTrackingStatus('Running lab sample...');
    try {
      const response = await fetch(`${API_BASE}/api/evaluation/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ organicCount }),
      });
      if (!response.ok) {
        throw new Error(`${response.status} from ${API_BASE}/api/evaluation/run`);
      }
      setEvalResult(await response.json());
      setTrackingStatus('Lab sample complete');
      setLoadError(null);
    } catch (err) {
      setTrackingStatus('Evaluation failed');
      setLoadError(err instanceof Error ? `Evaluation failed. ${err.message}` : 'Evaluation failed.');
    } finally {
      setEvalRunning(false);
    }
  };

  const openMonitor = () => {
    setView('dashboard');
    document.getElementById('monitor')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const currentTopicObj = topics.find(t => t.id === selectedTopic);
  const isDemoTopic = currentTopicObj?.source === 'demo' || currentTopicObj?.source === 'synthetic' || currentTopicObj?.id === 1;
  const jet = health?.jetstream;
  const live = Boolean(jet?.connected);
  const inauthenticCount = clusters.filter(c => c.classification === 'coordinated_inauthentic' && (c.score || c.coordinationScore || 0) >= 50).length;
  const sample = samples.length ? samples[sampleIdx % samples.length] : null;
  const reveal = {
    initial: { opacity: 0, y: 28 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, margin: '-80px' as const },
    transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] as const },
  };

  return (
    <MotionConfig reducedMotion="user">
      <div className="cw relative min-h-screen text-[#F6F1E8]">
        <div className="atmosphere" aria-hidden="true">
          <motion.div className="atmosphere-glow" style={{ y: glowY }} />
          <div className="atmosphere-ribs" />
          <div className="atmosphere-vignette" />
        </div>

        <motion.div className="scroll-progress" style={{ scaleX: scrollYProgress }} />

        <header className="nav-shell">
          <div className="nav-bar">
            <button type="button" onClick={() => { setView('dashboard'); window.scrollTo({ top: 0, behavior: 'smooth' }); }} className="flex items-center gap-2.5 bg-transparent border-0 cursor-pointer text-[#F6F1E8]">
              <svg viewBox="0 0 28 16" className="w-7 h-4 text-[#E07A62]" aria-hidden="true">
                <path d="M1 11c3.2-5 5.4-5 8.2 0s5 5 8.2 0 5-5 8.6 0" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
              <span className="font-medium tracking-tight text-[15px]">CoordWatch</span>
            </button>

            <nav className="nav-links" aria-label="Primary">
              {NAV.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setView(item.id)}
                  className={`nav-link ${view === item.id ? 'is-active' : ''}`}
                >
                  {view === item.id && <span className="nav-dot" />}
                  {item.label}
                </button>
              ))}
            </nav>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setRevealHandles(!revealHandles)}
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 text-xs text-[#F6F1E8]/80 hover:text-[#F6F1E8] bg-transparent border-0 cursor-pointer"
                title="Toggle between privacy aliases and Bluesky handles"
              >
                {revealHandles ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                {revealHandles ? 'Handles' : 'Aliases'}
              </button>
              <div className="flex items-center gap-2 pr-2 text-xs">
                <span className={`w-1.5 h-1.5 rounded-full ${live ? 'bg-[#E07A62] shadow-[0_0_0_4px_rgba(224,122,98,0.18)]' : 'bg-[#8E867C]'}`} />
                <span className="text-[#F6F1E8]/75 font-mono tabular-nums">
                  {live ? `${Number(jet.eventsPerSec || 0).toFixed(0)}/s` : 'Offline'}
                </span>
              </div>
            </div>
          </div>
        </header>

        {loadError && (
          <div className="banner banner-alert" role="status">{loadError}</div>
        )}

        {view === 'dashboard' && isDemoTopic && (
          <div className="banner banner-demo flex flex-wrap items-center justify-center gap-2 text-center">
            <span className="chip chip-coral">Simulated demo data</span>
            <span>Synthetic posts and generated accounts, for the method. Not real people, and not an accusation.</span>
          </div>
        )}

        {view === 'dashboard' ? (
          <>
            <section className={`relative z-10 mx-auto flex w-full max-w-[1180px] flex-col px-5 pb-6 pt-6 md:px-8 ${isDemoTopic || loadError ? 'min-h-[calc(100svh-10.5rem)]' : 'min-h-[calc(100svh-6.25rem)]'}`}>
              <motion.div style={{ y: heroY, opacity: heroOpacity }} className="grid flex-1 items-end gap-10 pb-10 lg:grid-cols-[1.15fr_0.85fr]">
                <div className="max-w-[640px] pb-2">
                  <p className="kicker mb-5">Public Bluesky · explainable leads</p>
                  <h1 className="display text-[clamp(3.3rem,7vw,6.5rem)] font-medium leading-[0.9] tracking-[-0.035em] text-[#F7F2EA]">
                    Signals that<br />move as one.
                  </h1>
                  <p className="mt-6 max-w-md text-[17px] leading-relaxed text-[#F6F1E8]/72">
                    A keyword on the public firehose. Accounts that post like a group. Every score comes with the posts, the timing, and the reason.
                  </p>
                  <div className="mt-8 flex flex-wrap items-center gap-5">
                    <button type="button" onClick={openMonitor} className="btn-coral px-5 py-3 text-sm">
                      Open the monitor <ArrowUpRight className="w-4 h-4" />
                    </button>
                    <button type="button" onClick={() => setView('ethics')} className="btn-ghost text-sm">
                      Read the method
                    </button>
                  </div>
                  {trackingStatus && <p className="mt-4 text-xs font-mono text-[#F0C7B8]">{trackingStatus}</p>}
                </div>

                <motion.div style={{ y: cardY }} className="flex w-full max-w-[400px] flex-col gap-4 justify-self-end">
                  <article className="glass-card p-5">
                    <div className="flex items-center justify-between gap-3 text-[12px] text-[#F6F1E8]/70">
                      <span className="inline-flex items-center gap-1.5">
                        <Radio className="w-3.5 h-3.5" />
                        {currentTopicObj ? currentTopicObj.keyword : 'No topic yet'}
                      </span>
                      {currentTopicObj && sourceChip(currentTopicObj.source)}
                    </div>
                    <div className="mt-4 border-t border-white/10 pt-4">
                      <h2 className="display text-[1.7rem] leading-none tracking-tight text-[#F7F2EA]">
                        {currentTopicObj?.keyword || 'Choose a keyword'}
                      </h2>
                      <div className="mt-5 grid grid-cols-3 gap-3 text-center">
                        <Stat label="Posts" value={String(currentTopicObj?.postCount || 0)} />
                        <Stat label="Accounts" value={String(currentTopicObj?.accountCount || 0)} />
                        <Stat label="Clusters" value={String(clusters.length)} />
                      </div>
                    </div>
                    <div className="mt-4 flex items-center justify-between">
                      <span className="chip chip-coral">
                        {inauthenticCount} inauthentic {inauthenticCount === 1 ? 'lead' : 'leads'}
                      </span>
                      <span className="text-[11px] text-[#F6F1E8]/55">Score is a lead, not a verdict</span>
                    </div>
                  </article>

                  <article className="glass-card ml-0 p-5 sm:ml-8">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="kicker">Live firehose</p>
                        <p className="mt-2 font-mono text-3xl tabular-nums tracking-tight text-[#F7F2EA]">
                          {live ? Number(jet.eventsPerSec || 0).toFixed(1) : '—'}
                          <span className="ml-2 text-sm font-sans font-normal text-[#F6F1E8]/60">events / sec</span>
                        </p>
                      </div>
                      <span className={`mt-1 h-2 w-2 rounded-full ${live ? 'bg-[#E07A62] animate-pulse' : 'bg-[#8E867C]'}`} />
                    </div>
                    <div className="mt-4 grid grid-cols-3 gap-2 border-t border-white/10 pt-4">
                      <Stat label="Scanned" value={compact(Number(jet?.totalEventsScanned || 0))} />
                      <Stat label="Kept" value={compact(Number(jet?.livePostsIngested || 0))} />
                      <Stat label="Enriched" value={compact(Number(jet?.accountsEnriched || 0))} />
                    </div>
                    <div className="mt-4 min-h-[76px] rounded-2xl border border-white/10 bg-[rgba(6,14,28,0.28)] px-3 py-2.5">
                      {sample ? (
                        <motion.div
                          key={`${sample.createdAt}-${sample.alias}-${sampleIdx}`}
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.45 }}
                        >
                          <div className="flex items-center justify-between font-mono text-[11px] text-[#F0C7B8]">
                            <span>{sample.alias || 'alias'}</span>
                            <span className="text-[#F6F1E8]/50">{sample.matchedTopic}</span>
                          </div>
                          <p className="mt-1 line-clamp-2 text-[13px] leading-snug text-[#F6F1E8]/85">{sample.text}</p>
                        </motion.div>
                      ) : (
                        <p className="text-sm text-[#F6F1E8]/55">Waiting for a public post that matches a topic.</p>
                      )}
                    </div>
                  </article>
                </motion.div>
              </motion.div>

              <div className="feature-rail">
                {SIGNALS.map((item) => (
                  <div key={item.title} className="flex gap-3 pt-4">
                    <item.icon className="mt-0.5 h-4 w-4 shrink-0 text-[#F6F1E8]/70" />
                    <div>
                      <div className="text-sm text-[#F7F2EA]">{item.title}</div>
                      <div className="mt-0.5 text-xs leading-relaxed text-[#F6F1E8]/55">{item.copy}</div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <main id="monitor" className="relative z-10 mx-auto max-w-[1180px] scroll-mt-28 space-y-6 px-5 pb-24 md:px-8">
              <motion.section {...reveal} className="glass-panel p-5 md:p-6">
                <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
                  <div>
                    <p className="kicker">Watch</p>
                    <h2 className="display mt-1 text-3xl text-[#F7F2EA]">Start a keyword</h2>
                  </div>
                  {trackingStatus && <span className="text-xs font-mono text-[#F0C7B8]">{trackingStatus}</span>}
                </div>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <input
                    ref={keywordRef}
                    value={newKeyword}
                    onChange={e => setNewKeyword(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && startTracking()}
                    className="field"
                    placeholder="A word or hashtag on the public Bluesky firehose"
                    aria-label="Keyword to monitor"
                  />
                  <button type="button" onClick={startTracking} className="btn-coral shrink-0 px-6 py-3 text-sm">
                    <Search className="w-4 h-4" /> Start tracking
                  </button>
                </div>
                <p className="mt-3 text-xs text-[#F6F1E8]/45">Press / to focus. New topics stay live and are polled with the ones already open.</p>
              </motion.section>

              {topics.length > 0 && (
                <motion.div {...reveal} className="topic-rail">
                  {topics.map(t => {
                    const active = selectedTopic === t.id;
                    return (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => setSelectedTopic(t.id)}
                        className={`min-w-[230px] rounded-[22px] border px-4 py-3 text-left transition ${active ? 'border-[#E07A62]/70 bg-[rgba(224,122,98,0.14)] shadow-[0_16px_40px_rgba(3,8,20,0.25)]' : 'border-white/10 bg-[rgba(10,24,46,0.35)] hover:border-white/25'}`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate font-medium text-[#F7F2EA]">{t.keyword}</span>
                          {sourceChip(t.source)}
                        </div>
                        <div className="mt-2 font-mono text-[11px] tabular-nums text-[#F6F1E8]/55">
                          {t.postCount} posts · {t.clusterCount} clusters
                        </div>
                      </button>
                    );
                  })}
                </motion.div>
              )}

              <motion.section {...reveal} className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <Metric kicker="Posts collected" value={currentTopicObj?.postCount || 0} />
                <Metric kicker="Unique accounts" value={currentTopicObj?.accountCount || 0} />
                <Metric kicker="Clusters found" value={clusters.length} />
                <Metric kicker="Inauthentic, score ≥ 50" value={inauthenticCount} accent />
              </motion.section>

              <motion.section {...reveal} className="glass-panel overflow-hidden">
                <div className="flex items-end justify-between gap-3 px-5 pb-2 pt-5">
                  <div>
                    <p className="kicker">Graph</p>
                    <h2 className="display mt-1 text-3xl text-[#F7F2EA]">Who moves together</h2>
                  </div>
                </div>
                <div className="p-3 pt-2">
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
                    <div className="flex h-64 items-center justify-center text-[#F6F1E8]/45">
                      <p>No coordination graph yet. Track a topic and wait for analysis.</p>
                    </div>
                  )}
                </div>
              </motion.section>

              {timeline.length > 0 && (
                <motion.section {...reveal} className="glass-panel p-5 md:p-6">
                  <div className="mb-4 flex items-end justify-between">
                    <div>
                      <p className="kicker">Time</p>
                      <h2 className="display mt-1 text-3xl text-[#F7F2EA]">When it clustered</h2>
                    </div>
                    <div className="flex items-center gap-4 text-[11px] text-[#F6F1E8]/60">
                      <span className="inline-flex items-center gap-1.5"><i className="inline-block h-2 w-2 rounded-sm bg-[#F6F1E8]/70" /> Posts</span>
                      <span className="inline-flex items-center gap-1.5"><i className="inline-block h-2 w-2 rounded-sm bg-[#E07A62]" /> Flagged</span>
                    </div>
                  </div>
                  <div className="flex h-40 items-end gap-1.5">
                    {timeline.map((b, i) => {
                      const maxCount = Math.max(...timeline.map(t => t.total), 1);
                      const h = (b.total / maxCount) * 100;
                      const flagged = b.total > 0 ? (b.flagged / b.total) * 100 : 0;
                      return (
                        <div key={i} className="flex h-full flex-1 flex-col items-center justify-end gap-2">
                          <div className="flex w-full flex-1 items-end">
                            <div className="relative w-full overflow-hidden rounded-t-md bg-[#F6F1E8]/18" style={{ height: `${Math.max(h, 4)}%` }}>
                              {b.flagged > 0 && (
                                <div className="absolute bottom-0 w-full bg-[#E07A62]" style={{ height: `${flagged}%` }} />
                              )}
                            </div>
                          </div>
                          <span className="w-full truncate text-center text-[10px] text-[#F6F1E8]/45">{b.label}</span>
                        </div>
                      );
                    })}
                  </div>
                </motion.section>
              )}

              <motion.section {...reveal} className="glass-panel overflow-hidden">
                <div className="border-b border-white/10 px-5 py-5">
                  <p className="kicker">Dossiers</p>
                  <h2 className="display mt-1 text-3xl text-[#F7F2EA]">Detected clusters</h2>
                </div>
                {clusters.length === 0 ? (
                  <div className="p-8 text-center text-[#F6F1E8]/45">
                    No coordinated clusters detected yet. (A coordination cluster requires ≥3 accounts synchronizing text, burst timing, or URLs).
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-white/10 text-left text-[11px] uppercase tracking-[0.14em] text-[#F6F1E8]/45">
                          <th className="px-5 py-3 font-medium">Cluster</th>
                          <th className="px-4 py-3 font-medium">Class</th>
                          <th className="px-4 py-3 font-medium">Score</th>
                          <th className="px-4 py-3 font-medium">Risk</th>
                          <th className="px-4 py-3 font-medium">Members</th>
                          <th className="px-4 py-3 font-medium">Signals</th>
                          <th className="px-4 py-3 font-medium" />
                        </tr>
                      </thead>
                      <tbody>
                        {clusters.map(cl => {
                          const score = cl.score ?? cl.coordinationScore ?? 0;
                          const band = cl.riskBand || (score >= 80 ? 'critical' : score >= 60 ? 'high' : score >= 40 ? 'medium' : 'low');
                          const memCount = cl.size ?? cl.memberCount ?? cl.members?.length ?? 0;
                          return (
                            <tr key={cl.id} className="border-b border-white/[0.06] transition-colors hover:bg-white/[0.04]">
                              <td className="px-5 py-4">
                                <div className="font-medium text-[#F7F2EA]">{cl.id}</div>
                                {cl.examplePosts?.[0] && (
                                  <div className="mt-0.5 max-w-md truncate text-xs text-[#F6F1E8]/50">“{cl.examplePosts[0].text}”</div>
                                )}
                              </td>
                              <td className="px-4 py-4 text-[#E8DFD2]">{clusterClassLabel(cl.classification)}</td>
                              <td className="px-4 py-4">
                                <div className="w-16">
                                  <div className="font-mono text-sm tabular-nums">{score}</div>
                                  <div className="score-pip mt-1"><span style={{ width: `${Math.min(100, score)}%` }} /></div>
                                </div>
                              </td>
                              <td className="px-4 py-4">{riskBadge(band)}</td>
                              <td className="px-4 py-4 text-[#E8DFD2]">{memCount} accounts</td>
                              <td className="px-4 py-4">
                                <div className="flex flex-wrap gap-1">
                                  {cl.signals && Object.entries(cl.signals).map(([k, v]) => (
                                    (v as number) > 0.1 && <span key={k} className="rounded-full border border-white/10 px-2 py-0.5 text-[11px] text-[#E8DFD2]">{k} {(v as number).toFixed(2)}</span>
                                  ))}
                                </div>
                              </td>
                              <td className="px-4 py-4">
                                <button
                                  type="button"
                                  onClick={() => setInspectedCluster(cl)}
                                  className="btn-ghost text-xs text-[#F0C7B8]"
                                >
                                  Inspect <ArrowUpRight className="w-3.5 h-3.5" />
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </motion.section>

              {/* ── Topic Captured Posts Feed ── */}
              <motion.section {...reveal} className="glass-panel overflow-hidden">
                <div className="flex items-center justify-between border-b border-white/10 px-5 py-5">
                  <div>
                    <p className="kicker">Live Stream</p>
                    <h2 className="display mt-1 text-3xl text-[#F7F2EA]">Captured Posts</h2>
                  </div>
                  <div className="text-xs text-[#F6F1E8]/50 font-mono">
                    {topicPosts.length} captured
                  </div>
                </div>
                {topicPosts.length === 0 ? (
                  <div className="p-8 text-center text-[#F6F1E8]/45">No posts captured yet for this keyword.</div>
                ) : (
                  <div className="divide-y divide-white/[0.06] max-h-96 overflow-y-auto">
                    {topicPosts.map((p: any) => (
                      <div key={p.id} className="p-4 hover:bg-white/[0.02] transition-colors">
                        <div className="flex items-center justify-between text-xs text-[#F6F1E8]/50 font-mono mb-1">
                          <span className="font-semibold text-[#F7F2EA]">
                            {revealHandles ? (p.author_handle || p.authorHandle || p.did) : (p.author_alias || p.authorAlias || `A-${p.did.slice(-6).toUpperCase()}`)}
                          </span>
                          <span>{p.created_at ? p.created_at.replace('T', ' ').slice(0, 19) + ' UTC' : ''}</span>
                        </div>
                        <p className="text-sm text-[#E8DFD2] leading-relaxed whitespace-pre-wrap">{p.text}</p>
                        {p.links?.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-2 text-xs">
                            {p.links.map((link: string, idx: number) => (
                              <a key={idx} href={link} target="_blank" rel="noreferrer" className="text-[#F0B5A2] hover:underline truncate max-w-xs">
                                🔗 {link}
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </motion.section>
            </main>
          </>
        ) : (
          <main className="relative z-10 mx-auto max-w-[1180px] px-5 pb-24 pt-10 md:px-8">
            <div className="mb-6">
              <p className="kicker">{view === 'evaluation' ? 'Laboratory' : 'Method'}</p>
              <h1 className="display mt-2 text-4xl text-[#F7F2EA] md:text-5xl">
                {view === 'evaluation' ? 'What the detector can and cannot see.' : 'How a score becomes a sentence.'}
              </h1>
            </div>
            {view === 'evaluation'
              ? <EvaluationLabView result={evalResult} onRerunEvaluation={runEval} isRunning={evalRunning} />
              : <EthicsAndDocsView activeTopicId={selectedTopic ?? undefined} />}
          </main>
        )}

        {inspectedCluster && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-[#06101c]/70 p-3 backdrop-blur-md md:p-6"
            onClick={() => setInspectedCluster(null)}
          >
            <div
              className="glass-card flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden shadow-2xl"
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
                isLiveTopic={currentTopicObj?.source === 'live'}
              />
            </div>
          </div>
        )}
      </div>
    </MotionConfig>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.14em] text-[#F6F1E8]/50">{label}</div>
      <div className="mt-1 font-mono text-lg tabular-nums text-[#F7F2EA]">{value}</div>
    </div>
  );
}

function Metric({ kicker, value, accent = false }: { kicker: string; value: number; accent?: boolean }) {
  return (
    <div className="glass-panel px-4 py-4">
      <div className="kicker">{kicker}</div>
      <div className={`mt-2 font-mono text-3xl tabular-nums ${accent ? 'text-[#F0B5A2]' : 'text-[#F7F2EA]'}`}>{value}</div>
    </div>
  );
}
