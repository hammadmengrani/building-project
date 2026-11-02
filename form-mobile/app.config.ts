// Executed by Expo in Node; the mobile TypeScript target has no Node globals.
declare const process: { env: Record<string, string | undefined> };
export default {
  expo: {
    name: "FORM Studio",
    slug: "form-studio-mobile",
    owner: "hammadmengrani",
    extra: {
      eas: {
        projectId: "7289d86c-2165-4703-b6d1-32008f6a3d06",
      },
    },
    version: "0.1.0",
    orientation: "portrait",
    userInterfaceStyle: "light",
    android: {
      package: "com.formstudio.mobile",
      permissions: ["android.permission.CAMERA"],
    },
    ios: {
      bundleIdentifier: "com.formstudio.mobile",
      infoPlist: {
        NSCameraUsageDescription:
          "Place your building on a real surface in AR.",
      },
    },
    plugins: [
      // Mods compose in reverse; normalize the manifest after Viro's mod.
      "./plugins/withOptionalAR",
      [
        "@reactvision/react-viro",
        { android: { xRMode: "AR" }, provider: "none" },
      ],
      [
        "expo-build-properties",
        {
          android: {
            usesCleartextTraffic: process.env.FORM_PRODUCTION !== "1",
          },
        },
      ],
    ],
  },
};
