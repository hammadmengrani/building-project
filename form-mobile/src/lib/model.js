function backendURL(value) {
  const url = new URL(value.trim());
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/"
  )
    throw new Error("Enter a server origin, e.g. http://192.168.1.10:8504");
  return url.origin;
}
function assetURL(origin, path) {
  const url = new URL(path, origin);
  if (
    url.origin !== new URL(origin).origin ||
    !url.pathname.startsWith("/output/")
  )
    throw new Error("Invalid model URL from server");
  return url.href;
}
function fit(bounds, width) {
  const { min, max } = bounds;
  if (
    !Array.isArray(min) ||
    !Array.isArray(max) ||
    min.length !== 3 ||
    max.length !== 3 ||
    !Number.isFinite(width) ||
    width <= 0 ||
    ![...min, ...max].every(Number.isFinite) ||
    max.some((n, i) => n <= min[i])
  )
    throw new Error("Invalid model dimensions");
  return {
    scale: width / Math.max(max[0] - min[0], max[2] - min[2]),
    position: [-(min[0] + max[0]) / 2, -min[1], -(min[2] + max[2]) / 2],
  };
}
module.exports = { backendURL, assetURL, fit };
