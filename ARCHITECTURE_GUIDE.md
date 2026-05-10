# AI-Stalker Architecture & Implementation Guide

**Purpose:** Clarify current architecture vs. planned multi-node architecture

---

## 🏗️ CURRENT ARCHITECTURE (TODAY)

```
┌─────────────────────────────────────────────────────────┐
│                    SINGLE NODE (ALPHA)                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │            Qt Main Window UI (PySide6)           │  │
│  │  • Tab 1: Auto (Face tracking + PTZ)            │  │
│  │  • Tab 2: Manual (Direct PTZ control)           │  │
│  │  • Menu: Sources (NDI/USB), Facial Recognition  │  │
│  └──────────────────────────────────────────────────┘  │
│                         ↑                               │
│  ┌──────────────────────────────────────────────────┐  │
│  │            Flow Layout (Camera Widgets)          │  │
│  │  • CameraWidget 1 (USB Camera)                  │  │
│  │  • CameraWidget 2 (NDI Source)                  │  │
│  │  • CameraWidget N...                            │  │
│  └──────────────────────────────────────────────────┘  │
│         ↑              ↑              ↑                 │
│    [Async]         [Async]         [Async]             │
│         │              │              │                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │        Multiprocess Architecture (Per Camera)    │  │
│  │                                                  │  │
│  │  Process 1: Camera Stream (USB/NDI)            │  │
│  │  ├─ OpenCV VideoCapture (USB)                  │  │
│  │  └─ NDI recv (Network)                         │  │
│  │  → Shared frame buffer (Queue, up to 120 frames)│  │
│  │                                                  │  │
│  │  Process 2: Facial Recognition (async)         │  │
│  │  ├─ face_recognition library                    │  │
│  │  ├─ Dlib correlation tracker                    │  │
│  │  └─ Pickle-based encoding database             │  │
│  │  → Detection results (Queue)                    │  │
│  │                                                  │  │
│  │  Process 3: Body Pose (MediaPipe, async)       │  │
│  │  ├─ MediaPipe Pose                              │  │
│  │  └─ Landmark bounding boxes                     │  │
│  │  → Pose results (Queue)                         │  │
│  │                                                  │  │
│  │  Main Thread: Draw + Display (30 FPS)          │  │
│  │  ├─ Merge face + pose + tracker                 │  │
│  │  ├─ Draw bounding boxes + labels               │  │
│  │  └─ Qt Timer update (1000/30 ms)               │  │
│  └──────────────────────────────────────────────────┘  │
│         ↓                                               │
│  ┌──────────────────────────────────────────────────┐  │
│  │         PTZ Control (VISCA)                      │  │
│  │                                                  │  │
│  │  USB VISCA:  Serial port (COM1, etc.)          │  │
│  │  ├─ Sony D100 protocol                          │  │
│  │  └─ Manual controls (left/right/up/down/zoom)  │  │
│  │                                                  │  │
│  │  Network VISCA (NDI-PTZ):                       │  │
│  │  ├─ visca_over_ip library                       │  │
│  │  └─ IP address + port-based connection          │  │
│  │                                                  │  │
│  │  Auto-Tracking:                                 │  │
│  │  ├─ Face centroid vs. frame center             │  │
│  │  ├─ Speed calculated from distance              │  │
│  │  └─ Commands sent every frame                   │  │
│  └──────────────────────────────────────────────────┘  │
│         ↓                                               │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Local Storage                           │  │
│  │  • encodings.pickle (face encodings)            │  │
│  │  • Config (ROOT_DIR hardcoded)                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Key Characteristics:**
- ✅ Single-node only
- ✅ Async multiprocess (smooth 30 FPS)
- ✅ All data local (no cloud)
- ❌ No cross-node communication
- ❌ No failover capability
- ❌ No observability

---

## 🎯 PHASE 1: MULTI-NODE FAILOVER (TARGET)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  MULTI-NODE CLUSTER (2-3 NODES)                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────┐  ┌────────────────────────────┐ │
│  │         PRIMARY NODE               │  │     SECONDARY NODE         │ │
│  │    (Leader, Active Recording)      │  │  (Standby, Shadow Tracking)│ │
│  ├────────────────────────────────────┤  ├────────────────────────────┤ │
│  │                                    │  │                            │ │
│  │  [UI Layer]                        │  │  [Dashboard Only]          │ │
│  │  • Full UI                         │  │  • Cluster status view     │ │
│  │  • Camera management               │  │  • Read-only mode (wait)   │ │
│  │  • PTZ control                     │  │                            │ │
│  │                                    │  │                            │ │
│  ├────────────────────────────────────┤  ├────────────────────────────┤ │
│  │                                    │  │                            │ │
│  │  [Camera Processing]               │  │  [Shadow Mode]             │ │
│  │  • Streams (USB + NDI)            │  │  • Receives replicated     │ │
│  │  • Face recognition                │  │    frame stream via Zenoh   │ │
│  │  • PTZ movement                    │  │  • Receives events via     │ │
│  │                                    │  │    NATS (read-only)        │ │
│  ├────────────────────────────────────┤  ├────────────────────────────┤ │
│  │                                    │  │                            │ │
│  │  [Cluster State]                   │  │  [Cluster State]           │ │
│  │  • Raft: LEADER                    │  │  • Raft: FOLLOWER          │ │
│  │  • Role: Primary (active)          │  │  • Role: Secondary (ready) │ │
│  │  • VIP: OWNS (192.168.1.100)       │  │  • VIP: LISTENING          │ │
│  │  • Memberlist: heartbeat out       │  │  • Memberlist: heartbeat   │ │
│  │                                    │  │                            │ │
│  ├────────────────────────────────────┤  ├────────────────────────────┤ │
│  │                                    │  │                            │ │
│  │  [Config Sync: Syncthing]          │  │  [Config Sync: Syncthing]  │ │
│  │  ├─ Watches: encodings.pickle      │  │  ├─ Watches: encodings.pkl │ │
│  │  ├─ Watches: config/               │  │  ├─ Watches: config/       │ │
│  │  ├─ Bi-directional sync <5s        │  │  └─ Bi-directional sync    │ │
│  │  └─ Conflicts: last-write-wins     │  │                            │ │
│  │                                    │  │                            │ │
│  ├────────────────────────────────────┤  ├────────────────────────────┤ │
│  │                                    │  │                            │ │
│  │  [Event Bus: NATS]                 │  │  [Event Bus: NATS]         │ │
│  │  • Publish:                        │  │  • Subscribe:              │ │
│  │    - events.detection              │  │    - events.detection      │ │
│  │    - events.alert                  │  │    - events.alert          │ │
│  │    - commands.ptz                  │  │    - health.node           │ │
│  │    - health.node                   │  │                            │ │
│  │                                    │  │                            │ │
│  ├────────────────────────────────────┤  ├────────────────────────────┤ │
│  │                                    │  │                            │ │
│  │  [Low-Latency Data: Zenoh]         │  │  [Low-Latency Data: Zenoh] │ │
│  │  • Publish frame stream            │  │  • Subscribe frame stream  │ │
│  │  • Key: /camera/{id}/frame         │  │  • Receive shadow copy     │ │
│  │                                    │  │                            │ │
│  └────────────────────────────────────┘  └────────────────────────────┘ │
│                    ↕                              ↕                      │
│         ┌──────────────────────────────────────────────────┐            │
│         │  CLUSTER CONTROL PLANE (Raft + Memberlist)     │            │
│         │                                                 │            │
│         │  • Leader election (primary vs. secondary)     │            │
│         │  • Membership tracking (alive/dead/suspect)    │            │
│         │  • Failover window: 1–60 min (configurable)    │            │
│         │  • VIP ownership (keepalived/NLB)              │            │
│         └──────────────────────────────────────────────────┘            │
│                    ↓                                                      │
│         ┌──────────────────────────────────────────────────┐            │
│         │  SHARED MESSAGE BROKER (NATS Cluster)          │            │
│         │                                                 │            │
│         │  Topics:                                       │            │
│         │  • events.detection (face found)              │            │
│         │  • events.alert (high-risk detected)          │            │
│         │  • commands.ptz (pan/tilt/zoom)               │            │
│         │  • health.node (heartbeat)                    │            │
│         │                                                 │            │
│         │  Guarantees:                                   │            │
│         │  • At-least-once delivery                     │            │
│         │  • Persistent storage (JetStream)             │            │
│         └──────────────────────────────────────────────────┘            │
│                    ↓                                                      │
│         ┌──────────────────────────────────────────────────┐            │
│         │  VIRTUAL IP (VIP: 192.168.1.100)               │            │
│         │                                                 │            │
│         │  • Primary owns VIP (keepalived/NLB)          │            │
│         │  • Secondary assumes on failover              │            │
│         │  • Clients connect via VIP (DNS)              │            │
│         │  • DNS TTL: 60 sec (minimal propagation lag)  │            │
│         └──────────────────────────────────────────────────┘            │
│                                                                          │
│  ┌────────────────────────────────────┐  ┌────────────────────────────┐ │
│  │         SHARED STORAGE              │  │  OPTIONAL REPLICATION    │ │
│  │      (Syncthing Network)            │  │  (DRBD Block-Level)      │ │
│  │                                    │  │                            │ │
│  │  ├─ config/                        │  │  Strict 1:1 mirror        │ │
│  │  ├─ encodings.pickle               │  │  For HA (not MVP)         │ │
│  │  ├─ ptz_presets/                   │  │                            │ │
│  │  └─ event_logs/                    │  │                            │ │
│  └────────────────────────────────────┘  └────────────────────────────┘ │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

FAILOVER SCENARIO
─────────────────────────────────────────────────────────────────────────

[T=0] Primary running normally
     • NATS: active
     • Raft: LEADER
     • VIP: OWNED (192.168.1.100)
     • Cameras: recording + tracking
     
[T=5 sec] Primary node CRASHES (power loss, network down, etc.)
     • Secondary detects missing heartbeat
     • Raft election triggered
     
[T=5–30 sec] Election in progress (configurable window)
     • Memberlist: primary marked as "SUSPECT" then "DEAD"
     • Secondary remains in FOLLOWER state
     
[T=30 sec] TIMEOUT REACHED (default: 5 min, but can be 1–60 min)
     • Secondary **PROMOTES to PRIMARY** (Raft: LEADER)
     • Synced config + encodings + models become active
     • Secondary assumes VIP (192.168.1.100)
     • NATS failover logic kicks in (persistent queue consumed)
     
[T=30–60 sec] FAILOVER COMPLETE ✅
     • Secondary is now PRIMARY (recording + tracking active)
     • UI updates to show new leader
     • Events resume flowing (with <30 sec gap acceptable for MVP)
     
[T=5+ min] Original Primary RECOVERS (rebooted, network restored)
     • Rejoins cluster as SECONDARY (follower)
     • Syncthing catches up all files
     • UI shows: 2 nodes, 1 primary + 1 secondary (ready for next failover)
```

