'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { trackChatQuestion, trackChatResponse } from '@/lib/analytics';
import { colors } from '@/lib/colors';
import type { ChatStatsData, ChatStatsTopic } from '@/lib/types';

const STOP_WORDS = new Set([
  'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
  'should', 'may', 'might', 'shall', 'can', 'need', 'dare', 'ought',
  'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
  'as', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
  'between', 'out', 'off', 'over', 'under', 'again', 'further', 'then',
  'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each',
  'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
  'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
  'just', 'because', 'but', 'and', 'or', 'if', 'while', 'about', 'up',
  'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am',
  'i', 'me', 'my', 'myself', 'we', 'our', 'you', 'your', 'he', 'him',
  'she', 'her', 'it', 'its', 'they', 'them', 'their', 'tell', 'give',
  'show', 'much', 'many', 'like', 'get', 'make',
]);

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9%+\-/\s]/g, ' ')
    .split(/\s+/)
    .filter(w => w.length > 0 && !STOP_WORDS.has(w));
}

function buildNgrams(tokens: string[], maxN: number = 3): string[] {
  const ngrams: string[] = [...tokens];
  for (let n = 2; n <= maxN; n++) {
    for (let i = 0; i <= tokens.length - n; i++) {
      ngrams.push(tokens.slice(i, i + n).join(' '));
    }
  }
  return ngrams;
}

function scoreTopic(queryTokens: string[], queryNgrams: string[], topic: ChatStatsTopic): number {
  let score = 0;
  const keywords = topic.keywords;

  for (const keyword of keywords) {
    const kwTokens = tokenize(keyword);

    // Exact multi-word keyword match in query ngrams — heavily weighted
    if (kwTokens.length > 1) {
      const kwPhrase = kwTokens.join(' ');
      if (queryNgrams.includes(kwPhrase)) {
        score += 6 * kwTokens.length;
        continue;
      }
    }

    // Single keyword token matches
    for (const kwToken of kwTokens) {
      for (const qt of queryTokens) {
        if (qt === kwToken) {
          score += 3;
        } else if (qt.includes(kwToken) || kwToken.includes(qt)) {
          score += 1.5;
        }
      }
    }
  }

  // Bonus: question text overlap
  const questionTokens = tokenize(topic.question);
  for (const qt of queryTokens) {
    if (questionTokens.includes(qt)) {
      score += 0.5;
    }
  }

  return score;
}

function matchStats(query: string, data: ChatStatsData): string {
  const queryTokens = tokenize(query);
  if (queryTokens.length === 0) {
    return "Try asking about player stats, school rankings, career transitions, or pro destinations!";
  }

  const queryNgrams = buildNgrams(queryTokens);

  const scored: { key: string; topic: ChatStatsTopic; score: number }[] = [];
  for (const [key, topic] of Object.entries(data.topics)) {
    const s = scoreTopic(queryTokens, queryNgrams, topic);
    if (s > 0) {
      scored.push({ key, topic, score: s });
    }
  }

  scored.sort((a, b) => b.score - a.score);

  if (scored.length === 0 || scored[0].score < 2) {
    // Suggest available topics
    const sampleTopics = Object.values(data.topics)
      .slice(0, 8)
      .map(t => t.question);
    return (
      "I couldn't find a strong match for that question. Here are some things I can answer:\n\n" +
      sampleTopics.map(q => `• ${q}`).join('\n') +
      "\n\nTry rephrasing or ask about stats, schools, conferences, careers, or destinations!"
    );
  }

  // Return the best match
  const best = scored[0];
  let response = best.topic.template;

  // If there's a close second match on a different topic, mention it
  if (scored.length > 1 && scored[1].score >= scored[0].score * 0.7) {
    const second = scored[1];
    if (second.key !== best.key) {
      response += `\n\nRelated: ${second.topic.question}`;
    }
  }

  return response;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function ChatAssistant() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [statsData, setStatsData] = useState<ChatStatsData | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch('/data/chat-stats.json')
      .then(r => r.json())
      .then(setStatsData)
      .catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = useCallback(
    async (query: string) => {
      if (!query.trim()) return;

      const trimmed = query.trim();
      const userMsg: Message = { role: 'user', content: trimmed };
      setMessages(prev => [...prev, userMsg]);
      setInput('');
      setIsTyping(true);
      trackChatQuestion(trimmed);

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: query.trim() }),
        });
        const data = await res.json();
        const answer = data.answer || data.error || 'Sorry, something went wrong.';
        setMessages(prev => [...prev, { role: 'assistant', content: answer }]);
        trackChatResponse(trimmed, true);
      } catch {
        // Fallback to local matching
        let answer: string;
        if (statsData) {
          answer = matchStats(query, statsData);
        } else {
          answer = 'Unable to connect. Please try again.';
        }
        setMessages(prev => [...prev, { role: 'assistant', content: answer }]);
        trackChatResponse(trimmed, false);
      } finally {
        setIsTyping(false);
      }
    },
    [statsData]
  );

  return (
    <section className="px-2 sm:px-6 pt-2 pb-0">
      <div className="max-w-4xl mx-auto">
        {/* Chat container */}
        <div
          className="rounded-2xl border overflow-hidden"
          style={{
            background: colors.bg.secondary,
            borderColor: 'rgba(255,255,255,0.05)',
          }}
        >
          {/* Messages */}
          {messages.length > 0 && (
            <div
              className="max-h-[300px] overflow-y-auto p-4 space-y-4"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
            >
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className="max-w-[90%] sm:max-w-[80%] px-3 sm:px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-line"
                    style={{
                      background:
                        msg.role === 'user'
                          ? 'rgba(124, 92, 252, 0.15)'
                          : 'rgba(255,255,255,0.05)',
                      color: msg.role === 'user' ? colors.text.primary : colors.text.secondary,
                    }}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
              {isTyping && (
                <div className="flex justify-start">
                  <div
                    className="px-4 py-2.5 rounded-2xl text-sm"
                    style={{ background: 'rgba(255,255,255,0.05)', color: colors.text.muted }}
                  >
                    <span className="animate-pulse">Thinking...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}

          {/* Input */}
          <div className="p-2 sm:p-3 flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  setIsOpen(true);
                  handleSubmit(input);
                }
              }}
              onFocus={() => setIsOpen(true)}
              placeholder='Ask about stats, careers, or destinations...'
              className="chat-input flex-1 bg-transparent px-3 sm:px-4 py-2.5 rounded-xl text-sm border min-w-0 w-full"
              style={{
                color: colors.text.primary,
                borderColor: 'rgba(255,255,255,0.08)',
              }}
            />
            <button
              onClick={() => {
                setIsOpen(true);
                handleSubmit(input);
              }}
              className="px-4 py-2.5 rounded-xl text-sm font-medium transition-all hover:opacity-80 flex-shrink-0 w-full sm:w-auto"
              style={{ background: '#d4a04a', color: '#fff' }}
            >
              Ask
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
