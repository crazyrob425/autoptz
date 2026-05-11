"""
Camera Capability Detection Module

Probes ONVIF cameras for capabilities like PTZ, audio, events, etc.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


@dataclass
class CameraCapabilities:
    """Data class for camera capabilities"""
    model: str
    manufacturer: str
    firmware_version: str
    has_ptz: bool
    has_audio: bool
    has_events: bool
    supported_profiles: List[str]
    audio_codecs: List[str]
    video_codecs: List[str]
    ptz_features: Dict[str, Any]
    event_types: List[str]
    raw_capabilities: Dict[str, Any]

    def to_dict(self):
        return asdict(self)


class CapabilityProber:
    """Probe camera capabilities via ONVIF and HTTP"""

    def __init__(self, rtsp_url: str, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize prober for a specific camera.
        
        Args:
            rtsp_url: RTSP URL or IP address of camera
            username: Optional username for auth
            password: Optional password for auth
        """
        self.rtsp_url = rtsp_url
        self.username = username
        self.password = password
        self.host = self._extract_host(rtsp_url)
        self.auth = HTTPBasicAuth(username, password) if username and password else None

    def _extract_host(self, url: str) -> str:
        """Extract host from RTSP URL or return as-is if IP"""
        if url.startswith('rtsp://'):
            return url.split('://')[1].split(':')[0].split('/')[0]
        return url.split(':')[0].split('/')[0]

    def probe_device_info(self) -> Dict[str, str]:
        """
        Probe camera device information (model, manufacturer, firmware).
        Tries multiple endpoints.
        """
        endpoints = [
            f"http://{self.host}/device.xml",
            f"http://{self.host}/onvif/device_service",
            f"http://{self.host}/api/system",
        ]

        for endpoint in endpoints:
            try:
                response = requests.get(endpoint, auth=self.auth, timeout=2)
                if response.status_code == 200:
                    data = response.text
                    info = {
                        'model': self._parse_xml_value(data, 'model'),
                        'manufacturer': self._parse_xml_value(data, 'manufacturer'),
                        'firmware_version': self._parse_xml_value(data, 'firmwareVersion'),
                    }
                    if any(info.values()):
                        return info
            except Exception as e:
                logger.debug(f"Failed to probe {endpoint}: {e}")
                continue

        return {
            'model': 'Unknown',
            'manufacturer': 'Unknown',
            'firmware_version': 'Unknown',
        }

    def probe_ptz_capabilities(self) -> Dict[str, Any]:
        """Probe PTZ (Pan-Tilt-Zoom) capabilities"""
        try:
            from zeep import Client

            client = Client(f"http://{self.host}:8080/onvif/device_service")
            device_service = client.bind('http://www.onvif.org/ver10/device/wsdl', 'DeviceService')

            try:
                capabilities = device_service.GetCapabilities()
                ptz_caps = capabilities.get('PTZ', {})
                
                return {
                    'has_ptz': bool(ptz_caps),
                    'pan_support': ptz_caps.get('PanTiltLimits', {}).get('Range', {}).get('XRange') is not None,
                    'zoom_support': ptz_caps.get('ZoomLimits', {}).get('Range', {}).get('XRange') is not None,
                    'continuous_move': ptz_caps.get('ContinuousMove', False),
                    'relative_move': ptz_caps.get('RelativeMove', False),
                    'absolute_move': ptz_caps.get('AbsoluteMove', False),
                    'raw_ptz': ptz_caps,
                }
            except Exception as e:
                logger.debug(f"GetCapabilities failed: {e}")
                return {'has_ptz': False, 'reason': str(e)}

        except ImportError:
            logger.warning("zeep not available for ONVIF probing")
            return {'has_ptz': False, 'reason': 'zeep not available'}

    def probe_audio_capabilities(self) -> Dict[str, Any]:
        """Probe audio input/output capabilities"""
        result = {
            'has_audio': False,
            'audio_inputs': [],
            'audio_outputs': [],
            'audio_codecs': [],
        }

        try:
            from zeep import Client

            client = Client(f"http://{self.host}:8080/onvif/device_service")
            media_service = client.bind('http://www.onvif.org/ver10/media/wsdl', 'MediaService')

            try:
                profiles = media_service.GetProfiles()
                for profile in profiles:
                    if 'AudioSourceConfiguration' in profile:
                        result['has_audio'] = True
                        result['audio_inputs'].append(profile['AudioSourceConfiguration'])

                    if 'AudioEncoderConfiguration' in profile:
                        codec = profile['AudioEncoderConfiguration'].get('Encoding', 'Unknown')
                        if codec not in result['audio_codecs']:
                            result['audio_codecs'].append(codec)

            except Exception as e:
                logger.debug(f"Audio probe failed: {e}")

        except ImportError:
            pass

        return result

    def probe_event_capabilities(self) -> Dict[str, Any]:
        """Probe event/trigger capabilities"""
        result = {
            'has_events': False,
            'event_types': [],
            'supported_event_topics': [],
        }

        try:
            from zeep import Client

            client = Client(f"http://{self.host}:8080/onvif/device_service")
            events_service = client.bind('http://www.onvif.org/ver10/events/wsdl', 'EventService')

            try:
                capabilities = events_service.GetEventProperties()
                if capabilities:
                    result['has_events'] = True
                    # Extract event topic namespace
                    result['supported_event_topics'] = [
                        str(t) for t in capabilities.get('TopicNamespaceLocation', [])
                    ]

            except Exception as e:
                logger.debug(f"Event probe failed: {e}")

        except ImportError:
            pass

        return result

    def probe_media_profiles(self) -> List[str]:
        """Probe available media profiles and their resolutions"""
        profiles = []

        try:
            from zeep import Client

            client = Client(f"http://{self.host}:8080/onvif/device_service")
            media_service = client.bind('http://www.onvif.org/ver10/media/wsdl', 'MediaService')

            try:
                profile_list = media_service.GetProfiles()
                for profile in profile_list:
                    profile_name = profile.get('Name', 'Unknown')
                    video_config = profile.get('VideoEncoderConfiguration', {})
                    resolution = video_config.get('Resolution', {})
                    width = resolution.get('Width', '?')
                    height = resolution.get('Height', '?')
                    
                    profile_str = f"{profile_name} ({width}x{height})"
                    profiles.append(profile_str)

            except Exception as e:
                logger.debug(f"Profile probe failed: {e}")

        except ImportError:
            pass

        return profiles or ['Default']

    def full_probe(self) -> CameraCapabilities:
        """
        Run comprehensive capability probe.
        Returns CameraCapabilities object.
        """
        logger.info(f"Starting full capability probe for {self.rtsp_url}")

        device_info = self.probe_device_info()
        ptz_info = self.probe_ptz_capabilities()
        audio_info = self.probe_audio_capabilities()
        event_info = self.probe_event_capabilities()
        profiles = self.probe_media_profiles()

        capabilities = CameraCapabilities(
            model=device_info.get('model', 'Unknown'),
            manufacturer=device_info.get('manufacturer', 'Unknown'),
            firmware_version=device_info.get('firmware_version', 'Unknown'),
            has_ptz=ptz_info.get('has_ptz', False),
            has_audio=audio_info.get('has_audio', False),
            has_events=event_info.get('has_events', False),
            supported_profiles=profiles,
            audio_codecs=audio_info.get('audio_codecs', []),
            video_codecs=['H.264', 'MJPEG'],  # Common defaults
            ptz_features=ptz_info,
            event_types=event_info.get('supported_event_topics', []),
            raw_capabilities={
                'device': device_info,
                'ptz': ptz_info,
                'audio': audio_info,
                'events': event_info,
            }
        )

        logger.info(f"Probe complete: {capabilities.manufacturer} {capabilities.model}")
        return capabilities

    @staticmethod
    def _parse_xml_value(xml_text: str, tag_name: str) -> str:
        """Simple XML tag extraction"""
        import re
        pattern = f"<{tag_name}>([^<]+)</{tag_name}>"
        match = re.search(pattern, xml_text, re.IGNORECASE)
        return match.group(1) if match else ""
