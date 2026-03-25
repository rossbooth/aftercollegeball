export const colors = {
  bg: {
    primary: '#0a0a12',
    secondary: '#10101c',
    tertiary: '#161628',
    hover: '#1c1c34',
  },
  buckets: {
    nba: '#6cb4ee',       // light blue
    gleague: '#a78bfa',   // soft purple
    europe: '#4ade80',    // green
    other_intl: '#f9a857', // warm amber
    nopro: '#52526e',
    // Legacy
    international: '#4ade80',
  },
  bucketLinks: {
    nba: '#6cb4ee',
    gleague: '#a78bfa',
    europe: '#4ade80',
    other_intl: '#f9a857',
    nopro: '#52526e',
    international: '#4ade80',
  },
  bucketLinksHover: {
    nba: '#8ec8ff',
    gleague: '#c4a6ff',
    europe: '#6ef5a0',
    other_intl: '#ffbd70',
    nopro: '#6b6b80',
    international: '#6ef5a0',
  },
  glow: {
    nba: 'rgba(108, 180, 238, 0.25)',
    gleague: 'rgba(167, 139, 250, 0.25)',
    europe: 'rgba(74, 222, 128, 0.25)',
    other_intl: 'rgba(249, 168, 87, 0.25)',
  },
  text: {
    primary: '#e2e4f0',
    secondary: '#8e90a8',
    muted: '#52526e',
  },
  accent: '#6cb4ee',
} as const;

export type BucketKey = keyof typeof colors.buckets;

export const bucketLabels: Record<string, string> = {
  nba: 'NBA',
  gleague: 'NBA G-League',
  europe: 'Europe Leagues',
  other_intl: 'Other International Leagues',
  nopro: 'No Pro Career',
  international: 'International League',
};
