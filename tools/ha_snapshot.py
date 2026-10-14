#!/usr/bin/env python3
"""Make a searchable, read-only list of your Home Assistant entities.

The list is written to .local/ha_index.jsonl (one entity per line) so that you,
or an AI assistant, can look up real entity ids instead of guessing them when
writing AppDaemon YAML. See LLM_GUIDE.md in the repository root.

What it does:
  * Connects to Home Assistant's WebSocket API with a long-lived access token.
  * Only READS: entity, device and area registries, current states, and the
    names of the notify services. It never calls a service or changes anything.
  * Needs only Python 3.8+ and the standard library. Nothing to install.

Files (all in .local/ next to this repository's README, which git ignores):
  .local/ha_token       Your long-lived access token, one line. You create it.
  .local/ha_url         Your Home Assistant address. Saved when you use --url.
  .local/ha_index.jsonl The result. Contains your entity names and areas.

Usage:
  python3 tools/ha_snapshot.py --init
  python3 tools/ha_snapshot.py --url http://homeassistant.local:8123
  python3 tools/ha_snapshot.py            # later runs reuse the saved address

The token is never printed. The script refuses to run if git does not ignore
the .local folder, so the token and your index cannot be committed by mistake.
"""

import argparse
import base64
import json
import os
import socket
import ssl
import stat
import struct
import subprocess
import sys
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL = os.path.join(ROOT, ".local")
TOKEN_FILE = os.path.join(LOCAL, "ha_token")
URL_FILE = os.path.join(LOCAL, "ha_url")
INDEX_FILE = os.path.join(LOCAL, "ha_index.jsonl")
DEFAULT_URL = "http://homeassistant.local:8123"

# Attributes worth keeping. Everything else (pictures, GPS, long lists) is dropped.
KEEP_ATTRS = (
    "device_class",
    "unit_of_measurement",
    "state_class",
    "options",
    "hvac_modes",
    "supported_color_modes",
    "source_list",
)
# Never store the state of these, it would reveal where people are.
NO_STATE_DOMAINS = ("person", "device_tracker", "zone")
MAX_STATE_LEN = 40


# --------------------------------------------------------------------------
# Minimal WebSocket client (RFC 6455), enough for Home Assistant. Stdlib only.
# --------------------------------------------------------------------------
class WebSocket:
    def __init__(self, url, verify_tls=True, timeout=30):
        p = urlparse(url)
        if p.scheme not in ("http", "https", "ws", "wss"):
            raise ValueError("The address must start with http:// or https://")
        secure = p.scheme in ("https", "wss")
        host = p.hostname
        port = p.port or (443 if secure else 80)
        base = p.path.rstrip("/")
        path = base + "/api/websocket"

        sock = socket.create_connection((host, port), timeout=timeout)
        if secure:
            ctx = ssl.create_default_context()
            if not verify_tls:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            sock = ctx.wrap_socket(sock, server_hostname=host)
        self.sock = sock
        self.buf = b""

        key = base64.b64encode(os.urandom(16)).decode()
        host_header = host if p.port is None else "%s:%d" % (host, port)
        request = (
            "GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\n"
            "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n" % (path, host_header, key)
        )
        self.sock.sendall(request.encode())
        head = self._read_until(b"\r\n\r\n")
        status = head.split(b"\r\n", 1)[0].decode(errors="replace")
        if " 101 " not in status:
            raise ConnectionError("WebSocket handshake failed: " + status)

    def _read_until(self, marker):
        while marker not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("Connection closed during handshake")
            self.buf += chunk
        head, self.buf = self.buf.split(marker, 1)
        return head

    def _read_exact(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(max(65536, n - len(self.buf)))
            if not chunk:
                raise ConnectionError("Connection closed by Home Assistant")
            self.buf += chunk
        data, self.buf = self.buf[:n], self.buf[n:]
        return data

    def _send_frame(self, opcode, payload):
        header = bytes([0x80 | opcode])
        n = len(payload)
        if n < 126:
            header += bytes([0x80 | n])
        elif n < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(header + mask + masked)

    def send_json(self, obj):
        self._send_frame(0x1, json.dumps(obj).encode())

    def recv_json(self):
        message = b""
        while True:
            b1, b2 = self._read_exact(2)
            fin, opcode = b1 & 0x80, b1 & 0x0F
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read_exact(8))[0]
            payload = self._read_exact(length)  # server frames are not masked
            if opcode == 0x8:
                raise ConnectionError("Home Assistant closed the connection")
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            message += payload
            if fin:
                return json.loads(message.decode())

    def close(self):
        try:
            self._send_frame(0x8, b"")
        except OSError:
            pass
        self.sock.close()


