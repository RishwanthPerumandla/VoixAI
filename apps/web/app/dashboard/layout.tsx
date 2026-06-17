'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, ArrowUpRight, LayoutDashboard, Phone, Radio, ShoppingBag } from 'lucide-react';
import { cn } from '@/lib/shadcn/utils';

const NAV = [
  { href: '/dashboard', label: 'Overview', icon: LayoutDashboard, exact: true },
  { href: '/dashboard/calls', label: 'Call logs', icon: Phone },
  { href: '/dashboard/orders', label: 'Orders', icon: ShoppingBag },
  { href: '/dashboard/observability', label: 'Observability', icon: Activity },
];

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="dashboard-light min-h-screen bg-[var(--voix-bg-primary)] text-[var(--voix-text-primary)]">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 z-[60] hidden w-64 flex-col border-r border-[var(--voix-border-subtle)] bg-[var(--voix-sidebar-bg)] md:flex">
        <div className="flex items-center gap-2.5 px-6 py-5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--voix-accent)] text-base font-bold text-[var(--voix-accent-foreground)] shadow-sm">
            V
          </span>
          <div>
            <p className="text-sm leading-tight font-semibold">VoixAI</p>
            <p className="text-[11px] leading-tight text-[var(--voix-text-muted)]">
              Voice Agent Console
            </p>
          </div>
        </div>

        <nav className="mt-2 flex flex-1 flex-col gap-1 px-3">
          {NAV.map((item) => {
            const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition',
                  active
                    ? 'bg-[var(--voix-accent-soft)] text-[var(--voix-accent-hover)]'
                    : 'text-[var(--voix-text-muted)] hover:bg-[var(--voix-bg-subtle)] hover:text-[var(--voix-text-secondary)]'
                )}
              >
                <Icon style={{ color: active ? 'var(--voix-accent)' : undefined }} size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="m-3 rounded-xl border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] p-3">
          <Link
            href="/"
            className="flex items-center justify-between gap-2 text-xs font-medium text-[var(--voix-text-secondary)] transition hover:text-[var(--voix-text-primary)]"
          >
            <span className="flex items-center gap-2">
              <Radio size={14} style={{ color: 'var(--voix-accent)' }} />
              Open live agent
            </span>
            <ArrowUpRight size={14} />
          </Link>
        </div>
      </aside>

      {/* Topbar */}
      <header className="fixed inset-x-0 top-0 z-[55] flex h-14 items-center justify-between border-b border-[var(--voix-border-subtle)] bg-[var(--voix-topbar-bg)] px-4 backdrop-blur-md md:left-64 md:px-8">
        <div className="flex items-center gap-2 md:hidden">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--voix-accent)] text-sm font-bold text-[var(--voix-accent-foreground)]">
            V
          </span>
          <span className="text-sm font-semibold">VoixAI</span>
        </div>
        <p className="hidden text-sm text-[var(--voix-text-muted)] md:block">
          Wingstop inbound ordering · production agent
        </p>
        <div className="flex items-center gap-2 rounded-full border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] px-3 py-1.5">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--voix-success)] opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--voix-success)]" />
          </span>
          <span className="text-xs font-medium text-[var(--voix-text-secondary)]">
            Systems operational
          </span>
        </div>
      </header>

      {/* Mobile nav */}
      <nav className="fixed inset-x-0 bottom-0 z-[60] flex items-center justify-around border-t border-[var(--voix-border-subtle)] bg-[var(--voix-topbar-bg)] py-2 backdrop-blur-md md:hidden">
        {NAV.map((item) => {
          const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex flex-col items-center gap-0.5 px-3 py-1 text-[10px]"
              style={{ color: active ? 'var(--voix-accent)' : 'var(--voix-text-muted)' }}
            >
              <Icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <main className="px-4 pt-20 pb-24 md:ml-64 md:px-8 md:pb-10">{children}</main>
    </div>
  );
}
