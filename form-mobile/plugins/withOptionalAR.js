const { withAndroidManifest } = require("expo/config-plugins");
module.exports = (config) =>
  withAndroidManifest(config, (mod) => {
    const manifest = mod.modResults.manifest;
    const features = manifest["uses-feature"] || [];
    manifest["uses-feature"] = features.filter(
      (f) => f.$["android:name"] !== "android.hardware.camera.ar",
    );
    manifest["uses-feature"].push({
      $: {
        "android:name": "android.hardware.camera.ar",
        "android:required": "false",
      },
    });
    const app = manifest.application[0];
    app["meta-data"] = (app["meta-data"] || []).filter(
      (m) => m.$["android:name"] !== "com.google.ar.core",
    );
    app["meta-data"].push({
      $: { "android:name": "com.google.ar.core", "android:value": "optional" },
    });
    return mod;
  });
