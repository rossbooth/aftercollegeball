'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import { sankey, sankeyLinkHorizontal, SankeyNode as D3SankeyNode, SankeyLink as D3SankeyLink } from 'd3-sankey';
import { trackCategoryClick, trackBackToOverview, trackFlowHover } from '@/lib/analytics';
import { colors, bucketLabels, type BucketKey } from '@/lib/colors';
import type { SankeyData, ViewLevel } from '@/lib/types';
import CountryBreakdown from './CountryBreakdown';
import PlayerDataTable from './PlayerDataTable';
import ChatAssistant from './ChatAssistant';

interface SankeyNodeExtra {
  id: string;
  label: string;
  count: number;
  pct?: string;
}

interface SankeyLinkExtra {
  source: string;
  target: string;
  value: number;
}

type SNode = D3SankeyNode<SankeyNodeExtra, SankeyLinkExtra>;

// Margins are dynamic based on width — set in the render effect
const DEFAULT_MARGIN = { top: 30, right: 200, bottom: 5, left: 200 };
const NODE_WIDTH = 10;
const NODE_PADDING = 18;

// Distinct colors for each sub-category within Level 2
const SUB_COLORS: Record<string, string> = {
  // NBA sub-categories — each distinct
  nba_long: '#38bdf8',      // sky blue (stayed NBA)
  nba_to_intl: '#f9a857',   // amber (went international)
  nba_to_gl: '#a78bfa',     // purple (went G-League)
  nba_left: '#f87171',      // coral red (left basketball)
  // G-League sub-categories — each distinct
  gl_to_nba: '#38bdf8',     // sky blue (made NBA)
  gl_to_intl: '#f9a857',    // amber (went international)
  gl_long: '#c084fc',       // light purple (stayed G-League)
  gl_left: '#f87171',       // coral red (left basketball)
  gl_extra: '#4ade80',      // green
  // Europe sub-categories — each distinct
  eu_to_nba: '#38bdf8',     // sky blue (made NBA)
  eu_to_gl: '#c084fc',      // light purple (went G-League)
  eu_to_other_intl: '#f9a857', // amber (went other intl)
  eu_long: '#34d399',       // emerald (stayed Europe)
  eu_left: '#f87171',       // coral red (left basketball)
  eu_extra: '#67e8f9',      // cyan
  // Other Intl sub-categories — each distinct
  oi_to_nba: '#38bdf8',     // sky blue (made NBA)
  oi_to_gl: '#c084fc',      // light purple (went G-League)
  oi_to_europe: '#34d399',  // emerald (went Europe)
  oi_long: '#fbbf24',       // yellow (stayed intl)
  oi_left: '#f87171',       // coral red (left basketball)
  oi_extra: '#fb923c',      // orange
};

function getBucketColor(id: string): string {
  // Check specific sub-category first
  if (id in SUB_COLORS) return SUB_COLORS[id];
  if (id in colors.buckets) return colors.buckets[id as BucketKey];
  // Source nodes in Level 2
  if (id.endsWith('_all')) {
    if (id.startsWith('nba')) return colors.buckets.nba;
    if (id.startsWith('gl')) return colors.buckets.gleague;
    if (id.startsWith('eu')) return colors.buckets.europe;
    if (id.startsWith('oi')) return colors.buckets.other_intl;
  }
  if (id.startsWith('nba')) return colors.buckets.nba;
  if (id.startsWith('gleague') || id.startsWith('gl')) return colors.buckets.gleague;
  if (id.startsWith('europe') || id.startsWith('eu')) return colors.buckets.europe;
  if (id.startsWith('other_intl') || id.startsWith('oi')) return colors.buckets.other_intl;
  if (id.startsWith('intl') || id.startsWith('international')) return colors.buckets.europe;
  if (id.startsWith('nopro')) return colors.buckets.nopro;
  return colors.text.secondary;
}

function getLinkColor(targetId: string): string {
  return getBucketColor(targetId);
}

// Clickable targets at Level 1 (all except source and nopro)
const CLICKABLE_IDS = new Set(['nba', 'gleague', 'europe', 'other_intl']);

