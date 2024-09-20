from uuid import UUID

from litestar import Litestar, delete, get, post, put
from litestar.contrib.sqlalchemy.base import UUIDBase
from litestar.contrib.sqlalchemy.plugins import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyInitPlugin,
    SQLAlchemySerializationPlugin,
)
from litestar.exceptions import HTTPException
from sqlalchemy import ForeignKey, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Author(UUIDBase):
    name: Mapped[str]
    books: Mapped[list["Book"]] = relationship(back_populates="author", lazy="selectin", cascade="all, delete")


class Book(UUIDBase):
    title: Mapped[str]
    author_id: Mapped[UUID] = mapped_column(ForeignKey("author.id"))
    author: Mapped[Author] = relationship(lazy="joined", innerjoin=True, viewonly=True)


@post(path="/authors", tags=["/authors"])
async def add_author(name: str, db_session: AsyncSession) -> Author:
    author = Author(id=None, name=name, books=[])
    db_session.add(author)
    await db_session.commit()
    await db_session.refresh(author)
    return author


@post(path="/books", tags=["/books"])
async def add_book(title: str, author_id: str, db_session: AsyncSession) -> Book | None:
    author = await db_session.get(Author, author_id)
    if not author:
        return None
    book = Book(id=None, title=title, author_id=author.id, author=author)
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    return book


@get(path="/authors", tags=["/authors"])
async def get_authors(db_session: AsyncSession) -> list[Author]:
    return list(await db_session.scalars(select(Author)))


@get(path="/books", tags=["/books"])
async def get_books(db_session: AsyncSession) -> list[Book]:
    return list(await db_session.scalars(select(Book)))


@get(path="/author", tags=["/authors"])
async def get_author(author_id: str, db_session: AsyncSession) -> Author | None:
    return await db_session.get(Author, author_id)


@get(path="/book", tags=["/books"])
async def get_book(book_id: str, db_session: AsyncSession) -> Book | None:
    return await db_session.get(Book, book_id)


@put(path="/authors", tags=["/authors"])
async def update_author(author_id: str, name: str, db_session: AsyncSession) -> Author | None:
    author = await db_session.get(Author, author_id)
    if author:
        author.name = name
        await db_session.commit()
        await db_session.refresh(author)
    return author


@put(path="/books", tags=["/books"])
async def update_book(book_id: str, title: str, db_session: AsyncSession) -> Book | None:
    book = await db_session.get(Book, book_id)
    if book:
        book.title = title
        await db_session.commit()
        await db_session.refresh(book)
    return book


@delete("/authors", tags=["/authors"])
async def delete_author(author_id: str, db_session: AsyncSession) -> None:
    author = await db_session.get(Author, author_id)
    if author is None:
        msg = "Unknown author_id"
        raise HTTPException(msg, status_code=400)
    await db_session.delete(author)
    await db_session.commit()


@delete("/books", tags=["/books"])
async def delete_book(book_id: str, db_session: AsyncSession) -> None:
    book = await db_session.get(Book, book_id)
    if book is None:
        msg = "Unknown book_id"
        raise HTTPException(msg, status_code=400)
    await db_session.delete(book)
    await db_session.commit()


sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///db.sqlite3",
    session_config=AsyncSessionConfig(expire_on_commit=False),
)


async def on_startup() -> None:
    async with sqlalchemy_config.get_engine().begin() as conn:
        await conn.run_sync(UUIDBase.metadata.create_all)


app = Litestar(
    [
        add_author,
        add_book,
        get_authors,
        get_books,
        get_author,
        get_book,
        update_author,
        update_book,
        delete_author,
        delete_book,
    ],
    on_startup=[on_startup],
    plugins=[SQLAlchemyInitPlugin(config=sqlalchemy_config), SQLAlchemySerializationPlugin()],
)
