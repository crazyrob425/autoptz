# 🤖 AI-Guided Camera Setup Wizard

## Overview

The **AI Setup Wizard** is an intelligent, conversational guide that walks you through discovering, configuring, and optimizing your IP cameras. It uses **Claude AI** with **Model Context Protocol (MCP)** to provide step-by-step guidance with automated camera capability detection.

## Key Features

### 🎯 Multi-Step Guided Setup
1. **Discovery** - Find all IP cameras on your network
2. **Capabilities** - Probe PTZ, audio, events, and supported profiles
3. **Configuration** - Set sensitivity thresholds and define trigger zones
4. **Summary** - Review and save your complete setup

### 🧠 Claude AI-Powered
- Natural language guidance through the entire setup process
- Claude makes intelligent decisions via MCP tool calling
- Explains each step and why it matters
- Handles edge cases and troubleshooting

### 🔧 MCP Tools Available to Claude
The wizard provides Claude with 7 powerful tools:

| Tool | Purpose |
|------|---------|
| `discover_cameras` | Scan network using NMAP + RTSP probing |
| `probe_camera_capabilities` | Get ONVIF GetCapabilities for PTZ/audio/events |
| `identify_driver_requirements` | Map manufacturer to driver needs |
| `configure_camera_sensitivity` | Set face confidence & motion thresholds |
| `define_trigger_zone` | Create ROI zones (rect/polygon/circle) |
| `test_camera_connection` | Verify reachability + auth |
| `get_setup_progress` | Query current wizard state |

## Usage

### Launching the Wizard

**Via Menu:**
1. Open AI-Stalker application
2. Click **Sources** → **🤖 AI Setup Wizard**
3. Click **Start Wizard**

**Programmatically:**
```python
from logic.ai_setup.mcp_camera_server import CameraSetupMCPServer
from logic.ai_setup.wizard_ai_controller import WizardAIController
from views.functions.setup_wizard import launch_setup_wizard

# Initialize MCP server and AI controller
mcp_server = CameraSetupMCPServer()
ai_controller = WizardAIController(mcp_server=mcp_server)

# Launch wizard (standalone or embedded)
wizard = launch_setup_wizard(parent=None, ai_controller=ai_controller, mcp_server=mcp_server)
wizard.exec()
```

### Step-by-Step Workflow

#### 1️⃣ Discovery Tab
- Click **Start Wizard** to begin
- Claude will scan your network for IP cameras
- Discovered cameras appear with IP, port, protocol, and confidence score
- Optional: Specify a subnet (e.g., `192.168.1.0/24`)

```
AI: Scanning your network for IP cameras...
   ✓ Found 3 cameras on your subnet
   - 192.168.1.100 (RTSP) - Confidence: 95%
   - 192.168.1.101 (HTTP) - Confidence: 87%
   - 192.168.1.102 (ONVIF) - Confidence: 92%
```

#### 2️⃣ Capabilities Tab
- Claude automatically probes each camera
- Displays: PTZ support, audio codecs, event capabilities, media profiles
- Shows firmware, manufacturer, model info
- Driver requirements are identified

```
Capabilities:
- Model: Hikvision DS-2CD2147G2
- Firmware: V5.5.42
- PTZ: ✓ Pan/Tilt/Zoom supported
- Audio: ✓ AAC codec
- Events: ✓ Motion detection
- Profiles: 1080p@30fps, 720p@30fps, D1@30fps
```

#### 3️⃣ Configuration Tab
**A) Sensitivity Settings**
- **Face Confidence Threshold** (0.0-1.0): How sure the AI must be to trigger face detection
  - Default: 0.7 (70% confidence)
  - Lower = more detections (but more false positives)
  - Higher = fewer detections (but higher accuracy)
- **Motion Threshold** (0.0-1.0): Sensitivity to movement
  - Default: 0.2 (very sensitive)
  - Useful for parking lots, hallways, blind spots

**B) Trigger Zones**
Define regions of interest (ROI) where you want monitoring:
- **Zone Name**: Descriptive name (e.g., "Entrance", "Parking Lot")
- **Zone Type**: 
  - Rectangle (easiest for doorways, gates)
  - Polygon (complex shapes like stairs)
  - Circle (round areas like specific desks)
