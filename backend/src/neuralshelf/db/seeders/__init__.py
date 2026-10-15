"""Development seed data: python -m neuralshelf.cli db:seed

Seeders are idempotent: running them again skips anything that already
exists. They refuse to run in production, because they create accounts
with well-known passwords.
"""

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from neuralshelf.core.security import hash_password
from neuralshelf.db.seeders.sample_pdf import make_pdf
from neuralshelf.features.documents.models import Document
from neuralshelf.features.documents.service import DocumentService
from neuralshelf.features.documents.storage import get_file_storage
from neuralshelf.features.users.models import User
from neuralshelf.features.users.repository import UserRepository


@dataclass(frozen=True)
class SeedAccount:
    name: str
    email: str
    password: str
    is_admin: bool


ADMIN = SeedAccount("Admin", "admin@neuralshelf.local", "Admin!12345", is_admin=True)
DEMO = SeedAccount("Demo User", "demo@neuralshelf.local", "Demo!12345", is_admin=False)

SAMPLE_FILENAME = "welcome-to-neuralshelf.pdf"
SAMPLE_PAGES = [
    "Welcome to NeuralShelf. Upload PDF documents and ask questions about them. "
    "Answers cite the document and page they came from.",
    "Photosynthesis takes place in the chloroplasts of plant cells. Chlorophyll absorbs "
    "sunlight, and the plant turns water and carbon dioxide into glucose and oxygen.",
    "The French Revolution began in 1789 with the storming of the Bastille in Paris.",
]


def seed_account(db: Session, account: SeedAccount) -> User:
    repository = UserRepository(db)
    user = repository.get_by_email(account.email)
    if user is not None:
        print(f"  = user {account.email} already exists")
        return user

    user = repository.create(
        name=account.name,
        email=account.email,
        password_hash=hash_password(account.password),
    )
    repository.set_admin(user, is_admin=account.is_admin)
    db.commit()
    role = "admin" if account.is_admin else "user"
    print(f"  + {role} {account.email} / {account.password}")
    return user


def seed_sample_document(db: Session, owner: User) -> None:
    """Upload a sample PDF for ``owner``; the worker indexes it like any upload."""
    exists = db.scalar(
        select(Document.id).where(
            Document.user_id == owner.id, Document.filename == SAMPLE_FILENAME
        )
    )
    if exists:
        print(f"  = sample document for {owner.email} already exists")
        return

    DocumentService(db, get_file_storage()).upload(
        user_id=owner.id,
        filename=SAMPLE_FILENAME,
        content_type="application/pdf",
        data=make_pdf(SAMPLE_PAGES),
    )
    print(f"  + sample document {SAMPLE_FILENAME} queued for {owner.email} (needs the worker)")


def seed_users(db: Session) -> None:
    seed_account(db, ADMIN)
    seed_account(db, DEMO)


def seed_documents(db: Session) -> None:
    demo = UserRepository(db).get_by_email(DEMO.email) or seed_account(db, DEMO)
    seed_sample_document(db, demo)


# Name -> seeder, for `db:seed --only <name>`. "all" runs everything in order.
SEEDERS: dict[str, Callable[[Session], None]] = {
    "users": seed_users,
    "documents": seed_documents,
}


def seed_all(db: Session) -> None:
    for seeder in SEEDERS.values():
        seeder(db)
