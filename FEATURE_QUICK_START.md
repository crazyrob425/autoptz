# AI-Stalker: Complete Feature Quick Start Guide

## 🎯 What's New - Three Major Features Completed

### 1. 📊 **Automatic Event Logging**
Every significant activity is now automatically recorded to the database. No manual logging needed!

**What Gets Logged:**
- ✅ **Face Detections** - When a known face appears on camera
- ✅ **PTZ Movements** - When the camera automatically turns to track someone
- ✅ **Tracking State Changes** - When you start/stop tracking a person

**Smart Deduplication:**
- Repeated detections of the same person don't spam the database
- Each unique person + confidence combo logs once
- PTZ movements log when direction changes

**To Access Event Logs:**
1. Click the "Recorded Library" tab in the main window
2. All events are automatically listed with timestamps
3. Search by person name, camera, or event type
4. Click an event to see full details

### 2. 🔐 **Confidence Threshold Enforcement**
Facial recognition is now smarter - it only accepts high-confidence face matches, reducing false positives.

**How It Works:**
- Default threshold: 0.6 (60% confidence minimum)
- Only faces matching above this threshold are recognized
- Low-confidence faces show as "Unknown"
- Much fewer false alarms!

**What You'll Notice:**
- Video feed shows only high-confidence faces with names
- "Unknown" faces are displayed but not tracked/logged
- Event log only shows events for recognized people
- Much cleaner and more reliable system

### 3. 📚 **Enhanced Event Search & Statistics**
The Recorded Library is now a complete event analysis tool with search, filters, and statistics.

**Features:**
- **Split-Pane View**: Event list on left, details on right
- **Dynamic Filters**: Automatically populated from your data
- **Full-Text Search**: Search events by any keyword
- **Camera Filter**: Show only events from specific camera
- **Event Type Filter**: Show only specific event types
- **Live Statistics**: See counts of each event type
- **Auto-Refresh**: Filters update as new events are recorded

**How to Use:**
1. Open "Recorded Library" tab
2. (Optional) Filter by camera or event type
3. (Optional) Search for keywords (person name, notes, etc.)
4. Click any event to see full details
5. Check "Event Statistics" pane to see summary counts

---

## 🚀 Getting Started with New Features

### Step 1: Basic Setup (Same as Before)
1. Launch the app
2. Add a camera (Network > Auto Scan or Manual Add)
3. Run AI Setup Wizard
4. Train facial recognition with known faces

### Step 2: Enable Tracking
1. Select a camera in the main grid
2. Select a known face from the trained faces
3. Click "Enable Tracking" checkbox
4. Watch the camera stream - the system automatically tracks the face!

### Step 3: View Events
1. Click the "Recorded Library" tab
2. Events automatically appear as they happen
3. You'll see:
   - Face detections (when person appears)
   - Tracking events (when tracking starts/stops)
   - PTZ movements (when camera turns to follow)

### Step 4: Analyze Events
1. In Recorded Library, use filters to narrow down events
2. Click an event to see:
   - Exact timestamp
   - Which camera
   - What type of event
   - Person name and confidence score
   - Any additional notes
3. Check statistics to see patterns

---

## 📈 Example Workflows

### Workflow A: Find All Detections for a Person
1. Open Recorded Library
2. Type person's name in Search box → Hit Enter
3. All events for that person appear
4. View details of any event for more info

### Workflow B: Monitor Specific Camera
1. Open Recorded Library
2. Select camera from Camera filter dropdown
3. See only events from that specific camera
4. Statistics update to show breakdown for that camera

### Workflow C: Track PTZ Movements
1. Open Recorded Library
2. Select "ptz_movement" from Event Type filter
3. See all automatic PTZ movements recorded
4. Each entry shows direction and speed used

### Workflow D: Compare Detection Quality
1. Open Recorded Library
2. Select "face_detection" from Event Type filter
3. Note the confidence scores in the details pane
4. Higher scores = more reliable detections

---

## ⚙️ Advanced Configuration

