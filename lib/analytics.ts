// Google Analytics event tracking
// All events are sent to GA4 via gtag

declare global {
  interface Window {
    gtag?: (...args: any[]) => void;
  }
}

function track(eventName: string, params?: Record<string, string | number | boolean>) {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', eventName, params);
  }
}

// === Sankey Diagram Events ===

/** User clicks into a category (NBA, G-League, Europe, etc.) */
export function trackCategoryClick(category: string) {
  track('category_click', { category });
}

/** User clicks back to Level 1 */
export function trackBackToOverview() {
  track('back_to_overview');
}

/** User hovers a flow band (shows tooltip) */
export function trackFlowHover(category: string, subcategory: string) {
  track('flow_hover', { category, subcategory });
}

// === Chat Events ===

/** User submits a chat question */
export function trackChatQuestion(question: string) {
  track('chat_question', {
    question: question.substring(0, 100), // Truncate for GA
  });
}

/** Chat response received */
export function trackChatResponse(question: string, success: boolean) {
  track('chat_response', {
    question: question.substring(0, 100),
    success,
  });
}

// === Player Table Events ===

/** User opens/closes View All Player Data */
export function trackPlayerTableToggle(open: boolean) {
  track('player_table_toggle', { action: open ? 'open' : 'close' });
}

/** User switches year tab */
export function trackYearTabClick(year: string | number) {
  track('year_tab_click', { year: String(year) });
}

/** User searches for a player */
export function trackPlayerSearch(query: string) {
  track('player_search', { query: query.substring(0, 50) });
}

/** User expands a player row to see timeline */
export function trackPlayerExpand(playerName: string) {
  track('player_expand', { player: playerName });
}

/** User changes destination filter */
export function trackDestinationFilter(filter: string) {
  track('destination_filter', { filter });
}

// === Scroll / Engagement Events ===

/** User scrolls to the diagram */
export function trackDiagramView() {
  track('diagram_view');
}

/** User scrolls to the player table */
export function trackPlayerTableView() {
  track('player_table_view');
}
