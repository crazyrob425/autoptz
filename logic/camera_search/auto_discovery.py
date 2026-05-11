import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from logic.camera_search.onvif_profiles import resolve_onvif_stream_uri


try:
    import nmap  # python-nmap
    NMAP_AVAILABLE = True
except ImportError:
    NMAP_AVAILABLE = False


COMMON_CAMERA_PORTS = [80, 443, 554, 8000, 8080, 8554, 8899]


def _local_ipv4_candidates():
    candidates = set()
    try:
        host_info = socket.gethostbyname_ex(socket.gethostname())
        for ip in host_info[2]:
            if ip and not ip.startswith("127."):
                candidates.add(ip)
    except Exception:
        pass

    # Fallback path using outbound socket route
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            candidates.add(ip)
    except Exception:
        pass

    return sorted(candidates)


def detect_local_subnets():
    """Return best-effort local /24 CIDRs for discovery."""
    cidrs = []
    for ip in _local_ipv4_candidates():
        try:
            network = ipaddress.ip_network(f"{ip}/24", strict=False)
            cidrs.append(str(network))
        except Exception:
            continue
    return sorted(set(cidrs))


def _socket_port_open(host, port, timeout=0.2):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    except Exception:
        return False
    finally:
        try:
            sock.close()
        except Exception:
            pass


def _probe_rtsp(host, port=554, timeout=0.6):
    """Probe RTSP endpoint using OPTIONS request."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        payload = (
            f"OPTIONS rtsp://{host}:{port}/ RTSP/1.0\r\n"
            "CSeq: 1\r\n"
            "User-Agent: AI-Stalker/1.0\r\n\r\n"
        ).encode("utf-8")
        sock.sendall(payload)
        data = sock.recv(2048)
        return b"RTSP" in data or b"200" in data or b"401" in data
    except Exception:
        return False
    finally:
        try:
            sock.close()
        except Exception:
            pass


def _probe_onvif_http(host, port=80, timeout=0.8):
    """Light ONVIF check via /onvif/device_service over HTTP."""
    try:
        import http.client
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("GET", "/onvif/device_service")
        resp = conn.getresponse()
        body = resp.read(512)
        conn.close()
        if resp.status in (200, 401, 403):
            return True
        # Some devices return SOAP fault text or XML hints
        return b"onvif" in body.lower() or b"soap" in body.lower()
    except Exception:
        return False


def _nmap_host_scan(cidr):
    discovered = {}
    scanner = nmap.PortScanner()
    ports = ",".join(str(p) for p in COMMON_CAMERA_PORTS)
    args = f"-n -T4 --open -p {ports}"
    scanner.scan(hosts=cidr, arguments=args)
    for host in scanner.all_hosts():
        if scanner[host].state() != 'up':
            continue
        open_ports = []
        for p in COMMON_CAMERA_PORTS:
            try:
                if scanner[host].has_tcp(p) and scanner[host]['tcp'][p]['state'] == 'open':
                    open_ports.append(p)
            except Exception:
                continue
        if open_ports:
            discovered[host] = sorted(open_ports)
    return discovered


def _threaded_host_scan(cidr, timeout=0.2, max_workers=128, should_cancel=None, progress_cb=None):
    discovered = {}
    network = ipaddress.ip_network(cidr, strict=False)
    hosts = [str(h) for h in network.hosts()]

    def scan_one(host):
        ports = [p for p in COMMON_CAMERA_PORTS if _socket_port_open(host, p, timeout=timeout)]
        return host, ports

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(scan_one, h) for h in hosts]
        completed = 0
        total = len(futures)
        for fut in as_completed(futures):
            if should_cancel and should_cancel():
                return discovered
            host, ports = fut.result()
            if ports:
                discovered[host] = sorted(ports)
            completed += 1
            if progress_cb:
                progress_cb({"stage": "port-scan", "message": f"Scanning {cidr}", "value": completed, "total": total})
    return discovered


def _heuristic_score(open_ports, supports_onvif, supports_rtsp):
    score = 0.15
    if supports_rtsp:
        score += 0.45
    if supports_onvif:
        score += 0.35
    if 80 in open_ports or 8080 in open_ports:
        score += 0.05
    if 554 in open_ports:
        score += 0.05
    return round(min(score, 0.99), 2)


def _guess_comm_method(supports_onvif, supports_rtsp, open_ports):
    if supports_onvif and supports_rtsp:
        return "ONVIF + RTSP"
    if supports_onvif:
        return "ONVIF"
    if supports_rtsp:
        return "RTSP"
    if 80 in open_ports or 8080 in open_ports or 443 in open_ports:
        return "HTTP API"
    return "Unknown"


def _suggest_rtsp_url(host, open_ports):
    if 554 in open_ports:
        return f"rtsp://{host}:554/"
    if 8554 in open_ports:
        return f"rtsp://{host}:8554/"
    return None


class CameraAutoDiscovery:
    """Fast local camera discovery with protocol inference and confidence scoring."""

    def discover(self, cidrs=None, progress_cb=None, should_cancel=None, credential_manager=None):
        cidrs = cidrs or detect_local_subnets()
        all_hosts = {}
        if progress_cb:
            progress_cb({"stage": "init", "message": "Preparing subnet scan", "value": 0, "total": max(1, len(cidrs))})

        for i, cidr in enumerate(cidrs, start=1):
            if should_cancel and should_cancel():
                return []
            try:
                if NMAP_AVAILABLE:
                    found = _nmap_host_scan(cidr)
                    if progress_cb:
                        progress_cb({"stage": "port-scan", "message": f"Scanned {cidr}", "value": i, "total": len(cidrs)})
                else:
                    found = _threaded_host_scan(cidr, should_cancel=should_cancel, progress_cb=progress_cb)
                all_hosts.update(found)
            except Exception:
                continue

        results = []
        total_hosts = max(1, len(all_hosts))
        for idx, (ip, open_ports) in enumerate(all_hosts.items(), start=1):
            if should_cancel and should_cancel():
                return results
            supports_rtsp = False
            supports_onvif = False
            onvif_stream_uri = None

            if 554 in open_ports or 8554 in open_ports:
                rtsp_port = 554 if 554 in open_ports else 8554
                supports_rtsp = _probe_rtsp(ip, port=rtsp_port)

            for p in (80, 8080, 8000, 8899):
                if p in open_ports and _probe_onvif_http(ip, p):
                    supports_onvif = True
                    break

            if supports_onvif:
                onvif_stream = resolve_onvif_stream_uri(ip, credential_manager=credential_manager)
                if onvif_stream and onvif_stream.get("uri"):
                    onvif_stream_uri = onvif_stream.get("uri")
                    supports_rtsp = True

            method = _guess_comm_method(supports_onvif, supports_rtsp, open_ports)
            score = _heuristic_score(open_ports, supports_onvif, supports_rtsp)

            results.append({
                "ip": ip,
                "label": f"IP Cam {ip}",
                "open_ports": open_ports,
                "supports_onvif": supports_onvif,
                "supports_rtsp": supports_rtsp,
                "communication_method": method,
                "confidence": score,
                "suggested_rtsp_url": _suggest_rtsp_url(ip, open_ports),
                "onvif_stream_uri": onvif_stream_uri,
            })

            if progress_cb:
                progress_cb({"stage": "probe", "message": f"Probing {ip}", "value": idx, "total": total_hosts})

        return sorted(results, key=lambda x: x["confidence"], reverse=True)
