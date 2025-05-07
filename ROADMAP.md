# 🗺️ Project Roadmap — xreal-vio-vr

This file outlines the development phases and high-level milestones of `xreal-vio-vr`.

✴ **Status:** Prototype Phase  
⚠️ Not stable — everything is subject to change.

---

## 🧠 Core Philosophy

- Hardware-first spatial interface for XREAL Ultra  
- No game engines, no Unity  
- Joy-Con + SLAM; later: marker-based tracking  
- Focused on Linux-native tools and wearable design  

---

## ✅ MVP: "DeskVoid Proto"

- [x] Frame and IMU stream pipeline (GStreamer)
- [ ] ORB-SLAM3 stereo+IMU integration
- [ ] Joy-Con capture for minimal tracked input
- [ ] SteamVR pose injection
- [ ] Head pose linked to XR desktop shell (xrdesktop / OpenVR)

---

## 🧱 Phase 2: VoidShell

- [ ] Godot-based spatial shell (XR-capable scene)
- [ ] STL viewer panel
- [ ] Hand gesture mapping
- [ ] UI sound pack loader

---

## 🌍 Phase 3: 

- [ ] Passthrough, webcam mode for cam sharing
- [ ] API
- [ ] 3D filesystem interface (Blender, etc)

---

## 💫 Stretch Concepts

- [ ] Anchor apps in space via local loop closure
- [ ] IMU-only gesture typing (requires training)
- [ ] peripheral integration
- [ ] Cross-device spatial mirroring (experimental)

---

## 🤝 Contributing

- Test stereo/IMU pose accuracy  
- Help package the OpenVR HMD driver  
- Mock up spatial UI layouts or sound packs  

---

## 🪪 License

GLP-3 — use it, fork it, extend it.  
Just don’t try to shove it in Unity, we did all that to escape it!

---

*Last updated: 2025-05-04 by @deskunreal*
