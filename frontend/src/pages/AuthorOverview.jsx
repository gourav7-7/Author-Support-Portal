import {
  Leaf,
  LayoutDashboard,
  BookOpen,
  Plus,
  ArrowRight,
  Clock3,
  IndianRupee,
} from "lucide-react";
import { useResource, navigate } from "../api.js";
import { money, number } from "../utils/format.js";
import {
  Notice,
  Loading,
  Empty,
  Metric,
  SectionTitle,
} from "../components/UI.jsx";
import { BookCard } from "../components/BookCard.jsx";
import { TicketTable } from "../components/TicketTable.jsx";

export function AuthorOverview({ user }) {
  const books = useResource("/books");
  const tickets = useResource("/tickets?page_size=5");
  if (!books.data)
    return books.error ? <Notice>{books.error}</Notice> : <Loading />;
  const items = books.data.items;
  const sum = (key) =>
    items.reduce((total, book) => total + (book[key] || 0), 0);
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">YOUR AUTHOR WORKSPACE</span>
          <h1>Hello, {user.name.split(" ")[0]}.</h1>
          <p>Every chapter, every question. We’re here for you.</p>
        </div>
        <button className="button primary" onClick={() => navigate("new")}>
          <Plus size={17} />
          Raise a support query
        </button>
      </div>
      <Notice>{books.error || tickets.error}</Notice>
      <div className="metrics">
        <Metric
          label="Your books"
          value={items.length}
          note={`${items.filter((b) => b.status === "Published & Live").length} published and live`}
          icon={BookOpen}
        />
        <Metric
          label="Copies sold"
          value={number(sum("total_copies_sold"))}
          note="Across your recorded titles"
          icon={LayoutDashboard}
        />
        <Metric
          label="Royalty earned"
          value={money(sum("total_royalty_earned"))}
          note="Lifetime recorded earnings"
          icon={IndianRupee}
        />
        <Metric
          label="Royalty pending"
          value={money(sum("royalty_pending"))}
          note="Subject to payout policy"
          icon={Clock3}
          tone="highlight"
        />
      </div>
      <div className="section-block">
        <SectionTitle
          title="On your bookshelf"
          subtitle="Your words, out in the world."
        >
          <button className="text-button" onClick={() => navigate("books")}>
            View all books <ArrowRight size={16} />
          </button>
        </SectionTitle>
        <div className="books-grid">
          {items.slice(0, 3).map((b, i) => (
            <BookCard key={b.book_id} book={b} index={i} />
          ))}
        </div>
      </div>
      <div className="section-block">
        <SectionTitle
          title="Your conversations"
          subtitle="Follow the progress of your support requests."
        >
          <button className="text-button" onClick={() => navigate("tickets")}>
            All tickets <ArrowRight size={16} />
          </button>
        </SectionTitle>
        {tickets.data?.items.length ? (
          <TicketTable items={tickets.data.items} />
        ) : (
          <Empty
            title="A fresh page"
            text="Your support conversations will appear here. Raise a query whenever you need a hand."
            action={
              <button
                className="button secondary"
                onClick={() => navigate("new")}
              >
                Start a conversation <ArrowRight size={16} />
              </button>
            }
          />
        )}
      </div>
      <div className="policy-strip">
        <Leaf size={25} />
        <div>
          <strong>A note on royalties</strong>
          <p>
            Royalties are calculated quarterly, with payouts within 45 days
            after quarter end. Balances below ₹1,000 carry forward.
          </p>
        </div>
      </div>
    </>
  );
}
