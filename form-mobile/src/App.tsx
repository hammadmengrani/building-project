import React, { useEffect, useRef, useState } from "react";
import {
  Alert,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  ActivityIndicator,
} from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { completedProject, Job, Project, request } from "./lib/api";
import { backendURL } from "./lib/model";
import Viewer from "./ar/Viewer";
import sampleManifest from "../assets/sample-manifest.json";

const PROMPT =
  "Create a spacious single-storey Pakistani family home, 18 x 16 metres. Exactly two large bedrooms, one shared bathroom, one generous open living/dining lounge and one kitchen with connected circulation. Prioritize a wide lounge with sofas facing a media wall and a coffee table; avoid extra small rooms. Use warm ivory plaster, walnut furniture, muted olive upholstery and pale stone floors. Provide usable doors and exterior windows. Keep furniture clear of all doors. No extra floors, pool or vehicles.";
const SAMPLE: Project = {
  id: "sample",
  name: "The quiet residence",
  created: 0,
  views: Object.fromEntries(
    ["exterior", "interior", "cutaway"].map((view) => [
      view,
      {
        asset:
          view === "exterior"
            ? require("../assets/sample-exterior.glb")
            : view === "interior"
              ? require("../assets/sample-interior.glb")
              : require("../assets/sample-cutaway.glb"),
        bounds: (sampleManifest.views as any)[view].bounds,
      },
    ]),
  ),
};
const KEY = "form.mobile.v1";
type Pending = { origin: string; id: string };
function Button({
  title,
  onPress,
  secondary = false,
  disabled = false,
}: {
  title: string;
  onPress: () => void;
  secondary?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={[
        s.button,
        secondary && s.secondary,
        disabled && { opacity: 0.45 },
      ]}
    >
      <Text style={[s.buttonText, secondary && { color: "#254c48" }]}>
        {title}
      </Text>
    </Pressable>
  );
}
export default function App() {
  const [tab, setTab] = useState("Home");
  const [origin, setOrigin] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [pending, setPending] = useState<Pending | null>(null);
  const [ready, setReady] = useState(false);
  const [prompt, setPrompt] = useState(PROMPT);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [viewer, setViewer] = useState<Project | null>(null);
  const [connected, setConnected] = useState(false);
  const active = useRef(false);
  const pollRunning = useRef(false);
  useEffect(() => {
    active.current = true;
    AsyncStorage.getItem(KEY)
      .then((raw) => {
        if (raw) {
          const data = JSON.parse(raw);
          setOrigin(data.origin || "");
          setProjects(data.projects || []);
          setPending(data.pending || null);
        }
      })
      .catch(() => setMessage("Saved workspace could not be read."))
      .finally(() => setReady(true));
    return () => {
      active.current = false;
    };
  }, []);
  useEffect(() => {
    if (ready)
      AsyncStorage.setItem(
        KEY,
        JSON.stringify({ origin, projects, pending }),
      ).catch(() =>
        setMessage("Phone storage is full; workspace was not saved."),
      );
  }, [ready, origin, projects, pending]);
  useEffect(() => {
    setConnected(false);
  }, [origin]);
  useEffect(() => {
    if (!pending || !ready) return;
    let stopped = false;
    const poll = async () => {
      if (pollRunning.current) return;
      pollRunning.current = true;
      try {
        const job: Job = await request(
          pending.origin,
          "/api/jobs/" + encodeURIComponent(pending.id),
        );
        if (stopped) return;
        setMessage(job.message || job.status);
        if (job.status === "complete") {
          const project = await completedProject(pending.origin, job);
          if (stopped) return;
          setProjects((old) => [
            project,
            ...old.filter((p) => p.id !== project.id),
          ]);
          setPending(null);
          setViewer(project);
          setMessage("Your building is ready.");
        } else if (["failed", "needs_input"].includes(job.status)) {
          setPending(null);
          setMessage(job.message || "Please revise the design brief.");
        }
      } catch (error) {
        if (!stopped)
          setMessage(
            "Connection interrupted. Reconnecting to this job — no new Groq request. " +
              (error as Error).message,
          );
      } finally {
        pollRunning.current = false;
      }
    };
    poll();
    const timer = setInterval(poll, 2500);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [pending, ready]);
  async function connect() {
    setBusy(true);
    try {
      const url = backendURL(origin);
      const config = await request(url, "/api/config");
      setOrigin(url);
      setConnected(true);
      setMessage(
        `Connected · Blender ${config.blender ? "ready" : "unavailable"} · Groq ${config.groq ? "configured" : "not configured"}`,
      );
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function generate(example = false) {
    setBusy(true);
    setMessage("Connecting to your studio…");
    try {
      const url = backendURL(origin);
      const config = await request(url, "/api/config");
      setConnected(true);
      if (!config.blender)
        throw new Error("Blender is unavailable on the backend.");
      if (!example && !config.groq)
        throw new Error(
          "Configure Groq on the backend or explore the offline sample.",
        );
      const body = example
        ? { scene: await request(url, "/api/demo"), edits: {} }
        : { prompt };
      const job = await request(
        url,
        example ? "/api/build" : "/api/design",
        body,
        config.token,
      );
      setPending({ origin: url, id: job.id });
      setMessage(
        "Building your scene. You can leave this screen; progress is saved.",
      );
    } catch (error) {
      setMessage(
        (error as Error).message +
          " If submission timed out, check the desktop job before submitting again.",
      );
    } finally {
      if (active.current) setBusy(false);
    }
  }
  if (viewer)
    return (
      <SafeAreaProvider>
        <StatusBar style="light" />
        <Viewer project={viewer} onClose={() => setViewer(null)} />
      </SafeAreaProvider>
    );
  return (
    <SafeAreaProvider>
      <SafeAreaView style={s.root}>
        <StatusBar style="dark" />
        <View style={s.header}>
          <Text style={s.logo}>
            FORM<Text style={{ color: "#b69463" }}> /</Text>
          </Text>
          <Text style={s.eyebrow}>ARCHITECTURE, IN YOUR HANDS</Text>
        </View>
        <ScrollView
          contentContainerStyle={s.content}
          keyboardShouldPersistTaps="handled"
        >
          {tab === "Home" && (
            <>
              <Text style={s.eyebrow}>YOUR PERSONAL ARCHITECTURE STUDIO</Text>
              <Text style={s.title}>Imagine a space.{"\n"}Step into it.</Text>
              <Text style={s.body}>
                Create a home, explore every room, then place a scale model in
                your world.
              </Text>
              <View style={s.hero}>
                <Image
                  source={require("../assets/interior-preview.png")}
                  style={s.heroImage}
                />
                <View style={s.heroCaption}>
                  <Text style={s.cardTitle}>The quiet residence</Text>
                  <Text style={s.muted}>
                    Detailed interior · included sample · no Groq call
                  </Text>
                </View>
              </View>
              <Button
                title="Explore in 3D →"
                onPress={() => setViewer(SAMPLE)}
              />
              <Button
                title="Create your own home"
                secondary
                onPress={() => setTab("Create")}
              />
              <View style={s.note}>
                <Text style={s.cardTitle}>A model on your table</Text>
                <Text style={s.body}>
                  AR uses your camera on supported devices. If your phone cannot
                  run native AR, you can still explore in 3D.
                </Text>
              </View>
            </>
          )}
          {tab === "Create" && (
            <>
              <Text style={s.eyebrow}>01 / DESIGN BRIEF</Text>
              <Text style={s.title}>Your home,{"\n"}your words.</Text>
              <Text style={s.body}>
                Describe the rooms, dimensions, finishes and mood. Generation
                runs on your studio backend.
              </Text>
              <TextInput
                accessibilityLabel="Design brief"
                multiline
                value={prompt}
                onChangeText={setPrompt}
                style={s.brief}
                textAlignVertical="top"
              />
              <Button
                title={
                  pending ? "Generation in progress…" : "Generate my building →"
                }
                disabled={busy || !!pending || !prompt.trim()}
                onPress={() => generate()}
              />
              <Button
                title="Build backend example · no Groq"
                secondary
                disabled={busy || !!pending}
                onPress={() => generate(true)}
              />
              <Text style={s.muted}>
                No automatic generation retries. Existing geometry and furniture
                support still applies; a prompt cannot add unsupported object
                types.
              </Text>
              {pending && (
                <View style={s.note}>
                  <ActivityIndicator color="#2d6259" />
                  <Text style={s.body}>Job {pending.id}</Text>
                  <Text style={s.muted}>
                    Progress resumes when you reopen the app.
                  </Text>
                  <Button
                    secondary
                    title="Stop following this job"
                    onPress={() =>
                      Alert.alert(
                        "Stop following?",
                        "The backend keeps running. This only removes the saved progress link.",
                        [
                          { text: "Keep following" },
                          {
                            text: "Stop following",
                            onPress: () => setPending(null),
                          },
                        ],
                      )
                    }
                  />
                </View>
              )}
            </>
          )}
          {tab === "Projects" && (
            <>
              <Text style={s.eyebrow}>02 / YOUR COLLECTION</Text>
              <Text style={s.title}>Spaces to explore.</Text>
              <Text style={s.body}>
                Projects stay on this phone. Generated models load from the same
                backend; keep that server available.
              </Text>
              {[SAMPLE, ...projects].map((project) => (
                <View style={s.note} key={project.id}>
                  <Text style={s.cardTitle}>{project.name}</Text>
                  <Text style={s.muted}>
                    {project.id === "sample"
                      ? "Included · works offline"
                      : new Date(project.created).toLocaleDateString()}
                  </Text>
                  <Button
                    title="Open building →"
                    onPress={() => setViewer(project)}
                  />
                  {project.id !== "sample" && (
                    <Pressable
                      onPress={() =>
                        Alert.alert(
                          "Remove project?",
                          "Only this phone’s saved link will be removed.",
                          [
                            { text: "Cancel" },
                            {
                              text: "Remove",
                              onPress: () =>
                                setProjects((old) =>
                                  old.filter((p) => p.id !== project.id),
                                ),
                            },
                          ],
                        )
                      }
                    >
                      <Text style={s.link}>Remove from phone</Text>
                    </Pressable>
                  )}
                </View>
              ))}
            </>
          )}
          {tab === "Settings" && (
            <>
              <Text style={s.eyebrow}>03 / WORKSPACE</Text>
              <Text style={s.title}>Connect your studio.</Text>
              <Text style={s.body}>
                Use your computer’s Wi-Fi/LAN address. “localhost” on your phone
                points to the phone itself.
              </Text>
              <Text style={s.label}>BACKEND ADDRESS</Text>
              <TextInput
                accessibilityLabel="Backend address"
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="url"
                placeholder="http://192.168.1.10:8504"
                value={origin}
                onChangeText={setOrigin}
                style={s.input}
              />
              <Button
                title={
                  connected ? "Connected · check again" : "Test connection"
                }
                disabled={busy}
                onPress={connect}
              />
              <View style={s.note}>
                <Text style={s.cardTitle}>Local development</Text>
                <Text style={s.body}>
                  Phone and computer need the same network. Run the backend on
                  0.0.0.0 and allow its port through your firewall. Groq
                  credentials stay on the computer.
                </Text>
                <Text style={s.muted}>
                  This is a LAN testing build. Public deployment needs HTTPS,
                  authentication and access control.
                </Text>
              </View>
              <View style={s.note}>
                <Text style={s.cardTitle}>Native AR requirements</Text>
                <Text style={s.body}>
                  Install a native development build, not Expo Go. AR capability
                  is checked before camera access. Vivo Y50 is not listed as an
                  ARCore-supported phone; use 3D preview or test AR on a
                  supported device.
                </Text>
              </View>
            </>
          )}
          {!!message && (
            <View accessibilityLiveRegion="polite" style={s.message}>
              {busy && <ActivityIndicator color="#2d6259" />}
              <Text style={s.body}>{message}</Text>
            </View>
          )}
        </ScrollView>
        <View style={s.tabs}>
          {["Home", "Create", "Projects", "Settings"].map((name, i) => (
            <Pressable
              key={name}
              accessibilityRole="tab"
              accessibilityState={{ selected: tab === name }}
              onPress={() => setTab(name)}
              style={s.tab}
            >
              <Text style={[s.tabIcon, tab === name && s.active]}>
                {["⌂", "＋", "▤", "⚙"][i]}
              </Text>
              <Text style={[s.tabText, tab === name && s.active]}>{name}</Text>
            </Pressable>
          ))}
        </View>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}
const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#f5f3ee" },
  header: {
    paddingHorizontal: 24,
    paddingVertical: 18,
    borderBottomWidth: 1,
    borderColor: "#dfded7",
  },
  logo: { fontSize: 29, fontWeight: "800", letterSpacing: -1 },
  eyebrow: {
    fontSize: 10,
    letterSpacing: 1.8,
    color: "#68736c",
    marginVertical: 8,
  },
  content: { padding: 24, paddingBottom: 35 },
  title: {
    fontSize: 38,
    lineHeight: 44,
    color: "#223a35",
    letterSpacing: -1.5,
    marginVertical: 12,
    fontWeight: "500",
  },
  body: { fontSize: 15, lineHeight: 24, color: "#55645e", marginVertical: 8 },
  hero: {
    marginTop: 24,
    marginBottom: 16,
    borderRadius: 20,
    overflow: "hidden",
    backgroundColor: "#e4ded2",
  },
  heroImage: { width: "100%", height: 245 },
  heroCaption: { padding: 18 },
  cardTitle: {
    fontSize: 20,
    color: "#253f38",
    fontWeight: "600",
    marginBottom: 6,
  },
  muted: { fontSize: 12, lineHeight: 19, color: "#778179" },
  button: {
    backgroundColor: "#2d6259",
    padding: 18,
    borderRadius: 12,
    marginVertical: 6,
    alignItems: "center",
  },
  secondary: {
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: "#bac8be",
  },
  buttonText: { color: "#fff", fontWeight: "600", fontSize: 15 },
  note: {
    padding: 20,
    borderRadius: 16,
    backgroundColor: "#eaece4",
    marginTop: 22,
  },
  brief: {
    minHeight: 285,
    padding: 18,
    borderWidth: 1,
    borderColor: "#c5cec3",
    backgroundColor: "#fff",
    borderRadius: 14,
    fontSize: 15,
    lineHeight: 23,
    color: "#243d36",
    marginVertical: 18,
  },
  input: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#c5cec3",
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    marginVertical: 10,
  },
  label: { fontSize: 11, letterSpacing: 1.4, color: "#6a766d", marginTop: 24 },
  message: {
    padding: 16,
    backgroundColor: "#e1e8dc",
    borderRadius: 12,
    marginTop: 18,
  },
  tabs: {
    flexDirection: "row",
    borderTopWidth: 1,
    borderColor: "#deded5",
    paddingVertical: 12,
    backgroundColor: "#faf9f5",
  },
  tab: { flex: 1, alignItems: "center", gap: 4 },
  tabIcon: { fontSize: 23, color: "#87928a" },
  tabText: { fontSize: 11, color: "#87928a" },
  active: { color: "#295c50", fontWeight: "700" },
  link: { color: "#7d4b42", paddingVertical: 12, fontSize: 13 },
});
