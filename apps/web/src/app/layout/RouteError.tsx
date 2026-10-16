import { isRouteErrorResponse, Link, useRouteError } from 'react-router'

import { Button } from '@/components/ui/button'

/** Shown when a page fails to load (e.g. a lazy chunk after a deploy) or throws. */
export function RouteError() {
  const error = useRouteError()
  const chunkFailed = error instanceof TypeError && /fetch|import/i.test(error.message)
  console.error(error)
  return (
    <div className="grid min-h-screen place-items-center p-6 text-center">
      <div>
        <h1 className="text-lg font-semibold">
          {isRouteErrorResponse(error) ? `${error.status} ${error.statusText}` : 'Something went wrong'}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {chunkFailed ? 'A new version of NeuralShelf is available.' : 'This page could not be displayed.'}
        </p>
        <div className="mt-5 flex justify-center gap-2">
          <Button onClick={() => window.location.reload()}>Reload</Button>
          <Button variant="outline" asChild>
            <Link to="/">Go to overview</Link>
          </Button>
        </div>
      </div>
    </div>
  )
}
