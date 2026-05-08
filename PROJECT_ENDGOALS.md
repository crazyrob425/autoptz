# AI-Stalker — Project End Goals & What We’re Building

## What this project is
**AI-Stalker** is an **AI-powered, locally-run, fail-safe security monitoring platform** that evolves AutoPTZ into a **multi-node security orchestrator**. The system is designed to coordinate security sensors (cameras, microphones, and other authorized devices) and produce **real-time events and operator-visible context**.

## Non-negotiable principles (how contributors must frame the project)
- **Consent-based, authorized use only.** The platform is built for environments where the operator has permission to monitor and record (home/office security, personal assets, properly authorized camera placements).
- **Fully local-first operation.** Sensitive video and metadata should remain on the user’s hardware by default (offline-first). Cloud AI is optional.
- **Zero paywall / no forced upgrade paths.** No “pro” tiers for core functionality. No subscription gates for features, upgrades, or recovery.
- **Reproducibility + auditability.** Designs and integrations should be explainable, inspectable, and maintainable.
- **Defensive engineering.** We build safeguards and resilience—not “mischief.”

> Contributors: when describing features, treat “repurposed / security appliance / failsafe node” as **authorized, user-installed device automation** for the app’s own local recording and monitoring—not anything involving unauthorized access.

## Overall end goals
### 1) A real, dependable local NVR + security AI
- A true security workflow: ingest → analyze → alert → record → summarize → store.
- Works with **USB cameras**, **NDI**, and planned **IP camera streaming (RTSP/ONVIF)**.
- Integrated **PTZ automation** (VISCA), coordinated with AI-driven tracking.

### 2) Advanced tracking and event understanding (all local)
- **AI people tracking** that stays stable across frames/cameras.
- **Facial recognition + profiling workflows** designed for operator control:
  - **Trusted/ignored identities** (to reduce noise and operator fatigue).
  - **High-risk identities** prioritized for attention.
  - Event-level summaries for what happened during a visit.
- **Behavioral context tagging** to provide operator awareness (e.g., distress, erratic movement, or falls) where the system can do so reliably.
- **Alert categories** for likely theft / violence / suspicious behavior patterns (implementation must be careful, conservative, and explainable).
- **Context capture**:
  - Who appeared (or stayed), and where.
  - When they arrived and when they left.
  - Who they interacted with (correlated identities).
  - What they brought / carried / removed (as supported by the implemented sensors + CV pipelines).

### 3) A multi-node “security hive” with automatic failover
- A **leader/failsafe chain** so recording and alerting continue if the primary node goes down.
- **Automatic takeover** with minimal or no user intervention.
- Configuration and relevant metadata/models are **synced** across nodes.
- Optional replication strategy (e.g., block-level or config+DB replication) to achieve resilience.

### 4) Idle-resource pooling across household computers
- The system should be able to use **idle compute** on other trusted household machines.
- It must never degrade normal usage:
  - Detect “idle” safely.
  - Activate only when idle thresholds are met.
  - Retreat immediately when the user resumes activity.

### 5) Full control for the operator (no paywalls)
- Core capabilities—failover, recording, AI inference, tracking, device management—must remain available without subscription.
- Updates and installer improvements must not require “pro” entitlements.

### 6) Security-first by design
- Encrypt sensitive data in transit and at rest where feasible.
- Add audit trails for configuration and admin actions.
- Keep integration boundaries clear and reduce supply-chain risk.
- Default retention should be minimal and configurable.

## What we’re building (feature pillars)
1. **Local AI NVR pipelines**
   - Ingest: cameras/mics/sensors
   - Normalize streams
   - Run CV/AI inference locally
   - Record and index events

2. **AI-assisted PTZ + tracking**
   - Automated camera movement based on detections
   - Stable tracking logic and handoff behavior

3. **Identity workflows**
   - Trusted/ignored face handling to reduce false alarms
   - Priority tracking for high-risk identities

4. **Event summarization**
   - “Rundown while they visit” and “what happened when they left”
   - Interaction graphs (as supported by identity + tracking confidence)
   - Sensor-supported context (movement, crossings, objects carried where implemented)

5. **Failover / continuity of service**
   - Multi-node health monitoring
   - Promotion and takeover logic
   - Consistent recovery of configurations and state

6. **Hive mode compute sharing**
   - Idle scheduling and safe withdrawal
   - Distributed inference jobs to idle nodes

7. **Authorized device expansion**
   - Home automation integration (e.g., smart home workflows)
   - Repurposed, user-owned/installed devices as additional local sensors
   - Planned future: repurposed smartphones as auxiliary sensors (authorized use only)

## “No wrong ideas” clarification (terminology guardrail)
When we use energetic or playful phrasing (e.g., “stalker,” “hive mind,” “security streaming device,” “repurposed e-waste”), the engineering meaning is:
- **We are building a lawful, consent-based security system**.
- **We are automating only user-owned/authorized devices installed for this app’s monitoring**.
- **Failover** means continued operation via additional user-installed nodes, not exploitation.

## Target outcome
By the end state, AI-Stalker becomes:
- **100% free in all ways** (no paywall features; no pro tiers).
- A **local-first** advanced security monitoring system.
- A **resilient multi-node** fail-safe NVR/orchestrator.
- An operator-friendly platform that turns video + sensor signals into **useful, explainable security context**—without unnecessary cloud dependency.

