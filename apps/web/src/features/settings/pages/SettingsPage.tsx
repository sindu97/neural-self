import { LogOut, ShieldCheck, UserRound } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/button'
import { ROUTES } from '@/core/constants'
import { useAuth, useCurrentUser } from '@/features/auth'
import { initials } from '@/lib/format'

/** Settings: profile details and signing out. */
export default function SettingsPage() {
  const user = useCurrentUser()
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [signingOut, setSigningOut] = useState(false)

  return (
    <>
      <PageHeader eyebrow="Manage" title="Settings" description="Your account and session." />

      <div className="grid max-w-3xl gap-5">
        <section className="rounded-[15px] border bg-card p-6">
          <SectionTitle icon={UserRound} title="Profile" />
          <div className="flex items-center gap-4">
            <div className="grid size-14 place-items-center rounded-full bg-[#fce5d6] text-base font-bold text-[#9b5a34]">
              {initials(user.name)}
            </div>
            <div>
              <div className="text-sm font-semibold">{user.name}</div>
              <div className="text-xs text-muted-foreground">{user.email}</div>
              <span className="mt-2 inline-block rounded-[7px] bg-accent px-2 py-1 text-[10px] font-bold text-primary">
                {user.is_admin ? 'Administrator' : 'Member'}
              </span>
            </div>
          </div>
          <p className="mt-5 text-xs text-muted-foreground">
            Editing your name and email isn't available yet.
          </p>
        </section>

        <section className="rounded-[15px] border bg-card p-6">
          <SectionTitle icon={ShieldCheck} title="Session" />
          <p className="text-xs leading-relaxed text-muted-foreground">
            Your sign-in is kept in a secure, HTTP-only cookie that scripts on the page cannot read, and
            refreshes automatically for up to 7 days. Signing out ends this session on the server.
          </p>
          <Button
            variant="destructive"
            className="mt-5"
            disabled={signingOut}
            onClick={async () => {
              setSigningOut(true)
              await logout()
              navigate(ROUTES.login, { replace: true })
            }}
          >
            <LogOut aria-hidden /> Sign out
          </Button>
        </section>
      </div>
    </>
  )
}

function SectionTitle({ icon: Icon, title }: { icon: typeof UserRound; title: string }) {
  return (
    <h2 className="mb-5 flex items-center gap-2 text-sm font-bold">
      <span className="grid size-7 place-items-center rounded-lg bg-accent text-primary">
        <Icon className="size-3.5" aria-hidden />
      </span>
      {title}
    </h2>
  )
}
