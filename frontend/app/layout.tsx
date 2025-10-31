import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AI Trading Monitor',
  description: 'Real-time AI cryptocurrency trading monitor',
  other: {
    'google-adsense-account': 'ca-pub-1893548939873847',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

