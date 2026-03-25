'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { trackPlayerTableToggle, trackYearTabClick, trackPlayerSearch, trackPlayerExpand, trackDestinationFilter } from '@/lib/analytics';
import { colors } from '@/lib/colors';
import type { ViewLevel } from '@/lib/types';

interface TimelineEntry {
  yr: string;
  lvl: string;
  tm: string | null;
}

interface Player {
  name: string;
  school: string;
  lastCollegeSeason: number;
  firstProDest: 'nba' | 'gleague' | 'europe' | 'other_intl' | 'none';
  firstProTeam: string | null;
  proYears: number;
  currentTeam: string | null;
  lastTeam: string | null;
  active: boolean;
  currentLevel: string;
  timeline: TimelineEntry[];
}

interface PlayerTableData {
  players: Player[];
}

interface PlayerDataTableProps {
  currentView: ViewLevel;
}

const DEST_LABELS: Record<string, string> = {
  all: 'All',
  nba: 'NBA',
  gleague: 'G-League',
  europe: 'Europe',
  other_intl: 'Other Intl',
  none: 'No Pro',
};

const DEST_COLORS: Record<string, string> = {
  nba: colors.buckets.nba,
  gleague: colors.buckets.gleague,
  europe: colors.buckets.europe,
  other_intl: colors.buckets.other_intl,
  none: colors.buckets.nopro,
};

const YEARS: (number | 'all')[] = ['all', 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025];
const PAGE_SIZE = 50;

const LEVEL_LABELS: Record<string, string> = {
  nba: 'NBA',
  gleague: 'G-League',
  europe: 'Europe',
  intl: 'Intl',
  other_intl: 'Intl',
  natl: 'National',
  out: 'Left Basketball',
  none: 'No Pro Career',
};

const LEVEL_COLORS: Record<string, string> = {
  nba: colors.buckets.nba,
  gleague: colors.buckets.gleague,
  europe: colors.buckets.europe,
  intl: colors.buckets.other_intl,
  other_intl: colors.buckets.other_intl,
  natl: '#8a8aaa',
  out: '#ef4444',
  none: '#5a5a6e',
};

const VIEW_TO_DEST: Record<ViewLevel, string | null> = {
  level1: null,
  nba: 'nba',
  gleague: 'gleague',
  europe: 'europe',
  other_intl: 'other_intl',
};

const ACTIVE_LABELS: Record<string, string> = {
  all: 'All Players',
  active: 'Still Active',
  inactive: 'Left Basketball',
};

