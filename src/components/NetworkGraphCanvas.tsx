import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { GraphNode, NetworkGraphData } from '../types';
import { ZoomIn, ZoomOut, RotateCcw, Sparkles, Compass } from 'lucide-react';

interface NetworkGraphCanvasProps {
  graph?: NetworkGraphData;
  graphData?: NetworkGraphData;
  selectedClusterId?: string | null;
  onSelectCluster?: (clusterId: string | null) => void;
  onNodeClick?: (nodeId: string) => void;
  revealHandles?: boolean;
}

interface PositionedNode extends GraphNode {
  x: number;
  y: number;
  radius: number;
  isSeedLabel: boolean;
}

function getClusterPalette(score: number, clusterId: string | null) {
  if (!clusterId) {
    return {
      fill: '#475569',
      stroke: '#1E293B',
      hullFill: 'rgba(30, 41, 59, 0.2)',
      hullStroke: 'rgba(100, 116, 139, 0.25)',
      edge: 'rgba(100, 116, 139, 0.22)',
      text: '#94A3B8',
    };
  }
  if (score >= 70) {
    return {
      fill: '#EF4444',
      stroke: '#FCA5A5',
      hullFill: 'rgba(239, 68, 68, 0.09)',
      hullStroke: 'rgba(239, 68, 68, 0.58)',
      edge: 'rgba(239, 68, 68, 0.38)',
      text: '#FCA5A5',
    };
  }
  if (score >= 50) {
    return {
      fill: '#F97316',
      stroke: '#FDBA74',
      hullFill: 'rgba(249, 115, 22, 0.09)',
      hullStroke: 'rgba(249, 115, 22, 0.52)',
      edge: 'rgba(249, 115, 22, 0.35)',
      text: '#FDBA74',
    };
  }
  return {
    fill: '#EAB308',
    stroke: '#FDE047',
    hullFill: 'rgba(234, 179, 8, 0.08)',
    hullStroke: 'rgba(234, 179, 8, 0.48)',
    edge: 'rgba(234, 179, 8, 0.32)',
    text: '#FDE047',
  };
}

