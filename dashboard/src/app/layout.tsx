import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'CareerPilot AI - Mission Control Dashboard',
  description: 'AI-Powered Autonomous Job Application & ATS Tailoring Tracking System',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="light">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-background text-on-background antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
