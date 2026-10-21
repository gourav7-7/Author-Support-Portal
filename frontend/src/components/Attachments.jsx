import { useState } from "react";
import { Paperclip, Download, X } from "lucide-react";
import { downloadAttachment, uploadAttachment } from "../api.js";
import { Notice, SectionTitle } from "./UI.jsx";

export function AttachmentPicker({ file, onChange, disabled = false }) {
  const [error, setError] = useState("");
  function choose(event) {
    const selected = event.target.files[0];
    event.target.value = "";
    setError("");
    if (!selected) return;
    if (!/\.(png|jpe?g|pdf)$/i.test(selected.name)) {
      setError("Choose a PNG, JPEG or PDF file.");
      return;
    }
    if (!selected.size || selected.size > 5 * 1024 * 1024) {
      setError("Choose a nonempty file up to 5 MiB.");
      return;
    }
    onChange(selected);
  }
  return <div className="attachment-box">
    <Paperclip size={20} />
    <div>
      <strong>Supporting attachment</strong>
      <p>PNG, JPEG or PDF · up to 5 MiB per file. Visible to you and the support team.</p>
      <label className="file-button">
        Choose a file
        <input type="file" accept=".png,.jpg,.jpeg,.pdf" disabled={disabled} onChange={choose} />
      </label>
      {file && <div className="selected-attachment">
        <small>{file.name} · {(file.size / 1024).toFixed(1)} KiB</small>
        <button type="button" className="text-button" disabled={disabled} aria-label="Remove selected attachment" onClick={() => onChange(null)}><X size={15} />Remove</button>
      </div>}
      <Notice>{error}</Notice>
    </div>
  </div>;
}

export function Attachments({ ticket, onUploaded }) {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const files = ticket.attachments || [];
  async function upload() {
    if (!file || busy) return;
    setBusy("upload");
    setError("");
    try {
      await uploadAttachment(ticket.id, file);
      setFile(null);
      onUploaded();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }
  async function download(attachment) {
    setBusy(attachment.id);
    setError("");
    try {
      await downloadAttachment(ticket.id, attachment);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }
  return <section className="panel attachment-panel">
    <SectionTitle title="Supporting files" subtitle={`${files.length}/3 attachments · reviewed by the support team`} />
    <Notice>{error}</Notice>
    {files.length ? <ul className="attachment-list">{files.map(attachment => <li key={attachment.id}>
      <div><Paperclip size={17} /><span>{attachment.filename}<small>{(attachment.size_bytes / 1024).toFixed(1)} KiB</small></span></div>
      <button type="button" className="text-button" disabled={!!busy} onClick={() => download(attachment)} aria-label={`Download ${attachment.filename}`}>
        <Download size={16} />{busy === attachment.id ? "Downloading…" : "Download"}
      </button>
    </li>)}</ul> : <p className="muted">No supporting files yet.</p>}
    {ticket.status !== "Closed" && files.length < 3 && <>
      <AttachmentPicker file={file} onChange={setFile} disabled={!!busy} />
      <button type="button" className="button secondary" disabled={!file || !!busy} onClick={upload}>
        <Paperclip size={16} />{busy === "upload" ? "Uploading…" : "Upload attachment"}
      </button>
    </>}
  </section>;
}
