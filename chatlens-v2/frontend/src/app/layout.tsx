import type { Metadata, Viewport } from 'next';
import { Inter, Outfit } from 'next/font/google';
import './globals.css';
import { ToastProvider } from '@/components/ui/toast';
import { AriaLiveRegion } from '@/components/ui/aria-live';
import { ServiceWorkerRegistration } from '@/components/ServiceWorkerRegistration';

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
  display: 'swap',
});

const outfit = Outfit({
  variable: '--font-outfit',
  subsets: ['latin'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'KL Sync — Academic Dashboard',
  description:
    'Secure, real-time access to your KL University timetable, attendance, marks and more.',
  keywords: [
    'KL University',
    'ERP',
    'timetable',
    'attendance',
    'academic dashboard',
  ],
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  themeColor: '#0b0f14',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${outfit.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/logo.webp" />
        <meta name="color-scheme" content="dark" />
      </head>
      <body
        className="min-h-full flex flex-col font-sans text-foreground bg-background"
        suppressHydrationWarning
      >
        <a href="#main-content" className="skip-nav">
          Skip to content
        </a>
        <AriaLiveRegion>
          <ToastProvider>{children}</ToastProvider>
        </AriaLiveRegion>
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}
