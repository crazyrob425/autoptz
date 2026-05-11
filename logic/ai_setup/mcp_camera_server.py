"""
MCP Server for Camera Setup Wizard

Provides tools for Claude AI to discover, probe, and configure cameras.
Implements Model Context Protocol server.
"""

import json
import logging
from typing import Any, Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)


class CameraSetupMCPServer:
    """
    MCP-compatible server providing camera setup tools.
    Claude can call these as JSON-RPC methods.
    """

    def __init__(self):
        self.discovered_cameras = []
        self.configured_cameras = {}
        self.sensitivity_config = {}
        self.trigger_zones = {}

    def define_tools(self) -> list[dict]:
        """
        Define available tools for Claude.
        Returns list of tool definitions in JSON Schema format.
        """
        return [
            {
                "name": "discover_cameras",
                "description": "Scan the network for available IP cameras. Performs NMAP scan + RTSP probing.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "subnet": {
                            "type": "string",
                            "description": "Network subnet to scan (e.g., '192.168.1.0/24'). If omitted, auto-detects.",
                        },
                        "timeout_seconds": {
                            "type": "integer",
                            "description": "Scan timeout in seconds. Default: 30",
                            "default": 30,
                        },
                    },
                },
            },
            {
                "name": "probe_camera_capabilities",
                "description": "Probe a specific camera's capabilities (PTZ, audio, events, profiles, etc.)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "camera_id": {
                            "type": "string",
                            "description": "Camera identifier (IP address or URL)",
                        },
                        "username": {
                            "type": "string",
                            "description": "Optional username for camera auth",
                        },
                        "password": {
                            "type": "string",
                            "description": "Optional password for camera auth",
                        },
                    },
                    "required": ["camera_id"],
                },
            },
            {
                "name": "identify_driver_requirements",
                "description": "Identify driver and firmware requirements for a specific camera model.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "manufacturer": {
                            "type": "string",
                            "description": "Camera manufacturer (e.g., 'Hikvision', 'Dahua')",
                        },
                        "model": {
                            "type": "string",
                            "description": "Camera model number",
                        },
                    },
                    "required": ["manufacturer", "model"],
                },
            },
            {
                "name": "configure_camera_sensitivity",
                "description": "Set detection sensitivity (face confidence, motion threshold, etc.).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "camera_id": {
                            "type": "string",
                            "description": "Camera identifier",
                        },
                        "face_confidence_threshold": {
                            "type": "number",
                            "description": "Face detection confidence (0.0-1.0). Default: 0.7",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                        "motion_threshold": {
                            "type": "number",
                            "description": "Motion detection threshold (0.0-1.0). Default: 0.2",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                        "recording_enabled": {
                            "type": "boolean",
                            "description": "Enable continuous/trigger recording",
                        },
                    },
                    "required": ["camera_id"],
                },
            },
            {
                "name": "define_trigger_zone",
                "description": "Define a region of interest (trigger zone) on the camera frame for detection.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "camera_id": {
                            "type": "string",
                            "description": "Camera identifier",
                        },
                        "zone_name": {
                            "type": "string",
                            "description": "Zone name (e.g., 'entrance', 'parking lot')",
                        },
                        "zone_type": {
                            "type": "string",
                            "enum": ["rectangle", "polygon", "circle"],
                            "description": "Shape of trigger zone",
                        },
                        "coordinates": {
                            "type": "array",
                            "description": "Coordinates for zone (e.g., [[x1,y1], [x2,y2]] for rect, [[x,y,r]] for circle)",
                            "items": {"type": "array"},
                        },
                        "detection_type": {
                            "type": "string",
                            "enum": ["face", "motion", "person"],
                            "description": "What to detect in this zone",
                        },
                        "action_on_detect": {
                            "type": "string",
                            "enum": ["record", "alert", "ptz_focus", "webhook"],
                            "description": "Action when detection occurs",
                        },
                    },
                    "required": ["camera_id", "zone_name", "zone_type", "coordinates", "detection_type"],
                },
            },
            {
                "name": "test_camera_connection",
                "description": "Test connectivity and authentication to a camera.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "camera_id": {
                            "type": "string",
                            "description": "Camera IP or URL",
                        },
                        "username": {
                            "type": "string",
                            "description": "Optional username",
                        },
                        "password": {
                            "type": "string",
                            "description": "Optional password",
                        },
                    },
                    "required": ["camera_id"],
                },
            },
            {
                "name": "get_setup_progress",
                "description": "Get current setup progress and configured cameras.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def handle_tool_call(self, tool_name: str, tool_input: dict) -> str:
        """
        Route tool calls to appropriate handler.
        Returns JSON string response.
        """
        try:
            if tool_name == "discover_cameras":
                return self._handle_discover_cameras(tool_input)
            elif tool_name == "probe_camera_capabilities":
                return self._handle_probe_capabilities(tool_input)
            elif tool_name == "identify_driver_requirements":
                return self._handle_identify_drivers(tool_input)
            elif tool_name == "configure_camera_sensitivity":
                return self._handle_configure_sensitivity(tool_input)
            elif tool_name == "define_trigger_zone":
                return self._handle_define_trigger_zone(tool_input)
            elif tool_name == "test_camera_connection":
                return self._handle_test_connection(tool_input)
            elif tool_name == "get_setup_progress":
                return self._handle_get_progress(tool_input)
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})
        except Exception as e:
            logger.error(f"Tool error: {tool_name}: {e}")
            return json.dumps({"error": str(e)})

    def _handle_discover_cameras(self, input_data: dict) -> str:
        """Discover cameras on network"""
        try:
            from logic.camera_search.auto_discovery import CameraDiscovery

            subnet = input_data.get("subnet")
            timeout = input_data.get("timeout_seconds", 30)

            discoverer = CameraDiscovery()
            candidates = discoverer.discover(timeout_seconds=timeout)

            self.discovered_cameras = [
                {
                    "ip": c.get("ip"),
                    "port": c.get("port"),
                    "protocol": c.get("protocol"),
                    "confidence": c.get("confidence"),
                    "rtsp_url": c.get("rtsp_url"),
                }
                for c in candidates
            ]

            return json.dumps({
                "success": True,
                "discovered_count": len(self.discovered_cameras),
                "cameras": self.discovered_cameras,
            })

        except ImportError:
            return json.dumps({
                "success": False,
                "error": "Discovery module not available"
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _handle_probe_capabilities(self, input_data: dict) -> str:
        """Probe camera capabilities"""
        try:
            from logic.camera_search.capability_prober import CapabilityProber

            camera_id = input_data.get("camera_id")
            username = input_data.get("username")
            password = input_data.get("password")

            prober = CapabilityProber(camera_id, username, password)
            capabilities = prober.full_probe()

            result = {
                "success": True,
                "capabilities": capabilities.to_dict(),
            }

            return json.dumps(result)

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _handle_identify_drivers(self, input_data: dict) -> str:
        """Identify driver requirements"""
        manufacturer = input_data.get("manufacturer", "Unknown").lower()
        model = input_data.get("model", "Unknown")

        # Known driver mappings
        driver_map = {
            "hikvision": {
                "windows": "Hikvision iVMS-4500 or SADP Tool",
                "requirements": ["RTSP stream", "HTTP API", "ONVIF"],
                "notes": "May require firmware update for full ONVIF support"
            },
            "dahua": {
                "windows": "Dahua SmartPSS or Dahua DMSS",
                "requirements": ["RTSP stream", "HTTP API", "ONVIF"],
                "notes": "Ensure camera is in ONVIF mode"
            },
            "axis": {
                "windows": "Axis Camera Station or native ONVIF",
                "requirements": ["ONVIF compliant", "RTSP stream"],
                "notes": "Native ONVIF support - minimal driver needed"
            },
            "uniview": {
                "windows": "Uniview iVMS-4500",
                "requirements": ["RTSP stream", "ONVIF"],
                "notes": "Full ONVIF support"
            },
            "generic": {
                "windows": "ONVIF-compatible client (VLC, etc.)",
                "requirements": ["RTSP stream", "ONVIF"],
                "notes": "Most modern cameras support standard ONVIF"
            }
        }

        driver_info = driver_map.get(manufacturer, driver_map["generic"])

        return json.dumps({
            "success": True,
            "manufacturer": manufacturer,
            "model": model,
            "driver_requirements": driver_info,
            "onvif_essential": True,
        })

    def _handle_configure_sensitivity(self, input_data: dict) -> str:
        """Configure detection sensitivity"""
        camera_id = input_data.get("camera_id")
        config = {
            "face_confidence": input_data.get("face_confidence_threshold", 0.7),
            "motion_threshold": input_data.get("motion_threshold", 0.2),
            "recording_enabled": input_data.get("recording_enabled", False),
        }

        self.sensitivity_config[camera_id] = config

        return json.dumps({
            "success": True,
            "camera_id": camera_id,
            "configuration": config,
            "message": f"Sensitivity configured for {camera_id}"
        })

    def _handle_define_trigger_zone(self, input_data: dict) -> str:
        """Define trigger zone"""
        camera_id = input_data.get("camera_id")
        zone_name = input_data.get("zone_name")

        zone = {
            "name": zone_name,
            "type": input_data.get("zone_type"),
            "coordinates": input_data.get("coordinates"),
            "detection_type": input_data.get("detection_type"),
            "action_on_detect": input_data.get("action_on_detect", "alert"),
        }

        if camera_id not in self.trigger_zones:
            self.trigger_zones[camera_id] = []

        self.trigger_zones[camera_id].append(zone)

        return json.dumps({
            "success": True,
            "camera_id": camera_id,
            "zone": zone,
            "total_zones": len(self.trigger_zones[camera_id])
        })

    def _handle_test_connection(self, input_data: dict) -> str:
        """Test camera connection"""
        camera_id = input_data.get("camera_id")

        try:
            import requests
            from requests.auth import HTTPBasicAuth

            username = input_data.get("username")
            password = input_data.get("password")
            auth = HTTPBasicAuth(username, password) if username else None

            url = f"http://{camera_id}:8080/onvif/device_service" if not camera_id.startswith('http') else camera_id
            response = requests.get(url, auth=auth, timeout=3)

            return json.dumps({
                "success": response.status_code in [200, 401, 403],
                "status_code": response.status_code,
                "reachable": True,
                "message": f"Camera at {camera_id} is reachable"
            })

        except Exception as e:
            return json.dumps({
                "success": False,
                "reachable": False,
                "message": f"Cannot reach camera: {str(e)}"
            })

    def _handle_get_progress(self, input_data: dict) -> str:
        """Get current setup progress"""
        return json.dumps({
            "discovered_cameras": len(self.discovered_cameras),
            "configured_cameras": len(self.configured_cameras),
            "sensitivity_configs": len(self.sensitivity_config),
            "trigger_zones_total": sum(len(z) for z in self.trigger_zones.values()),
            "summary": {
                "discovered": self.discovered_cameras,
                "sensitivity": self.sensitivity_config,
                "zones": self.trigger_zones,
            }
        })
