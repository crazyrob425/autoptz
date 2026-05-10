# AI-Stalker: Executive Summary (5-Minute Read)

**Date:** May 9, 2026 | **Status:** Alpha (Single-node working, Multi-node planning complete)

---

## 📊 COMPLETION STATUS

```
PHASE 0: Core Features (DONE - 100%)
├─ ✅ Qt UI with camera discovery
├─ ✅ USB + NDI camera streaming
├─ ✅ Facial recognition & tracking
├─ ✅ PTZ automation (VISCA USB + Network)
├─ ✅ MediaPipe body pose estimation
└─ ✅ Async multiprocess architecture

PHASE 1: Multi-Node Failover (PLANNED - 0%)
├─ ❌ Raft-based leader election
├─ ❌ Memberlist health checking
├─ ❌ Syncthing config sync
├─ ❌ NATS event bus
└─ ❌ Cluster dashboard

PHASE 2: AI Orchestration (FUTURE)
├─ ❌ OpenVINO inference
├─ ❌ Triton model server
├─ ❌ Event summarization
└─ ❌ LLM integration

OVERALL: 25% complete (Phase 0 done, Phase 1 ready to start)
```

---

## 🎯 WHAT'S WORKING NOW

1. **Live camera feeds** (USB hardware + NDI network)
   - Real-time streaming at 30 FPS
   - Multiple cameras simultaneously
   - Smooth Qt UI display

2. **Face detection & tracking**
   - Face detection every ~4 sec
   - Confidence scoring
   - Database of known faces (pickle-based)
   - Add/remove faces via UI dialogs

3. **Automated PTZ control**
   - Manual pan/tilt/zoom/focus
   - **Auto-tracking:** Face centroid tracked via Dlib + adaptive speed
   - USB VISCA (serial) + Network VISCA (IP) both supported

4. **Body pose estimation**
   - MediaPipe landmarks (head/shoulders/waist)
   - Bounding box extraction
   - Integrated with face tracking for stability

---

## ❌ CRITICAL GAPS

| Gap | Impact | Timeline |
|---|---|---|
| **No multi-node cluster** | Can't failover; single point of failure | Phase 1 (Weeks 2–3) |
| **No event bus** | Face detections stay on single node | Phase 1 (Week 4) |
| **No local AI runtime** | Limited to face detection + pose only | Phase 2 (Weeks 7–10) |
| **No event summaries** | No "who arrived/left" narratives | Phase 2 |
| **No observability** | Blind to cluster health / errors | Phase 1 (Week 6) |

---

## 🚀 MVP ROADMAP: 6 WEEKS TO PRODUCTION

### Week 1: Foundation
- Add Python logging (replace `print()`)
- Config file loader (`.env` + YAML)
- GitHub Actions CI/CD
- **Deliverable:** Dev environment ready

### Weeks 2–3: Cluster Fabric
- Raft leader election (Dragonboat)
- Memberlist gossip + health tracking
- Syncthing file sync
- Virtual IP failover (keepalived/NLB)
- **Deliverable:** 2-node failover working (<2 min takeover)

### Week 4: Event Bus
- NATS server + clustering
- Python client integration
- Wire camera events to NATS topics
- **Deliverable:** Multi-node events flowing

### Weeks 5–6: UI + Operations
- Cluster status dashboard
- Manual failover controls
- Failover playbooks + test scenarios
- **Deliverable:** MVP dashboard + docs

**Total: 6 weeks, 1 developer, production-ready 2-node failover cluster**

---

## 🏗️ ARCHITECTURE (AFTER MVP)

```
TWO-NODE CLUSTER:

  Primary Node                    Secondary Node
  ├─ Recording cameras           ├─ Receives replicated frames
  ├─ Face detection              ├─ Watches for primary failure
  ├─ PTZ tracking                ├─ Synced encodings + config
  ├─ Owns VIP (192.168.1.100)    ├─ Ready to promote
  │                              │
  └─ Raft LEADER ────────────→ FOLLOWER (election timeout: 5 min)
     │                           
     ├─ NATS: Publish events ── → Subscribe + log
     ├─ Syncthing: Sync files ─ → Sync files
     └─ Zenoh: Stream frames ── → Shadow copy
     
On Primary Failure → Secondary PROMOTES → Assumes VIP → Continues recording
```

---

## 📋 IMMEDIATE NEXT STEPS

**This Week:**
1. Review & approve roadmap
2. Assign developer + setup Jira tickets
3. Create cluster architecture diagram

**Week 1:**
1. Add `logging` module (replace all print statements)
2. Create `.env` config loader + YAML parser
3. Setup GitHub Actions (lint + basic tests)
4. Document Raft integration approach

**Week 2:**
1. Start Dragonboat POC (Raft leader election)
2. Add Memberlist health tracking
3. Test 2-node cluster formation

---

## 💡 KEY DECISIONS FOR MVP

| Decision | Why | Tradeoff |
|---|---|---|
| **Dragonboat for Raft** | Simpler than hashicorp/raft | Adds Go dependency (via wrapper) |
| **Syncthing for sync** | Cross-platform, battle-tested | Eventual consistency only |
| **NATS for events** | Lightweight clustering + pub/sub | Requires separate server |
| **Keepalived for VIP** | Linux standard; Windows NLB alternative | More complex than DNS-based failover |
| **Docker Compose for testing** | No real hardware needed | Docker dependency for local dev |

---

## 🎓 SUCCESS CRITERIA

Before Phase 2, MVP must pass:
- ✅ 2 nodes form cluster + elect leader
- ✅ Secondary promotes to primary in <configured timeout
- ✅ Config syncs across nodes <5 sec
- ✅ UI shows cluster status
- ✅ Operator can manually trigger failover
- ✅ <30 sec event loss during failover
- ✅ All tests pass (Windows + Linux)

---

## 📞 RESOURCES NEEDED

- **1 Full-time developer** (6 weeks)
- **2 Test machines** (Linux + Windows)
- **Docker Compose** (local cluster simulation)
- **DevOps support** (part-time, for infra questions)

---

## 🔮 BEYOND MVP (Phase 2–4)

**Phase 2 (Weeks 7–10):** AI Orchestration
- Local OpenVINO inference
- Event summarization (arrival/departure graphs)

**Phase 3 (Weeks 11–13):** Hive Compute Pooling
- Idle resource detection
- Distributed inference to secondary nodes

**Phase 4 (Weeks 14–16):** Smart Device Integration
- Home Assistant bridge
- Zigbee + audio alerts

---

## 📚 DOCUMENTATION CREATED

✅ [PROJECT_STATUS_ROADMAP.md](PROJECT_STATUS_ROADMAP.md) — Comprehensive 50+ page roadmap  
✅ [QUICK_STATUS.md](QUICK_STATUS.md) — 2-page summary  
✅ [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md) — Current vs. planned architecture  
✅ [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) — This file (for stakeholders)

---

## ⚡ BOTTOM LINE

**AI-Stalker is 25% complete.** 

✅ **The hard part (single-node AI/PTZ):** DONE and working great.

❌ **The next phase (multi-node failover):** Planned, 6-week timeline, ready to execute.

**Risk Level:** Low (no exotic dependencies; battle-tested tech stack)

**Go/No-Go:** **GO** ✅ — Recommend starting Week 1 tasks immediately.

---

**Owner:** Rob Branting | **Org:** Blacklisted Binary Labs  
**Last Updated:** May 9, 2026 | **Next Review:** May 16, 2026
