import { useCallback, useEffect, useState } from "react";

export async function api(path, options = {}) {
  const token = sessionStorage.getItem("bookleaf.token");
  const { rawBody, responseType, ...requestOptions } = options;
  let response;
  try {
    response = await fetch(`/api${path}`, {
      ...requestOptions,
      headers: {
        "Content-Type": rawBody === undefined ? "application/json" : rawBody.type || "application/octet-stream",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
      body:
        rawBody !== undefined ? rawBody : options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error(
      "Cannot reach the server. Check that the backend is running and try again.",
    );
  }
  if (response.ok && responseType === "blob") return response.blob();
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/login")
      window.dispatchEvent(new Event("session-expired"));
    const details = data.error?.details
      ?.map((item) => `${item.field}: ${item.message}`)
      .join(" ");
    const error = new Error(
      details || data.error?.message || `Request failed (${response.status}).`,
    );
    error.status = response.status;
    throw error;
  }
  return data;
}

export function uploadAttachment(ticketId, file) {
  return api(`/tickets/${ticketId}/attachments?filename=${encodeURIComponent(file.name)}`, {
    method: "POST", rawBody: file,
  });
}

export async function downloadAttachment(ticketId, attachment) {
  const blob = await api(`/tickets/${ticketId}/attachments/${attachment.id}`, { responseType: "blob" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = attachment.filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function useResource(path, poll = true) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const refresh = useCallback(() => setRevision((v) => v + 1), []);
  useEffect(() => {
    setData(null);
    setLoading(true);
  }, [path]);
  useEffect(() => {
    let alive = true,
      inFlight = false;
    const controller = new AbortController();
    async function load() {
      if (inFlight || !path) return;
      inFlight = true;
      try {
        const next = await api(path, { signal: controller.signal });
        if (alive) {
          setData(next);
          setError("");
        }
      } catch (err) {
        if (alive && err.name !== "AbortError") setError(err.message);
      } finally {
        inFlight = false;
        if (alive) setLoading(false);
      }
    }
    load();
    const tick = () => {
      if (!document.hidden) load();
    };
    const timer = poll ? window.setInterval(tick, 5000) : null;
    document.addEventListener("visibilitychange", tick);
    return () => {
      alive = false;
      controller.abort();
      if (timer) clearInterval(timer);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [path, poll, revision]);
  return { data, error, loading, refresh, setData };
}

export function navigate(path) {
  window.location.hash = `#/${path}`;
}
export function useRoute() {
  const read = () => window.location.hash.replace(/^#\/?/, "") || "overview";
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const changed = () => setRoute(read());
    window.addEventListener("hashchange", changed);
    return () => window.removeEventListener("hashchange", changed);
  }, []);
  return route;
}