**Failover Characteristics (MVP):**
- ✅ Automatic takeover (no manual intervention)
- ✅ <30 seconds event loss acceptable
- ✅ Config synced across nodes
- ✅ UI reflects cluster state
- ❌ No automatic failure detection at sub-5-sec level (depends on timeout config)
- ❌ No data replication (Syncthing eventual consistency only)

---

## 🔄 FAILOVER DECISION TREE

```
┌─────────────────────────────────┐
│  PRIMARY NODE                   │
│  Last heartbeat < NOW + TIMEOUT?│
└────────────────┬────────────────┘
                 │
         ┌───────┴────────┐
         │ NO             │ YES
         ↓                ↓
    STAY PRIMARY   PRIMARY DEAD?
                  (detected by Memberlist)
                         │
                    ┌────┴────┐
                    │          │
                   NO         YES
                    │          │
                    ↓          ↓
               WAIT        Raft Election
              (suspect)     Triggered
                            │
                       ┌────┴──────┐
                       │            │
                    SUCCESS      FAIL
                       │            │
                       ↓            ↓
                  SECONDARY    Try again
                BECOMES       (backoff)
                PRIMARY
                   │
                   ↓
            ┌──────────────┐
            │ VIP Transfer │ ← DNS clients fail over
            │ Syncthing    │
            │ Wake Services│
            └──────────────┘
                   │
                   ↓
            READY TO RECORD ✅
```

