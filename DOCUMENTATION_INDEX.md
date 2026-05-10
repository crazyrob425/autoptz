# AI-Stalker Documentation Index

**Generated:** May 9, 2026  
**Purpose:** Central hub for project status, architecture, and roadmap

---

## 📋 QUICK LINKS

### 🎯 For Decision Makers (5 minutes)
Start here if you need to know project status + approval decision:
- **[EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** — Status, gaps, 6-week MVP roadmap, resources needed

### 📊 For Project Managers (15 minutes)
Start here to understand timeline + milestones:
- **[QUICK_STATUS.md](QUICK_STATUS.md)** — Completion %s, phase breakdown, fast-track path

### 🏗️ For Architects & Developers (30 minutes)
Start here to understand current vs. planned architecture:
- **[ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md)** — Detailed system diagrams, failover flows, tech stack decisions

### 📖 For Full Deep Dive (60 minutes)
Complete reference document with all details:
- **[PROJECT_STATUS_ROADMAP.md](PROJECT_STATUS_ROADMAP.md)** — Comprehensive 50+ page analysis + roadmap

---

## 🗂️ DOCUMENT SUMMARY

| Document | Length | Audience | Key Content |
|---|---|---|---|
| **EXECUTIVE_SUMMARY.md** | 3 pages | Stakeholders | Status %, gaps, 6-week timeline, resources |
| **QUICK_STATUS.md** | 2 pages | Managers | Phase breakdown, progress %, fast-track path |
| **ARCHITECTURE_GUIDE.md** | 15 pages | Architects | Current vs. planned diagrams, failover flows |
| **PROJECT_STATUS_ROADMAP.md** | 50+ pages | Developers | Comprehensive analysis, milestone details, risks |
| **README.md** | Original project README | Users | Product features, capabilities, installation |
| **PROJECT_ENDGOALS.md** | Original end goals | Contributors | Project vision, non-negotiable principles |
| **AI_STALKER_IMPLEMENTATION_BLUEPRINT.md** | Original blueprint | Architects | Phase definitions, integration inventory |

---

## 🎯 CURRENT STATUS AT A GLANCE

```
PHASE 0: Core Features (DONE ✅)
├─ ✅ Qt UI with camera discovery
├─ ✅ USB + NDI streaming
├─ ✅ Facial recognition & tracking
├─ ✅ PTZ automation (VISCA)
└─ ✅ Async multiprocess architecture

PHASE 1: Multi-Node Failover (6 WEEKS)
├─ ⏳ Raft leader election (Weeks 2–3)
├─ ⏳ Memberlist + Syncthing (Weeks 2–3)
├─ ⏳ NATS event bus (Week 4)
└─ ⏳ Cluster UI + ops (Weeks 5–6)

PHASE 2+: AI Orchestration, Hive Mode, Smart Devices (Future)

OVERALL: 25% complete (Phase 0 done, Phase 1 ready to start)
```

---

## 📊 FILE COMPLETION STATUS

| File | Status | Last Updated | Notes |
|---|---|---|---|
| [startup.py](startup.py) | ✅ Working | N/A | Application entry point |
| [views/homepage/main_window.py](views/homepage/main_window.py) | ✅ Working | N/A | Main UI + camera management |
| [views/widgets/camera_widget.py](views/widgets/camera_widget.py) | ✅ Working | N/A | Per-camera async processing |
| [logic/image_processing/facial_recognition.py](logic/image_processing/facial_recognition.py) | ✅ Working | N/A | Face detection + tracking |
| [libraries/visca/camera.py](libraries/visca/camera.py) | ✅ Working | N/A | USB VISCA control |
| [libraries/visca/move_visca_ptz.py](libraries/visca/move_visca_ptz.py) | ✅ Working | N/A | PTZ movement wrapper |
| **All Phase 1+ components** | ❌ Not started | N/A | Raft, Memberlist, Syncthing, NATS, etc. |

---

## 🎓 HOW TO USE THESE DOCS

### For Your First Time
1. Read **EXECUTIVE_SUMMARY.md** (5 min) → understand status + decision
2. Skim **QUICK_STATUS.md** (5 min) → see timeline at high level
3. Review **ARCHITECTURE_GUIDE.md** (15 min) → understand technical design

### For Detailed Implementation
1. Start with **PROJECT_STATUS_ROADMAP.md** Milestone 0 section
2. Create GitHub Issues for each task (Week 1 + 2 items)
3. Reference specific sections as you implement

### For Code Review / Debugging
1. Check **ARCHITECTURE_GUIDE.md** "Current Architecture" section
2. Search [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md) for component name (e.g., "CameraWidget")
3. Cross-reference with source files for implementation details

### For Stakeholder Updates
1. Copy **EXECUTIVE_SUMMARY.md** status % into weekly report
2. Update completion % as milestones complete
3. Share **QUICK_STATUS.md** in all-hands meetings

---

## 🚀 NEXT IMMEDIATE ACTIONS

### This Week
- [ ] Review all 4 documents (focus on EXECUTIVE_SUMMARY + QUICK_STATUS)
- [ ] Approve 6-week timeline + resources
- [ ] Assign developer + setup Jira board

### Week 1 (Foundation)
- [ ] Add Python `logging` module (replace print statements)
- [ ] Create `.env` config loader
- [ ] Setup GitHub Actions CI/CD
- [ ] Document Raft integration approach

### Weeks 2–6 (Execution)
- See detailed milestones in [PROJECT_STATUS_ROADMAP.md](PROJECT_STATUS_ROADMAP.md) Sections 3–5

---

## 🔗 CROSS-REFERENCES

**If you want to understand:**

- **What's done?** → Read EXECUTIVE_SUMMARY.md "What's Working Now" section
- **What's missing?** → Read QUICK_STATUS.md "Fast-Track MVP Path" OR PROJECT_STATUS_ROADMAP.md "Critical Gaps"
- **How does failover work?** → Read ARCHITECTURE_GUIDE.md "Failover Scenario" section
- **What's the tech stack?** → Read ARCHITECTURE_GUIDE.md "Tech Stack Mapping" table
- **When will X be done?** → Search PROJECT_STATUS_ROADMAP.md for milestone timeline
- **What are risks?** → Read PROJECT_STATUS_ROADMAP.md "Risks" section OR EXECUTIVE_SUMMARY.md "Risk Level"

---

## 📞 QUESTIONS?

| Question | Answer Location |
|---|---|
| What's the current status? | EXECUTIVE_SUMMARY.md, Section "Completion Status" |
| How long to MVP? | QUICK_STATUS.md, Section "Fast-Track MVP Path" |
| What's our tech stack? | ARCHITECTURE_GUIDE.md, Section "Tech Stack Mapping" |
| What could go wrong? | PROJECT_STATUS_ROADMAP.md, Section "Risk Assessment" |
| How do we test failover? | PROJECT_STATUS_ROADMAP.md, Section "Milestone Validation" |
| What does the UI look like? | [views/homepage/main_window.py](views/homepage/main_window.py) (code) |
| Can this run on Windows? | Yes — native PySide6 + Windows Installer (Inno Setup) |
| Can this run on macOS? | Yes — PySide6 is cross-platform; NDI support needed |
| Can this run on Linux? | Yes — all dependencies available; RTSP support planned |

---

## 📝 DOCUMENT MAINTENANCE

**These docs are living documents.** Update them as you:
- Complete milestones (change status from ⏳ to ✅)
- Discover new risks (add to risk table)
- Make tech stack changes (update stack diagram)
- Adjust timeline (update roadmap section)

**Recommended Update Frequency:**
- Weekly: QUICK_STATUS.md completion percentages
- Bi-weekly: ARCHITECTURE_GUIDE.md after major decisions
- Monthly: PROJECT_STATUS_ROADMAP.md comprehensive review

---

## 🎓 RECOMMENDED READING ORDER

**For Developers:**
1. QUICK_STATUS.md (overview)
2. ARCHITECTURE_GUIDE.md (understand current system + failover)
3. PROJECT_STATUS_ROADMAP.md Milestone 0 section (start coding)

**For Architects:**
1. EXECUTIVE_SUMMARY.md (status)
2. ARCHITECTURE_GUIDE.md (all sections)
3. PROJECT_STATUS_ROADMAP.md sections 1–5 (design decisions)

**For Managers:**
1. EXECUTIVE_SUMMARY.md (all sections)
2. QUICK_STATUS.md (timeline)
3. ARCHITECTURE_GUIDE.md (risks section only)

**For QA/Testing:**
1. QUICK_STATUS.md (what's done)
2. PROJECT_STATUS_ROADMAP.md "Validation Checklists" (test scenarios)
3. ARCHITECTURE_GUIDE.md "Failover Scenario" (failover tests)

---

## ✅ DOCUMENT CHECKLIST

- [x] EXECUTIVE_SUMMARY.md — 5-min status for stakeholders
- [x] QUICK_STATUS.md — 2-page visual summary
- [x] ARCHITECTURE_GUIDE.md — Current vs. planned diagrams
- [x] PROJECT_STATUS_ROADMAP.md — 50+ page comprehensive analysis
- [x] DOCUMENTATION_INDEX.md — This file

**All documentation complete and ready for review.** ✅

---

**Owner:** Rob Branting | **Org:** Blacklisted Binary Labs  
**Created:** May 9, 2026  
**Last Updated:** May 9, 2026

---

### 🎯 TL;DR
- **Status:** 25% complete (Core features done, multi-node failover planned)
- **MVP Timeline:** 6 weeks (1 developer)
- **Next Step:** Approve roadmap → start Week 1 foundation tasks
- **Recommendation:** GO ✅ Ready to execute

**Questions?** Refer to this index or the individual documents above.
