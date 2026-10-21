import { useEffect, useRef, useState } from "react";
import {
  Leaf,
  BookOpen,
  MessagesSquare,
  ArrowLeft,
  Clock3,
  Sparkles,
  Send,
  RefreshCw,
  Check,
  UserRound,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react";
import { api, useResource, navigate } from "../api.js";
import { money, when } from "../utils/format.js";
import { Badge, Notice, Loading, SectionTitle } from "../components/UI.jsx";
import { Attachments } from "../components/Attachments.jsx";

export function TicketDetail({ ticketId, user, meta }) {
  const admin = user.role === "admin";
  const base = `${admin ? "/admin" : ""}/tickets/${ticketId}`;
  const resource = useResource(base);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState("");
  const [draft, setDraft] = useState(null);
  const [draftBusy, setDraftBusy] = useState(false);
  const [reply, setReply] = useState("");
  const [note, setNote] = useState("");
  const [mode, setMode] = useState("reply");
  const initialDraftStarted = useRef(false);
  async function getDraft(force = false) {
    setDraftBusy(true);
    setError("");
    try {
      const data = await api(`${base}/draft`, {
        method: "POST",
        body: { force },
      });
      setDraft(data);
      resource.setData((current) => current ? { ...current, version: Math.max(current.version, data.version),
        draft_text: data.text, draft_source: data.source, draft_review_notes: data.review_notes,
        draft_generated_at: data.generated_at, draft_stale: current.version > data.version } : current);
      resource.refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setDraftBusy(false);
    }
  }
  useEffect(() => {
    if (
      admin &&
      resource.data &&
      resource.data.triage_status !== "pending" &&
      !initialDraftStarted.current
    ) {
      initialDraftStarted.current = true;
      getDraft();
    }
  }, [ticketId, admin, resource.data?.triage_status]);
  useEffect(() => {
    const ticket = resource.data;
    if (admin && ticket?.draft_text && !draftBusy) {
      setDraft((current) => current?.generated_at === ticket.draft_generated_at && current?.text === ticket.draft_text
        ? current : { text: ticket.draft_text, source: ticket.draft_source,
          review_notes: ticket.draft_review_notes, generated_at: ticket.draft_generated_at, cached: true });
    }
  }, [admin, draftBusy, resource.data?.draft_text, resource.data?.draft_generated_at]);
  async function update(change) {
    setBusy("update");
    setError("");
    setSuccess("");
    try {
      const data = await api(base, {
        method: "PATCH",
        body: { ...change, version: resource.data.version },
      });
      resource.setData(data);
      setSuccess("Ticket updated.");
      resource.refresh();
    } catch (err) {
      setError(err.message);
      resource.refresh();
    } finally {
      setBusy("");
    }
  }
  async function send(resolve = false) {
    const text = mode === "note" ? note : reply;
    if (!text.trim()) return;
    setBusy("send");
    setError("");
    setSuccess("");
    try {
      const data = await api(`${base}/messages`, {
        method: "POST",
        body: {
          body: text,
          kind: mode,
          resolve,
          version: resource.data.version,
        },
      });
      resource.setData(data);
      if (mode === "note") setNote("");
      else setReply("");
      setSuccess(mode === "note" ? "Internal note saved." : "Reply sent.");
      resource.refresh();
    } catch (err) {
      setError(err.message);
      resource.refresh();
    } finally {
      setBusy("");
    }
  }
  async function triage() {
    setBusy("triage");
    setError("");
    try {
      await api(`${base}/triage`, { method: "POST" });
      resource.refresh();
      setSuccess("Triage scheduled. Your manual overrides are preserved.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }
  if (!resource.data)
    return (
      <>
        <button className="back-button" onClick={() => navigate("tickets")}>
          <ArrowLeft size={16} />
          Back to tickets
        </button>
        {resource.error ? <Notice>{resource.error}</Notice> : <Loading />}
      </>
    );
  const ticket = resource.data;
  const text = mode === "note" ? note : reply;
  return (
    <>
      <button className="back-button" onClick={() => navigate("tickets")}>
        <ArrowLeft size={16} />
        {admin ? "Support queue" : "My tickets"}
      </button>
      <div className="ticket-heading">
        <div>
          <span className="eyebrow">
            {ticket.reference} ·{" "}
            {ticket.book_title || "GENERAL / ACCOUNT LEVEL"}
          </span>
          <h1>{ticket.subject}</h1>
          <p>
            {admin ? `${ticket.author.name} · ` : ""}Opened{" "}
            {when(ticket.created_at)}
          </p>
        </div>
        <div className="ticket-heading-badges">
          <Badge value={ticket.priority} priority />
          <Badge value={ticket.status} />
          <span className="live-label">
            <span />
            Updates every 5s
          </span>
        </div>
      </div>
      <Notice>{error || resource.error}</Notice>
      <Notice kind="success" onClose={() => setSuccess("")}>
        {success}
      </Notice>
      <div className="conversation-layout">
        <div className="conversation-main">
          <section className="panel conversation">
            <SectionTitle title="Conversation" />
            <article className="message original">
              <div className="message-header">
                <span className="avatar">
                  {(ticket.author?.name || user.name)[0]}
                </span>
                <div>
                  <strong>{ticket.author?.name || user.name}</strong>
                  <small>Original query · {when(ticket.created_at)}</small>
                </div>
              </div>
              <p>{ticket.description}</p>
            </article>
            {ticket.messages.map((message) => (
              <article
                key={message.id}
                className={`message ${message.kind === "note" ? "internal" : message.sender_role === "admin" ? "support" : ""}`}
              >
                <div className="message-header">
                  <span className="avatar">
                    {message.sender_role === "admin" ? (
                      <Leaf size={17} />
                    ) : (
                      message.sender_name[0]
                    )}
                  </span>
                  <div>
                    <strong>
                      {message.sender_name}
                      {message.kind === "note" && (
                        <span className="note-tag">
                          <LockKeyhole size={12} />
                          Internal note
                        </span>
                      )}
                    </strong>
                    <small>{when(message.created_at)}</small>
                  </div>
                </div>
                <p>{message.body}</p>
              </article>
            ))}
            {!ticket.messages.length && (
              <p className="awaiting">
                <Clock3 size={15} />
                {admin
                  ? "No responses yet. Review the query and prepare a reply."
                  : "Your query is with our team. Replies will appear here automatically."}
              </p>
            )}
          </section>
          <Attachments ticket={ticket} onUploaded={() => {
            resource.setData((current) => current ? { ...current, draft_stale: true } : current);
            resource.refresh();
          }} />
          {admin && (
            <section className="panel ai-panel">
              <SectionTitle
                title="A thoughtful starting point"
                subtitle="Review the facts and next steps before using this draft."
              >
                <Sparkles size={21} />
              </SectionTitle>
              <div className="ai-meta">
                <span
                  className={`badge ${draft?.source === "llm" ? "resolved" : "medium"}`}
                >
                  {draftBusy
                    ? "Preparing draft…"
                    : !draft
                      ? ticket.triage_status === "pending"
                        ? "Waiting for triage"
                        : "Draft not ready"
                      : draft.source === "llm"
                        ? "AI-generated draft"
                        : "Template fallback"}
                </span>
                {draft?.cached && <small>Saved draft reused</small>}
              </div>
              {draftBusy ? (
                <div className="draft-loading">
                  <RefreshCw className="spin" size={17} />
                  Preparing a response using the query, book data and relevant
                  policies…
                </div>
              ) : draft ? (
                <>
                  <div className="draft-preview">{draft.text}</div>
                  <div className="review-note">
                    <ShieldCheck size={16} />
                    <p>{draft.review_notes}</p>
                  </div>
                </>
              ) : (
                <p className="muted">
                  Draft unavailable. You can still write a reply below.
                </p>
              )}
              {draft && ticket.draft_stale && (
                <Notice kind="info">
                  The conversation or classification changed. Regenerate the
                  draft before using it.
                </Notice>
              )}
              <div className="ai-actions">
                <button
                  className="button secondary"
                  disabled={draftBusy || !draft || ticket.draft_stale}
                  onClick={() => {
                    if (
                      !reply.trim() ||
                      window.confirm(
                        "Replace the reply you are editing with this draft?",
                      )
                    ) {
                      setMode("reply");
                      setReply(draft.text);
                    }
                  }}
                >
                  <Check size={16} />
                  Use draft in reply
                </button>
                <button
                  className="text-button"
                  disabled={draftBusy}
                  onClick={() => getDraft(true)}
                >
                  <RefreshCw size={15} />
                  Regenerate
                </button>
              </div>
            </section>
          )}
          <section className="panel composer">
            <div className="composer-tabs">
              <button
                className={mode === "reply" ? "active" : ""}
                onClick={() => setMode("reply")}
              >
                <MessagesSquare size={16} />
                {admin ? "Reply to author" : "Add a reply"}
              </button>
              {admin && (
                <button
                  className={mode === "note" ? "active" : ""}
                  onClick={() => setMode("note")}
                >
                  <LockKeyhole size={15} />
                  Internal note
                </button>
              )}
            </div>
            {ticket.status === "Closed" ? (
              <Notice kind="info">
                This conversation is closed.{" "}
                {admin
                  ? "Change the status to reopen it."
                  : "Create a new query if you need further help."}
              </Notice>
            ) : (
              <>
                <label className="sr-only" htmlFor="message-body">
                  {mode === "note" ? "Internal note" : "Reply"}
                </label>
                <textarea
                  id="message-body"
                  maxLength={6000}
                  rows={7}
                  value={text}
                  onChange={(e) =>
                    mode === "note"
                      ? setNote(e.target.value)
                      : setReply(e.target.value)
                  }
                  placeholder={
                    mode === "note"
                      ? "Add context for the operations team. Authors cannot see this note."
                      : "Write your reply here…"
                  }
                />
                <div className="composer-footer">
                  <span>
                    {mode === "note"
                      ? "Visible only to admins"
                      : admin
                        ? "Visible to the author after sending"
                        : "Visible to the BookLeaf support team"}{" "}
                    · {text.length}/6,000
                  </span>
                  <div>
                    {admin && mode === "reply" && (
                      <button
                        className="button secondary"
                        disabled={!!busy || !text.trim()}
                        onClick={() => send(true)}
                      >
                        Send & resolve
                      </button>
                    )}
                    <button
                      className="button primary"
                      disabled={!!busy || !text.trim()}
                      onClick={() => send(false)}
                    >
                      {busy === "send"
                        ? "Saving…"
                        : mode === "note"
                          ? "Save note"
                          : "Send reply"}
                      <Send size={15} />
                    </button>
                  </div>
                </div>
              </>
            )}
          </section>
        </div>
        <aside className="ticket-sidebar">
          <section className="panel">
            <SectionTitle title="Ticket details" />
            {admin ? (
              <>
                <label>
                  Status
                  <select
                    disabled={!!busy || draftBusy}
                    value={ticket.status}
                    onChange={(e) => update({ status: e.target.value })}
                  >
                    {meta?.statuses.map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Category
                  <select
                    disabled={!!busy || draftBusy}
                    value={ticket.category}
                    onChange={(e) => update({ category: e.target.value })}
                  >
                    {meta?.categories.map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                  {ticket.category_overridden && (
                    <small className="field-help">Manually reviewed</small>
                  )}
                </label>
                <label>
                  Priority
                  <select
                    disabled={!!busy || draftBusy}
                    value={ticket.priority}
                    onChange={(e) => update({ priority: e.target.value })}
                  >
                    {meta?.priorities.map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                  {ticket.priority_overridden && (
                    <small className="field-help">Manually reviewed</small>
                  )}
                </label>
                <div className="assignment">
                  <span className="eyebrow">ASSIGNED TO</span>
                  <p>
                    <UserRound size={16} />
                    {ticket.assignee_name || "Unassigned"}
                  </p>
                  <button
                    className="button secondary full"
                    disabled={!!busy || draftBusy}
                    onClick={() =>
                      update({
                        assignment:
                          ticket.assigned_to === user.id ? "unassign" : "self",
                      })
                    }
                  >
                    {ticket.assigned_to === user.id
                      ? "Unassign"
                      : "Assign to me"}
                  </button>
                </div>
                <div className="triage-summary">
                  <span className="eyebrow">
                    {ticket.triage_source === "llm"
                      ? "AI TRIAGE"
                      : ticket.triage_status === "pending"
                        ? "TRIAGE IN PROGRESS"
                        : "RULE-BASED TRIAGE"}
                  </span>
                  <p>
                    {ticket.triage_reason ||
                      "The ticket has been saved and is awaiting classification."}
                  </p>
                  {ticket.ai_error && <small>{ticket.ai_error}</small>}
                  <button
                    className="text-button"
                    disabled={
                      !!busy || draftBusy || ticket.triage_status === "pending"
                    }
                    onClick={triage}
                  >
                    <RefreshCw size={14} />
                    Retry AI triage
                  </button>
                </div>
              </>
            ) : (
              <dl className="stacked-facts">
                <div>
                  <dt>Category</dt>
                  <dd>{ticket.category}</dd>
                </div>
                <div>
                  <dt>Priority</dt>
                  <dd>{ticket.priority}</dd>
                </div>
                <div>
                  <dt>Latest activity</dt>
                  <dd>{when(ticket.updated_at)}</dd>
                </div>
              </dl>
            )}
          </section>
          {ticket.book && (
            <section className="panel book-context">
              <BookOpen size={21} />
              <span className="eyebrow">BOOK AT A GLANCE</span>
              <h3>{ticket.book.title}</h3>
              <p>{ticket.book.status}</p>
              <dl className="stacked-facts">
                <div>
                  <dt>ISBN</dt>
                  <dd>{ticket.book.isbn}</dd>
                </div>
                <div>
                  <dt>Royalty earned</dt>
                  <dd>{money(ticket.book.total_royalty_earned)}</dd>
                </div>
                <div>
                  <dt>Royalty paid</dt>
                  <dd>{money(ticket.book.royalty_paid)}</dd>
                </div>
                <div>
                  <dt>Royalty pending</dt>
                  <dd>{money(ticket.book.royalty_pending)}</dd>
                </div>
              </dl>
            </section>
          )}
          {admin && (
            <details className="panel activity">
              <summary>Activity history</summary>
              {ticket.events
                .slice()
                .reverse()
                .map((event, i) => (
                  <div key={i}>
                    <small>
                      {when(event.created_at)} · {event.actor}
                    </small>
                    <p>{event.action}</p>
                  </div>
                ))}
            </details>
          )}
        </aside>
      </div>
    </>
  );
}
