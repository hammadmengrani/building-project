// Exercise EAS's actual directory traversal, including untracked mobile files.
const { makeShallowCopyAsync } = require("eas-cli/build/vcs/local");
const fs = require("node:fs/promises");
const path = require("node:path");
const os = require("node:os");
(async () => {
  const destination = await fs.mkdtemp(
    path.join(os.tmpdir(), "form-eas-upload-"),
  );
  const root = path.resolve(__dirname, "../..");
  await makeShallowCopyAsync(root, destination);
  for (const file of [
    "package.json",
    "package-lock.json",
    "app.config.ts",
    "eas.json",
    "src/App.tsx",
    "plugins/withOptionalAR.js",
    "assets/sample-exterior.glb",
  ]) {
    await fs.access(path.join(destination, "form-mobile", file));
  }
  for (const file of [
    "realistic-studio",
    "venv",
    ".git",
    "form-mobile/node_modules",
    "form-mobile/android",
    "form-mobile/ios",
    "form-mobile/.env",
  ]) {
    try {
      await fs.access(path.join(destination, file));
    } catch (error) {
      if (error.code === "ENOENT") continue;
      throw error;
    }
    throw new Error("Unexpected upload entry: " + file);
  }
  console.log(
    "PASS: EAS upload contains mobile package/config/source/assets; excludes backend, secrets and native build folders.",
  );
  console.log("Verified staging directory:", destination);
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
