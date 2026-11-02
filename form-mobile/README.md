# FORM mobile — React Native + native 3D/AR

An Android-first prototype connected to the existing Python/Blender studio. Includes a real, bundled architectural GLB sample, project history, prompt submission, resumable job polling, roof-off/cutaway views and tabletop plane placement. No Groq key belongs in this app.

For an APK without Android Studio, use the **Cloud APK — no Android Studio** instructions below. The local-native setup is optional.

## Run locally

Requirements: Node compatible with Expo 57 (Node 22 LTS recommended), Android Studio, Android SDK, JDK required by the generated Gradle project, USB debugging and a physical Android device. Native camera AR cannot be tested using an ordinary emulator or Expo Go.

```sh
cd /home/hammad/building-project/form-mobile
npm install
npm run android
```

`expo run:android` creates and installs a native development build. Subsequent JS sessions use `npm start`. Rebuild the native client after native dependencies/plugin changes. Basic local AR does not require a ReactVision cloud account or paid anchors. iOS requires macOS/Xcode and an appropriate Apple signing setup.

In another terminal, start the existing backend yourself:

```sh
cd /home/hammad/building-project/realistic-studio
./run.sh --host 0.0.0.0 --port 8504
```

Set Settings → backend address to `http://YOUR_COMPUTER_LAN_IP:8504`. Both devices must share a network and the firewall must permit that port. Never use the computer's `localhost` address on a phone. Only expose this unauthenticated development server on a trusted LAN. No server is started automatically by the app.

## First test

1. Home → Explore in 3D works with bundled models and no backend/quota.
2. Preview roof-off, cutaway, orbit and zoom.
3. Place in your space checks AR support, then requests camera permission. Scan a textured horizontal surface in good light and tap a detected plane. Rotate, resize or reposition the model.
4. Connect the backend, build its example without a Groq call, then try a prompt. Updated backend exports `mobile-manifest.json` and clean per-view GLBs. Older jobs need rebuilding.

Vivo Y50 is absent from Google's ARCore supported-device list. Installation and regular 3D are intended to remain available because AR is optional. Actual plane AR needs a supported device. Unsupported/unknown AR results show a fallback message; they do not claim simulated camera overlays are AR.

## Architecture and scope

- `src/App.tsx`: home/create/projects/settings and persistent workspace.
- `src/lib/api.ts`: existing session token flow, generation submission and model manifest loading.
- `src/ar/Viewer.tsx`: Viro native 3D, device support/permission checks and horizontal-plane placement.
- `plugins/withOptionalAR.js`: optional Android AR manifest feature; unsupported phones can install.
- `assets/sample-*.glb`: real finished-building sample exported by Blender, not a still image posing as 3D.
- Parent `scripts/building.py`: separate architecture-only mobile exports with glTF Y-up metre bounds. Full web construction/service exports remain available.

Project history stores model URLs, not downloads. Generated projects need their original backend online; only the included sample works offline. No login, multiuser authorization, public hosting, structural approval, quantity engineering, room walking collisions or guaranteed arbitrary furniture generation is claimed. Backend constraints still apply. No automatic Groq retries; polling only reads an existing job. Stop following does not cancel a running backend job.

For production set `FORM_PRODUCTION=1` before prebuild and use an HTTPS endpoint. Add real authentication/authorization, persistent backend job storage, rate limiting, model size budgets, signed assets and device QA before public deployment. Development HTTP permission is intentional for LAN testing.

## Checks

```sh
npm run typecheck
npm test
npx expo export --platform android
```

These check TypeScript, model URL/scale behavior and Metro bundling. They do not verify native compilation, camera tracking, driver compatibility, permissions or phone performance. Those require an installed native build and physical device.

Sources: [Viro Expo integration](https://viro-community.readme.io/docs/integrating-with-expo), [Expo development builds](https://docs.expo.dev/develop/development-builds/introduction/), [ARCore devices](https://developers.google.com/ar/devices).

For a standalone local Android release build (bundled JS, no Metro connection), after configuring the Android toolchain:

```sh
npx expo run:android --variant release
```

Use a proper release signing key before distribution. Public/store publication and cloud builds are outside this local prototype setup.

Dependency audit at setup reported 14 advisories (2 high) in the compatible Expo/Viro dependency tree, including the CLI's transitive Zod dependency. Suggested automatic fixes downgrade Expo/Viro across incompatible major versions, so no `audit fix --force` was applied. This is a development prototype; review upstream patches and rerun `npm audit` before distribution.

## Cloud APK — no Android Studio

The `preview` EAS profile produces an installable APK with bundled JavaScript. It does not need Metro or Expo Go. Android compilation happens on Expo's servers.

```sh
cd /home/hammad/building-project/form-mobile
npm run expo:login
npm run build:apk
```

Use your own Expo account in the terminal; do not paste passwords/tokens into chat. On first run, EAS may ask to create/link the `form-studio-mobile` project and generate an Android keystore. Let EAS manage the keystore for this new app. When using the dynamic `app.config.ts`, EAS may display a project ID to copy into `expo.extra.eas.projectId`; follow its exact instruction before rerunning the build. Do not invent a project ID.

The build page supplies an APK download/install link after a successful build. Free-plan build availability and queue limits apply; do not select a paid upgrade unless you intend to purchase it. The included 3D sample is offline; generation still needs the studio backend. This preview profile allows LAN HTTP. Production requires HTTPS and uses an AAB profile instead.

`.easignore` excludes generated native directories so EAS runs fresh prebuild with the native AR plugins. It also excludes local environment files and signing keys. The Python backend and its secrets do not belong in the mobile upload.

After adding the EAS CLI development tool, the full local dependency audit reports 38 advisories (8 high), including build-tool dependencies. This is not a security-reviewed distribution build. No forced major-version dependency changes were applied.

`npm run build:apk` first runs `check:upload`, exercising the actual EAS copy operation. It verifies that the mobile package/config/assets are included and backend/secrets/generated native folders are excluded. This catches directory traversal mistakes that file-only ignore checks miss.
