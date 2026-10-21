import { BookOpen, Clock3 } from "lucide-react";
import { navigate } from "../api.js";
import { date, ageHours, age } from "../utils/format.js";
import { Badge } from "./UI.jsx";

export function TicketTable({ items, admin = false }) {
  return (
    <div className="ticket-table">
      <div className={`ticket-table-head ${admin ? "admin" : ""}`}>
        <span>CONVERSATION</span>
        {admin && <span>AUTHOR / CATEGORY</span>}
        <span>PRIORITY & STATUS</span>
        <span>OPENED</span>
      </div>
      {items.map((ticket) => (
        <button
          className={`ticket-row ${admin ? "admin" : ""}`}
          key={ticket.id}
          onClick={() => navigate(`tickets/${ticket.id}`)}
        >
          <div>
            <span className="ticket-reference">{ticket.reference}</span>
            <strong>{ticket.subject}</strong>
            <small>
              <BookOpen size={12} />
              {ticket.book_title || "General / Account Level"}
            </small>
          </div>
          {admin && (
            <div>
              <span>{ticket.author.name}</span>
              <small>{ticket.category}</small>
              {ticket.triage_status === "pending" && (
                <small className="amber">Triage in progress</small>
              )}
            </div>
          )}
          <div className="row-badges">
            <Badge value={ticket.priority} priority />
            <Badge value={ticket.status} />
          </div>
          <div>
            <span>{age(ticket.created_at)}</span>
            <small>{date(ticket.created_at)}</small>
            {["Open", "In Progress"].includes(ticket.status) &&
              ageHours(ticket.created_at) > 48 && (
                <small className="amber">
                  <Clock3 size={12} />
                  Waiting &gt;48h
                </small>
              )}
          </div>
        </button>
      ))}
    </div>
  );
}
