import { useState } from "react";
import {
  MessagesSquare,
  ArrowRight,
  ArrowLeft,
  Check,
} from "lucide-react";
import { api, useResource, navigate, uploadAttachment } from "../api.js";
import { Notice } from "../components/UI.jsx";
import { AttachmentPicker } from "../components/Attachments.jsx";

export function NewTicket({ selectedBook }) {
  const books = useResource("/books", false);
  const [bookId, setBookId] = useState(selectedBook || "");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  const [createdTicket, setCreatedTicket] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    let ticket = createdTicket;
    try {
      if (!ticket) {
        ticket = await api("/tickets", {
          method: "POST",
          body: { book_id: bookId || null, subject, description },
        });
        setCreatedTicket(ticket);
      }
      if (file) await uploadAttachment(ticket.id, file);
      navigate(`tickets/${ticket.id}`);
    } catch (err) {
      setError(ticket ? `Your ticket was saved, but the attachment could not be uploaded. ${err.message} Retry the upload or open your saved ticket.` : err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <button className="back-button" onClick={() => navigate("tickets")}>
        <ArrowLeft size={16} />
        Your conversations
      </button>
      <div className="page-heading">
        <div>
          <span className="eyebrow">LET’S TALK</span>
          <h1>How can we help?</h1>
          <p>Tell us what’s on your mind. Our team will take it from here.</p>
        </div>
      </div>
      <div className="form-layout">
        <form className="panel ticket-form" onSubmit={submit}>
          <Notice>{error || books.error}</Notice>
          <label>
            Which book is this about?
            <select disabled={busy || !!createdTicket} value={bookId} onChange={(e) => setBookId(e.target.value)}>
              <option value="">General / Account Level</option>
              {books.data?.items.map((book) => (
                <option key={book.book_id} value={book.book_id}>
                  {book.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            Subject
            <input
              required
              minLength={3}
              maxLength={180}
              value={subject}
              disabled={busy || !!createdTicket}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="A short summary of your question"
            />
          </label>
          <label>
            Your query
            <textarea
              required
              minLength={10}
              maxLength={6000}
              rows={7}
              value={description}
              disabled={busy || !!createdTicket}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Share the details that will help us understand and resolve your concern…"
            />
            <span className="field-help">
              {description.length}/6,000 characters
            </span>
          </label>
          <AttachmentPicker file={file} onChange={setFile} disabled={busy} />
          <div className="form-actions">
            <button
              type="button"
              className="button secondary"
              disabled={busy}
              onClick={() => navigate(createdTicket ? `tickets/${createdTicket.id}` : "tickets")}
            >
              {createdTicket ? "Open saved ticket" : "Cancel"}
            </button>
            <button className="button primary" disabled={busy || books.loading}>
              {busy ? createdTicket ? "Uploading…" : "Submitting…" : createdTicket ? file ? "Retry attachment upload" : "Open saved ticket" : "Submit support query"}
              <ArrowRight size={17} />
            </button>
          </div>
        </form>
        <aside className="help-card">
          <MessagesSquare size={28} />
          <h3>A good conversation starts with a little context.</h3>
          <p>
            Include the book title, the affected platform or the royalty period
            where relevant.
          </p>
          <div>
            <Check size={16} />
            Only you and the support team can access your ticket.
          </div>
          <div>
            <Check size={16} />
            Replies appear automatically while you’re here.
          </div>
          <div>
            <Check size={16} />
            Our team reviews every response before sending.
          </div>
          <p className="small">
            Please don’t include passwords or full bank-account details.
          </p>
        </aside>
      </div>
    </>
  );
}
