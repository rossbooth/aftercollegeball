'use client';

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { sankey, sankeyLinkHorizontal, SankeyNode as D3SankeyNode, SankeyLink as D3SankeyLink } from 'd3-sankey';
import { colors } from '@/lib/colors';
import type { SankeyData } from '@/lib/types';

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

const MARGIN = { top: 30, right: 250, bottom: 30, left: 200 };
const NODE_WIDTH = 18;
const NODE_PADDING = 22;

// Country flag emojis
const COUNTRY_COLORS: Record<string, string> = {
  eu_spain: '#e74c3c',
  eu_germany: '#f1c40f',
  eu_france: '#3498db',
  eu_italy: '#2ecc71',
  eu_turkey: '#e74c3c',
  eu_greece: '#3498db',
  eu_israel: '#3498db',
  eu_uk: '#9b59b6',
  eu_lithuania: '#f39c12',
  eu_serbia: '#e74c3c',
  eu_belgium: '#f1c40f',
  eu_netherlands: '#e67e22',
  eu_denmark: '#e74c3c',
  eu_croatia: '#e74c3c',
  eu_poland: '#e74c3c',
  eu_russia: '#3498db',
  eu_czech_republic: '#e74c3c',
  eu_other: '#7f8c8d',
};

function getCountryColor(id: string): string {
  return COUNTRY_COLORS[id] || '#4abfa0';
}

export default function CountryBreakdown() {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<SankeyData | null>(null);
  const [tooltip, setTooltip] = useState<{
    x: number; y: number; label: string; pct: string; count: number;
  } | null>(null);
  const [dimensions, setDimensions] = useState({ width: 1000, height: 550 });

  useEffect(() => {
    fetch('/data/europe-countries.json')
      .then(r => r.json())
      .then(setData)
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(entries => {
      const { width } = entries[0].contentRect;
      setDimensions({ width: Math.max(600, width), height: Math.max(450, Math.min(600, width * 0.5)) });
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!data || !svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const { width, height } = dimensions;

    svg.selectAll('*').remove();

    const sankeyNodes: SankeyNodeExtra[] = data.nodes.map(n => ({ ...n }));
    const sankeyLinks: SankeyLinkExtra[] = data.links.map(l => ({ ...l }));

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

    const defs = svg.append('defs');

    graph.links.forEach((link, i) => {
      const targetNode = link.target as SNode;
      const targetId = targetNode.id || '';
      const gradient = defs
        .append('linearGradient')
        .attr('id', `country-gradient-${i}`)
        .attr('gradientUnits', 'userSpaceOnUse')
        .attr('x1', (link.source as SNode).x1 || 0)
        .attr('x2', (link.target as SNode).x0 || 0);
      gradient.append('stop').attr('offset', '0%').attr('stop-color', getCountryColor(targetId));
      gradient.append('stop').attr('offset', '100%').attr('stop-color', getCountryColor(targetId));
    });

    const linkGroup = svg
      .append('g')
      .selectAll('path')
      .data(graph.links)
      .join('path')
      .attr('class', 'sankey-link')
      .attr('d', sankeyLinkHorizontal())
      .attr('stroke', (_, i) => `url(#country-gradient-${i})`)
      .attr('stroke-width', d => Math.max(2, d.width || 0))
      .style('stroke-opacity', 0.45)
      .on('mouseenter', function (event, d) {
        const targetNode = d.target as SNode;
        linkGroup.style('stroke-opacity', 0.08);
        d3.select(this).style('stroke-opacity', 0.8);
        setTooltip({
          x: event.pageX, y: event.pageY,
          label: targetNode.label,
          pct: targetNode.pct || '',
          count: targetNode.count || d.value,
        });
      })
      .on('mousemove', function (event) {
        setTooltip(prev => prev ? { ...prev, x: event.pageX, y: event.pageY } : null);
      })
      .on('mouseleave', function () {
        linkGroup.style('stroke-opacity', 0.45);
        setTooltip(null);
      });

    const nodeGroup = svg
      .append('g')
      .selectAll('g')
      .data(graph.nodes)
      .join('g')
      .attr('class', 'sankey-node');

    nodeGroup
      .append('rect')
      .attr('x', d => d.x0 || 0)
      .attr('y', d => d.y0 || 0)
      .attr('height', d => Math.max(2, (d.y1 || 0) - (d.y0 || 0)))
      .attr('width', d => (d.x1 || 0) - (d.x0 || 0))
      .attr('fill', d => d.id.startsWith('eu_') ? getCountryColor(d.id) : colors.buckets.europe)
      .attr('rx', 3)
      .attr('ry', 3);

    // Labels
    nodeGroup
      .append('text')
      .attr('x', d => {
        const isSource = d.sourceLinks && d.sourceLinks.length > 0 && (!d.targetLinks || d.targetLinks.length === 0);
        return isSource ? (d.x0 || 0) - 10 : (d.x1 || 0) + 10;
      })
      .attr('y', d => ((d.y0 || 0) + (d.y1 || 0)) / 2)
      .attr('dy', '0.35em')
      .attr('text-anchor', d => {
        const isSource = d.sourceLinks && d.sourceLinks.length > 0 && (!d.targetLinks || d.targetLinks.length === 0);
        return isSource ? 'end' : 'start';
      })
      .text(d => {
        const pct = d.pct ? ` (${d.pct})` : '';
        return `${d.label}${pct}`;
      })
      .style('fill', colors.text.primary)
      .style('font-size', '13px')
      .style('font-weight', '600')
      .style('pointer-events', 'none');
  }, [data, dimensions]);

  return (
    <div ref={containerRef}>
      <h3 className="text-base font-semibold mb-3" style={{ color: colors.text.primary }}>
        By Country League
      </h3>
      <svg
        ref={svgRef}
        width={dimensions.width}
        height={dimensions.height}
        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
        style={{ maxWidth: '100%', height: 'auto' }}
      />
      {tooltip && (
        <div
          className="fixed z-50 pointer-events-none px-3 py-2 rounded-lg border"
          style={{
            left: tooltip.x + 16, top: tooltip.y - 10,
            background: 'rgba(10, 10, 15, 0.92)',
            borderColor: 'rgba(255,255,255,0.1)',
            backdropFilter: 'blur(16px)',
          }}
        >
          <div className="text-sm font-semibold" style={{ color: colors.text.primary }}>{tooltip.label}</div>
          <div className="text-lg font-bold" style={{ color: colors.text.primary }}>{tooltip.pct}</div>
          <div className="text-xs" style={{ color: colors.text.muted }}>{tooltip.count.toLocaleString()} players</div>
        </div>
      )}
    </div>
  );
}
