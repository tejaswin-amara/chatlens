import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function proxy(request: NextRequest) {
  const isDashboard = request.nextUrl.pathname.startsWith('/dashboard');

  if (isDashboard) {
    const sessionCookie = request.cookies.get('kl_erp_session');
    // Reject missing and legacy/plain session cookies before the dashboard shell renders.
    if (!sessionCookie?.value || !sessionCookie.value.startsWith('enc.')) {
      return NextResponse.redirect(new URL('/', request.url));
    }
  }

  return NextResponse.next();
}

export default proxy;

export const config = {
  matcher: ['/dashboard/:path*', '/dashboard'],
};
