import { NextResponse } from 'next/server';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

// Don't cache across hot reloads in dev
let statsContext: string | null = null;
if (process.env.NODE_ENV === 'development') statsContext = null;

function getStatsContext(): string {
  if (statsContext) return statsContext;

  const candidates = [
    join(process.cwd(), 'public', 'data', 'chat-context.txt'),
    '/Users/rjb/Desktop/Hoop Research/d1-basketball-outcomes/website/public/data/chat-context.txt',
  ];

  for (const p of candidates) {
    if (existsSync(p)) {
      try {
        statsContext = readFileSync(p, 'utf-8');
        return statsContext;
      } catch {}
    }
  }

  statsContext = 'No stats data available.';
  return statsContext;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const message = body.message as string;
    const history = (body.history || []) as ChatMessage[];

    if (!message || typeof message !== 'string') {
      return NextResponse.json({ error: 'Missing message' }, { status: 400 });
    }

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return NextResponse.json({ answer: 'Chat API not configured. Please add GEMINI_API_KEY.' });
    }

    const context = getStatsContext();

    const systemPrompt = `You are a data assistant for aftercollegeball.xyz — a site tracking what happens to NCAA D1 men's basketball players after college.

RULES:
- Answer concisely (2-3 sentences max unless listing players)
- Use specific numbers from the data
- Never make up data or guess
- For player lists, include school and career length
- If someone asks about a player not in the data, say so
- Use your general basketball knowledge for questions about team locations, countries, etc. — you don't need data for common facts
- Always complete your sentences fully
- Remember the conversation context — if someone says "he" or "that team", refer back to the previous messages

DATA:
${context}`;

    // Build conversation history for Gemini
    // Gemini uses alternating user/model roles
    const contents: { role: string; parts: { text: string }[] }[] = [];

    // Include last 10 messages of history for context
    const recentHistory = history.slice(-10);
    for (const msg of recentHistory) {
      contents.push({
        role: msg.role === 'user' ? 'user' : 'model',
        parts: [{ text: msg.content }],
      });
    }

    // Add current message
    contents.push({
      role: 'user',
      parts: [{ text: message }],
    });

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          system_instruction: { parts: [{ text: systemPrompt }] },
          contents,
          generationConfig: {
            temperature: 0.3,
            maxOutputTokens: 800,
          },
        }),
      }
    );

    if (!response.ok) {
      const err = await response.text();
      console.error('Gemini API error:', response.status, err);
      return NextResponse.json({ answer: 'Sorry, the AI service is temporarily unavailable. Please try again.' });
    }

    const result = await response.json();
    const answer = result.candidates?.[0]?.content?.parts?.[0]?.text
      || 'Sorry, I couldn\'t generate a response.';

    return NextResponse.json({ answer });
  } catch (e) {
    console.error('Chat API error:', e);
    return NextResponse.json({ answer: 'Something went wrong. Please try again.' });
  }
}
