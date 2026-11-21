import type { NextRequest } from "next/server";

// Same-origin proxy to the backend. BACKEND_URL is read at request time (not build time).
// The upstream body is passed through untouched, so SSE streams without buffering.
export const dynamic = "force-dynamic";

const HOP_BY_HOP = new Set([
  "connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade",
  "proxy-authorization", "proxy-authenticate", "host", "content-length", "content-encoding",
]);

async function proxy(req: NextRequest): Promise<Response> {
  const backend = process.env.BACKEND_URL ?? "http://localhost:8000";
  const url = new URL(req.nextUrl.pathname + req.nextUrl.search, backend);

  const headers = new Headers();
  req.headers.forEach((v, k) => {
    if (!HOP_BY_HOP.has(k.toLowerCase())) headers.set(k, v);
  });

  const hasBody = !["GET", "HEAD"].includes(req.method);
  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method: req.method,
      headers,
      body: hasBody ? req.body : undefined,
      // @ts-expect-error duplex is required by Node's fetch for streamed request bodies
      duplex: hasBody ? "half" : undefined,
      cache: "no-store",
      redirect: "manual",
      signal: req.signal,
    });
  } catch {
    return Response.json({ error: "backend_unreachable" }, { status: 502 });
  }

  const out = new Headers();
  upstream.headers.forEach((v, k) => {
    if (!HOP_BY_HOP.has(k.toLowerCase())) out.set(k, v);
  });
  out.set("cache-control", "no-store");
  out.set("x-accel-buffering", "no");
  return new Response(upstream.body, { status: upstream.status, headers: out });
}

export {
  proxy as GET,
  proxy as POST,
  proxy as PUT,
  proxy as PATCH,
  proxy as DELETE,
  proxy as OPTIONS,
};
