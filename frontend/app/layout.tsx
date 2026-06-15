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
          <header className="flex items-center gap-6 border-b border-neutral-800 px-6 py-3">
            <Link href="/" className="font-semibold text-emerald-400">
              AI Development Studio
            </Link>
            <nav className="flex gap-4 text-sm text-neutral-400">
              <Link href="/" className="hover:text-neutral-100">
                Projects
              </Link>
              <Link href="/workspace" className="hover:text-neutral-100">
                Workspace
              </Link>
              <Link href="/dashboard" className="hover:text-neutral-100">
                Dashboard
              </Link>
            </nav>
          </header>
          <main className="flex-1 p-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
