import { NextRequest, NextResponse } from "next/server";

const getBackendBaseUrl = () => {
  // If explicitly set via environment variable
  if (process.env.API_INTERNAL_URL) {
    return process.env.API_INTERNAL_URL.replace("/:path*", "").replace(/\/api\/v1\/?$/, "");
  }
  if (process.env.BACKEND_URL) {
    return process.env.BACKEND_URL.replace(/\/api\/v1\/?$/, "");
  }
  // Inside Docker network, the service name is 'api' on port 8742
  if (process.env.NODE_ENV === "production" || process.env.HOSTNAME === "0.0.0.0") {
    return "http://api:8742";
  }
  // Local development outside Docker
  return "http://127.0.0.1:8742";
};

async function handleProxy(req: NextRequest, { params }: { params: { path: string[] } }) {
  const pathSegments = params.path || [];
  const subPath = pathSegments.join("/");
  const searchParams = req.nextUrl.search; // includes '?' if query params exist

  const backendBase = getBackendBaseUrl();
  const targetUrl = `${backendBase}/api/v1/${subPath}${searchParams}`;

  const headers = new Headers();
  req.headers.forEach((val, key) => {
    // Exclude host and connection headers
    if (!["host", "connection", "content-length"].includes(key.toLowerCase())) {
      headers.set(key, val);
    }
  });

  const method = req.method;
  let body: any = null;

  if (!["GET", "HEAD"].includes(method)) {
    try {
      body = await req.arrayBuffer();
    } catch {
      body = null;
    }
  }

  try {
    const response = await fetch(targetUrl, {
      method,
      headers,
      body,
      cache: "no-store",
    });

    const responseData = await response.arrayBuffer();
    const responseHeaders = new Headers();

    response.headers.forEach((val, key) => {
      if (!["content-encoding", "transfer-encoding"].includes(key.toLowerCase())) {
        responseHeaders.set(key, val);
      }
    });

    return new NextResponse(responseData, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error: any) {
    // If connection to backend fails, try fallback to 127.0.0.1:8742 or api:8000
    try {
      const fallbackBase = backendBase.includes("api:8000") ? "http://127.0.0.1:8742" : "http://api:8000";
      const fallbackUrl = `${fallbackBase}/api/v1/${subPath}${searchParams}`;

      const fallbackRes = await fetch(fallbackUrl, {
        method,
        headers,
        body,
        cache: "no-store",
      });

      const fbData = await fallbackRes.arrayBuffer();
      const fbHeaders = new Headers();
      fallbackRes.headers.forEach((val, key) => {
        if (!["content-encoding", "transfer-encoding"].includes(key.toLowerCase())) {
          fbHeaders.set(key, val);
        }
      });

      return new NextResponse(fbData, {
        status: fallbackRes.status,
        statusText: fallbackRes.statusText,
        headers: fbHeaders,
      });
    } catch (fallbackError: any) {
      console.error(`[API Proxy Error] Failed to proxy to ${targetUrl}:`, error?.message);
      return NextResponse.json(
        { detail: `خطا در برقراری ارتباط با وب‌سرویس بک‌اند رادار: ${error?.message || "سرور پاسخگو نیست"}` },
        { status: 502 }
      );
    }
  }
}

export const GET = handleProxy;
export const POST = handleProxy;
export const PUT = handleProxy;
export const DELETE = handleProxy;
export const PATCH = handleProxy;
export const OPTIONS = handleProxy;
