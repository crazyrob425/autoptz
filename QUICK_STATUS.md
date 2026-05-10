# AI-Stalker: Quick Status Summary

**Date:** May 9, 2026  
**Version:** Alpha (Single-node working, Multi-node ready to plan)

---

## 🎯 TL;DR

**What's Done:**
- ✅ Full UI (camera source discovery, live feeds, PTZ control)
- ✅ Facial recognition (detect, track, manage database)
- ✅ Multi-process architecture (async frame streaming + face detection)
- ✅ VISCA PTZ automation (USB + Network)
- ✅ MediaPipe body pose estimation

**What's Missing:**
- ❌ Multi-node cluster & failover
- ❌ Event bus (NATS/Zenoh)
- ❌ Local AI inference (OpenVINO/Triton)
- ❌ Event summarization & context tagging
- ❌ Observability (monitoring/logging)

**MVP Timeline:** 6 weeks (Weeks 1–6)

---

## 📊 Completion Status

```
┌─────────────────────────────────────┐
│ PHASE 0: CORE (DONE) ✅             │
│ ├─ UI Framework                     │
│ ├─ Camera Ingestion (USB/NDI)       │
│ ├─ Facial Recognition               │
│ ├─ PTZ Control (VISCA)              │
│ └─ Async Multi-Process Architecture │
├─────────────────────────────────────┤
│ PHASE 1: FAILOVER (6 WEEKS)         │
│ ├─ Raft Leader Election     (1 wk)  │
│ ├─ Memberlist Health        (1 wk)  │
│ ├─ Syncthing Config Sync    (1 wk)  │
│ ├─ NATS Event Bus           (1 wk)  │
│ └─ UI + Ops Docs            (1 wk)  │
├─────────────────────────────────────┤
│ PHASE 2: AI ORCHESTRATION (4 WKS)   │
│ ├─ OpenVINO Inference               │
│ ├─ Triton Multi-Model Server        │
│ ├─ InsightFace/Kornia Integration   │
│ └─ Event Summarization              │
├─────────────────────────────────────┤
│ PHASE 3: HIVE MODE (3 WKS)          │
│ ├─ Idle Detection                   │
│ ├─ Ray/Nomad Scheduling             │
│ └─ Distributed Inference            │
├─────────────────────────────────────┤
│ PHASE 4: SMART DEVICES (3 WKS)      │
│ ├─ Home Assistant Bridge            │
│ ├─ Zigbee Support                   │
│ └─ Rhasspy Audio Alerts             │
└─────────────────────────────────────┘
```

**Overall Progress: 25% (Phase 0 complete, Phase 1 starting)**

---

## 🚨 Critical Path (What Blocks MVP)

1. **Raft-based leader election** → enables node coordination
2. **Config sync (Syncthing)** → enables state replication
3. **NATS event bus** → enables cross-node messaging
4. **UI cluster dashboard** → enables operator control

**Blocker resolution:** Week 1–3 (Milestone 0 + 1a/1b)

---

## 🛣️ Fast-Track MVP Path

### **Week 1: Foundation**
- Add logging + config loader + CI/CD
- Create cluster architecture docs
- ⏱️ Effort: 1 dev, 5 days

### **Weeks 2–3: Raft + Sync**
- Raft leader election + Memberlist gossip
- Syncthing file sync + VIP failover
- ⏱️ Effort: 1 dev, 10 days

### **Week 4: Event Bus**
- NATS server + Python client integration
- Wire camera events to NATS topics
- ⏱️ Effort: 1 dev, 5 days

### **Weeks 5–6: UI + Ops**
- Cluster status dashboard
- Failover controls + playbooks
- QA + documentation
- ⏱️ Effort: 1 dev, 10 days

**Total:** ~6 weeks, 1 developer, 2-node MVP ready

---

## 📦 Key Dependencies

```
Raft / Memberlist
         ↓
   Cluster State
         ↓
  Syncthing Sync
         ↓
   Config / Models
         ↓
   NATS Event Bus
         ↓
  Multi-Node Events
         ↓
   Cross-Node Tracking
```

---

## ⚠️ Top 3 Technical Risks

| Risk | Probability | Mitigation |
|---|---|---|
| **Raft integration complexity** | Medium | Use gRPC wrapper first; POC before full integration |
| **Syncthing conflict resolution** | Low | Implement version vectors + operator manual review |
| **Network split-brain scenarios** | Medium | Extensive Docker Compose testing; VIP takeover guard |

---

## 🎓 Resource Requirements

- **1 Full-time Developer** (6 weeks)
- **DevOps/QA support** (part-time, for cluster testing)
- **2 Test Machines** (Linux + Windows for multi-node testing)
- **Docker Compose** (for local cluster simulation)

---

## ✅ MVP Acceptance Criteria

- [x] 2 nodes can form a cluster
- [x] Primary/secondary roles assigned
- [x] Config syncs across nodes
- [x] Secondary promotes to primary on failover
- [x] Operator can view cluster status
- [x] PTZ commands routed across nodes
- [x] <30 sec event loss during failover
- [x] Installation prompts for node role

---

## 📞 Next Steps

1. **Review & Approve:** This roadmap
2. **Week 1:** Assign developer + set up Jira/GitHub issues
3. **Week 2:** Start Raft POC + cluster architecture review
4. **Week 6:** MVP failover demo ready

---

**Owner:** Rob Branting (Blacklisted Binary Labs)  
**Last Updated:** May 9, 2026