class HA:
    def __init__(self, url, token, verify_tls=True):
        self.ws = WebSocket(url, verify_tls=verify_tls)
        msg = self.ws.recv_json()
        if msg.get("type") != "auth_required":
            raise ConnectionError("Unexpected reply from Home Assistant: %r" % msg.get("type"))
        self.ws.send_json({"type": "auth", "access_token": token})
        msg = self.ws.recv_json()
        if msg.get("type") != "auth_ok":
            raise PermissionError("Home Assistant rejected the token (%s)" % msg.get("type"))
        self.next_id = 1

    def call(self, command):
        """Send one read-only command and return its result, or None if refused."""
        i = self.next_id
        self.next_id += 1
        self.ws.send_json({"id": i, "type": command})
        while True:
            msg = self.ws.recv_json()
            if msg.get("id") != i:
                continue
            if msg.get("success"):
                return msg.get("result")
            err = msg.get("error", {})
            print("  Warning: '%s' was refused (%s). %s" % (
                command, err.get("code", "?"),
                "This needs an administrator account." if err.get("code") == "unauthorized" else ""))
            return None

    def close(self):
        self.ws.close()


# --------------------------------------------------------------------------
# Safety: the token and the index must be ignored by git.
# --------------------------------------------------------------------------
def git_ignores(path):
    """True if git ignores path, False if not, None if this is not a git checkout."""
    try:
        r = subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, ValueError):
        return None
    if r.returncode == 0:
        return True
    if r.returncode == 1:
        # Exit 1 = not ignored, but only meaningful inside a git work tree.
        inside = subprocess.run(["git", "-C", ROOT, "rev-parse", "--is-inside-work-tree"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return False if inside.returncode == 0 else None
    return None


def require_ignored():
    for path in (TOKEN_FILE, INDEX_FILE):
        if git_ignores(path) is False:
            sys.exit(
                "STOP: git does not ignore %s.\n"
                "Add this line to the .gitignore in %s and run again:\n\n    .local/\n"
                % (os.path.relpath(path, ROOT), ROOT))


# --------------------------------------------------------------------------
# Build the index
# --------------------------------------------------------------------------
def short(value):
    text = str(value)
    return text if len(text) <= MAX_STATE_LEN else text[:MAX_STATE_LEN] + "..."


def build_records(entity_reg, device_reg, area_reg, states, services, include_disabled):
    areas = {a["area_id"]: a.get("name") for a in (area_reg or [])}
    devices = {d["id"]: d for d in (device_reg or [])}
    state_by_id = {s["entity_id"]: s for s in (states or [])}
    records = {}

    def device_fields(device_id):
        d = devices.get(device_id)
        if not d:
            return {}
        return {
            "device": d.get("name_by_user") or d.get("name"),
            "manufacturer": d.get("manufacturer"),
            "model": d.get("model"),
        }

    for e in (entity_reg or []):
        eid = e["entity_id"]
        disabled = bool(e.get("disabled_by"))
        if disabled and not include_disabled:
            continue
        dev = devices.get(e.get("device_id"), {})
        area_id = e.get("area_id") or dev.get("area_id")
        rec = {
            "entity_id": eid,
            "name": e.get("name") or e.get("original_name"),
            "area": areas.get(area_id),
            "integration": e.get("platform"),
            "device_class": e.get("device_class") or e.get("original_device_class"),
        }
        rec.update(device_fields(e.get("device_id")))
        if e.get("entity_category"):
            rec["category"] = e["entity_category"]
        if e.get("hidden_by"):
            rec["hidden"] = True
        if disabled:
            rec["disabled"] = True
        records[eid] = rec

    for eid, s in state_by_id.items():
        rec = records.setdefault(eid, {"entity_id": eid, "integration": None})
        attrs = s.get("attributes") or {}
        if attrs.get("friendly_name"):
            rec["name"] = attrs["friendly_name"]
        for key in KEEP_ATTRS:
            if attrs.get(key) not in (None, "", []):
                rec[key] = attrs[key]
        if eid.split(".", 1)[0] not in NO_STATE_DOMAINS:
            rec["state"] = short(s.get("state"))

    out = []
    for eid in sorted(records):
        rec = {k: v for k, v in records[eid].items() if v not in (None, "")}
        rec["domain"] = eid.split(".", 1)[0]
        rec["kind"] = "entity"
        out.append(rec)

    # notify services are not entities, but notify_mobiles needs their names.
    notify = {}
    if isinstance(services, dict):
        notify = services.get("notify") or {}
    for name in sorted(notify):
        out.append({"kind": "notify_service", "entity_id": "notify." + name,
                    "domain": "notify", "name": name})
    return out


def summarize(records):
    entities = [r for r in records if r["kind"] == "entity"]
    by_domain = {}
    areas = set()
    for r in entities:
        by_domain[r["domain"]] = by_domain.get(r["domain"], 0) + 1
        if r.get("area"):
            areas.add(r["area"])
    print("Saved %d entities and %d notify services to %s" % (
        len(entities), len(records) - len(entities), os.path.relpath(INDEX_FILE, ROOT)))
    top = sorted(by_domain.items(), key=lambda kv: -kv[1])[:12]
    print("Most common types: " + ", ".join("%s %d" % kv for kv in top))
    print("Areas (%d): %s" % (len(areas), ", ".join(sorted(areas)) or "none"))


# --------------------------------------------------------------------------
def read_first_line(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.readline().strip()
    except OSError:
        return ""


def do_init():
    os.makedirs(LOCAL, exist_ok=True)
    created = not os.path.exists(TOKEN_FILE)
    if created:
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write("")
    os.chmod(TOKEN_FILE, stat.S_IRUSR | stat.S_IWUSR)
    status = git_ignores(TOKEN_FILE)
    if status is False:
        print("WARNING: git does NOT ignore .local/. Add the line  .local/  to .gitignore before you continue.")
    elif status is None:
        print("Note: this is not a git checkout, so nothing can be committed from here.")
    else:
        print("OK: git ignores the .local folder.")
    print("%s %s" % ("Created" if created else "Already exists:", TOKEN_FILE))
    if read_first_line(TOKEN_FILE):
        print("The token file is filled in. Nothing more to do with --init; run the script without it:")
        print("    python3 tools/ha_snapshot.py --url http://homeassistant.local:8123")
        return
    print("Next: open that file in a PLAIN TEXT editor, paste your long-lived access token on")
    print("the first line (nothing else), and save. Then run this script again.")
    if sys.platform == "darwin":
        print("On a Mac, this opens it as plain text:  open -e \"%s\"" % TOKEN_FILE)
        print("(Finder hides the .local folder; press Cmd+Shift+. to show hidden files.)")


def main():
    ap = argparse.ArgumentParser(description="Read-only snapshot of Home Assistant entities.")
    ap.add_argument("--init", action="store_true", help="create the .local folder and an empty token file")
    ap.add_argument("--url", help="Home Assistant address, for example http://homeassistant.local:8123")
    ap.add_argument("--insecure", action="store_true", help="do not verify a self-signed https certificate")
    ap.add_argument("--include-disabled", action="store_true", help="also list disabled entities")
    args = ap.parse_args()

    if args.init:
        do_init()
        return

    require_ignored()

    token = os.environ.get("HA_TOKEN") or read_first_line(TOKEN_FILE)
    if not token:
        sys.exit("No token found. Run  python3 tools/ha_snapshot.py --init  and follow the steps in LLM_GUIDE.md.")
    if token.startswith("{\\rtf") or "\\rtf" in token[:20]:
        sys.exit("The token file was saved as rich text (RTF). Open it in a plain text editor "
                 "(TextEdit: Format, Make Plain Text), paste only the token and save again.")
    url = args.url or os.environ.get("HA_URL") or read_first_line(URL_FILE) or DEFAULT_URL

    print("Connecting to %s ..." % url)
    try:
        ha = HA(url, token, verify_tls=not args.insecure)
    except PermissionError as exc:
        sys.exit("%s\nCreate a new long-lived token and paste it into %s" % (exc, TOKEN_FILE))
    except (OSError, ConnectionError, ValueError) as exc:
        sys.exit("Could not connect: %s\nCheck the address (including :8123) and that Home Assistant is running." % exc)

    try:
        entity_reg = ha.call("config/entity_registry/list")
        device_reg = ha.call("config/device_registry/list")
        area_reg = ha.call("config/area_registry/list")
        states = ha.call("get_states")
        services = ha.call("get_services")
    finally:
        ha.close()

    if states is None:
        sys.exit("Could not read the entity states, nothing was saved.")

    records = build_records(entity_reg, device_reg, area_reg, states, services, args.include_disabled)
    os.makedirs(LOCAL, exist_ok=True)
    tmp = INDEX_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.replace(tmp, INDEX_FILE)
    if args.url:
        with open(URL_FILE, "w", encoding="utf-8") as f:
            f.write(args.url.strip() + "\n")
    summarize(records)
    if entity_reg is None:
        print("Areas, devices and integrations are missing because the token's user is not an administrator.")


if __name__ == "__main__":
    main()
