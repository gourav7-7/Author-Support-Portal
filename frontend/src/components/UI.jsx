import { Leaf, AlertCircle, RefreshCw, Inbox, X } from "lucide-react";
import { cls } from "../utils/format.js";

export function Badge({ value, priority = false }) {
  return (
    <span className={`badge ${priority ? "priority" : ""} ${cls(value)}`}>
      {priority && <span className="priority-dot" />}
      {value}
    </span>
  );
}

export function Notice({ children, kind = "error", onClose }) {
  return children ? (
    <div
      className={`notice ${kind}`}
      role={kind === "error" ? "alert" : "status"}
    >
      <AlertCircle size={17} />
      <span>{children}</span>
      {onClose && (
        <button className="icon-button" onClick={onClose} aria-label="Dismiss">
          <X size={16} />
        </button>
      )}
    </div>
  ) : null;
}

export function Loading() {
  return (
    <div className="loading" role="status">
      <RefreshCw size={19} className="spin" /> Loading your workspace…
    </div>
  );
}

export function Empty({ title, text, action }) {
  return (
    <div className="empty">
      <Inbox size={32} />
      <h3>{title}</h3>
      <p>{text}</p>
      {action}
    </div>
  );
}

export function Metric({ label, value, note, icon: Icon, tone = "" }) {
  return (
    <div className={`metric ${tone}`}>
      <span className="metric-icon">
        <Icon size={19} />
      </span>
      <span className="eyebrow">{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  );
}

export function Brand({ inverse = false }) {
  return (
    <div className={`brand ${inverse ? "inverse" : ""}`}>
      <span className="brand-mark">
        <Leaf size={24} strokeWidth={1.6} />
      </span>
      <div>
        AuthorCare<small>AUTHOR CARE</small>
      </div>
    </div>
  );
}

export function SectionTitle({ title, subtitle, children }) {
  return (
    <div className="section-title">
      <div>
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}