---

## 📡 MESSAGE FLOW (DURING OPERATION)

```
Camera 1 (USB)                    NATS Bus                    Secondary Node
    │                               │                               │
    ├─ Detect face                 │                               │
    ├─ Publish to NATS ─────────── events.detection ─ ─ ─ ─ ─ → Subscribe
    │                              │                               │
    ├─ Calculate PTZ move           │                               │
    ├─ Publish to NATS ─────────── commands.ptz                   (logged)
    │                              │                               │
    └─ Move camera                 │                               │
                                   │                               │
                                   Zenoh Bus                       │
                                   │                               │
                                   │ /camera/1/frame ─ ─ ─ ─ ─ → Receive
                                   │ (shadow stream)              (shadow copy)
                                   │
                            Health Heartbeat
                            │
          Primary ────────── heartbeat ────────────→ Secondary
          every 5 sec (or   (I am LEADER)           (confirm received)
          configurable)
```

---

## 🛠️ TECH STACK MAPPING

| Layer | Component | Technology | Purpose |
|---|---|---|---|
| **Consensus** | Leader Election | Dragonboat (or Raft gRPC) | Elect primary vs. secondary |
| **Membership** | Health Tracking | Memberlist | Detect node failures |
| **Config Sync** | File Replication | Syncthing | Replicate encodings + config |
| **Event Bus** | Message Broker | NATS | Pub/sub for detection events |
| **Data Streaming** | Low-Latency Frames | Zenoh | Shadow-copy frames on secondary |
| **VIP Failover** | Virtual IP | keepalived (Linux) / NLB (Windows) | DNS failover |
| **Process Mgmt** | Node Orchestration | Docker Compose / systemd | Service management |
| **Monitoring** | Observability | Netdata + Vector (Phase 2) | Dashboard + logging |

