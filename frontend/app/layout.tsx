import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000'),
  title: 'GlyphForge — Shape-aware ASCII Art Lab',
  description: '自然言語や参照画像から、形状を保ったASCII Art / AAを生成・最適化するローカルラボ。',
  openGraph: {
    title: 'GlyphForge — Shape-aware ASCII Art Lab',
    description: '自然言語や参照画像から、文字の形でASCII Artを再構築・最適化。',
    images: [{ url: '/og.png', width: 1200, height: 630, alt: 'GlyphForge social preview' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'GlyphForge — Shape-aware ASCII Art Lab',
    description: '自然言語や参照画像から、文字の形でASCII Artを再構築・最適化。',
    images: ['/og.png'],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