export default function PlayerDataTable({ currentView }: PlayerDataTableProps) {
  const [isOpen, setIsOpen] = useState(true);
  const [allPlayers, setAllPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeYear, setActiveYear] = useState<number | 'all'>('all');
  const [page, setPage] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [destFilter, setDestFilter] = useState<string>('all');
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [expandedPlayer, setExpandedPlayer] = useState<string | null>(null);

  // Load data immediately
  useEffect(() => {
    if (allPlayers.length > 0) return;
    setLoading(true);
    fetch('/data/player-table.json')
      .then((r) => r.json())
      .then((data: PlayerTableData) => {
        setAllPlayers(data.players);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load player data:', err);
        setError('Failed to load player data');
        setLoading(false);
      });
  }, [allPlayers.length]);

  // Reset page when filters change
  useEffect(() => {
    setPage(0);
  }, [activeYear, currentView, searchQuery, destFilter, activeFilter]);

  const toggleOpen = useCallback(() => {
    setIsOpen((prev) => {
      trackPlayerTableToggle(!prev);
      return !prev;
    });
  }, []);

  // Filter players
  const filteredPlayers = allPlayers.filter((p) => {
    if (activeYear !== 'all' && p.lastCollegeSeason !== activeYear) return false;
    // View-level filter from Sankey
    const viewDest = VIEW_TO_DEST[currentView];
    if (viewDest !== null && p.firstProDest !== viewDest) return false;
    // Destination dropdown filter (only when on level1 view)
    if (viewDest === null && destFilter !== 'all' && p.firstProDest !== destFilter) return false;
    // Active/inactive filter
    if (activeFilter === 'active' && !p.active) return false;
    if (activeFilter === 'inactive' && (p.active || p.firstProDest === 'none')) return false;
    // Search
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!p.name.toLowerCase().includes(q) && !p.school.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  const totalPages = Math.max(1, Math.ceil(filteredPlayers.length / PAGE_SIZE));
  const pagedPlayers = filteredPlayers.slice(
    page * PAGE_SIZE,
    (page + 1) * PAGE_SIZE
  );

  return (
    <div className="mt-6">
      {/* Toggle button */}
      <button
        onClick={toggleOpen}
        className="flex items-center gap-2 mx-auto text-sm transition-colors hover:opacity-80 py-3 min-h-[44px]"
        style={{ color: colors.text.secondary }}
      >
        <svg
          className="w-4 h-4 transition-transform duration-200"
          style={{ transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)' }}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5l7 7-7 7"
          />
        </svg>
        View All Player Data
      </button>

      {/* Collapsible content */}
      {isOpen && (
        <div
          className="mt-4 rounded-xl border overflow-hidden"
          style={{
            background: colors.bg.secondary,
            borderColor: 'rgba(255,255,255,0.06)',
          }}
        >
          {/* Year tabs */}
          <div
            className="flex overflow-x-auto border-b scrollbar-hide"
            style={{ borderColor: 'rgba(255,255,255,0.06)', WebkitOverflowScrolling: 'touch' }}
          >
            {YEARS.map((year) => (
              <button
                key={year}
                onClick={() => { trackYearTabClick(year); setActiveYear(year); }}
                className="px-3 sm:px-4 py-2.5 text-xs sm:text-sm font-medium whitespace-nowrap transition-colors min-h-[44px]"
                style={{
                  color:
                    activeYear === year
                      ? colors.text.primary
                      : colors.text.muted,
                  borderBottom:
                    activeYear === year
                      ? `2px solid ${colors.accent}`
                      : '2px solid transparent',
                  background:
                    activeYear === year ? colors.bg.tertiary : 'transparent',
                }}
              >
                {year === 'all' ? 'All' : year}
              </button>
            ))}
          </div>

          {/* Filters row */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 px-3 sm:px-4 py-3 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
            {/* Search */}
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); if (e.target.value.length === 3) trackPlayerSearch(e.target.value); }}
              placeholder="Search player or school..."
              className="bg-transparent px-3 py-2 rounded-lg text-sm border flex-1 min-w-0 w-full sm:w-auto sm:min-w-[180px]"
              style={{
                color: colors.text.primary,
                borderColor: 'rgba(255,255,255,0.08)',
              }}
            />
            {/* Destination filter — only show on level1 view */}
            {currentView === 'level1' && (
              <select
                value={destFilter}
                onChange={(e) => { trackDestinationFilter(e.target.value); setDestFilter(e.target.value); }}
                className="bg-transparent px-3 py-2 rounded-lg text-sm border cursor-pointer min-h-[44px]"
                style={{
                  color: colors.text.primary,
                  borderColor: 'rgba(255,255,255,0.08)',
                  background: colors.bg.tertiary,
                }}
              >
                {Object.entries(DEST_LABELS).map(([val, label]) => (
                  <option key={val} value={val} style={{ background: '#1a1a2e' }}>{label}</option>
                ))}
              </select>
            )}
            {/* Active/inactive filter */}
            <select
              value={activeFilter}
              onChange={(e) => setActiveFilter(e.target.value)}
              className="bg-transparent px-3 py-2 rounded-lg text-sm border cursor-pointer min-h-[44px]"
              style={{
                color: colors.text.primary,
                borderColor: 'rgba(255,255,255,0.08)',
                background: colors.bg.tertiary,
              }}
            >
              {Object.entries(ACTIVE_LABELS).map(([val, label]) => (
                <option key={val} value={val} style={{ background: '#1a1a2e' }}>{label}</option>
              ))}
            </select>
            {/* Result count */}
            <span className="text-xs" style={{ color: colors.text.muted }}>
              {filteredPlayers.length} players
            </span>
          </div>

          {/* Loading / Error states */}
          {loading && (
            <div
              className="py-12 text-center text-sm"
              style={{ color: colors.text.muted }}
            >
              Loading player data...
            </div>
          )}

          {error && (
            <div
              className="py-12 text-center text-sm"
              style={{ color: '#e04a4a' }}
            >
              {error}
            </div>
          )}

          {/* Table */}
          {!loading && !error && (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[700px]">
                  <thead>
                    <tr
                      style={{
                        borderBottom: '1px solid rgba(255,255,255,0.06)',
                      }}
                    >
                      <th
                        className="text-left px-4 py-3 font-semibold"
                        style={{ color: colors.text.secondary }}
                      >
                        Player
                      </th>
                      <th
                        className="text-left px-4 py-3 font-semibold"
                        style={{ color: colors.text.secondary }}
                      >
                        School
                      </th>
                      <th
                        className="text-left px-4 py-3 font-semibold"
                        style={{ color: colors.text.secondary }}
                      >
                        First Pro Destination
                      </th>
                      <th
                        className="text-left px-4 py-3 font-semibold"
                        style={{ color: colors.text.secondary }}
                      >
                        Current Status
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {pagedPlayers.length === 0 ? (
                      <tr>
                        <td
                          colSpan={4}
                          className="px-4 py-8 text-center"
                          style={{ color: colors.text.muted }}
                        >
                          No players found for this selection.
                        </td>
                      </tr>
                    ) : (
                      pagedPlayers.map((player, i) => {
                        const playerKey = `${player.name}-${player.school}-${i}`;
                        return (<React.Fragment key={playerKey}>
                        <tr
                          className="transition-colors cursor-pointer"
                          style={{
                            borderBottom: expandedPlayer === playerKey ? 'none' : '1px solid rgba(255,255,255,0.03)',
                          }}
                          onClick={() => { const next = expandedPlayer === playerKey ? null : playerKey; if (next) trackPlayerExpand(player.name); setExpandedPlayer(next); }}
                          onMouseEnter={(e) => {
                            (e.currentTarget as HTMLElement).style.background =
                              colors.bg.hover;
                          }}
                          onMouseLeave={(e) => {
                            (e.currentTarget as HTMLElement).style.background =
                              expandedPlayer === playerKey ? 'rgba(255,255,255,0.02)' : 'transparent';
                          }}
                        >
                          <td
                            className="px-4 py-2.5"
                            style={{ color: colors.text.primary }}
                          >
                            <span className="flex items-center gap-1.5">
                              <svg
                                className="w-3 h-3 transition-transform flex-shrink-0"
                                style={{ transform: expandedPlayer === playerKey ? 'rotate(90deg)' : 'rotate(0deg)', color: colors.text.muted }}
                                fill="none" stroke="currentColor" viewBox="0 0 24 24"
                              >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                              </svg>
                              {player.name}
                            </span>
                          </td>
                          <td
                            className="px-4 py-2.5"
                            style={{ color: colors.text.secondary }}
                          >
                            {player.school}
                          </td>
                          <td className="px-4 py-2.5">
                            <span
                              className="inline-flex items-center gap-1.5"
                              style={{
                                color: DEST_COLORS[player.firstProDest],
                              }}
                            >
                              <span
                                className="w-1.5 h-1.5 rounded-full inline-block"
                                style={{
                                  background:
                                    DEST_COLORS[player.firstProDest],
                                }}
                              />
                              {DEST_LABELS[player.firstProDest]}
                              {player.firstProTeam && (
                                <span
                                  style={{ color: colors.text.muted }}
                                >
                                  {' '}
                                  &middot; {player.firstProTeam}
                                </span>
                              )}
                            </span>
                          </td>
                          <td className="px-4 py-2.5">
                            <span className="inline-flex items-center gap-1.5 text-sm">
                              <span
                                className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                                style={{ background: LEVEL_COLORS[player.currentLevel] || '#5a5a6e' }}
                              />
                              <span style={{ color: colors.text.secondary }}>
                                <span style={{ color: LEVEL_COLORS[player.currentLevel] || '#5a5a6e' }}>
                                  {LEVEL_LABELS[player.currentLevel] || player.currentLevel}
                                </span>
                                {player.active && player.currentTeam && (
                                  <span style={{ color: colors.text.muted }}> · {player.currentTeam}</span>
                                )}
                                {player.proYears > 0 && (
                                  <span style={{ color: colors.text.muted }}> · {player.proYears} yr career</span>
                                )}
                              </span>
                            </span>
                          </td>
                        </tr>
                        {/* Expanded timeline row */}
                        {expandedPlayer === playerKey && player.timeline.length > 0 && (
                          <tr>
                            <td colSpan={4} className="px-2 sm:px-6 py-4 sm:py-6" style={{ background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                              <div className="flex items-start gap-0 overflow-x-auto pb-2 justify-start sm:justify-center" style={{ WebkitOverflowScrolling: 'touch' }}>
                                {/* College */}
                                <div className="flex flex-col items-center min-w-[80px] sm:min-w-[100px]">
                                  <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-xs sm:text-sm font-bold" style={{ background: 'rgba(255,255,255,0.1)', color: colors.text.secondary }}>
                                    🎓
                                  </div>
                                  <div className="text-xs sm:text-sm mt-1.5 text-center font-medium" style={{ color: colors.text.muted }}>{player.school}</div>
                                  <div className="text-xs" style={{ color: colors.text.muted }}>{player.lastCollegeSeason}</div>
                                </div>
                                {player.timeline.map((entry, idx) => (
                                  <div key={idx} className="flex items-start">
                                    {/* Arrow connector */}
                                    <div className="flex items-center h-8 sm:h-10">
                                      <div className="w-6 sm:w-10 h-[2px]" style={{ background: LEVEL_COLORS[entry.lvl] || '#5a5a6e' }} />
                                      <div className="w-0 h-0" style={{
                                        borderTop: '5px solid transparent',
                                        borderBottom: '5px solid transparent',
                                        borderLeft: `6px solid ${LEVEL_COLORS[entry.lvl] || '#5a5a6e'}`,
                                      }} />
                                    </div>
                                    {/* Node */}
                                    <div className="flex flex-col items-center min-w-[80px] sm:min-w-[100px]">
                                      <div
                                        className="w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-xs font-bold"
                                        style={{ background: LEVEL_COLORS[entry.lvl] || '#5a5a6e', color: '#fff' }}
                                      >
                                        {`'${entry.yr.slice(2)}`}
                                      </div>
                                      <div className="text-xs mt-1.5 font-medium text-center" style={{ color: LEVEL_COLORS[entry.lvl] || '#5a5a6e' }}>
                                        {LEVEL_LABELS[entry.lvl] || entry.lvl}
                                      </div>
                                      {entry.tm && (
                                        <div className="text-xs text-center max-w-[110px] truncate" style={{ color: colors.text.muted }}>
                                          {entry.tm}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>);
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {filteredPlayers.length > PAGE_SIZE && (
                <div
                  className="flex flex-col sm:flex-row items-center justify-between gap-2 px-3 sm:px-4 py-3 border-t"
                  style={{ borderColor: 'rgba(255,255,255,0.06)' }}
                >
                  <span
                    className="text-xs"
                    style={{ color: colors.text.muted }}
                  >
                    <span className="hidden sm:inline">Showing </span>{page * PAGE_SIZE + 1}&ndash;
                    {Math.min((page + 1) * PAGE_SIZE, filteredPlayers.length)}{' '}
                    of {filteredPlayers.length.toLocaleString()}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPage((p) => Math.max(0, p - 1))}
                      disabled={page === 0}
                      className="px-3 py-2 min-h-[44px] text-xs rounded-md transition-colors disabled:opacity-30"
                      style={{
                        color: colors.text.secondary,
                        background: colors.bg.tertiary,
                      }}
                    >
                      Prev
                    </button>
                    <span
                      className="text-xs"
                      style={{ color: colors.text.muted }}
                    >
                      {page + 1} / {totalPages}
                    </span>
                    <button
                      onClick={() =>
                        setPage((p) => Math.min(totalPages - 1, p + 1))
                      }
                      disabled={page >= totalPages - 1}
                      className="px-3 py-2 min-h-[44px] text-xs rounded-md transition-colors disabled:opacity-30"
                      style={{
                        color: colors.text.secondary,
                        background: colors.bg.tertiary,
                      }}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}

              {/* Player count summary */}
              {filteredPlayers.length <= PAGE_SIZE &&
                filteredPlayers.length > 0 && (
                  <div
                    className="px-4 py-3 border-t text-xs"
                    style={{
                      borderColor: 'rgba(255,255,255,0.06)',
                      color: colors.text.muted,
                    }}
                  >
                    {filteredPlayers.length.toLocaleString()} players
                  </div>
                )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
