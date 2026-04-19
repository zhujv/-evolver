export type JsonRpcRequest = {
  method: string;
  params?: Record<string, unknown>;
  id?: number;
};

/**
 * JSON-RPC（经 Vite dev 代理 /rpc → 后端 16888，或生产同源部署）。
 */
export async function rpcCall<T = unknown>(
  req: JsonRpcRequest,
  token?: string
): Promise<T> {
  const merged: Record<string, unknown> = { ...(req.params ?? {}) };
  if (token && merged.auth_token === undefined) {
    merged.auth_token = token;
  }
  const payload = {
    method: req.method,
    params: merged,
    id: req.id ?? 1,
  };
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch("/rpc", {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  const text = await res.text();
  if (!res.ok) {
    throw new Error(
      `HTTP ${res.status} ${res.statusText}: ${text.slice(0, 400)}`
    );
  }
  let data: { result?: T; error?: { message?: string }; id?: number };
  try {
    data = JSON.parse(text) as typeof data;
  } catch {
    throw new Error(
      `非 JSON 响应（请确认已启动后端 16888，且 dev/preview 已配置 /rpc 代理）: ${text.slice(0, 240)}`
    );
  }
  if (data.error) {
    const err = data.error as { message?: string; code?: number };
    throw new Error(err.message ?? "RPC error");
  }
  return data.result as T;
}