export default function SankeyDiagram() {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [currentView, setCurrentView] = useState<ViewLevel>('level1');
  const [data, setData] = useState<SankeyData | null>(null);
  const [tappedId, setTappedId] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    label: string;
    pct: string;
    count: number;
    subtitle?: string;
  } | null>(null);
  const [dimensions, setDimensions] = useState({ width: 1000, height: 550 });
  const [isVertical, setIsVertical] = useState(false);
  const navGuardRef = useRef(false);
  const isTouchRef = useRef(false);

  // Detect touch device
  useEffect(() => {
    isTouchRef.current = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  }, []);

  // Block clicks for 800ms after any view change to prevent touch event bleed
  const safeSetView = useCallback((id: ViewLevel) => {
    navGuardRef.current = true;
    setTappedId(null);
    setTooltip(null);
    setCurrentView(id);
    setTimeout(() => { navGuardRef.current = false; }, 800);
  }, []);

  // Unified tap handler: first tap = tooltip, second tap on same = navigate
  const handleTapOrClick = useCallback((id: string, tooltipData: { x: number; y: number; label: string; pct: string; count: number; subtitle?: string }) => {
    if (navGuardRef.current) return;
    if (currentView !== 'level1' || !CLICKABLE_IDS.has(id)) return;

    if (isTouchRef.current) {
      if (tappedId === id) {
        // Second tap — navigate
        trackCategoryClick(id);
        safeSetView(id as ViewLevel);
      } else {
        // First tap — show tooltip
        setTappedId(id);
        setTooltip(tooltipData);
      }
    } else {
      // Desktop click — navigate immediately
      trackCategoryClick(id);
      safeSetView(id as ViewLevel);
    }
  }, [currentView, tappedId, safeSetView]);

  // Clear tapped state when tapping outside
  useEffect(() => {
    const handleTouchOutside = () => {
      if (tappedId) {
        setTappedId(null);
        setTooltip(null);
      }
    };
    document.addEventListener('touchstart', handleTouchOutside, { passive: true });
    return () => document.removeEventListener('touchstart', handleTouchOutside);
  }, [tappedId]);

  // Load data based on current view
  useEffect(() => {
    const fileMap: Record<ViewLevel, string> = {
      level1: '/data/sankey-level1.json',
      nba: '/data/sankey-nba.json',
      gleague: '/data/sankey-gleague.json',
      europe: '/data/sankey-europe.json',
      other_intl: '/data/sankey-other-intl.json',
    };
    fetch(fileMap[currentView])
      .then(r => r.json())
      .then(setData)
      .catch(console.error);
  }, [currentView]);

  // Responsive sizing — on mobile, fit within viewport; no horizontal scroll
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(entries => {
      const containerWidth = entries[0].contentRect.width;
      setIsVertical(false); // Always horizontal

      {
        // Horizontal layout — scale to fit container
        const svgWidth = containerWidth < 640
          ? Math.max(300, containerWidth)
          : containerWidth < 768
          ? Math.max(320, containerWidth)
          : Math.max(700, containerWidth);
        const svgHeight = containerWidth < 768
          ? Math.max(260, containerWidth * 0.75)
          : Math.max(320, Math.min(550, containerWidth * 0.5));
        setDimensions({ width: svgWidth, height: svgHeight });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Render D3 Sankey
  useEffect(() => {
    if (!data || !svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const { width, height } = dimensions;

    svg.selectAll('*').remove();

    if (isVertical) {
      // ===== VERTICAL SANKEY (mobile < 640px) =====
      // Strategy: run d3-sankey in a transposed space (swap width/height),
      // then swap x/y when rendering so flows go top-to-bottom.
      const vMargin = { top: 60, right: 10, bottom: 60, left: 10 };
      // The sankey layout will think width = our height, height = our width
      const layoutWidth = height - vMargin.top - vMargin.bottom;
      const layoutHeight = width - vMargin.left - vMargin.right;

      const sankeyNodes: SankeyNodeExtra[] = data.nodes.map(n => ({ ...n }));
      const sankeyLinks: SankeyLinkExtra[] = data.links.map(l => ({
        source: l.source,
        target: l.target,
        value: l.value,
      }));

      const graph = sankey<SankeyNodeExtra, SankeyLinkExtra>()
        .nodeId(d => d.id)
        .nodeWidth(NODE_WIDTH)
        .nodePadding(14)
        .extent([
          [0, 0],
          [layoutWidth, layoutHeight],
        ])({
          nodes: sankeyNodes,
          links: sankeyLinks,
        });

      // Cap "No Pro Career" node
      const noProNode = graph.nodes.find(n => (n as SNode).id === 'nopro') as SNode | undefined;
      const otherDestNodes = graph.nodes.filter(n => {
        const sn = n as SNode;
        return sn.targetLinks && sn.targetLinks.length > 0 && sn.id !== 'nopro';
      });
      if (noProNode && otherDestNodes.length > 0) {
        const maxProHeight = Math.max(...otherDestNodes.map(n => ((n as SNode).y1 || 0) - ((n as SNode).y0 || 0)));
        const cappedHeight = maxProHeight * 1.5;
        const currentHeight = (noProNode.y1 || 0) - (noProNode.y0 || 0);
        if (currentHeight > cappedHeight) {
          noProNode.y1 = (noProNode.y0 || 0) + cappedHeight;
        }
      }

      // Now swap coordinates: layout x -> render y, layout y -> render x
      // After swap, add margins
      const swapX = (layoutY: number) => layoutY + vMargin.left;
      const swapY = (layoutX: number) => layoutX + vMargin.top;

      const defs = svg.append('defs');

      // Glow filter
      const glowFilter = defs.append('filter').attr('id', 'sankey-glow').attr('x', '-20%').attr('y', '-20%').attr('width', '140%').attr('height', '140%');
      glowFilter.append('feGaussianBlur').attr('stdDeviation', '6').attr('in', 'SourceGraphic').attr('result', 'blur');
      glowFilter.append('feColorMatrix').attr('in', 'blur').attr('type', 'saturate').attr('values', '1.5').attr('result', 'saturated');
      const glowMerge = glowFilter.append('feMerge');
      glowMerge.append('feMergeNode').attr('in', 'saturated');
      glowMerge.append('feMergeNode').attr('in', 'SourceGraphic');

      // Draw vertical links using custom paths
      // For each link, we need to draw a path from source node (top) to target node (bottom)
      // In the transposed space: source x0,x1,y0,y1 -> rendered positions
      const linkGroup = svg
        .append('g')
        .attr('class', 'sankey-links')
        .style('filter', 'url(#sankey-glow)');

      graph.links.forEach((link, i) => {
        const sourceNode = link.source as SNode;
        const targetNode = link.target as SNode;
        const targetId = targetNode.id || '';

        // Create gradient for vertical flow (top to bottom)
        const gradient = defs
          .append('linearGradient')
          .attr('id', `link-gradient-${i}`)
          .attr('gradientUnits', 'userSpaceOnUse')
          .attr('x1', 0)
          .attr('y1', swapY(sourceNode.x1 || 0))
          .attr('x2', 0)
          .attr('y2', swapY(targetNode.x0 || 0));

        gradient.append('stop').attr('offset', '0%').attr('stop-color', getLinkColor(targetId));
        gradient.append('stop').attr('offset', '100%').attr('stop-color', getLinkColor(targetId));

        // Build a vertical bezier path
        // Source: horizontal band from swapX(link.y0) to swapX(link.y0 + link.width)
        // at vertical position swapY(sourceNode.x1)
        // Target: horizontal band at swapY(targetNode.x0)
        const sy = swapY(sourceNode.x1 || 0);
        const ty = swapY(targetNode.x0 || 0);
        const sx = swapX(link.y0 as number || 0);
        const sw = link.width || 0;
        const tx = swapX(link.y1 as number || 0) - sw; // target x position
        const midY = (sy + ty) / 2;

        const path = `M ${sx},${sy}
          L ${sx + sw},${sy}
          C ${sx + sw},${midY} ${tx + sw},${midY} ${tx + sw},${ty}
          L ${tx},${ty}
          C ${tx},${midY} ${sx},${midY} ${sx},${sy}`;

        linkGroup.append('path')
          .attr('d', path)
          .attr('fill', `url(#link-gradient-${i})`)
          .attr('fill-opacity', 0.35)
          .attr('stroke', 'none')
          .style('cursor', (currentView === 'level1' && CLICKABLE_IDS.has(targetId)) ? 'pointer' : 'default')
          .on('mouseenter', function (event) {
            event.preventDefault();
            const isNoPro = targetId === 'nopro';
            setTooltip({
              x: event.touches ? event.touches[0].clientX : event.clientX,
              y: event.touches ? event.touches[0].clientY : event.clientY,
              label: targetNode.label,
              pct: targetNode.pct || '',
              count: targetNode.count || link.value,
              subtitle: isNoPro ? 'More Data Coming Soon' : undefined,
            });
          })
          .on('mouseleave', function () {
            setTooltip(null);
          })
          .on('click', function (event) {
            event.stopPropagation();
            const isNoPro = targetId === 'nopro';
            handleTapOrClick(targetId, {
              x: event.clientX, y: event.clientY,
              label: targetNode.label, pct: targetNode.pct || '',
              count: targetNode.count || link.value,
              subtitle: isNoPro ? 'More Data Coming Soon' : undefined,
            });
          });
      });

      // Draw nodes (swapped coordinates)
      const nodeGroup = svg
        .append('g')
        .attr('class', 'sankey-nodes')
        .selectAll('g')
        .data(graph.nodes)
        .join('g')
        .attr('class', d => {
          const clickable = currentView === 'level1' && CLICKABLE_IDS.has(d.id);
          return `sankey-node ${clickable ? 'clickable' : ''}`;
        });

      // Node rectangles (swapped: x->y, y->x, width->height, height->width)
      nodeGroup
        .append('rect')
        .attr('x', d => swapX(d.y0 || 0))
        .attr('y', d => swapY(d.x0 || 0))
        .attr('width', d => Math.max(2, (d.y1 || 0) - (d.y0 || 0)))
        .attr('height', d => Math.max(2, (d.x1 || 0) - (d.x0 || 0)))
        .attr('fill', d => getBucketColor(d.id))
        .attr('rx', 5)
        .attr('ry', 5)
        .style('opacity', 1)
        .style('cursor', d => (currentView === 'level1' && CLICKABLE_IDS.has(d.id)) ? 'pointer' : 'default')
        .on('click', (_, d) => {
          if (currentView === 'level1' && CLICKABLE_IDS.has(d.id)) {
            if (navGuardRef.current) return;
            safeSetView(d.id as ViewLevel);
          }
        })
        .on('mouseenter', function (event, d) {
          if (d.id === 'all' || (!d.targetLinks || d.targetLinks.length === 0)) return;
          const isNoPro = d.id === 'nopro';
          setTooltip({
            x: event.touches ? event.touches[0].clientX : event.clientX,
            y: event.touches ? event.touches[0].clientY : event.clientY,
            label: d.label,
            pct: d.pct || '',
            count: d.count,
            subtitle: isNoPro ? 'More Data Coming Soon' : undefined,
          });
        })
        .on('mouseleave', function () {
          setTooltip(null);
        });

      // Invisible expanded hit areas for tap targets (min 44px)
      nodeGroup
        .append('rect')
        .attr('x', d => swapX(d.y0 || 0) - 10)
        .attr('y', d => {
          const nodeHeight = (d.x1 || 0) - (d.x0 || 0);
          const minHeight = 44;
          const extra = Math.max(0, minHeight - nodeHeight) / 2;
          return swapY(d.x0 || 0) - extra;
        })
        .attr('width', d => Math.max(44, (d.y1 || 0) - (d.y0 || 0) + 20))
        .attr('height', d => {
          const nodeHeight = (d.x1 || 0) - (d.x0 || 0);
          return Math.max(44, nodeHeight);
        })
        .attr('fill', 'transparent')
        .style('cursor', d => (currentView === 'level1' && CLICKABLE_IDS.has(d.id)) ? 'pointer' : 'default')
        .on('click', (_, d) => {
          if (currentView === 'level1' && CLICKABLE_IDS.has(d.id)) {
            trackCategoryClick(d.id);
            if (navGuardRef.current) return;
            safeSetView(d.id as ViewLevel);
          }
        })
        ;

      // Labels — above source nodes, below destination nodes
      nodeGroup
        .append('text')
        .attr('x', d => {
          const nodeWidth = (d.y1 || 0) - (d.y0 || 0);
          return swapX(d.y0 || 0) + nodeWidth / 2;
        })
        .attr('y', d => {
          const isSource = d.sourceLinks && d.sourceLinks.length > 0 && (!d.targetLinks || d.targetLinks.length === 0);
          return isSource ? swapY(d.x0 || 0) - 10 : swapY(d.x1 || 0) + 14;
        })
        .attr('text-anchor', 'middle')
        .style('fill', colors.text.primary)
        .style('font-size', '10px')
        .style('font-weight', '600')
        .style('pointer-events', 'none')
        .each(function (d) {
          const el = d3.select(this);
          const label = d.label.length > 16 ? d.label.slice(0, 14) + '...' : d.label;
          const match = label.match(/^(.+?)(\s*\(.+\))$/);
          if (match) {
            el.text('');
            el.append('tspan').text(match[1]);
            el.append('tspan')
              .attr('x', el.attr('x'))
              .attr('dy', '1.2em')
              .text(match[2].trim())
              .style('font-weight', '400')
              .style('font-size', '8px');
          } else {
            el.text(label);
          }
        });

      // Count / percentage labels
      nodeGroup
        .append('text')
        .attr('x', d => {
          const nodeWidth = (d.y1 || 0) - (d.y0 || 0);
          return swapX(d.y0 || 0) + nodeWidth / 2;
        })
        .attr('y', d => {
          const isSource = d.sourceLinks && d.sourceLinks.length > 0 && (!d.targetLinks || d.targetLinks.length === 0);
          if (isSource) return swapY(d.x0 || 0) - 24;
          const hasLabel = d.label.includes('(');
          return swapY(d.x1 || 0) + (hasLabel ? 36 : 28);
        })
        .attr('text-anchor', 'middle')
        .text(d => {
          const isSource = d.sourceLinks && d.sourceLinks.length > 0 && (!d.targetLinks || d.targetLinks.length === 0);
          if (isSource) return '';
          return d.pct || '';
        })
        .style('fill', colors.text.muted)
        .style('font-size', '9px')
        .style('font-weight', '400')
        .style('pointer-events', 'none');

    } else {
      // ===== HORIZONTAL SANKEY (desktop / tablet) =====
      const isMedium = width < 768;
      const MARGIN = isMedium
        ? { top: 15, right: 90, bottom: 10, left: 8 }
        : DEFAULT_MARGIN;

      const sankeyNodes: SankeyNodeExtra[] = data.nodes.map(n => ({ ...n }));
      const sankeyLinks: SankeyLinkExtra[] = data.links.map(l => ({
        source: l.source,
        target: l.target,
        value: l.value,
      }));

      const graph = sankey<SankeyNodeExtra, SankeyLinkExtra>()
        .nodeId(d => d.id)
        .nodeWidth(NODE_WIDTH)
        .nodePadding(NODE_PADDING)
        .extent([
          [MARGIN.left, MARGIN.top],
          [width - MARGIN.right, height - MARGIN.bottom],
        ])({
          nodes: sankeyNodes,
          links: sankeyLinks,
        });

      // Cap the "No Pro Career" node so it's not proportionally huge
      const noProNode = graph.nodes.find(n => (n as SNode).id === 'nopro') as SNode | undefined;
      const otherDestNodes = graph.nodes.filter(n => {
        const sn = n as SNode;
        return sn.targetLinks && sn.targetLinks.length > 0 && sn.id !== 'nopro';
      });

      if (noProNode && otherDestNodes.length > 0) {
        const maxProHeight = Math.max(...otherDestNodes.map(n => ((n as SNode).y1 || 0) - ((n as SNode).y0 || 0)));
        const cappedHeight = maxProHeight * 1.5;
        const currentHeight = (noProNode.y1 || 0) - (noProNode.y0 || 0);
        if (currentHeight > cappedHeight) {
          noProNode.y1 = (noProNode.y0 || 0) + cappedHeight;
        }
      }

      // Find the actual bottom of all destination nodes after capping
      const allDestNodes = graph.nodes.filter(n => {
        const sn = n as SNode;
        return sn.targetLinks && sn.targetLinks.length > 0;
      });
      const maxDestY = allDestNodes.length > 0
        ? Math.max(...allDestNodes.map(n => (n as SNode).y1 || 0))
        : Math.max(...graph.nodes.map(n => (n as SNode).y1 || 0));

      // Clamp source nodes to not extend below the last destination
      graph.nodes.forEach(n => {
        const sn = n as SNode;
        const isSource = sn.sourceLinks && sn.sourceLinks.length > 0 && (!sn.targetLinks || sn.targetLinks.length === 0);
        if (isSource && (sn.y1 || 0) > maxDestY) {
          sn.y1 = maxDestY;
        }
      });

      const actualHeight = maxDestY;
      svg.attr('height', actualHeight).attr('viewBox', `0 0 ${width} ${actualHeight}`);

      const defs = svg.append('defs');

      // Create gradient for each link
      graph.links.forEach((link, i) => {
        const targetNode = link.target as SNode;
        const targetId = targetNode.id || '';
        const gradient = defs
          .append('linearGradient')
          .attr('id', `link-gradient-${i}`)
          .attr('gradientUnits', 'userSpaceOnUse')
          .attr('x1', (link.source as SNode).x1 || 0)
          .attr('x2', (link.target as SNode).x0 || 0);

        gradient.append('stop').attr('offset', '0%').attr('stop-color', getLinkColor(targetId));
        gradient.append('stop').attr('offset', '100%').attr('stop-color', getLinkColor(targetId));
      });

      // Glow filter for the whole diagram
      const glowFilter = defs.append('filter').attr('id', 'sankey-glow').attr('x', '-20%').attr('y', '-20%').attr('width', '140%').attr('height', '140%');
      glowFilter.append('feGaussianBlur').attr('stdDeviation', '6').attr('in', 'SourceGraphic').attr('result', 'blur');
      glowFilter.append('feColorMatrix').attr('in', 'blur').attr('type', 'saturate').attr('values', '1.5').attr('result', 'saturated');
      const glowMerge = glowFilter.append('feMerge');
      glowMerge.append('feMergeNode').attr('in', 'saturated');
      glowMerge.append('feMergeNode').attr('in', 'SourceGraphic');

      // Draw links — single layer, no overlapping glow
      const linkGroup = svg
        .append('g')
        .attr('class', 'sankey-links')
        .style('filter', 'url(#sankey-glow)')
        .selectAll('path')
        .data(graph.links)
        .join('path')
        .attr('class', d => {
          const targetNode = d.target as SNode;
          const clickable = currentView === 'level1' && CLICKABLE_IDS.has(targetNode.id);
          return `sankey-link ${clickable ? 'clickable' : ''}`;
        })
        .attr('d', sankeyLinkHorizontal())
        .attr('stroke', (_, i) => `url(#link-gradient-${i})`)
        .attr('stroke-width', d => Math.max(2, d.width || 0))
        .style('stroke-opacity', 0.45)
        .style('cursor', d => {
          const targetNode = d.target as SNode;
          return (currentView === 'level1' && CLICKABLE_IDS.has(targetNode.id)) ? 'pointer' : 'default';
        })
        .on('mouseenter', function (event, d) {
          const targetNode = d.target as SNode;
          linkGroup.style('stroke-opacity', 0.06);
          d3.select(this).style('stroke-opacity', 0.7);

          const isNoPro = targetNode.id === 'nopro';
          setTooltip({
            x: event.clientX,
            y: event.clientY,
            label: targetNode.label,
            pct: targetNode.pct || '',
            count: targetNode.count || d.value,
            subtitle: isNoPro ? 'More Data Coming Soon' : undefined,
          });
        })
        .on('mousemove', function (event) {
          setTooltip(prev => prev ? { ...prev, x: event.clientX, y: event.clientY } : null);
        })
        .on('mouseleave', function () {
          linkGroup.style('stroke-opacity', 0.45);
          setTooltip(null);
        })
        .on('click', function (event, d) {
          const targetNode = d.target as SNode;
          const isNoPro = targetNode.id === 'nopro';
          handleTapOrClick(targetNode.id, {
            x: event.clientX,
            y: event.clientY,
            label: targetNode.label,
            pct: targetNode.pct || '',
            count: targetNode.count || d.value,
            subtitle: isNoPro ? 'More Data Coming Soon' : undefined,
          });
        });

      // Draw nodes
      const nodeGroup = svg
        .append('g')
        .attr('class', 'sankey-nodes')
        .selectAll('g')
        .data(graph.nodes)
        .join('g')
        .attr('class', d => {
          const clickable = currentView === 'level1' && CLICKABLE_IDS.has(d.id);
          return `sankey-node ${clickable ? 'clickable' : ''}`;
        });

      // Node rectangles
      nodeGroup
        .append('rect')
        .attr('x', d => d.x0 || 0)
        .attr('y', d => d.y0 || 0)
        .attr('height', d => Math.max(2, (d.y1 || 0) - (d.y0 || 0)))
        .attr('width', d => (d.x1 || 0) - (d.x0 || 0))
        .attr('fill', d => getBucketColor(d.id))
        .attr('rx', 5)
        .attr('ry', 5)
        .style('opacity', 1)
        .style('cursor', d => (currentView === 'level1' && CLICKABLE_IDS.has(d.id)) ? 'pointer' : 'default')
        .on('click', (_, d) => {
          if (currentView === 'level1' && CLICKABLE_IDS.has(d.id)) {
            if (navGuardRef.current) return;
            safeSetView(d.id as ViewLevel);
          }
        })
        .on('mouseenter', function (event, d) {
          if (d.id === 'all' || (!d.targetLinks || d.targetLinks.length === 0)) return;
          const isNoPro = d.id === 'nopro';
          setTooltip({
            x: event.clientX,
            y: event.clientY,
            label: d.label,
            pct: d.pct || '',
            count: d.count,
            subtitle: isNoPro ? 'More Data Coming Soon' : undefined,
          });
        })
        .on('mousemove', function (event) {
          setTooltip(prev => prev ? { ...prev, x: event.clientX, y: event.clientY } : null);
        })
        .on('mouseleave', function () {
          setTooltip(null);
        });

      // Node labels
      nodeGroup
        .append('text')
        .attr('x', d => {
          const isSource = d.sourceLinks && d.sourceLinks.length > 0 && (!d.targetLinks || d.targetLinks.length === 0);
          return isSource ? (d.x0 || 0) - 14 : (d.x1 || 0) + 14;
        })
        .attr('y', d => ((d.y0 || 0) + (d.y1 || 0)) / 2)
        .attr('dy', '-0.15em')
        .attr('text-anchor', d => {
          const isSource = d.sourceLinks && d.sourceLinks.length > 0 && (!d.targetLinks || d.targetLinks.length === 0);
          return isSource ? 'end' : 'start';
        })
        .style('fill', colors.text.primary)
        .style('font-size', isMedium ? '8px' : '13px')
        .style('font-weight', '600')
        .style('pointer-events', 'none')
        .each(function (d) {
          const el = d3.select(this);
          const label = isMedium ? (d.label.length > 14 ? d.label.slice(0, 12) + '\u2026' : d.label) : d.label;
          // Split source node labels with parenthetical onto two lines
          const match = label.match(/^(.+?)(\s*\(.+\))$/);
          if (match) {
            el.text('');
            el.append('tspan').text(match[1]);
            el.append('tspan')
              .attr('x', el.attr('x'))
              .attr('dy', '1.2em')
              .text(match[2].trim())
              .style('font-weight', '400')
              .style('font-size', isMedium ? '7px' : '11px');
          } else {
            el.text(label);
          }
        });

      // Count + percentage labels (hide on mobile for source nodes to save space)
      nodeGroup
        .append('text')
        .attr('x', d => {
          const isSource = d.sourceLinks && d.sourceLinks.length > 0 && (!d.targetLinks || d.targetLinks.length === 0);
          return isSource ? (d.x0 || 0) - 14 : (d.x1 || 0) + 14;
        })
        .attr('y', d => ((d.y0 || 0) + (d.y1 || 0)) / 2)
        .attr('dy', d => {
          const isSource = d.sourceLinks && d.sourceLinks.length > 0 && (!d.targetLinks || d.targetLinks.length === 0);
          // Source nodes with two-line labels need more offset
          const hasParen = d.label.includes('(');
          return (isSource && hasParen) ? '2.5em' : '1.1em';
        })
        .attr('text-anchor', d => {
          const isSource = d.sourceLinks && d.sourceLinks.length > 0 && (!d.targetLinks || d.targetLinks.length === 0);
          return isSource ? 'end' : 'start';
        })
        .text(d => {
          if (isMedium) {
            const isSource = d.sourceLinks && d.sourceLinks.length > 0 && (!d.targetLinks || d.targetLinks.length === 0);
            if (isSource) return '';
            return d.pct || '';
          }
          const pct = d.pct ? ` (${d.pct})` : '';
          return `${d.count.toLocaleString()} players${pct}`;
        })
        .style('fill', colors.text.muted)
        .style('font-size', isMedium ? '7px' : '11px')
        .style('font-weight', '400')
        .style('pointer-events', 'none');

      // "More Data Coming Soon" for nopro node
      nodeGroup
        .filter(d => d.id === 'nopro')
        .append('text')
        .attr('x', d => (d.x1 || 0) + 14)
        .attr('y', d => ((d.y0 || 0) + (d.y1 || 0)) / 2)
        .attr('dy', '2.3em')
        .attr('text-anchor', 'start')
        .text('More Data Coming Soon')
        .style('fill', colors.text.muted)
        .style('font-size', '10px')
        .style('font-style', 'italic')
        .style('pointer-events', 'none');
    }
  }, [data, dimensions, currentView, isVertical]);

  const handleBack = useCallback(() => {
    trackBackToOverview();
    safeSetView('level1');
  }, [safeSetView]);

  const breadcrumbLabel = currentView !== 'level1'
    ? (bucketLabels[currentView] || currentView)
    : null;

  return (
    <section className="py-4">
      <div ref={containerRef} className="max-w-[1400px] mx-auto px-2 sm:px-4">
        {/* Chat — above diagram */}
        <ChatAssistant />

        {/* Instruction or breadcrumb */}
        <div className="flex items-center justify-center gap-2 mt-3 mb-2 min-h-[44px]">
          {breadcrumbLabel ? (
            <>
              <button
                onClick={handleBack}
                className="flex items-center gap-1.5 text-sm transition-colors hover:opacity-80 py-2 min-h-[44px]"
                style={{ color: colors.accent }}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                All D1 Players
              </button>
              <span style={{ color: colors.text.muted }}>/</span>
              <span className="text-sm font-semibold" style={{ color: getBucketColor(currentView) }}>
                {breadcrumbLabel}
              </span>
            </>
          ) : (
            <span className="text-xs sm:text-sm flex items-center gap-1.5" style={{ color: colors.text.muted }}>
              <span className="hidden sm:inline">Or click</span>
              <span className="sm:hidden">Tap</span>
              {' '}a category to explore further
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7" />
              </svg>
            </span>
          )}
        </div>

        {/* Diagram */}
        <div className="flex justify-center overflow-hidden -mx-2 px-2 sm:mx-0 sm:px-0">
          <svg
            ref={svgRef}
            className="w-full h-auto max-w-full sm:w-auto sm:h-auto sm:max-w-none"
            width={dimensions.width}
            height={dimensions.height}
            viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
            preserveAspectRatio="xMidYMid meet"
            style={{ display: 'block', overflow: 'hidden' }}
          />
        </div>

        {/* Player data table */}
        <PlayerDataTable currentView={currentView} />

        {/* Country breakdown shown below when viewing Europe */}
        {currentView === 'europe' && (
          <div className="mt-12">
            <CountryBreakdown />
          </div>
        )}

        {/* Tooltip */}
        {tooltip && (
          <div
            className="fixed z-50 pointer-events-none px-2 py-1.5 sm:px-4 sm:py-3 rounded-lg sm:rounded-xl border"
            style={{
              left: Math.min(tooltip.x + 8, (typeof window !== 'undefined' ? window.innerWidth - 160 : tooltip.x + 8)),
              top: tooltip.y - 60,
              background: 'rgba(10, 10, 15, 0.95)',
              borderColor: 'rgba(255,255,255,0.1)',
              backdropFilter: 'blur(16px)',
              maxWidth: typeof window !== 'undefined' && window.innerWidth < 640 ? 160 : 260,
            }}
          >
            <div className="text-xs sm:text-sm font-semibold" style={{ color: colors.text.primary }}>
              {tooltip.label}
            </div>
            <div className="text-sm sm:text-lg font-bold" style={{ color: colors.text.primary }}>
              {tooltip.pct}
            </div>
            <div className="text-[10px] sm:text-xs" style={{ color: colors.text.muted }}>
              {tooltip.count.toLocaleString()} players
            </div>
            {tooltip.subtitle && (
              <div className="text-xs mt-2 italic" style={{ color: colors.accent }}>
                {tooltip.subtitle}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
