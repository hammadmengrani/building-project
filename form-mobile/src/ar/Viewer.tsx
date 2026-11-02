import React, { useRef, useState } from "react";
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  Platform,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Constants from "expo-constants";
import type { Project } from "../lib/api";
import { fit } from "../lib/model";
let cached: any;
function nativeViro() {
  if (Platform.OS === "web" || Constants.executionEnvironment === "storeClient")
    return null;
  if (!cached) cached = require("@reactvision/react-viro");
  return cached;
}
function Building({ data }: { data: any }) {
  const V = nativeViro();
  const model = data.project.views[data.view];
  const normalized = fit(model.bounds, data.ar ? data.width : 2.5);
  return (
    <V.ViroNode
      rotation={[0, data.yaw, 0]}
      scale={[normalized.scale, normalized.scale, normalized.scale]}
    >
      <V.Viro3DObject
        source={model.asset ?? { uri: model.uri }}
        type="GLB"
        position={normalized.position}
        onLoadStart={() => data.setStatus("Loading building…")}
        onLoadEnd={() =>
          data.setStatus(
            data.ar
              ? "Model ready. Rotate or resize below."
              : "Drag to orbit · controls below",
          )
        }
        onError={(event: any) =>
          data.setStatus(
            "Model could not load. Check the backend connection. " +
              String(event?.nativeEvent?.error ?? ""),
          )
        }
      />
    </V.ViroNode>
  );
}
function PreviewScene(props: any) {
  const V = nativeViro();
  const data = props.sceneNavigator.viroAppProps;
  return (
    <V.ViroScene>
      <V.ViroAmbientLight color="#ffffff" intensity={500} />
      <V.ViroDirectionalLight
        color="#fff4df"
        direction={[-1, -2, -1]}
        intensity={1000}
      />
      <V.ViroOrbitCamera
        position={[0, data.height, data.distance]}
        focalPoint={[0, 0.5, 0]}
        active
      />
      <Building data={data} />
    </V.ViroScene>
  );
}
function ARScene(props: any) {
  const V = nativeViro();
  const selector = useRef<any>(null);
  const data = props.sceneNavigator.viroAppProps;
  return (
    <V.ViroARScene
      anchorDetectionTypes={["PlanesHorizontal"]}
      onTrackingUpdated={(state: number) => {
        if (state === 3)
          data.setStatus(
            "Move your phone slowly. Tap a detected horizontal surface.",
          );
      }}
      onAnchorFound={(a: any) => selector.current?.handleAnchorFound(a)}
      onAnchorUpdated={(a: any) => selector.current?.handleAnchorUpdated(a)}
      onAnchorRemoved={(a: any) =>
        a && selector.current?.handleAnchorRemoved(a)
      }
    >
      <V.ViroAmbientLight color="#ffffff" intensity={500} />
      <V.ViroDirectionalLight
        color="#ffffff"
        direction={[-1, -2, -1]}
        intensity={900}
      />
      <V.ViroARPlaneSelector
        ref={selector}
        alignment="Horizontal"
        hideOverlayOnSelection
        onPlaneSelected={() =>
          data.setStatus("Surface selected. Loading your model…")
        }
      >
        <Building data={data} />
      </V.ViroARPlaneSelector>
    </V.ViroARScene>
  );
}
class RenderBoundary extends React.Component<
  { children: React.ReactNode; onError: (message: string) => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error: Error) {
    this.props.onError(error.message);
  }
  render() {
    return this.state.failed ? (
      <View style={s.center}>
        <Text style={s.text}>
          Native viewer unavailable. Rebuild the development client with Viro
          installed.
        </Text>
      </View>
    ) : (
      this.props.children
    );
  }
}
export default function Viewer({
  project,
  onClose,
}: {
  project: Project;
  onClose: () => void;
}) {
  const [ar, setAR] = useState(false),
    [view, setView] = useState("exterior"),
    [yaw, setYaw] = useState(0),
    [width, setWidth] = useState(0.65),
    [distance, setDistance] = useState(3.8),
    [height, setHeight] = useState(2.3),
    [reset, setReset] = useState(0),
    [checking, setChecking] = useState(false),
    [status, setStatus] = useState("Loading 3D preview…");
  let V: any;
  try {
    V = nativeViro();
  } catch {
    V = null;
  }
  async function enterAR() {
    setChecking(true);
    try {
      if (!V)
        throw new Error(
          "Native AR needs an installed development build; Expo Go cannot run it.",
        );
      const support = await V.isARSupportedOnDevice();
      if (!support?.isARSupported)
        throw new Error("AR is unavailable on this device.");
      const permissions = await V.requestRequiredPermissions(["camera"]);
      if (!permissions.camera)
        throw new Error(
          "Camera access is needed for AR. Enable it in Android settings.",
        );
      setAR(true);
      setReset((n) => n + 1);
      setStatus(
        "Move slowly to detect a table or floor, then tap its surface.",
      );
    } catch (error) {
      setStatus(
        "AR unavailable: " +
          (error as Error).message +
          " You can continue in 3D.",
      );
    } finally {
      setChecking(false);
    }
  }
  const data = { project, view, yaw, width, distance, height, setStatus, ar };
  const button = (label: string, action: () => void, selected = false) => (
    <Pressable
      key={label}
      accessibilityRole="button"
      onPress={action}
      style={[s.button, selected && s.selected]}
    >
      <Text style={s.text}>{label}</Text>
    </Pressable>
  );
  return (
    <SafeAreaView style={s.root}>
      <View style={s.header}>
        {button("‹ Close", onClose)}
        <Text numberOfLines={1} style={s.name}>
          {project.name}
        </Text>
      </View>
      <View style={s.viewport}>
        {V ? (
          <RenderBoundary key={`${ar}-${reset}`} onError={setStatus}>
            {ar ? (
              <V.ViroARSceneNavigator
                style={{ flex: 1 }}
                initialScene={{ scene: ARScene }}
                viroAppProps={data}
                pbrEnabled
              />
            ) : (
              <V.Viro3DSceneNavigator
                style={{ flex: 1 }}
                initialScene={{ scene: PreviewScene }}
                viroAppProps={data}
                hdrEnabled
                pbrEnabled
              />
            )}
          </RenderBoundary>
        ) : (
          <View style={s.center}>
            <Text style={s.name}>Install the native development build</Text>
            <Text style={s.text}>
              This screen uses native 3D and AR. It is unavailable in Expo Go
              and web previews.
            </Text>
          </View>
        )}
        <View pointerEvents="none" style={s.badge}>
          <Text style={s.text}>{ar ? "AR · TABLETOP" : "3D EXPLORER"}</Text>
        </View>
      </View>
      <View style={s.controls}>
        <View style={s.row}>
          {Object.keys(project.views).map((v) =>
            button(
              v === "interior" ? "Roof off" : v[0].toUpperCase() + v.slice(1),
              () => setView(v),
              view === v,
            ),
          )}
        </View>
        <Text accessibilityLiveRegion="polite" style={s.status}>
          {status}
        </Text>
        <View style={s.row}>
          {button("↶ Rotate", () => setYaw((v) => v - 15))}
          {button("Rotate ↷", () => setYaw((v) => v + 15))}
          {button(ar ? "Smaller" : "Zoom −", () =>
            ar
              ? setWidth((v) => Math.max(0.2, v - 0.15))
              : setDistance((v) => Math.min(8, v + 0.4)),
          )}
          {button(ar ? "Larger" : "Zoom +", () =>
            ar
              ? setWidth((v) => Math.min(2, v + 0.15))
              : setDistance((v) => Math.max(1.5, v - 0.4)),
          )}
        </View>
        {!ar && (
          <View style={s.row}>
            {button("Eye level", () => setHeight(0.8))}
            {button("Bird’s eye", () => setHeight(3.5))}
          </View>
        )}
        {ar ? (
          <View style={s.row}>
            {button("Reposition", () => {
              setReset((n) => n + 1);
              setStatus("Scan and tap a new surface.");
            })}
            {button("Back to 3D", () => {
              setAR(false);
              setStatus("Loading 3D preview…");
            })}
            <Text style={s.text}>{width.toFixed(2)} m wide</Text>
          </View>
        ) : (
          button(
            checking ? "Checking device…" : "Place in your space →",
            () => {
              if (!checking) enterAR();
            },
            true,
          )
        )}
        {checking && <ActivityIndicator color="#d2b17a" />}
      </View>
    </SafeAreaView>
  );
}
const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#172724" },
  header: { flexDirection: "row", alignItems: "center", padding: 10, gap: 12 },
  name: { fontSize: 17, fontWeight: "600", color: "#f4f1e7", flexShrink: 1 },
  viewport: { flex: 1, backgroundColor: "#d7ddd7" },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 28,
    gap: 16,
    backgroundColor: "#32453e",
  },
  controls: { padding: 14, gap: 8 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 7, alignItems: "center" },
  button: {
    paddingHorizontal: 13,
    paddingVertical: 12,
    backgroundColor: "#30463e",
    borderRadius: 9,
  },
  selected: { backgroundColor: "#587966" },
  text: { color: "#f1f0e7", fontSize: 12, lineHeight: 20 },
  status: { fontSize: 12, color: "#d8dfd2", lineHeight: 19, minHeight: 38 },
  badge: {
    position: "absolute",
    top: 16,
    left: 16,
    backgroundColor: "#243f36dd",
    padding: 10,
    borderRadius: 8,
  },
});