---

## 📝 CONFIGURATION EXAMPLE (YAML)

```yaml
# config.yaml (synced across all nodes)

cluster:
  name: "ai-stalker-hive-01"
  role: "primary"  # or "secondary" at startup
  node_id: "node-001"
  
raft:
  snapshot_interval: 3600  # seconds
  election_timeout: 300  # 5 minutes
  heartbeat_interval: 5   # seconds
  
memberlist:
  retransmit_mult: 3
  probe_interval: 5
  probe_timeout: 2
  suspicion_mult: 4
  
syncthing:
  api_key: "auto-generated"
  folders:
    - path: "./config"
      ignore_deletes: false
    - path: "./models/encodings.pickle"
      ignore_deletes: true  # never auto-delete encodings
      
nats:
  urls:
    - "nats://primary:4222"
    - "nats://secondary:4222"
  jetstream_enabled: true
  
zenoh:
  endpoints:
    - "tcp/primary:7447"
    - "tcp/secondary:7447"
    
vip:
  address: "192.168.1.100"
  port: 8080
  interface: "eth0"  # primary network interface
  
failover:
  timeout_seconds: 300  # 5 min for MVP
  auto_demote_on_recover: true  # recovered primary becomes secondary
  
cameras:
  - id: "cam-001"
    name: "Front Door"
    type: "usb"
    device: "COM1"
    ptz_type: "visca"
  - id: "cam-002"
    name: "Kitchen"
    type: "ndi"
    ndi_name: "KITCHEN\\Kitchen Camera"
    ptz_type: "ndi"
```

---

## ✅ MVP VALIDATION CHECKLIST

- [ ] 2 nodes form cluster + elect leader
- [ ] Config syncs across nodes in <5 sec
- [ ] Secondary becomes primary within timeout
- [ ] VIP follows primary (DNS clients reconnect)
- [ ] NATS event queue persists during failover (<30 sec loss ok)
- [ ] UI shows cluster status (primary/secondary, sync state)
- [ ] Operator can manually trigger failover
- [ ] Installer prompts for cluster role + node ID
- [ ] All tests pass on Windows + Linux

---

**Next:** Implement Milestone 0 (logging + config) to prep for Milestone 1a (Raft).
