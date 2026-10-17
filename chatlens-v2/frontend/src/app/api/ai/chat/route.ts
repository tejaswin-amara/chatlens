import { NextRequest, NextResponse } from 'next/server';
import {
  decodeSession,
  isDemoModeEnabled,
  ScraperSession,
} from '@/lib/session';
import {
  resolveSessionToken,
  checkRateLimitDistributed,
  getClientIP,
} from '@/lib/request-utils';
import { processAIChat, ToolExecutionContext } from '@/lib/ai/executor';
import { DEMO_SESSION } from '@/lib/fixtures';

export const dynamic = 'force-dynamic';

interface ChatMessageInput {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export async function POST(request: NextRequest) {
  const clientIP = getClientIP(request);
  const rl = await checkRateLimitDistributed(`ai-chat:${clientIP}`, 60, 60_000);
  if (!rl.allowed) {
    return NextResponse.json(
      {
        success: false,
        error: 'Rate limit exceeded. Please wait before sending more messages.',
      },
      {
        status: 429,
        headers: { 'Retry-After': String(Math.ceil(rl.resetMs / 1000)) },
      }
    );
  }

  try {
    let body: Record<string, unknown>;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { success: false, error: 'Invalid JSON payload in request body' },
        { status: 400 }
      );
    }
    const messages = body?.messages as ChatMessageInput[] | undefined;
    if (!Array.isArray(messages) || messages.length === 0) {
      return NextResponse.json(
        {
          success: false,
          error: 'Request body must contain a non-empty messages array',
        },
        { status: 400 }
      );
    }
    if (messages.length > 40) {
      return NextResponse.json(
        {
          success: false,
          error: 'Messages must contain between 1 and 40 items.',
        },
        { status: 400 }
      );
    }

    const lastMessage = messages[messages.length - 1];
    if (
      !lastMessage ||
      typeof lastMessage.content !== 'string' ||
      lastMessage.content.trim().length === 0
    ) {
      return NextResponse.json(
        {
          success: false,
          error:
            'Last message in conversation must contain valid string content',
        },
        { status: 400 }
      );
    }

    const validMessages = messages.every(
      (message) =>
        message &&
        ['user', 'assistant', 'system'].includes(message.role) &&
        typeof message.content === 'string' &&
        message.content.length > 0 &&
        message.content.length <= 8_000
    );
    if (!validMessages) {
      return NextResponse.json(
        {
          success: false,
          error:
            'Each message must contain a valid role and bounded text content.',
        },
        { status: 400 }
      );
    }

    const sessionToken =
      resolveSessionToken(request) ||
      request.headers.get('x-session-id') ||
      (typeof body.sessionId === 'string' ? body.sessionId : undefined);

    const demoMode = isDemoModeEnabled();
    let session: ScraperSession;
    if (!sessionToken) {
      if (!demoMode)
        return NextResponse.json(
          { success: false, error: 'Authentication required.' },
          { status: 401 }
        );
      session = DEMO_SESSION;
    } else {
      try {
        session = await decodeSession(sessionToken);
      } catch {
        if (demoMode) {
          session = DEMO_SESSION;
        } else {
          return NextResponse.json(
            { success: false, error: 'Session expired. Please sign in again.' },
            { status: 401 }
          );
        }
      }
    }

    const academicYear =
      (typeof body.academicYear === 'string' ? body.academicYear : undefined) ||
      request.nextUrl.searchParams.get('academicYear') ||
      '2025-2026';
    const semesterId =
      (typeof body.semesterId === 'string' ? body.semesterId : undefined) ||
      request.nextUrl.searchParams.get('semesterId') ||
      '1';
    const executionContext: ToolExecutionContext = {
      session,
      academicYear,
      semesterId,
      isDemo: demoMode && session === DEMO_SESSION,
    };
    const { assistantResponseText, toolCalls } = await processAIChat(
      messages,
      executionContext
    );

    return NextResponse.json({
      success: true,
      message: { role: 'assistant', content: assistantResponseText },
      toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
      mode: executionContext.isDemo ? 'demo' : 'live',
    });
  } catch (error) {
    console.error(
      '[AI CHAT API] Unexpected handler error:',
      error instanceof Error ? error.message : 'Unknown error'
    );
    return NextResponse.json(
      {
        success: false,
        error: 'The assistant is temporarily unavailable. Please try again.',
      },
      { status: 503 }
    );
  }
}
