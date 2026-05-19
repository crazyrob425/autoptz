# TODO - Auto Patrol + RTSP PTZ Follow (AI Enhanced)

## Progress
- [x] MobileNetSSD assets missing check complete (repo has only backups; no caffemodel/prototxt present)
- [ ] Implement ONVIF PTZ controller driver for continuous pan/tilt + stop
- [ ] Add MobileNetSSD person detector pipeline
- [ ] Add patrol state machine (sweep when idle)
- [ ] Add follow-any-person behavior on detection
- [ ] Add UI controls for Patrol Mode + Follow
- [ ] Auto-assign ONVIF PTZ controller for RTSP cameras (prompt/best-effort)
- [ ] Smoke-test: sweep -> detect -> follow -> resume patrol

