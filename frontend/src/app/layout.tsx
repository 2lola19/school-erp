import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Providers from './providers';
import { SyncProvider } from '@/components/SyncProvider';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  manifest: '/manifest.json',
  title: 'School ERP',
  description: 'Multi-tenant School Management System',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="manifest" href="/manifest.json" />
      </head>
      <body className={inter.className}>
        <Providers>
          <SyncProvider>
            {children}
          </SyncProvider>
        </Providers>
      </body>
    </html>
  );
}