// Forwards /api/* to the FastAPI backend, so the browser only ever talks to
// this app. The backend can then sit on an internal-only address, needs no
// CORS, and its URL is read at runtime (GTAB_API_URL) instead of being baked
// into the client bundle at build time like a NEXT_PUBLIC_ variable would be.

import type { NextRequest } from "next/server";

type Context = { params: Promise<{ path: string[] }> };

async function forward(request: NextRequest, { params }: Context) {
  const { path } = await params;
  const base = (process.env.GTAB_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
  const target = `${base}/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`;

  // Only the headers the backend needs - hop-by-hop ones (host, connection,
  // content-length of a re-streamed body) must not be copied across.
  const headers = new Headers();
  for (const name of ["content-type", "accept"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.body,
      // Stream the upload through rather than buffering the whole video.
      duplex: "half",
      cache: "no-store",
      redirect: "manual",
    } as RequestInit & { duplex: "half" });
  } catch {
    return Response.json(
      { detail: "The transcription service is unavailable." },
      { status: 502 },
    );
  }

  // fetch has already decoded the body, so drop headers describing the
  // encoded one.
  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");
  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export { forward as GET, forward as POST };
