import os


try:
    import onvif
    from onvif import ONVIFCamera
    ONVIF_AVAILABLE = True
except Exception:
    ONVIF_AVAILABLE = False


def _default_wsdl_path():
    if not ONVIF_AVAILABLE:
        return ""
    try:
        return os.path.join(os.path.dirname(onvif.__file__), "wsdl")
    except Exception:
        return ""


def _credential_candidates(host, credential_manager=None):
    candidates = []
    if credential_manager is not None:
        rec = credential_manager.get(host)
        if rec and rec.get("username"):
            candidates.append((rec.get("username"), rec.get("password", ""), rec.get("port", 80), rec.get("wsdl_path", "")))

    # conservative defaults for unmanaged cameras
    candidates.extend([
        ("admin", "admin", 80, ""),
        ("admin", "12345", 80, ""),
        ("admin", "", 80, ""),
    ])

    seen = set()
    uniq = []
    for u, p, port, wsdl in candidates:
        key = (u, p, int(port), wsdl)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(key)
    return uniq


def resolve_onvif_stream_uri(host, credential_manager=None):
    """Try ONVIF media profiles and return exact stream URI if available."""
    if not ONVIF_AVAILABLE:
        return None

    for username, password, port, wsdl_path in _credential_candidates(host, credential_manager):
        try:
            wsdl = wsdl_path or _default_wsdl_path()
            if wsdl:
                cam = ONVIFCamera(host, int(port), username, password, wsdl)
            else:
                cam = ONVIFCamera(host, int(port), username, password)

            media = cam.create_media_service()
            profiles = media.GetProfiles()
            if not profiles:
                continue

            profile = profiles[0]
            req = media.create_type("GetStreamUri")
            req.StreamSetup = {
                "Stream": "RTP-Unicast",
                "Transport": {"Protocol": "RTSP"}
            }
            req.ProfileToken = profile.token
            uri_resp = media.GetStreamUri(req)
            uri = getattr(uri_resp, "Uri", None)
            if uri:
                return {
                    "uri": uri,
                    "username": username,
                    "password": password,
                    "port": int(port),
                }
        except Exception:
            continue

    return None
