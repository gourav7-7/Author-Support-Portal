import { MessagesSquare, ArrowLeft } from "lucide-react";
import { useResource, navigate } from "../api.js";
import { money, number, date } from "../utils/format.js";
import {
  Badge,
  Notice,
  Loading,
  Empty,
  SectionTitle,
} from "../components/UI.jsx";
import { BookCover, BookCard } from "../components/BookCard.jsx";

export function BooksPage({ bookId }) {
  const resource = useResource("/books");
  if (!resource.data)
    return resource.error ? <Notice>{resource.error}</Notice> : <Loading />;
  const items = resource.data.items;
  if (bookId) {
    const book = items.find((b) => b.book_id === bookId);
    if (!book)
      return (
        <Empty
          title="Book not found"
          text="This book is not available in your account."
        />
      );
    const fields = [
      ["ISBN", book.isbn],
      ["Genre", book.genre],
      [
        "Publication date",
        book.publication_date
          ? date(book.publication_date)
          : "Not published yet",
      ],
      ["MRP", money(book.mrp)],
      ["Royalty per copy", money(book.author_royalty_per_copy)],
      ["Copies sold", number(book.total_copies_sold)],
      ["Royalty earned", money(book.total_royalty_earned)],
      ["Royalty paid", money(book.royalty_paid)],
      ["Royalty pending", money(book.royalty_pending)],
      [
        "Last payout",
        book.last_royalty_payout_date
          ? date(book.last_royalty_payout_date)
          : "No payout recorded",
      ],
      ["Print partner", book.print_partner || "Not assigned"],
      [
        "Distribution channels",
        book.available_on.join(", ") || "Not listed yet",
      ],
    ];
    return (
      <>
        <button className="back-button" onClick={() => navigate("books")}>
          <ArrowLeft size={16} />
          My books
        </button>
        <div className="book-detail">
          <BookCover book={book} index={items.indexOf(book)} large />
          <div>
            <span className="eyebrow">
              {book.book_id} · {book.genre}
            </span>
            <h1>{book.title}</h1>
            <Badge value={book.status} />
            <p className="muted">
              Publication and royalty information from your BookLeaf account.
            </p>
            <button
              className="button primary"
              onClick={() => navigate(`new?book=${book.book_id}`)}
            >
              <MessagesSquare size={17} />
              Ask about this book
            </button>
          </div>
        </div>
        <div className="panel">
          <SectionTitle title="Book & royalty details" />
          <dl className="facts-grid">
            {fields.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </div>
        <p className="footnote">
          Recorded distribution channels do not indicate live marketplace stock.
          Royalty figures are a sample-data snapshot.
        </p>
      </>
    );
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">YOUR PUBLISHING JOURNEY</span>
          <h1>My books</h1>
          <p>Published stories and chapters still taking shape.</p>
        </div>
        <span className="count-label">{items.length} titles</span>
      </div>
      <Notice>{resource.error}</Notice>
      <div className="books-grid">
        {items.map((b, i) => (
          <BookCard key={b.book_id} book={b} index={i} />
        ))}
      </div>
    </>
  );
}