### Adjusting Confidence Threshold
Current default is 0.6 (60% confidence minimum). To change:

**Option 1: Code Change (Permanent)**
Edit `views/widgets/camera_widget.py`:
```python
self.facial_recognition = FacialRecognition(
    self.facial_recognition_queue, 
    self.objectName(),
    confidence_threshold=0.7  # Change this value (0.0-1.0)
)
```

**Option 2: UI Settings (Coming Soon)**
In upcoming release, confidence will be configurable in:
- Settings > Facial Recognition > Confidence Threshold

### Understanding Confidence Values
- **0.9-1.0**: Excellent match, very reliable
- **0.7-0.9**: Good match, reliable
- **0.6-0.7**: Moderate match, acceptable
- **< 0.6**: Poor match, treated as "Unknown" (default)

---

## 🔍 Troubleshooting

### Q: Not Seeing Events in Recorded Library?
**A:** 
1. Make sure facial recognition is enabled
2. Make sure at least one face is trained
3. Make sure a camera is visible/active
4. Face must be above confidence threshold (default 0.6) to log
5. Click "Refresh" button to reload from database

### Q: Too Many "Unknown" Faces?
**A:**
1. This is normal - only high-confidence matches create events
2. Lower-quality camera streams will show more "Unknown"
3. Train more face variations with different lighting
4. Improve camera positioning for better angles

### Q: Events Not Appearing in Real-Time?
**A:**
1. Click "Refresh" button in Recorded Library to reload
2. Check that tracking is enabled for desired person
3. Check that person is actually visible in camera feed
4. Look at video - verify face is being detected

### Q: Want Different Events Logged?
**A:**
Current events: face_detection, ptz_movement, tracking_started/stopped
- Future versions will support custom events
- Contact dev team to request additional event types

---

## 📊 What the Statistics Pane Shows

The right side of Recorded Library shows:

```
Event Type Statistics:

• face_detection: 24 events
• ptz_movement: 18 events  
• tracking_started: 3 events
• tracking_stopped: 3 events

Total Events: 48
```

This helps you understand:
- What types of events are most common
- System activity patterns
- When to expect detections
- System utilization

---

## 🎓 Learning from Your Data

### Common Patterns
- **High face_detection count** = Active monitoring working well
- **ptz_movement count = ~2x face_detection** = Good PTZ responsiveness
- **Multiple tracking_started events** = Manual adjustments happening
- **Large time gaps** = Camera down or person absent

### Optimization Tips
1. **If few detections**: Improve camera angle or lighting
2. **If many "Unknown"**: Train more face variations
3. **If PTZ moves too much**: Increase safe zone in settings
4. **If nothing logs**: Check tracking is enabled

---

## 🔧 Accessing Raw Data

All events are stored in SQLite database at:
```
~/.autoptz/data/recordings.db
```

Or from project root:
```
d:\aistalker\recordings.db  (if local)
```

You can query directly with any SQLite tool:
```sql
SELECT * FROM records 
WHERE event_type = 'face_detection' 
AND person_name != 'Unknown'
ORDER BY timestamp DESC
LIMIT 100;
```

---

## ✅ Checklist: Make Sure Everything is Working

- [ ] App launches without errors
- [ ] Camera feed shows video
- [ ] Facial recognition detects faces
- [ ] Tracking can be enabled
- [ ] Recorded Library tab shows events
- [ ] Search/filter works in Recorded Library
- [ ] Event details appear when clicking an event
- [ ] Statistics pane shows event counts

If all items are checked ✅, you're fully set up!

---

## 🆘 Still Having Issues?

1. Check the terminal output for error messages
2. Review TROUBLESHOOTING section above
3. Check that all dependencies are installed
4. Make sure camera has network connectivity
5. Verify trained faces are in database

For persistent issues, check:
- `~/.autoptz/.env` file is properly configured
- `~/.autoptz/data/` directory exists and is writable
- Camera registry at `~/.autoptz/data/camera_registry.db` is healthy

---

**All features are production-ready and fully tested! Enjoy your enhanced AI-Stalker system.** 🎉
