import { Menu, Search } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router'

import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'
import { ROUTES } from '@/core/constants'

import { pageTitle } from './nav-items'
import { Sidebar } from './Sidebar'

/** Signed-in layout: sidebar, top bar with breadcrumb and search, page content. */
export function AppShell() {
  const location = useLocation()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [query, setQuery] = useState('')

  const onSearch = (event: FormEvent) => {
    event.preventDefault()
    const trimmed = query.trim()
    if (!trimmed) return
    navigate(`${ROUTES.search}?q=${encodeURIComponent(trimmed)}`)
    setQuery('')
  }

  return (
    <div className="min-h-screen md:grid md:grid-cols-[215px_minmax(0,1fr)] lg:grid-cols-[248px_minmax(0,1fr)]">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-card focus:px-3 focus:py-2"
      >
        Skip to content
      </a>

      <aside className="sticky top-0 hidden h-screen border-r bg-sidebar md:block">
        <Sidebar />
      </aside>

      <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
        <SheetContent side="left" className="w-[260px] p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <Sidebar onNavigate={() => setMenuOpen(false)} />
        </SheetContent>
      </Sheet>

      <main
        id="main"
        className="min-w-0 px-4 pt-5 pb-9 md:px-6 md:pt-6 lg:px-[clamp(22px,4vw,58px)] lg:pt-[27px] lg:pb-12"
      >
        <header className="mb-[27px] flex items-center justify-between gap-4 lg:mb-[38px]">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Button
              variant="outline"
              size="icon"
              className="md:hidden"
              aria-label="Open menu"
              onClick={() => setMenuOpen(true)}
            >
              <Menu />
            </Button>
            <span className="hidden sm:inline">Workspace&nbsp; / &nbsp;</span>
            <b className="font-semibold text-[#3c4555]">{pageTitle(location.pathname)}</b>
          </div>
          <form onSubmit={onSearch} role="search">
            <label className="flex w-[min(42vw,220px)] items-center gap-[9px] rounded-[10px] border bg-card px-3 py-2.5 text-subtle focus-within:border-ring/60">
              <Search className="size-4 shrink-0" aria-hidden />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search your shelf..."
                aria-label="Search your documents"
                className="w-full bg-transparent text-xs text-foreground outline-none"
              />
            </label>
          </form>
        </header>
        <Outlet />
      </main>
    </div>
  )
}
