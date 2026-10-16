import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import type { DocumentItem } from '@/lib/api/types'

/** Confirmation before deleting a document. Open while `document` is set. */
export function DeleteDocumentDialog({
  document,
  onConfirm,
  onOpenChange,
}: {
  document: DocumentItem | null
  onConfirm: (document: DocumentItem) => void
  onOpenChange: (open: boolean) => void
}) {
  return (
    <AlertDialog open={document !== null} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this document?</AlertDialogTitle>
          <AlertDialogDescription>
            <strong className="text-foreground">{document?.filename}</strong> and its indexed text will be
            removed. It will no longer appear in search or new answers. This can't be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            className="bg-destructive text-white hover:bg-destructive/90"
            onClick={() => document && onConfirm(document)}
          >
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
