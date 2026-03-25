import { NextResponse } from 'next/server';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

// Don't cache across hot reloads in dev
let statsContext: string | null = null;
if (process.env.NODE_ENV === 'development') statsContext = null;

function getStatsContext(): string {
  if (statsContext) return statsContext;

  // Try multiple possible paths
  const candidates = [
    join(process.cwd(), 'public', 'data', 'chat-stats.json'),
    join(process.cwd(), 'website', 'public', 'data', 'chat-stats.json'),
    '/Users/rjb/Desktop/Hoop Research/d1-basketball-outcomes/website/public/data/chat-stats.json',
  ];

  let data: any = null;
  for (const p of candidates) {
    if (existsSync(p)) {
      try {
        data = JSON.parse(readFileSync(p, 'utf-8'));
        break;
      } catch {}
    }
  }

  if (!data || !data.topics) {
    statsContext = 'No stats data available.';
    return statsContext;
  }

  const lines: string[] = [];
  const topics = data.topics;
  if (typeof topics === 'object' && !Array.isArray(topics)) {
    for (const [key, topic] of Object.entries(topics)) {
      const t = topic as any;
      lines.push(`## ${t.question || key}`);
      lines.push(t.template || '');
      lines.push('');
    }
  } else if (Array.isArray(topics)) {
    for (const topic of topics) {
      lines.push(`## ${topic.question}`);
      lines.push(topic.template);
      lines.push('');
    }
  }
  statsContext = lines.join('\n');
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
    const maxContext = 25000;
    const trimmedContext = context.length > maxContext
      ? context.substring(0, maxContext) + '\n\n[... additional data truncated for length]'
      : context;

    // Small delay to avoid rate limits on free tier
    await new Promise(r => setTimeout(r, 500));

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
            content: `You are a data assistant for a website tracking NCAA D1 men's basketball players from 2015 to present. You answer questions about where players ended up after college (NBA, G-League, Europe, Other International leagues, or no pro career).

Answer concisely using ONLY the stats below. Be specific with numbers. Keep answers to 2-3 sentences max. Do not make up data.

DATA:
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