- **Detection Type**: Face, Motion, or Person
- **Action on Detect**: Record, Alert, PTZ Focus, or Webhook

Example workflow:
```
1. Enter Zone Name: "Main Entrance"
2. Select Zone Type: Rectangle
3. Choose Detection Type: Face
4. Set Action: Record
5. Click "Add Trigger Zone"
6. Claude adds zone and saves coordinates
```

#### 4️⃣ Summary Tab
- Review all configured cameras
- See sensitivity settings per camera
- List all trigger zones
- Click **Save Configuration** to persist

### Configuration Example

```yaml
Discovered Cameras: 3
  - Hikvision DS-2CD2147G2 (192.168.1.100)
  - Dahua IPC-HDB5830CP (192.168.1.101)
  - Axis M3045-V (192.168.1.102)

Sensitivity:
  Camera 1:
    Face Confidence: 0.75
    Motion Threshold: 0.25
    Recording: Enabled
  Camera 2:
    Face Confidence: 0.70
    Motion Threshold: 0.20
    Recording: Enabled

Trigger Zones:
  Camera 1:
    - Zone: "Lobby" (Rectangle)
      Detection: Face
      Action: Record + Alert
    - Zone: "Parking" (Polygon)
      Detection: Motion
      Action: Record

  Camera 2:
    - Zone: "Entrance" (Rectangle)
      Detection: Person
      Action: PTZ Focus
```

## Requirements

### Dependencies
```bash
pip install anthropic mcp
```

### Environment
- **ANTHROPIC_API_KEY** environment variable (for Claude API access)
  - Get key at: https://console.anthropic.com/
  - Set via:
    ```bash
    # Windows PowerShell
    $env:ANTHROPIC_API_KEY = "sk-ant-..."
    
    # Linux/Mac
    export ANTHROPIC_API_KEY="sk-ant-..."
    ```

### Network
- Local network access to IP cameras
- ONVIF support on cameras (for capability probing)
- RTSP ports open (typically 554, 8554)
- HTTP ports (typically 80, 8080) for device communication

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│           SetupWizardDialog (UI Layer)                  │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Tabs: Discovery | Capabilities | Config | Summary │ │
│  │ Conversation display + user input field            │ │
│  └────────────────────────────────────────────────────┘ │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
         ┌──────────────────────────┐
         │ SetupWizardWorker        │
         │ (QThread - async AI)     │
         └────────────┬─────────────┘
                      │
                      ↓
      ┌──────────────────────────────────┐
      │   WizardAIController             │
      │   - Claude API client            │
      │   - Conversation history mgmt    │
      │   - Tool call orchestration      │
      └────────────┬─────────────────────┘
                   │
                   ↓
        ┌──────────────────────────────────┐
        │   CameraSetupMCPServer           │
        │   (MCP Tool Definitions + Impl)  │
        │  ┌──────────────────────────────┐│
        │  │ 7 Camera Operation Tools      ││
        │  │ - discover_cameras           ││
        │  │ - probe_camera_capabilities  ││
        │  │ - configure_camera_sensitivity
        │  │ - define_trigger_zone        ││
        │  │ etc...                       ││
        │  └──────────────────────────────┘│
        └────────────┬─────────────────────┘
                     │
           ┌─────────┴──────────┐
           ↓                    ↓
    ┌─────────────────┐  ┌─────────────────┐
    │CameraDiscovery  │  │CapabilityProber │
    │(NMAP + RTSP)    │  │(ONVIF GetCaps)  │
    └─────────────────┘  └─────────────────┘
           │                    │
           └─────────┬──────────┘
                     ↓
        ┌──────────────────────────┐
        │   Actual IP Cameras      │
        │   (ONVIF/RTSP endpoints) │
        └──────────────────────────┘
