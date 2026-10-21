import { Leaf, ArrowRight, CircleDot } from "lucide-react";
import { navigate } from "../api.js";
import { number } from "../utils/format.js";

export function BookCover({ book, index = 0, large = false }) {
  return (
    <div
      className={`book-cover cover-${index % 5} ${large ? "large" : ""}`}
      aria-hidden="true"
    >
      <Leaf size={large ? 30 : 20} />
      <span>{book.title}</span>
      <small>BOOKLEAF PUBLISHING</small>
    </div>
  );
}

export function BookCard({ book, index }) {
  return (
    <button
      className="book-card"
      onClick={() => navigate(`books/${book.book_id}`)}
    >
      <BookCover book={book} index={index} />
      <div className="book-card-info">
        <span className="eyebrow">{book.genre}</span>
        <h3>{book.title}</h3>
        <span
          className={`book-stage ${book.status.includes("Production") ? "production" : ""}`}
        >
          <CircleDot size={12} />
          {book.status}
        </span>
        <div className="book-card-bottom">
          <span>
            {number(book.total_copies_sold)} <small>copies sold</small>
          </span>
          <ArrowRight size={18} />
        </div>
      </div>
    </button>
  );
}
