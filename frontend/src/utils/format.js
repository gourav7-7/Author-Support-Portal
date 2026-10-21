export const money = (value) =>
  value == null
    ? "Not set"
    : new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 2,
      }).format(value);
export const number = (value) =>
  new Intl.NumberFormat("en-IN").format(value || 0);
export const date = (value) =>
  value
    ? new Date(
        value.length === 10 ? value + "T00:00:00" : value,
      ).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "Not yet available";
export const when = (value) =>
  value
    ? new Date(value).toLocaleString("en-IN", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";
export const ageHours = (value) =>
  Math.max(0, (Date.now() - new Date(value)) / 3600000);
export const age = (value) => {
  const h = ageHours(value);
  return h < 1
    ? "Just now"
    : h < 24
      ? `${Math.floor(h)}h ago`
      : `${Math.floor(h / 24)}d ago`;
};
export const cls = (value) => value?.toLowerCase().replace(/[^a-z]+/g, "-");
