import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'FINORA — Intelligent Financial Audit',
  description: 'A cinematic, explainable financial audit intelligence workspace.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
