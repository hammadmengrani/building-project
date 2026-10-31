# FORM AR Lab — laptop webcam

Open `http://localhost:8504/ar/index.html` on the laptop running the studio. The studio home page also has a **Webcam AR** link. Uses the existing server; no extra backend URL, npm install, APK or Expo is needed.

## First augmentation

1. Load the included sample or your self-contained GLB file.
2. Open **Open printable marker**. Print the official Hiro marker, preserving the complete black border and white margin. Alternatively download the PNG and display it on another device, such as your phone.
3. Select Webcam AR → Enable camera and allow webcam access for localhost.
4. Hold the marker in front of the webcam, with the entire square visible, in good light. The status changes to **Marker found · anchored** and the building appears on the marker. Losing the marker hides the building.
5. Adjust model size/rotation or select roof-off/cutaway. Stop camera when finished. Hiding the tab also stops the stream.

This is real marker pose tracking, not markerless floor/room tracking or engineering measurement. Simply enabling the camera without showing the marker will not augment a building. The marker cannot be shown on the same laptop screen and seen by its front-facing webcam at the same time; use paper or another screen.

## Studio generation

Expand Create a new building to submit a prompt to the existing Groq/Blender backend. One request is sent; job polling only reads existing progress. The backend example needs Blender but no Groq request. Generation constraints remain those of the original studio. Job progress is saved locally. Stop following does not cancel the backend job. Generated scenes use architecture-only mobile GLBs exported by the updated Blender builder.

## Browser and privacy

Use a current desktop browser with WebGL, WebAssembly and webcam access. Camera requires localhost or HTTPS. Ordinary HTTP LAN addresses generally do not provide a secure camera context. Camera frames are processed locally by AR.js and are not uploaded to Groq. The prompt is sent to the studio backend and its configured Groq provider. No external CDN/fonts are required by this page; AR.js, camera parameters, pattern and sample assets are vendored locally.

Copy diagnostics collects mode, secure-context status, camera/tracking booleans, job ID and recent error messages, not tokens or video. Permission, unavailable/busy cameras, model errors and lost WebGL contexts are surfaced in the status bar. GLBs must be self-contained and fit the 64 MB preview budget; this does not limit building floors in the generation engine.

## Verified / limitations

- Browser-loaded real sample exterior/roof-off GLB, wireframe controls and API configuration connection verified.
- `/ar/tracker-check.html` runs the actual AR.js detector on the official Hiro fixture: marker detected with finite pose matrix.
- Fixture detection does not prove live webcam tracking, calibration accuracy, placement alignment or a particular laptop driver's performance. Physical paper/camera placement must be checked by the user.
- Generic camera calibration is bundled; no survey-grade accuracy is claimed.

AR.js version 3.4.7, official repository: https://github.com/AR-js-org/AR.js/tree/3.4.7. License retained under vendor/. Camera documentation: https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia . Three.js and loaders are reused from the existing studio's vendor directory.
