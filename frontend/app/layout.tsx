import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Development Studio",
  description: "Self-hosted multi-agent software engineering platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen flex-col">
          <header className="flex items-center justify-between border-b border-neutral-800 bg-neutral-950/80 px-6 py-3 backdrop-blur-sm">
            <div className="flex items-center gap-6">
              <Link href="/" className="flex items-center gap-2 font-semibold text-emerald-400">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                ADS
              </Link>
              <nav className="flex gap-5 text-sm">
                <Link
                  href="/"
                  className="text-neutral-400 transition-colors hover:text-neutral-100"
                >
                  Projects
                </Link>
                <Link
                  href="/workspace"
                  className="text-neutral-400 transition-colors hover:text-neutral-100"
                >
                  Workspace
                </Link>
                <Link
                  href="/dashboard"
                  className="text-neutral-400 transition-colors hover:text-neutral-100"
                >
                  Dashboard
                </Link>
                <Link
                  href="/dashboard/llm-config"
                  className="text-neutral-400 transition-colors hover:text-neutral-100"
                >
                  LLM Config
                </Link>
              </nav>
            </div>
            <div className="flex items-center gap-3">
              <a
                href="https://github.com/rayanmaya189-glitch/ai-studio"
                target="_blank"
                rel="noopener noreferrer"
                className="text-neutral-500 transition-colors hover:text-neutral-300"
                title="GitHub"
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                </svg>
              </a>
            </div>
          </header>
          <main className="flex-1 p-6">{children}</main>
        </div>
      </body>
    </html>
  );
}