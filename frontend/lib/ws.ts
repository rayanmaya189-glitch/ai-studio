export function makeWsUrl(path: string): string {
  const proto = typeof window !== "undefined" ? window.location.protocol : "http:";
  const wsProto = proto === "https:" ? "wss:" : "ws:";
  const host = typeof window !== "undefined" ? window.location.host : "";
  return `${wsProto}//${host}${path.startsWith("/") ? "" : "/"}${path}`;
}