```

### Data Flow

1. **User clicks "Start Wizard"**
   - SetupWizardWorker spawned (QThread)
   - Initial message sent to Claude

2. **Claude processes message**
   - Uses MCP schema to understand available tools
   - Calls `discover_cameras` tool
   - Claude receives JSON result

3. **Results processed**
   - Conversation continues in loop
   - UI updates with discoveries
   - User can interact or let Claude proceed

4. **Setup completed**
   - Claude generates summary
   - Configuration saved to registry/DB
   - User can export or finalize

## Advanced Usage

### Customizing Tools

Add custom tools to `CameraSetupMCPServer`:

```python
def define_tools(self) -> list[dict]:
    """Extend with custom tools"""
    base_tools = super().define_tools()
    
    custom_tool = {
        "name": "configure_recording_schedule",
        "description": "Set recording times (24/7, motion-triggered, scheduled)",
        "inputSchema": {...}
    }
    
    return base_tools + [custom_tool]

def handle_tool_call(self, tool_name: str, tool_input: dict) -> str:
    if tool_name == "configure_recording_schedule":
        return self._handle_recording_schedule(tool_input)
    else:
        return super().handle_tool_call(tool_name, tool_input)
```

### Integrating with Existing System

The wizard integrates with existing services:

```python
# Access existing managers
mcp_server.credential_manager = credential_manager
mcp_server.camera_registry = camera_registry

# Tools can now persist configurations
def _handle_configure_sensitivity(self, input_data: dict) -> str:
    camera_id = input_data.get("camera_id")
    
    # Save to registry
    self.camera_registry.update_sensitivity(camera_id, config)
    
    # Also update existing camera widget
    # This allows live updates during setup
    
    return json.dumps({"success": True, ...})
```

### Exporting Configuration

```python
# After wizard completes
setup_data = wizard.setup_data

# Export as JSON
import json
with open("camera_setup.json", "w") as f:
    json.dump(setup_data, f, indent=2)

# Or import to another instance
wizard2 = SetupWizardDialog()
wizard2.setup_data = setup_data
wizard2.restore_from_export()
```

## Troubleshooting

### "Setup Wizard not available"
**Issue**: Missing dependencies
**Solution**:
```bash
pip install anthropic mcp
```

### "API key not found"
**Issue**: ANTHROPIC_API_KEY env var not set
**Solution**:
```bash
# Windows
set ANTHROPIC_API_KEY=sk-ant-...

# PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Linux/Mac
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "Cannot reach camera"
**Issue**: Camera not responding
**Solutions**:
1. Check camera is powered on and connected
2. Verify camera IP on network (use `ipconfig /all`)
3. Test ping: `ping 192.168.1.100`
4. Check firewall allows RTSP (port 554)
5. Verify ONVIF is enabled on camera

### "Probe failed - ONVIF not supported"
**Issue**: Camera doesn't support ONVIF
**Solution**: 
- Many older cameras don't support ONVIF
- Wizard still works (uses RTSP/HTTP)
- PTZ/audio capabilities may be unavailable
- Can still configure sensitivity & zones via metadata

### Claude making wrong decisions
**Issue**: AI recommends incorrect settings
**Solution**:
- Override in Configuration tab manually
- Provide more context in conversation
- Claude learns from feedback in current session
- Consider tuning system prompt in `WizardAIController.get_system_prompt()`

## Performance

- **Discovery scan**: 30-60 seconds per subnet (depends on network size)
- **Capability probe**: 2-5 seconds per camera
- **Configuration save**: <1 second
- **UI responsiveness**: All operations non-blocking (QThread)

## Security Considerations

⚠️ **Important**: 
- Credentials are stored locally by `CameraCredentialManager`
- API key should never be hardcoded - use environment variables
- Trigger zones include coordinate data (do not expose via web)
- Consider encrypting credential storage in production

## Future Enhancements

- [ ] Firmware update recommendations per manufacturer
- [ ] Automatic PTZ preset creation during zone definition
- [ ] Live preview during trigger zone drawing
- [ ] Multi-language support via Claude
- [ ] Preset templates (retail, parking, warehouse)
- [ ] Integration with cloud recording services
- [ ] AI-generated scene descriptions ("busy hallway", "empty parking lot")

## See Also

- [Camera Discovery](../logic/camera_search/auto_discovery.py) - Network scanning
- [Capability Prober](../logic/camera_search/capability_prober.py) - ONVIF probing
- [Credential Manager](../logic/camera_search/credential_manager.py) - Auth storage
- [Camera Registry](../logic/camera_search/camera_registry.py) - Persistence layer
- [Main Window Integration](../views/homepage/main_window.py) - UI integration
