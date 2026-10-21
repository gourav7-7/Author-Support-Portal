import { useEffect, useState } from "react";
import {
  MessagesSquare,
  Plus,
  Search,
  Clock3,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Inbox,
} from "lucide-react";
import { useResource, navigate } from "../api.js";
import { date } from "../utils/format.js";
import {
  Notice,
  Loading,
  Empty,
  Metric,
  SectionTitle,
} from "../components/UI.jsx";
import { TicketTable } from "../components/TicketTable.jsx";

export function TicketsPage({ admin, meta }) {
  const [filters, setFilters] = useState({
    status: "",
    category: "",
    priority: "",
    q: "",
    date_from: "",
    date_to: "",
    assignment: "",
  });
  const [page, setPage] = useState(1);
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(filters.q), 300);
    return () => clearTimeout(timer);
  }, [filters.q]);
  const params = new URLSearchParams({ page: String(page), page_size: "15" });
  Object.entries(filters).forEach(([key, value]) => {
    if (value && key !== "q") params.set(key, value);
  });
  if (debounced) params.set("q", debounced);
  const tickets = useResource(`${admin ? "/admin" : ""}/tickets?${params}`);
  const overview = useResource(admin ? "/admin/overview" : null);
  const change = (key, value) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setPage(1);
  };
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">
            {admin ? "OPERATIONS WORKSPACE" : "YOUR SUPPORT SPACE"}
          </span>
          <h1>{admin ? "Every query, in good hands." : "My tickets"}</h1>
          <p>
            {admin
              ? "Prioritise the right conversations. Give every author a clear next step."
              : "Stay close to the progress of every conversation."}
          </p>
        </div>
        {!admin && (
          <button className="button primary" onClick={() => navigate("new")}>
            <Plus size={17} />
            New support query
          </button>
        )}
      </div>
      {admin && overview.data && (
        <div className="metrics">
          <Metric
            label="Open tickets"
            value={overview.data.counts.Open}
            note="Ready for your attention"
            icon={Inbox}
          />
          <Metric
            label="In progress"
            value={overview.data.counts["In Progress"]}
            note="Conversations moving forward"
            icon={MessagesSquare}
          />
          <Metric
            label="High & critical"
            value={overview.data.urgent}
            note="Unresolved priority tickets"
            icon={AlertCircle}
            tone="highlight"
          />
          <Metric
            label="Waiting over 48h"
            value={overview.data.waiting_over_48h}
            note="Oldest unresolved conversations"
            icon={Clock3}
          />
        </div>
      )}
      <Notice>{tickets.error || overview.error}</Notice>
      <div className="section-block">
        <SectionTitle
          title={admin ? "Support queue" : "All conversations"}
          subtitle={
            admin
              ? "Unresolved first, then priority and oldest creation time."
              : "Replies and status changes update automatically."
          }
        >
          <span className="live-label">
            <span />
            Live updates · 5s
          </span>
        </SectionTitle>
        <div className="filters">
          <label>
            <span className="filter-label">Status</span>
            <select
              value={filters.status}
              onChange={(e) => change("status", e.target.value)}
            >
              <option value="">All statuses</option>
              {meta?.statuses.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          {admin && (
            <>
              <label>
                <span className="filter-label">Category</span>
                <select
                  value={filters.category}
                  onChange={(e) => change("category", e.target.value)}
                >
                  <option value="">All categories</option>
                  {meta?.categories.map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
              <label>
                <span className="filter-label">Priority</span>
                <select
                  value={filters.priority}
                  onChange={(e) => change("priority", e.target.value)}
                >
                  <option value="">All priorities</option>
                  {meta?.priorities.map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
              <label className="search-field">
                <span className="filter-label">Search</span>
                <span>
                  <Search size={16} />
                  <input
                    value={filters.q}
                    maxLength={150}
                    onChange={(e) => change("q", e.target.value)}
                    placeholder="Author, book or query"
                  />
                </span>
              </label>
              <label>
                <span className="filter-label">From (UTC)</span>
                <input
                  type="date"
                  value={filters.date_from}
                  onChange={(e) => change("date_from", e.target.value)}
                />
              </label>
              <label>
                <span className="filter-label">To (UTC)</span>
                <input
                  type="date"
                  value={filters.date_to}
                  onChange={(e) => change("date_to", e.target.value)}
                />
              </label>
              <label>
                <span className="filter-label">Assignment</span>
                <select
                  value={filters.assignment}
                  onChange={(e) => change("assignment", e.target.value)}
                >
                  <option value="">Everyone</option>
                  <option value="mine">Assigned to me</option>
                  <option value="unassigned">Unassigned</option>
                </select>
              </label>
            </>
          )}
          <button
            className="text-button reset-filters"
            onClick={() => {
              setFilters({
                status: "",
                category: "",
                priority: "",
                q: "",
                date_from: "",
                date_to: "",
                assignment: "",
              });
              setPage(1);
            }}
          >
            Reset
          </button>
        </div>
        {tickets.loading && !tickets.data ? (
          <Loading />
        ) : tickets.data?.items.length ? (
          <TicketTable items={tickets.data.items} admin={admin} />
        ) : (
          <Empty
            title="No tickets here yet"
            text={
              admin
                ? "New author queries will arrive here. Try another filter, or sign in as an author to create a ticket."
                : "Raise a query to start a conversation with the BookLeaf team."
            }
          />
        )}
        {tickets.data && (
          <div className="pagination">
            <span>
              {tickets.data.total} ticket{tickets.data.total === 1 ? "" : "s"} ·
              Page {page} of {Math.max(1, Math.ceil(tickets.data.total / 15))}
            </span>
            <div>
              <button
                className="icon-button"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                aria-label="Previous page"
              >
                <ChevronLeft size={18} />
              </button>
              <button
                className="icon-button"
                disabled={page * 15 >= tickets.data.total}
                onClick={() => setPage((p) => p + 1)}
                aria-label="Next page"
              >
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
