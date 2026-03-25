export interface SankeyNode {
  id: string;
  label: string;
  count: number;
  pct?: string;
}

export interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

export interface SankeyData {
  nodes: SankeyNode[];
  links: SankeyLink[];
}

export interface ExamplePlayers {
  [key: string]: string[];
}

export interface FAQItem {
  patterns: string[];
  question: string;
  answer: string;
}

export interface FAQData {
  faqs: FAQItem[];
}

export interface ChatStatsTopic {
  keywords: string[];
  question: string;
  data: Record<string, unknown>;
  template: string;
}

export interface ChatStatsData {
  generated: string;
  total_players: number;
  counts: Record<string, number>;
  percentages: Record<string, number>;
  topics: Record<string, ChatStatsTopic>;
}

export type ViewLevel = 'level1' | 'nba' | 'gleague' | 'europe' | 'other_intl';

export interface EuropeCountryData {
  nodes: SankeyNode[];
  links: SankeyLink[];
}
