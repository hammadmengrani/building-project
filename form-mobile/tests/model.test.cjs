const { test } = require("node:test");
const assert = require("node:assert/strict");
const { backendURL, assetURL, fit } = require("../src/lib/model");
test("LAN server address validation", () => {
  assert.equal(
    backendURL(" http://192.168.1.10:8504/ "),
    "http://192.168.1.10:8504",
  );
  for (const bad of [
    "file:///etc/passwd",
    "http://user:secret@host",
    "http://host/api",
    "http://host?key=x",
  ])
    assert.throws(() => backendURL(bad));
});
test("models stay on configured backend", () => {
  assert.equal(
    assetURL("http://host:8504", "/output/a/mobile-exterior.glb"),
    "http://host:8504/output/a/mobile-exterior.glb",
  );
  assert.throws(() =>
    assetURL("http://host", "https://evil.test/output/a.glb"),
  );
  assert.throws(() => assetURL("http://host", "/api/config"));
});
test("metre dimensions fit tabletop and ground model", () => {
  const f = fit({ min: [-10, -0.2, -8], max: [10, 12, 8] }, 0.6);
  assert.equal(f.scale, 0.03);
  assert.equal(Math.abs(f.position[0]), 0);
  assert.equal(f.position[1], 0.2);
  assert.equal(Math.abs(f.position[2]), 0);
  assert.throws(() => fit({ min: [0, 0, 0], max: [0, 1, 1] }, 1));
});