export const NetworkGraphCanvas: React.FC<NetworkGraphCanvasProps> = ({
  graph: graphProp,
  graphData,
  selectedClusterId = null,
  onSelectCluster,
  onNodeClick,
  revealHandles = false,
}) => {
  const graph = graphProp || graphData || { nodes: [], links: [] };
  const containerRef = useRef<HTMLDivElement | null>(null);
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);
  const orbitalCanvasRef = useRef<HTMLCanvasElement | null>(null);

  const [graphMode, setGraphMode] = useState<'force2d' | 'orbital'>('orbital');
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({
    width: 780,
    height: 410,
  });
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);
  const [signalFilter, setSignalFilter] = useState<'all' | 'text' | 'timing' | 'age' | 'links'>('all');

  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const updateDims = () => {
      const rect = el.getBoundingClientRect();
      if (rect.width > 100) {
        setDimensions({ width: Math.floor(rect.width), height: 410 });
      }
    };
    updateDims();
    const ro = new ResizeObserver(updateDims);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const filteredLinks = useMemo(() => {
    if (signalFilter === 'all') return graph.links;
    return graph.links.filter(
      (l) => l.dominantSignal === signalFilter || l.signals[signalFilter] >= 0.45
    );
  }, [graph.links, signalFilter]);

  // Deterministic initial coordinates for both ForceGraph2D and Orbital view
  const layout = useMemo(() => {
    const width = dimensions.width || 780;
    const height = dimensions.height || 410;
    const cx = width / 2;
    const cy = height / 2 + 8;

    const clusterGroups = new Map<string, GraphNode[]>();
    const organicNodes: GraphNode[] = [];

    for (const n of graph.nodes) {
      if (n.clusterId) {
        const list = clusterGroups.get(n.clusterId) || [];
        list.push(n);
        clusterGroups.set(n.clusterId, list);
      } else {
        organicNodes.push(n);
      }
    }

    const clusterIds = Array.from(clusterGroups.keys()).sort();
    const clusterMeta = new Map<
      string,
      { cx: number; cy: number; hullRadius: number; maxScore: number; count: number }
    >();

    const nodes: PositionedNode[] = [];

    clusterIds.forEach((cid, cIdx) => {
      const members = clusterGroups.get(cid)!;
      members.sort((a, b) => b.score - a.score || b.postCount - a.postCount);

      let sectorX = cx;
      let sectorY = cy;
      if (clusterIds.length === 2) {
        sectorX = cIdx === 0 ? cx - 125 : cx + 125;
        sectorY = cIdx === 0 ? cy - 10 : cy + 10;
      } else if (clusterIds.length === 3) {
        const coords = [
          { x: cx - 140, y: cy - 35 },
          { x: cx + 135, y: cy - 42 },
          { x: cx + 8, y: cy + 105 },
        ];
        sectorX = coords[cIdx].x;
        sectorY = coords[cIdx].y;
      } else if (clusterIds.length > 3) {
        const angle = (cIdx / clusterIds.length) * Math.PI * 2 - Math.PI / 2;
        sectorX = cx + Math.cos(angle) * 140;
        sectorY = cy + Math.sin(angle) * 105;
      }

      const goldenAngle = 2.399963229728653;
      const spacing = 14.5;
      let maxDist = 28;

      members.forEach((m, mIdx) => {
        const r = mIdx === 0 ? 0 : spacing * Math.sqrt(mIdx + 0.6);
        const theta = mIdx * goldenAngle;
        const nx = sectorX + Math.cos(theta) * r;
        const ny = sectorY + Math.sin(theta) * r * 0.92;
        if (r + 18 > maxDist) maxDist = r + 18;

        nodes.push({
          ...m,
          x: nx,
          y: ny,
          radius: Math.min(8.5, 4.5 + Math.sqrt(m.postCount || 1) * 1.2),
          isSeedLabel: mIdx === 0,
        });
      });

      const maxScore = Math.max(...members.map((m) => m.score));
      clusterMeta.set(cid, {
        cx: sectorX,
        cy: sectorY,
        hullRadius: maxDist,
        maxScore,
        count: members.length,
      });
    });

    organicNodes.forEach((n, idx) => {
      const ring = idx % 2;
      const totalInRing = Math.ceil(organicNodes.length / 2) || 1;
      const posInRing = Math.floor(idx / 2);
      const angle = (posInRing / totalInRing) * Math.PI * 2 + ring * 0.35;
      const rx = ring === 0 ? 290 : 330;
      const ry = ring === 0 ? 155 : 178;

      nodes.push({
        ...n,
        x: cx + Math.cos(angle) * rx,
        y: cy + Math.sin(angle) * ry,
        radius: 3.8,
        isSeedLabel: false,
      });
    });

    const nodeMap = new Map<string, PositionedNode>();
    for (const n of nodes) nodeMap.set(n.id, n);

    return { nodes, nodeMap, clusterMeta, width, height };
  }, [graph.nodes, dimensions.width, dimensions.height]);

  // Data structure for react-force-graph-2d
  const forceGraphData = useMemo(() => {
    const cx = layout.width / 2;
    const cy = layout.height / 2;
    return {
      nodes: layout.nodes.map((n) => ({
        ...n,
        x: n.x - cx,
        y: n.y - cy,
      })),
      links: filteredLinks.map((l) => ({
        ...l,
        source: l.source,
        target: l.target,
      })),
    };
  }, [layout, filteredLinks]);

  const activeEgoNode =
    hoveredNode || (focusedNodeId ? layout.nodeMap.get(focusedNodeId) || null : null);

  const egoNeighbors = useMemo(() => {
    const set = new Set<string>();
    if (!activeEgoNode) return set;
    set.add(activeEgoNode.id);
    for (const l of filteredLinks) {
      const sId = typeof l.source === 'object' ? (l.source as GraphNode).id : l.source;
      const tId = typeof l.target === 'object' ? (l.target as GraphNode).id : l.target;
      if (sId === activeEgoNode.id) set.add(tId);
      if (tId === activeEgoNode.id) set.add(sId);
    }
    return set;
  }, [activeEgoNode, filteredLinks]);

  // Custom node renderer for react-force-graph-2d
  const paintForceNode = useCallback(
    (nodeObj: Record<string, unknown>, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const node = nodeObj as unknown as PositionedNode;
      const nx = typeof node.x === 'number' ? node.x : 0;
      const ny = typeof node.y === 'number' ? node.y : 0;
      const r = node.radius || 5;

      const inSelectedCluster = !selectedClusterId || node.clusterId === selectedClusterId;
      const isEgoMember = !activeEgoNode || egoNeighbors.has(node.id);
      const isHovered = activeEgoNode?.id === node.id;
      const dimmed = (!inSelectedCluster && !isHovered) || (activeEgoNode && !isEgoMember);
      const pal = getClusterPalette(node.score, node.clusterId);

      // Subtle outer halo for high-risk cluster seeds
      if (!dimmed && node.clusterId && (isHovered || node.isSeedLabel)) {
        ctx.beginPath();
        ctx.arc(nx, ny, r + 3.5, 0, Math.PI * 2);
        ctx.fillStyle = pal.hullFill.replace('0.09', '0.28');
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(nx, ny, isHovered ? r + 2 : r, 0, Math.PI * 2);
      ctx.fillStyle = dimmed ? 'rgba(51, 65, 85, 0.30)' : pal.fill;
      ctx.fill();

      ctx.lineWidth = (isHovered ? 2 : 1.1) / Math.max(0.7, globalScale * 0.8);
      ctx.strokeStyle = isHovered
        ? '#F8FAFC'
        : dimmed
          ? 'rgba(15, 23, 42, 0.4)'
          : '#090B10';
      ctx.stroke();

      // Draw non-overlapping label on hover or for the 2 seed nodes of the selected cluster
      if (
        isHovered ||
        (node.isSeedLabel && node.clusterId === selectedClusterId && !activeEgoNode)
      ) {
        const label = revealHandles
          ? node.handle.replace('.bsky.social', '')
          : `${node.alias} (${node.clusterId || 'org'})`;
        const fontSize = Math.max(8.5, 10.5 / Math.max(0.85, globalScale));
        ctx.font = `600 ${fontSize}px "JetBrains Mono", monospace`;
        const tw = ctx.measureText(label).width;
        const lx = nx + r + 4;
        const ly = ny - fontSize / 2;

        ctx.fillStyle = 'rgba(9, 11, 16, 0.90)';
        ctx.fillRect(lx - 2.5, ly - 1.5, tw + 5, fontSize + 3);
        ctx.fillStyle = isHovered ? '#38BDF8' : pal.text;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(label, lx, ly);
      }
    },
    [selectedClusterId, activeEgoNode, egoNeighbors, revealHandles]
  );

  // Orbital mode canvas rendering
  useEffect(() => {
    if (graphMode !== 'orbital') return;
    const canvas = orbitalCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const displayW = layout.width;
    const displayH = layout.height;
    if (canvas.width !== displayW * dpr || canvas.height !== displayH * dpr) {
      canvas.width = displayW * dpr;
      canvas.height = displayH * dpr;
    }

    ctx.save();
    ctx.scale(dpr, dpr);

    ctx.fillStyle = '#090B10';
    ctx.fillRect(0, 0, displayW, displayH);

    const cx = displayW / 2;
    const cy = displayH / 2 + 8;
    ctx.strokeStyle = 'rgba(30, 41, 59, 0.38)';
    ctx.lineWidth = 1;
    for (const r of [110, 220, 320]) {
      ctx.beginPath();
      ctx.ellipse(cx, cy, r, r * 0.56, 0, 0, Math.PI * 2);
      ctx.stroke();
    }

    ctx.translate(displayW / 2 + pan.x, displayH / 2 + pan.y);
    ctx.scale(zoom, zoom);
    ctx.translate(-displayW / 2, -displayH / 2);

    for (const [cid, meta] of layout.clusterMeta.entries()) {
      const isSelected = selectedClusterId === cid;
      const pal = getClusterPalette(meta.maxScore, cid);

      ctx.beginPath();
      ctx.arc(meta.cx, meta.cy, meta.hullRadius, 0, Math.PI * 2);
      ctx.fillStyle = isSelected ? pal.hullFill.replace('0.09', '0.16') : pal.hullFill;
      ctx.fill();

      ctx.lineWidth = isSelected ? 1.75 : 1;
      ctx.setLineDash(isSelected ? [] : [5, 4]);
      ctx.strokeStyle = isSelected ? pal.hullStroke : 'rgba(71, 85, 105, 0.4)';
      ctx.stroke();
      ctx.setLineDash([]);

      const badgeText = `${cid} · ${meta.count} nodes · ${meta.maxScore}/100`;
      ctx.font = '600 10.5px "JetBrains Mono", monospace';
      const textWidth = ctx.measureText(badgeText).width;
      const bx = meta.cx - textWidth / 2 - 8;
      const by = meta.cy - meta.hullRadius - 24;
      const bw = textWidth + 16;
      const bh = 18;

      ctx.fillStyle = isSelected ? '#1E293B' : 'rgba(15, 23, 42, 0.92)';
      ctx.strokeStyle = isSelected ? pal.stroke : 'rgba(51, 65, 85, 0.8)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(bx, by, bw, bh, 4);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = isSelected ? '#F8FAFC' : pal.text;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(badgeText, meta.cx, by + bh / 2);
    }

    for (const link of filteredLinks) {
      const s = layout.nodeMap.get(link.source);
      const t = layout.nodeMap.get(link.target);
      if (!s || !t) continue;

      const isEgoLink =
        activeEgoNode && (link.source === activeEgoNode.id || link.target === activeEgoNode.id);
      const inSelectedCluster =
        !selectedClusterId ||
        s.clusterId === selectedClusterId ||
        t.clusterId === selectedClusterId;

      const midX = (s.x + t.x) / 2;
      const midY = (s.y + t.y) / 2;
      const dx = t.x - s.x;
      const dy = t.y - s.y;
      const ctrlX = midX - dy * 0.12;
      const ctrlY = midY + dx * 0.12;

      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.quadraticCurveTo(ctrlX, ctrlY, t.x, t.y);

      if (isEgoLink) {
        ctx.lineWidth = 1.8;
        ctx.strokeStyle = '#38BDF8';
      } else if (!inSelectedCluster) {
        ctx.lineWidth = 0.6;
        ctx.strokeStyle = 'rgba(51, 65, 85, 0.12)';
      } else {
        const pal = getClusterPalette(Math.max(s.score, t.score), s.clusterId);
        ctx.lineWidth = Math.max(0.75, link.weight * 1.6);
        ctx.strokeStyle = pal.edge;
      }
      ctx.stroke();
    }

    for (const node of layout.nodes) {
      paintForceNode(node as unknown as Record<string, unknown>, ctx, 1);
    }

    ctx.restore();
  }, [
    graphMode,
    layout,
    filteredLinks,
    selectedClusterId,
    activeEgoNode,
    zoom,
    pan,
    paintForceNode,
  ]);

  const handleZoomIn = () => {
    if (graphMode === 'force2d' && fgRef.current) {
      const cur = fgRef.current.zoom();
      fgRef.current.zoom(Math.min(3.5, cur * 1.25), 250);
    } else {
      setZoom((z) => Math.min(2.4, Number((z + 0.25).toFixed(2))));
    }
  };

  const handleZoomOut = () => {
    if (graphMode === 'force2d' && fgRef.current) {
      const cur = fgRef.current.zoom();
      fgRef.current.zoom(Math.max(0.5, cur * 0.8), 250);
    } else {
      setZoom((z) => Math.max(0.65, Number((z - 0.25).toFixed(2))));
    }
  };

  const handleResetView = () => {
    setFocusedNodeId(null);
    if (graphMode === 'force2d' && fgRef.current) {
      fgRef.current.centerAt(0, 0, 300);
      fgRef.current.zoom(1, 300);
    } else {
      setZoom(1);
      setPan({ x: 0, y: 0 });
    }
  };

  const screenToWorld = (clientX: number, clientY: number) => {
    const canvas = orbitalCanvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const scaleX = layout.width / rect.width;
    const scaleY = layout.height / rect.height;
    const canvasX = (clientX - rect.left) * scaleX;
    const canvasY = (clientY - rect.top) * scaleY;

    const worldX = (canvasX - layout.width / 2 - pan.x) / zoom + layout.width / 2;
    const worldY = (canvasY - layout.height / 2 - pan.y) / zoom + layout.height / 2;
    return { x: worldX, y: worldY };
  };

  const findNodeAt = (worldX: number, worldY: number): PositionedNode | null => {
    for (let i = layout.nodes.length - 1; i >= 0; i--) {
      const n = layout.nodes[i];
      const d = Math.hypot(n.x - worldX, n.y - worldY);
      if (d <= n.radius + 5) return n;
    }
    return null;
  };

  return (
    <div className="flex flex-col bg-[#0E121B] border border-slate-800/90 rounded-lg overflow-hidden">
      {/* Graph Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-slate-800/90 bg-[#0B0E16]">
        <div>
          <h2 className="text-sm font-semibold text-slate-100 tracking-tight">
            2D Force-Directed Similarity Graph &amp; Louvain Communities
          </h2>
          <p className="text-xs text-slate-400 mt-0.5 font-mono tabular-nums">
            {graph.nodes.length} actor nodes · {filteredLinks.length} weighted similarity edges ·{' '}
            {layout.clusterMeta.size} Louvain communities
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Graph Engine Switcher: react-force-graph-2d vs Orbital Containment */}
          <div
            role="group"
            aria-label="Graph layout engine"
            className="flex items-center gap-0.5 p-0.5 bg-[#090B10] border border-slate-800 rounded"
          >
            <button
              type="button"
              onClick={() => setGraphMode('force2d')}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-sm transition-colors whitespace-nowrap shrink-0 ${
                graphMode === 'force2d'
                  ? 'bg-sky-600 text-white font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sparkles className="w-3 h-3" />
              ForceGraph2D
            </button>
            <button
              type="button"
              onClick={() => setGraphMode('orbital')}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-sm transition-colors whitespace-nowrap shrink-0 ${
                graphMode === 'orbital'
                  ? 'bg-sky-600 text-white font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Compass className="w-3 h-3" />
              Cluster Hulls
            </button>
          </div>

          {/* Signal Edge Filter */}
          <div
            role="group"
            aria-label="Filter graph edges by signal type"
            className="flex items-center gap-0.5 p-0.5 bg-[#090B10] border border-slate-800 rounded"
          >
            {(
              [
                { id: 'all', label: 'All Signals' },
                { id: 'text', label: 'Text' },
                { id: 'timing', label: 'Timing' },
                { id: 'age', label: 'Age' },
                { id: 'links', label: 'Links' },
              ] as const
            ).map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setSignalFilter(tab.id)}
                className={`px-2 py-1 text-xs font-medium rounded-sm transition-colors whitespace-nowrap shrink-0 ${
                  signalFilter === tab.id
                    ? 'bg-slate-800 text-slate-100'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              aria-label="Zoom in network graph"
              onClick={handleZoomIn}
              className="p-1.5 text-slate-400 hover:text-slate-100 bg-[#090B10] border border-slate-800 rounded transition-colors"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              aria-label="Zoom out network graph"
              onClick={handleZoomOut}
              className="p-1.5 text-slate-400 hover:text-slate-100 bg-[#090B10] border border-slate-800 rounded transition-colors"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              aria-label="Reset network graph view"
              onClick={handleResetView}
              className="p-1.5 text-slate-400 hover:text-slate-100 bg-[#090B10] border border-slate-800 rounded transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Canvas Viewport */}
      <div
        ref={containerRef}
        data-testid="network-graph-canvas"
        data-nodes-count={graph.nodes.length}
        data-links-count={filteredLinks.length}
        className="relative w-full h-[410px] bg-[#090B10] select-none overflow-hidden"
      >
        {graphMode === 'force2d' ? (
          <ForceGraph2D
            ref={fgRef}
            width={dimensions.width}
            height={dimensions.height}
            graphData={forceGraphData}
            backgroundColor="#090B10"
            cooldownTicks={40}
            onEngineStop={() => {
              fgRef.current?.pauseAnimation();
            }}
            d3AlphaDecay={0.05}
            d3VelocityDecay={0.35}
            nodeRelSize={5}
            nodeCanvasObject={paintForceNode}
            nodePointerAreaPaint={(nodeObj, color, ctx) => {
              const n = nodeObj as unknown as PositionedNode;
              ctx.fillStyle = color;
              ctx.beginPath();
              ctx.arc(n.x || 0, n.y || 0, (n.radius || 5) + 4, 0, 2 * Math.PI);
              ctx.fill();
            }}
            linkWidth={(linkObj) => {
              const l = linkObj as { weight?: number };
              return Math.max(0.8, (l.weight || 0.4) * 1.8);
            }}
            linkColor={(linkObj) => {
              const l = linkObj as {
                source?: GraphNode | string;
                target?: GraphNode | string;
              };
              const sNode =
                typeof l.source === 'object'
                  ? l.source
                  : layout.nodeMap.get(String(l.source));
              const tNode =
                typeof l.target === 'object'
                  ? l.target
                  : layout.nodeMap.get(String(l.target));
              if (
                activeEgoNode &&
                (sNode?.id === activeEgoNode.id || tNode?.id === activeEgoNode.id)
              ) {
                return '#38BDF8';
              }
              const cid = sNode?.clusterId || tNode?.clusterId || null;
              if (selectedClusterId && cid !== selectedClusterId) {
                return 'rgba(51, 65, 85, 0.14)';
              }
              return getClusterPalette(
                Math.max(sNode?.score || 0, tNode?.score || 0),
                cid
              ).edge;
            }}
            linkCurvature={0.14}
            onNodeHover={(nodeObj) => {
              setHoveredNode((nodeObj as unknown as GraphNode) || null);
            }}
            onNodeClick={(nodeObj) => {
              const n = nodeObj as unknown as GraphNode;
              setFocusedNodeId((prev) => (prev === n.id ? null : n.id));
              if (n.clusterId) {
                onSelectCluster(n.clusterId);
              }
            }}
          />
        ) : (
          <canvas
            ref={orbitalCanvasRef}
            onMouseMove={(e) => {
              if (isDraggingRef.current) {
                setPan({
                  x: e.clientX - dragStartRef.current.x,
                  y: e.clientY - dragStartRef.current.y,
                });
                return;
              }
              const { x, y } = screenToWorld(e.clientX, e.clientY);
              setHoveredNode(findNodeAt(x, y));
            }}
            onMouseDown={(e) => {
              const { x, y } = screenToWorld(e.clientX, e.clientY);
              const hit = findNodeAt(x, y);
              if (hit) {
                setFocusedNodeId((prev) => (prev === hit.id ? null : hit.id));
                if (hit.clusterId) onSelectCluster(hit.clusterId);
                return;
              }
              setFocusedNodeId(null);
              isDraggingRef.current = true;
              dragStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
            }}
            onMouseUp={() => {
              isDraggingRef.current = false;
            }}
            onMouseLeave={() => {
              isDraggingRef.current = false;
            }}
            className="w-full h-full cursor-grab active:cursor-grabbing block"
          />
        )}

        {/* Quick Cluster Selector Overlay on Top-Left of Graph Canvas (shown in ForceGraph2D mode) */}
        {graphMode === 'force2d' && (
          <div className="absolute top-3 left-3 flex flex-wrap items-center gap-1.5 pointer-events-auto">
            {Array.from(layout.clusterMeta.entries()).map(([cid, meta]) => {
              const isSel = selectedClusterId === cid;
              const dotColor =
                meta.maxScore >= 70
                  ? 'bg-red-500'
                  : meta.maxScore >= 50
                    ? 'bg-orange-500'
                    : 'bg-yellow-400';
              return (
                <button
                  key={cid}
                  type="button"
                  onClick={() => onSelectCluster(cid)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-mono rounded border transition-colors ${
                    isSel
                      ? 'bg-slate-800/95 text-white border-sky-500 font-semibold'
                      : 'bg-[#090B10]/90 text-slate-300 border-slate-800 hover:border-slate-600'
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${dotColor}`} />
                  {cid} · {meta.count} nodes · {meta.maxScore}/100
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Integrated Bottom Telemetry & Legend Strip inside Graph Card */}
      <div className="px-4 py-2.5 bg-[#0B0E16] border-t border-slate-800/90 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-4 text-slate-300">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
            Coordinated Ring (70–100)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-orange-500 inline-block" />
            Elevated (50–69)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-yellow-400 inline-block" />
            FP Discounted News Burst (&lt;50)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-slate-500 inline-block" />
            Independent Organic Account
          </span>
        </div>

        <div className="font-mono text-slate-400 tabular-nums">
          {activeEgoNode ? (
            <span className="text-sky-300">
              Node {revealHandles ? activeEgoNode.handle : activeEgoNode.alias} ·{' '}
              {activeEgoNode.clusterId || 'Organic'} · Score {activeEgoNode.score}/100 ·{' '}
              {Math.max(0, egoNeighbors.size - 1)} connected peers
            </span>
          ) : (
            <span>Click any node or cluster placard to open its forensic dossier</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default NetworkGraphCanvas;
