import { NextResponse } from 'next/server';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

// Don't cache across hot reloads in dev
let statsContext: string | null = null;
if (process.env.NODE_ENV === 'development') statsContext = null;

function getStatsContext(): string {
  if (statsContext) return statsContext;

  // Try the comprehensive context file first, then fall back to chat-stats.json
  const contextCandidates = [
    join(process.cwd(), 'public', 'data', 'chat-context.txt'),
    '/Users/rjb/Desktop/Hoop Research/d1-basketball-outcomes/website/public/data/chat-context.txt',
  ];

  for (const p of contextCandidates) {
    if (existsSync(p)) {
      try {
        statsContext = readFileSync(p, 'utf-8');
        return statsContext;
      } catch {}
    }
  }

  // Fallback to chat-stats.json
  const jsonCandidates = [
    join(process.cwd(), 'public', 'data', 'chat-stats.json'),
    '/Users/rjb/Desktop/Hoop Research/d1-basketball-outcomes/website/public/data/chat-stats.json',
  ];

  for (const p of jsonCandidates) {
    if (existsSync(p)) {
      try {
        const data = JSON.parse(readFileSync(p, 'utf-8'));
        const lines: string[] = [];
        const topics = data.topics;
        if (typeof topics === 'object' && !Array.isArray(topics)) {
          for (const [key, topic] of Object.entries(topics)) {
            const t = topic as any;
            lines.push(`## ${t.question || key}`);
            lines.push(t.template || '');
            lines.push('');
          }
        }
        statsContext = lines.join('\n');
        return statsContext;
      } catch {}
    }
  }

  statsContext = 'No stats data available.';
  return statsContext;
}

export async function POST(req: Request) {
  try {
    const { message } = await req.json();

    if (!message || typeof message !== 'string') {
      return NextResponse.json({ error: 'Missing message' }, { status: 400 });
    }

    const apiKey = process.env.GROQ_API_KEY;
    if (!apiKey) {
      return NextResponse.json({ answer: 'Chat API not configured. Please add GROQ_API_KEY to .env.local.' });
    }

    const context = getStatsContext();

    // Truncate context if too long for Groq (keep under ~25K chars)
    const maxContext = 90000;
    const trimmedContext = context.length > maxContext
      ? context.substring(0, maxContext) + '\n\n[... additional data truncated for length]'
      : context;

    // Delay to avoid rate limits on Groq free tier
    await new Promise(r => setTimeout(r, 1000));

    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'llama-3.3-70b-versatile',
        messages: [
          {
            role: 'system',
            content: `You are a data assistant for aftercollegeball.xyz — a site tracking what happens to NCAA D1 men's basketball players after college. You have data on 18,688 players from 2015-2025.

RULES:
- Answer concisely (2-3 sentences max)
- Use specific numbers from the data below
- If the data doesn't cover the question, say "I don't have individual player-level data for that, but here's what I know about the group..." and give relevant aggregate stats
- Never make up data or player names
- You know aggregate stats (averages, percentages, counts) but NOT individual player stats or rankings

KEY FACTS:
- 18,688 total D1 players tracked (2015-2025)
- NBA: 816 (4.4%) — avg 14.8 PPG in college
- G-League: 1,065 (5.7%) — avg 12.1 PPG in college
- Europe: 2,073 (11.1%) — avg 10.3 PPG in college
- Other International: 3,168 (17.0%) — avg 9.5 PPG in college
- No Pro Career: 11,566 (61.9%) — avg 4.8 PPG in college
- Top NBA schools: Kentucky (41), Duke (40), Arizona (20), Kansas (19), Gonzaga (17)
- G-League to NBA: only 48 players (4.5% of G-Leaguers)
- Average G-League career before going overseas: 1.4 years
- 60% of G-League players go international after
- Only 1 in 22 D1 players made the NBA

DETAILED DATA:
${trimmedContext}`
          },
          {
            role: 'user',
            content: message,
          },
        ],
        temperature: 0.3,
        max_tokens: 300,
      }),
    });

    if (!response.ok) {
      const err = await response.text();
      console.error('Groq API error:', response.status, err);
      return NextResponse.json({ answer: 'Sorry, the AI service is temporarily unavailable. Please try again.' });
    }

    const result = await response.json();
    const answer = result.choices?.[0]?.message?.content || 'Sorry, I couldn\'t generate a response.';

    return NextResponse.json({ answer });
  } catch (e) {
    console.error('Chat API error:', e);
    return NextResponse.json({ answer: 'Something went wrong. Please try again.' });
  }
}
