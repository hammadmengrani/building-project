import { assetURL, backendURL } from "./model";
export type Bounds = { min: number[]; max: number[] };
export type Model = { uri?: string; asset?: number; bounds: Bounds };
export type Project = {
  id: string;
  name: string;
  created: number;
  origin?: string;
  scene?: any;
  views: Record<string, Model>;
};
export type Job = {
  id: string;
  status: string;
  message: string;
  scene?: any;
  model?: string;
};
export async function request(
  origin: string,
  path: string,
  body?: object,
  token?: string,
) {
  const control = new AbortController();
  const timeout = setTimeout(() => control.abort(), 20000);
  try {
    const response = await fetch(backendURL(origin) + path, {
      signal: control.signal,
      method: body ? "POST" : "GET",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "X-Studio-Token": token } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    const data = await response.json();
    if (!response.ok)
      throw new Error(data.message || `Server returned ${response.status}`);
    return data;
  } finally {
    clearTimeout(timeout);
  }
}
export async function completedProject(
  origin: string,
  job: Job,
): Promise<Project> {
  if (!job.model) throw new Error("Server did not return a model");
  const base = new URL(assetURL(origin, job.model)).pathname.replace(
    /\/[^/]+$/,
    "",
  );
  const manifest = await request(origin, base + "/mobile-manifest.json");
  const views: Record<string, Model> = {};
  for (const [key, raw] of Object.entries(manifest.views) as [string, any][]) {
    if (
      !["exterior", "interior", "cutaway"].includes(key) ||
      !/^[\w-]+\.glb$/.test(raw.file)
    )
      continue;
    views[key] = {
      uri: assetURL(origin, base + "/" + raw.file),
      bounds: raw.bounds,
    };
  }
  if (!views.exterior)
    throw new Error(
      "Mobile export missing. Restart the updated backend and rebuild the scene.",
    );
  return {
    id: job.id,
    name: job.scene?.name || "My residence",
    created: Date.now(),
    origin,
    scene: job.scene,
    views,
  };
}
