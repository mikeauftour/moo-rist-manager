import base64, hashlib, hmac, html, http.client, http.cookies, json, os, re, secrets, socket, threading, time, urllib.parse, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FILE = Path(os.getenv('DATA_FILE', '/data/state.json'))
LOCK = threading.RLock()
PREFIX = 'moo-single-'
IMAGE = '0.0.39'
SESSIONS = {}
REMEMBER_FILE = FILE.with_name('remember_sessions.json')
REMEMBER_SECONDS = 30 * 24 * 60 * 60
TRAFFIC_SAMPLES = {}  # receiver network counters per stream, process-local


def save(s):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix('.tmp')
    with open(tmp, 'w') as f:
        os.fchmod(f.fileno(), 0o600)
        json.dump(s, f)
    os.replace(tmp, FILE)


def load():
    if FILE.exists():
        return json.loads(FILE.read_text())
    return {'admin': None, 'next_id': 2, 'streams': [{'id': 1, 'name': 'Server 1 – Moo Standard', 'user': '', 'password': '', 'in': 2030, 'out': 5556}]}


def remember_read():
    try:
        records = json.loads(REMEMBER_FILE.read_text())
        if not isinstance(records, dict):
            return {}
        now = time.time()
        return {k: v for k, v in records.items()
                if isinstance(v, dict) and isinstance(v.get('expires'), (int, float))
                and v['expires'] > now and isinstance(v.get('csrf'), str)}
    except (OSError, ValueError, TypeError):
        return {}


def remember_write(records):
    REMEMBER_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = REMEMBER_FILE.with_suffix('.tmp')
    with open(tmp, 'w') as f:
        os.fchmod(f.fileno(), 0o600)
        json.dump(records, f)
    os.replace(tmp, REMEMBER_FILE)


def remember_digest(token):
    return hashlib.sha256(token.encode('ascii')).hexdigest()


def remember_create(token, session):
    records = remember_read()
    records[remember_digest(token)] = session
    remember_write(records)


def remember_revoke(token):
    records = remember_read()
    records.pop(remember_digest(token), None)
    remember_write(records)


def password_hash(p):
    salt = secrets.token_bytes(16)
    return base64.b64encode(salt).decode() + ':' + base64.b64encode(hashlib.pbkdf2_hmac('sha256', p.encode(), salt, 400000)).decode()


def verify(p, stored):
    try:
        a, b = stored.split(':', 1)
        salt = base64.b64decode(a)
        return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256', p.encode(), salt, 400000), base64.b64decode(b))
    except Exception:
        return False


class DockerError(Exception):
    pass


def docker(method, path, body=None):
    class UnixConnection(http.client.HTTPConnection):
        def connect(self):
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.settimeout(40)
            self.sock.connect('/var/run/docker.sock')
    conn = UnixConnection('localhost', timeout=40)
    try:
        raw = json.dumps(body).encode() if body is not None else None
        conn.request(method, '/v1.41' + path, body=raw, headers={'Content-Type': 'application/json'} if raw else {})
        resp = conn.getresponse()
        data = resp.read()
        result = json.loads(data) if data else {}
        if resp.status >= 400:
            raise DockerError(result.get('message', f'Docker HTTP {resp.status}'))
        return result
    finally:
        conn.close()


def exists(name):
    try:
        return docker('GET', '/containers/' + name + '/json')
    except DockerError as e:
        if 'No such container' in str(e):
            return None
        raise


def status(stream):
    names = [f'{PREFIX}{stream["id"]}-rx', f'{PREFIX}{stream["id"]}-tx']
    states = []
    for name in names:
        obj = exists(name)
        states.append(obj['State']['Running'] if obj else False)
    return 'Läuft' if all(states) else ('Teilweise aktiv' if any(states) else 'Gestoppt')


def image_pull(image):
    # Docker may return multiple newline-separated JSON status messages.
    class UnixConnection(http.client.HTTPConnection):
        def connect(self):
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.settimeout(120)
            self.sock.connect('/var/run/docker.sock')
    conn = UnixConnection('localhost', timeout=120)
    try:
        conn.request('POST', '/v1.41/images/create?fromImage=' + urllib.parse.quote(image, safe='') , headers={'Content-Length': '0'})
        resp = conn.getresponse()
        if resp.status >= 400:
            raise DockerError(resp.read().decode()[:500])
        while True:
            line = resp.readline()
            if not line:
                break
            try:
                msg = json.loads(line)
                if msg.get('error'):
                    raise DockerError(msg['error'])
            except ValueError:
                pass
    finally:
        conn.close()


def ensure_network():
    try:
        docker('GET', '/networks/moo-single-net')
    except DockerError as e:
        if 'not found' not in str(e).lower() and 'no such network' not in str(e).lower():
            raise
        docker('POST', '/networks/create', {'Name': 'moo-single-net', 'Driver': 'bridge', 'Labels': {'app': 'moo-single-manager'}})


def start_stream(s):
    ensure_network()
    for image in [f'moothecow/moo-rist:{IMAGE}', f'moothecow/moo-rist-forwarder:{IMAGE}']:
        try:
            docker('GET', '/images/' + urllib.parse.quote(image, safe='') + '/json')
        except DockerError:
            image_pull(image)
    sid = s['id']
    rx, tx = f'{PREFIX}{sid}-rx', f'{PREFIX}{sid}-tx'
    auth = '&username=' + s['user'] + '&password=' + s['password']
    specs = [
        (tx, f'moothecow/moo-rist-forwarder:{IMAGE}', ['ristsender', '-v', '-1', '-i', f'udp://@{tx}:12345', '-o', f'rist://@{tx}:5556?cname=moo-rist-relay', '-p', '1'], 5556, s['out']),
        (rx, f'moothecow/moo-rist:{IMAGE}', ['ristreceiver', '-v', '6', '-b', '1800', '-i', f'rist://@{rx}:2030?rtt-min=70&rtt-max=1200{auth}', '-o', f'rist://{tx}:12345', '-p', '1'], 2030, s['in']),
    ]
    for name, image, cmd, internal, external in specs:
        obj = exists(name)
        if obj and obj['State']['Running']:
            continue
        if obj:
            docker('DELETE', '/containers/' + name + '?force=true')
        config = {'Image': image, 'Cmd': cmd, 'Labels': {'app': 'moo-single-manager', 'stream': str(sid)}, 'HostConfig': {'RestartPolicy': {'Name': 'unless-stopped'}, 'NetworkMode': 'moo-single-net', 'PortBindings': {f'{internal}/udp': [{'HostPort': str(external)}]}} , 'ExposedPorts': {f'{internal}/udp': {}}}
        docker('POST', '/containers/create?name=' + name, config)
        docker('POST', '/containers/' + name + '/start')


def stop_stream(s):
    for suffix in ['rx', 'tx']:
        name = f'{PREFIX}{s["id"]}-{suffix}'
        if exists(name):
            docker('DELETE', '/containers/' + name + '?force=true')


def docker_logs(name, tail=80):
    # Docker log API uses 8-byte multiplexed frame headers for non-TTY containers.
    class UnixConnection(http.client.HTTPConnection):
        def connect(self):
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.settimeout(8)
            self.sock.connect('/var/run/docker.sock')
    conn = UnixConnection('localhost', timeout=8)
    try:
        url = '/v1.41/containers/' + urllib.parse.quote(name, safe='') + '/logs?stdout=1&stderr=1&tail=' + str(tail)
        conn.request('GET', url)
        resp = conn.getresponse()
        raw = resp.read(262144)
        if resp.status != 200:
            return ''
        chunks = []
        pos = 0
        while pos + 8 <= len(raw) and raw[pos] in (0, 1, 2) and raw[pos+1:pos+4] == b'\x00\x00\x00':
            size = int.from_bytes(raw[pos+4:pos+8], 'big')
            if size > len(raw) - pos - 8:
                break
            chunks.append(raw[pos+8:pos+8+size])
            pos += 8 + size
        if chunks and pos == len(raw):
            raw = b''.join(chunks)
        return raw.decode('utf-8', errors='replace')[-18000:]
    finally:
        conn.close()


def connection_state(log_text):
    """Latest explicit peer event wins; don't mistake 'connected count is 0' for online."""
    positive = ('authentication successful', 'authentication succeeded', 'authenticated peer',
                'peer connected', 'connection established', 'peer state connected',
                'eap authentication success', 'eap authentication succeeded')
    negative = ('authentication failed', 'peer disconnected', 'connection closed',
                'connection timeout', 'peer timed out', 'removing timed-out peer',
                'listening peer', 'peer connected count is 0')
    for line in reversed(log_text.lower().splitlines()):
        if 'peer connected count is' in line:
            m = re.search(r'peer connected count is\s+(\d+)', line)
            if m:
                return 'Getrennt' if int(m.group(1)) == 0 else 'Verbunden (Loghinweis)'
        if any(x in line for x in negative):
            return 'Getrennt'
        if any(x in line for x in positive):
            return 'Verbunden (Loghinweis)'
    return 'Nicht nachgewiesen'


def rist_log_metrics(log_text):
    """Only extract explicitly labelled measurements; never infer loss or RTT from traffic."""
    values = {'rtt_ms': None, 'loss_pct': None, 'quality_source': 'Keine Messdaten in Receiver-Logs'}
    # Accept explicitly labelled fields only. A bare number or configured rtt-min is not telemetry.
    rtt_re = re.compile(r'(?<![\w-])(?:rtt|round[ -]?trip(?:[ -]?time)?)\s*[:=]\s*(\d+(?:[.,]\d+)?)\s*ms\b', re.I)
    loss_re = re.compile(r'(?<![\w-])(?:packet[ -]?loss|loss[ -]?rate|loss)\s*[:=]\s*(\d+(?:[.,]\d+)?)\s*%', re.I)
    for line in reversed(log_text.splitlines()):
        if values['rtt_ms'] is None:
            m = rtt_re.search(line)
            if m:
                v = float(m.group(1).replace(',', '.'))
                if 0 <= v <= 60000: values['rtt_ms'] = v
        if values['loss_pct'] is None:
            m = loss_re.search(line)
            if m:
                v = float(m.group(1).replace(',', '.'))
                if 0 <= v <= 100: values['loss_pct'] = v
        if values['rtt_ms'] is not None and values['loss_pct'] is not None: break
    if values['rtt_ms'] is not None or values['loss_pct'] is not None:
        values['quality_source'] = 'Receiver-Log (letzter protokollierter Wert; Alter unbekannt)'
    return values


def rist_json_metrics(log_text, now=None):
    """Read schema_version=5 receiver-stats JSON emitted by moo-rist 0.0.39.

    Only recent receiver samples are used. Loss is a packet count, not a percent.
    """
    now = time.time() if now is None else now
    for line in reversed(log_text.splitlines()):
        marker = line.find('{"schema_version"')
        if marker < 0:
            continue
        try:
            timestamp = float(line.split('|', 1)[0])
            data = json.loads(line[marker:])
            flow = data['receiver-stats']['flowinstant']
            stats = flow['stats']
            peers = flow.get('peers') or []
            live_peers = [x for x in peers if x.get('dead') == 0 and isinstance(x.get('stats'), dict)]
            peer = live_peers[0]['stats'] if live_peers else {}
            if data.get('schema_version') != 5 or not (0 <= now - timestamp <= 20):
                continue
            def number(value):
                return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None
            received = number(stats.get('received'))
            bitrate = number(stats.get('bitrate'))
            rtt = number(peer.get('rtt'))
            avg_rtt = number(peer.get('avg_rtt'))
            return {
                'rtt_ms': rtt, 'avg_rtt_ms': avg_rtt,
                'loss_pct': None, 'lost': number(stats.get('lost')),
                'missing': number(stats.get('missing')),
                'recovered': number(stats.get('recovered_total')),
                'retries': number(stats.get('retries')),
                'quality': number(stats.get('quality')),
                'rist_kbps': round(bitrate / 1000, 1) if bitrate is not None else None,
                'received': received, 'flow_dead': number(flow.get('dead')),
                'active_peer': bool(number(flow.get('dead', 0)) == 0 and live_peers and (number(peer.get('received_data')) or 0) > 0 and (received or 0) > 0),
                'quality_source': 'libRIST JSON · letzte 20 Sekunden · Paketwerte pro Statistikintervall'
            }
        except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError):
            continue
    return None


def receiver_traffic(stream_id, name):
    """Estimate incoming container traffic from Docker stats; never claim RIST authentication."""
    try:
        data = docker('GET', '/containers/' + name + '/stats?stream=false&one-shot=true')
        networks = data.get('networks') or {}
        current = sum(int(n.get('rx_bytes', 0)) for n in networks.values())
        container_id = data.get('id') or name
        now = time.monotonic()
        previous = TRAFFIC_SAMPLES.get(stream_id)
        TRAFFIC_SAMPLES[stream_id] = (container_id, current, now)
        if previous is None or previous[0] != container_id or current < previous[1]:
            return {'state': 'Messung läuft', 'rate_kbps': None}
        elapsed = now - previous[2]
        if elapsed <= 0:
            return {'state': 'Messung läuft', 'rate_kbps': None}
        delta = current - previous[1]
        kbps = round(delta * 8 / elapsed / 1000, 1)
        return {'state': 'Netzwerkverkehr erkannt' if delta > 1024 else 'Kein relevanter Verkehr gemessen', 'rate_kbps': kbps}
    except (DockerError, OSError, ValueError, KeyError, TypeError, TimeoutError):
        return {'state': 'Messung nicht verfügbar', 'rate_kbps': None}


def stream_diagnostics(stream):
    sid = stream['id']
    rx_name = f'{PREFIX}{sid}-rx'
    tx_name = f'{PREFIX}{sid}-tx'
    rx, tx = exists(rx_name), exists(tx_name)
    rx_up = bool(rx and rx['State']['Running'])
    tx_up = bool(tx and tx['State']['Running'])
    result = {'id': sid, 'receiver': rx_up, 'forwarder': tx_up,
              'status': 'Läuft' if rx_up and tx_up else ('Teilweise aktiv' if rx_up or tx_up else 'Gestoppt'),
              'connection': 'Nicht nachgewiesen', 'quality': {'rtt_ms': None, 'loss_pct': None, 'quality_source': 'Keine Messdaten'}, 'traffic': {'state': 'Receiver gestoppt', 'rate_kbps': None}, 'logs': [], 'updated': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if rx_up:
        result['traffic'] = receiver_traffic(sid, rx_name)
        logs = docker_logs(rx_name)
        log_connection = connection_state(logs)
        result['connection'] = log_connection
        result['quality'] = rist_log_metrics(logs)
        rist = rist_json_metrics(logs)
        if rist is not None:
            # Never display stale RTT/quality as live data after a dead flow.
            if rist['flow_dead'] not in (None, 0):
                result['connection'] = 'Verbindung unterbrochen'
                result['quality'] = {'quality_source': 'RIST-Flow unterbrochen · keine aktuellen Messdaten'}
            elif rist['active_peer']:
                result['connection'] = 'Aktiver RIST-Empfang (Statistik)'
                result['quality'] = rist
            elif rist['received'] == 0:
                result['connection'] = 'Kein Datenempfang'
                result['quality'] = {'quality_source': 'Keine empfangenen Datenpakete · keine aktuellen Messdaten'}
            else:
                result['connection'] = 'Status unbekannt'
                result['quality'] = {'quality_source': 'Keine bestätigten aktiven Peers'}
        elif log_connection == 'Verbunden (Loghinweis)':
            # Old positive events can remain in the log long after a disconnect.
            result['connection'] = 'Keine aktuellen RIST-Messdaten'
            result['quality'] = {'quality_source': 'Keine aktuellen RIST-Messdaten'}
        elif log_connection == 'Getrennt':
            result['quality'] = {'quality_source': 'Verbindung getrennt · keine aktuellen Messdaten'}
        result['logs'] = [line.replace(stream.get('password', ''), '[GEHEIM]')[-350:] if stream.get('password') else line[-350:] for line in logs.splitlines()[-10:]]
    return result


def port_conflict(port):
    # Check actual published bindings of all Docker containers (including stopped).
    containers = docker('GET', '/containers/json?all=1')
    for container in containers:
        for binding in container.get('Ports', []):
            if binding.get('PublicPort') == port and binding.get('Type') == 'udp':
                return container.get('Names', ['unbekannt'])[0]
    # Check host UDP sockets; Docker's port bindings remain authoritative at start.
    for path in ('/proc/net/udp', '/proc/net/udp6'):
        try:
            for line in Path(path).read_text().splitlines()[1:]:
                parts = line.split()
                if len(parts) > 1 and int(parts[1].split(':')[1], 16) == port:
                    return 'Host-Prozess'
        except (OSError, ValueError, IndexError):
            pass
    return None


def valid_user(v):
    return bool(re.fullmatch(r'[A-Za-z0-9_-]{1,48}', v))


def generate_rist_password():
    # Cryptographically secure; characters are compatible with RIST credentials.
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789_-'
    return ''.join(secrets.choice(alphabet) for _ in range(20))


def valid_password(v):
    return bool(re.fullmatch(r'[A-Za-z0-9_-]{12,100}', v))


STYLE = '''<style>*{box-sizing:border-box}body{margin:0;background:#0d1729;color:#eaf2ff;font:16px Arial,sans-serif}header{background:#142139;padding:18px 24px;display:flex;justify-content:space-between;align-items:center}header b{font-size:22px}main{max-width:1060px;margin:24px auto;padding:0 12px}.panel{background:#1a2b44;border:1px solid #314c70;border-radius:12px;padding:24px;margin-bottom:20px}.stream{border:1px solid #375375;border-radius:14px;padding:24px;margin:18px 0}h2{font-size:20px;margin:0 0 22px}h3{margin:0 0 10px}.muted{color:#a6c7f7;font-size:13px}.row{display:flex;gap:12px;flex-wrap:wrap;align-items:end}.field{flex:1;min-width:180px}label{display:block;margin-bottom:8px;font-size:14px}input{background:#0d1729;color:white;border:1px solid #59728e;border-radius:8px;padding:13px;width:100%;font-size:15px}button{background:#439ff9;border:0;border-radius:8px;padding:13px 16px;font-weight:bold;cursor:pointer}button.stop{background:#f7c975}button.danger{background:#e68e9a}button.secondary{background:#385170;color:white}form{display:inline-block}form.inline{display:flex;gap:10px;align-items:end;flex-wrap:wrap}.split{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin:12px 0}.addr{color:#77caff;font-family:monospace;overflow-wrap:anywhere}hr{border:0;border-top:1px solid #385170;margin:22px 0}.ok{color:#4aefba}.error{background:#4e2731;padding:14px;border-radius:8px;margin:15px 0}.success{background:#17473e;padding:14px;border-radius:8px;margin:15px 0}@media(max-width:650px){.panel,.stream{padding:15px}header b{font-size:17px}}.monitor{margin-top:22px;padding:18px;background:#12233b;border:1px solid #385170;border-radius:12px}.monitor h4{margin:0 0 14px;font-size:16px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.monitor h4 small{font-weight:normal;color:#a6c7f7}.monitor-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.metric-head{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}.traffic-tag{font-style:normal;font-size:12px;color:#a6c7f7}.traffic-tag.tag-ok{color:#48eab3;font-weight:bold}.traffic-tag.tag-off{color:#f7c975;font-weight:bold}.metric{background:#0e1b30;border:1px solid #314c70;border-radius:10px;padding:14px;min-width:0}.metric span,.metric small{display:block;color:#a6c7f7;font-size:12px}.metric strong{display:block;margin:10px 0;color:#eaf2ff;overflow-wrap:anywhere}.edit{margin-top:20px}.stream .row{margin-bottom:0}@media(max-width:750px){.monitor-grid{grid-template-columns:1fr}}
/* V0.6: kompakte Statuskarten; ausschließlich Darstellung, keine Backend-Änderung. */
.monitor{margin-top:14px;padding:12px;border-radius:10px}
.monitor h4{margin:0 0 9px;font-size:15px;align-items:center}
.monitor h4 small{font-size:11px}
.monitor-grid{gap:8px;grid-template-columns:repeat(3,minmax(0,1fr))}
.metric{padding:9px 10px;border-radius:8px;min-height:66px}
.metric span,.metric small{font-size:11px;line-height:1.3}
.metric strong{font-size:14px;line-height:1.3;margin:6px 0 0}
.metric .metric-head{flex-wrap:nowrap;align-items:baseline}
.metric .metric-head span{min-width:0}
.traffic-tag{white-space:nowrap;font-size:11px}
.metric > small{display:none}
.monitor > p.muted{font-size:11px;line-height:1.35;margin:8px 0 0}
.monitor > details{margin-top:8px;font-size:12px}
@media(max-width:750px){.monitor-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:480px){.monitor-grid{grid-template-columns:1fr}.monitor{padding:10px}.metric{min-height:0}}
.remember-choice{display:flex;align-items:center;gap:9px;cursor:pointer;color:#dcecff}.remember-choice input{width:auto;accent-color:#439ff9}
.password-wrap{display:flex;align-items:stretch;gap:6px}.password-wrap input{min-width:0;flex:1}.password-eye{flex:0 0 46px;min-width:46px;padding:8px;background:#233d61;color:#dcecff;border:1px solid #50719a;border-radius:8px;cursor:pointer}.password-eye:hover{background:#30537f}
</style>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print('%s %s' % (self.address_string(), fmt % args), flush=True)

    def send(self, body, status_code=200, cookie=None):
        raw = body.encode()
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(raw)

    def send_json(self, data, status_code=200):
        raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(raw)

    def redirect(self, cookie=None):
        self.send_response(303)
        self.send_header('Location', '/')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()

    def session(self):
        jar = http.cookies.SimpleCookie()
        try:
            jar.load(self.headers.get('Cookie', ''))
            token = jar['session'].value if 'session' in jar else ''
        except Exception:
            token = ''
        item = SESSIONS.get(token)
        if item and item['expires'] > time.time():
            return item
        if token:
            return remember_read().get(remember_digest(token))
        return None

    def page(self, content, message=''):
        notice = f'<div class="error">{html.escape(message)}</div>' if message else ''
        return '<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RIST Hosting Manager</title>' + STYLE + '<header><b>◉ RIST Hosting Manager</b><span>Single User Edition</span></header><main>' + notice + content + '</main></html>'

    def do_GET(self):
        with LOCK:
            s = load()
            if self.path == '/api/status':
                if not s['admin'] or not self.session():
                    return self.send_json({'error': 'Nicht angemeldet'}, 401)
                diagnostics = []
                for stream in s['streams']:
                    try:
                        diagnostics.append(stream_diagnostics(stream))
                    except (DockerError, OSError, ValueError) as e:
                        diagnostics.append({'id': stream['id'], 'status': 'Docker-Fehler', 'connection': 'Unbekannt', 'quality': {'rtt_ms': None, 'loss_pct': None, 'quality_source': 'Keine Messdaten'}, 'traffic': {'state': 'Messung nicht verfügbar', 'rate_kbps': None}, 'logs': [], 'error': str(e)[:180]})
                return self.send_json({'streams': diagnostics})
            if not s['admin']:
                content = '''<section class="panel"><h2>Ersteinrichtung</h2><p>Ein Administrator und ein fester Hauptstream. Beide Zugangsdaten müssen festgelegt werden.</p><form method="post" action="/setup"><div class="row"><div class="field"><label>Administratorpasswort (mindestens 12 Zeichen)</label><input name="admin" type="password" minlength="12" required></div><div class="field"><label>RIST-Benutzername</label><input name="user" required></div><div class="field"><label>RIST-Passwort</label><p class="muted">Wird beim Abschließen automatisch sicher generiert (20 Zeichen). Nach der Anmeldung über das Augensymbol sichtbar.</p></div></div><p class="muted">RIST-Zugangsdaten: nur Buchstaben, Zahlen, _ und -. Administratorpasswort frei wählbar.</p><button>Einrichtung abschließen</button></form></section>'''
                return self.send(self.page(content))
            sess = self.session()
            if not sess:
                return self.send(self.page('''<section class="panel"><h2>Anmelden</h2><form method="post" action="/login"><label>Administratorpasswort</label><input type="password" name="password" required><p><label class="remember-choice"><input type="checkbox" name="remember" value="yes"> 30 Tage angemeldet bleiben</label></p><p><button>Anmelden</button></p></form></section>'''))
            csrf = html.escape(sess['csrf'], quote=True)
            host = html.escape(self.headers.get('Host', '').split(':')[0], quote=True)
            if not host or not re.fullmatch(r'[A-Za-z0-9.\-:\[\]]+', host):
                host = 'SERVER-IP'
            parts = [f'<section class="panel"><h2>Stream hinzufügen</h2><p>Jeder neue Stream erhält automatisch eigene UDP-Ports und zwei Moo-Container.</p><form method="post" action="/create"><input type="hidden" name="csrf" value="{csrf}"><div class="row"><div class="field"><label>Anzeigename</label><input name="name" maxlength="80" required placeholder="Mein Stream"></div><div class="field"><label>RIST-Benutzername</label><input name="user" required></div><div class="field"><label>RIST-Passwort</label><p class="muted">Wird beim Anlegen automatisch sicher generiert (20 Zeichen). Danach beim Stream über das Augensymbol anzeigen.</p></div><button>Stream hinzufügen</button></div></form></section><section class="panel"><h2>RIST-Server ({len(s["streams"])})</h2>']
            for stream in s['streams']:
                sid = stream['id']
                try:
                    st = status(stream)
                except Exception as e:
                    st = 'Docker-Fehler'
                name = html.escape(stream['name'])
                color = 'ok' if st == 'Läuft' else 'muted'
                parts.append(f'<article class="stream" data-stream-id="{sid}"><div class="split"><h3>{name}</h3><b class="{color}">Status: {st}</b></div><p class="muted">{"Hauptstream · nicht löschbar" if sid == 1 else "Eigener Stream"}</p><hr><b>RIST-Verbindungen</b><div class="split"><span>Eingang · Encoder / IRLBOX</span><span class="addr">rist://{host}:{stream["in"]}</span></div><div class="split"><span>Ausgang · OBS / Empfänger</span><span class="addr">rist://{host}:{stream["out"]}</span></div><hr><b>RIST-Zugangsdaten</b><div class="split"><span>RIST-Benutzername</span><span>{html.escape(stream["user"])}</span></div><form class="inline" method="post" action="/password"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="id" value="{sid}"><div class="field"><label for="rist-password-{sid}">RIST-Passwort</label><div class="password-wrap"><input id="rist-password-{sid}" type="password" name="password" value="{html.escape(stream['password'], quote=True)}" minlength="12" autocomplete="off" spellcheck="false" required><button class="password-eye" type="button" aria-label="Passwort anzeigen" aria-pressed="false" onclick="toggleRistPassword(this)" title="Passwort anzeigen">👁</button></div></div><button>Passwort speichern</button></form><p class="muted">Das gespeicherte Passwort ist standardmäßig verborgen. Nur bei einer tatsächlichen Änderung wird der Stream gestoppt; anschließend neu starten. Passwort niemals öffentlich teilen.</p><hr><b>Streamsteuerung</b><div class="row" style="margin-top:12px"><form method="post" action="/start"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="id" value="{sid}"><button>▶ Starten</button></form><form method="post" action="/stop"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="id" value="{sid}"><button class="stop">■ Stoppen</button></form>')
                if sid != 1:
                    parts.append(f'<form method="post" action="/delete" onsubmit="return confirm(\'Stream wirklich löschen?\')"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="id" value="{sid}"><button class="danger">Löschen</button></form>')
                parts.append(f'''</div><section class="monitor"><h4>Live-Überwachung <small data-role="updated">Warte auf Messung …</small></h4><div class="monitor-grid"><div class="metric"><span>Receiver / Forwarder</span><strong data-role="process">Prüfe …</strong></div><div class="metric"><span>RIST-Verbindung (Loghinweis)</span><strong data-role="connection">Prüfe …</strong></div><div class="metric"><div class="metric-head"><span>Receiver-Netzwerkverkehr</span><em data-role="traffic" class="traffic-tag">Prüfe …</em></div><strong data-role="rate">Messung läuft …</strong><small>Aktuell empfangene Netzwerkdaten · kbit/s</small></div><div class="metric"><span>Verlorene Pakete (RIST)</span><strong data-role="loss">Keine Messdaten</strong><small>Im letzten libRIST-Statistikintervall · keine Prozentquote</small></div><div class="metric"><span>RTT / Round-Trip-Time</span><strong data-role="rtt">Keine Messdaten</strong><small>Aktuelle RTT und Durchschnitt · ms</small></div><div class="metric"><span>RIST-Bitrate</span><strong data-role="rist-rate">Keine Messdaten</strong><small>libRIST · kbit/s</small></div><div class="metric"><span>Wiederhergestellt / Fehlend</span><strong data-role="recovery">Keine Messdaten</strong><small>Pakete pro Statistikintervall</small></div><div class="metric"><span>Qualität / Wiederholungen</span><strong data-role="quality">Keine Messdaten</strong><small>libRIST-Qualitätswert / Retries</small></div></div><p class="muted" data-role="quality-source">RIST-Qualitätswerte sind nur verfügbar, wenn der Receiver sie protokolliert.</p><p class="muted">Netzwerkverkehr ist nur ein Hinweis auf eingehende Daten, kein Nachweis für erfolgreiches RIST-Handshake oder Videobild.</p><p class="muted" data-role="error" hidden></p><details><summary class="muted">Letzte Receiver-Meldungen</summary><pre data-role="logs" style="white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;color:#a6c7f7"></pre></details></section><details class="edit"><summary>Stream bearbeiten</summary><form class="inline" method="post" action="/edit"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="id" value="{sid}"><div class="field"><label>Anzeigename</label><input name="name" value="{html.escape(stream['name'], quote=True)}" maxlength="80" required></div><div class="field"><label>RIST-Benutzername</label><input name="user" value="{html.escape(stream['user'], quote=True)}" required></div><button>Änderungen speichern</button></form><p class="muted">Eine Änderung des RIST-Benutzernamens stoppt diesen Stream; anschließend neu starten. Eine reine Namensänderung unterbricht nichts.</p></details></article>''')
            parts.append(f'</section><form method="post" action="/logout"><input type="hidden" name="csrf" value="{csrf}"><button class="secondary">Abmelden</button></form><p class="muted">Status zeigt Docker-Containerstatus, keine bestätigte RIST-Verbindung. IP-Anzeige basiert auf der aufgerufenen Serveradresse.</p>')
            parts.append(r'''<script>
function toggleRistPassword(button){
 const input=button.parentElement.querySelector('input');
 const visible=input.type==='password';
 input.type=visible?'text':'password';
 button.setAttribute('aria-pressed',String(visible));
 button.setAttribute('aria-label',visible?'Passwort verbergen':'Passwort anzeigen');
 button.title=visible?'Passwort verbergen':'Passwort anzeigen';
}
let refreshInProgress = false;
async function refreshStreams(){
 if(refreshInProgress) return;
 refreshInProgress = true;
 try {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 18000);
  let response;
  try { response = await fetch('/api/status', {cache:'no-store', signal:controller.signal}); }
  finally { clearTimeout(timeout); }
  if(!response.ok) throw new Error('HTTP '+response.status);
  const data = await response.json();
  if(!Array.isArray(data.streams)) throw new Error('Ungültige Statusantwort');
  for(const stream of data.streams){
   const card=document.querySelector('[data-stream-id="'+stream.id+'"]');
   if(!card)continue;
   const update=(role,value)=>{const el=card.querySelector('[data-role="'+role+'"]');if(el)el.textContent=value;};
   update('process',stream.error?'Nicht verfügbar':(stream.receiver?'Läuft':'Aus')+' / '+(stream.forwarder?'Läuft':'Aus'));
   update('connection',stream.connection||'Unbekannt');
   const traffic=stream.traffic||{};
   const trafficKnown=typeof traffic.rate_kbps==='number';
   const trafficDetected=trafficKnown && traffic.state==='Netzwerkverkehr erkannt';
   update('traffic',trafficDetected?'Erkannt':(trafficKnown?'Kein Verkehr':(traffic.state||'Nicht verfügbar')));
   update('rate',trafficKnown?traffic.rate_kbps.toLocaleString('de-DE',{maximumFractionDigits:1,minimumFractionDigits:1})+' kbit/s':'Keine Messdaten');
   const trafficBadge=card.querySelector('[data-role="traffic"]');
   if(trafficBadge)trafficBadge.className='traffic-tag '+(trafficDetected?'tag-ok':(trafficKnown?'tag-off':''));
   const q=stream.quality||{};
   update('loss',typeof q.lost==='number'?q.lost.toLocaleString('de-DE')+' Pakete':(typeof q.loss_pct==='number'?q.loss_pct.toLocaleString('de-DE')+' %':'Keine Messdaten'));
   update('rtt',typeof q.rtt_ms==='number'?q.rtt_ms.toLocaleString('de-DE',{maximumFractionDigits:2})+' ms'+(typeof q.avg_rtt_ms==='number'?' · Ø '+q.avg_rtt_ms.toLocaleString('de-DE',{maximumFractionDigits:2})+' ms':''):'Keine Messdaten');
   update('rist-rate',typeof q.rist_kbps==='number'?q.rist_kbps.toLocaleString('de-DE',{maximumFractionDigits:1})+' kbit/s':'Keine Messdaten');
   update('recovery',typeof q.recovered==='number'&&typeof q.missing==='number'?q.recovered+' / '+q.missing:'Keine Messdaten');
   update('quality',typeof q.quality==='number'?q.quality+' / '+(q.retries??'–'):'Keine Messdaten');
   update('quality-source',q.quality_source||'Keine Messdaten');
   update('logs',(stream.logs||[]).join('\n'));
   update('updated','Aktualisiert: '+new Date().toLocaleTimeString('de-DE'));
   const err=card.querySelector('[data-role="error"]');
   if(err){err.hidden=!stream.error;err.textContent=stream.error||'';}
  }
 }catch(e){
  for(const card of document.querySelectorAll('.stream')){
   const el=card.querySelector('[data-role="updated"]');
   if(el)el.textContent='Statusabfrage fehlgeschlagen: '+e.message;
  }
 }finally{refreshInProgress=false;}
}
refreshStreams();setInterval(refreshStreams,5000);
</script>''')
            return self.send(self.page(''.join(parts)))

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        if length > 8192:
            return self.send(self.page('', 'Anfrage zu groß.'), 413)
        data = urllib.parse.parse_qs(self.rfile.read(length).decode(errors='replace'))
        def get(key):
            return data.get(key, [''])[0]
        with LOCK:
            s = load()
            path = self.path
            try:
                if path == '/setup' and not s['admin']:
                    if len(get('admin')) < 12 or not valid_user(get('user')):
                        raise ValueError('Adminpasswort mindestens 12 Zeichen; RIST-Benutzername nur A-Z, 0-9, _ und -.')
                    s['admin'] = password_hash(get('admin'))
                    s['streams'][0]['user'] = get('user')
                    s['streams'][0]['password'] = generate_rist_password()
                    save(s)
                    return self.redirect()
                if path == '/login' and s['admin']:
                    if not verify(get('password'), s['admin']):
                        raise ValueError('Falsches Passwort.')
                    token = secrets.token_urlsafe(32)
                    remember = get('remember') == 'yes'
                    lifetime = REMEMBER_SECONDS if remember else 43200
                    session = {'csrf': secrets.token_urlsafe(32), 'expires': time.time() + lifetime}
                    if remember:
                        remember_create(token, session)
                    else:
                        SESSIONS[token] = session
                    # LAN uses HTTP; Secure cookies require HTTPS and would break LAN login.
                    cookie = f'session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={lifetime}' if remember else f'session={token}; HttpOnly; SameSite=Strict; Path=/'
                    return self.redirect(cookie)
                sess = self.session()
                if not sess or not hmac.compare_digest(get('csrf'), sess['csrf']):
                    return self.send(self.page('', 'Nicht angemeldet oder ungültige Sitzung.'), 403)
                if path == '/logout':
                    jar = http.cookies.SimpleCookie()
                    try:
                        jar.load(self.headers.get('Cookie', ''))
                        current_token = jar['session'].value if 'session' in jar else ''
                    except Exception:
                        current_token = ''
                    SESSIONS.pop(current_token, None)
                    if current_token:
                        remember_revoke(current_token)
                    return self.redirect('session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
                if path == '/create':
                    name = get('name').strip()
                    if not name or len(name) > 80 or not valid_user(get('user')):
                        raise ValueError('Ungültige Stream-Daten. RIST-Benutzername nur A-Z, 0-9, _ und -.')
                    sid = s['next_id']
                    pin, pout = 2030 + sid - 1, 5556 + sid - 1
                    if pout > 65535:
                        raise ValueError('Keine weiteren Portpaare verfügbar.')
                    # Port allocation is monotonic; never reuse IDs automatically.
                    for port in (pin, pout):
                        conflict = port_conflict(port)
                        if conflict:
                            raise ValueError(f'UDP-Port {port} bereits belegt: {conflict}')
                    s['streams'].append({'id': sid, 'name': name, 'user': get('user'), 'password': generate_rist_password(), 'in': pin, 'out': pout})
                    s['next_id'] += 1
                    save(s)
                elif path in ('/start', '/stop', '/delete', '/password', '/edit'):
                    sid = int(get('id'))
                    stream = next((x for x in s['streams'] if x['id'] == sid), None)
                    if stream is None:
                        raise ValueError('Stream nicht gefunden.')
                    if path == '/start':
                        start_stream(stream)
                    elif path == '/stop':
                        stop_stream(stream)
                    elif path == '/delete':
                        if sid == 1:
                            raise ValueError('Der Hauptstream kann nicht gelöscht werden.')
                        stop_stream(stream)
                        s['streams'].remove(stream)
                        save(s)
                    elif path == '/edit':
                        name = get('name').strip()
                        user = get('user').strip()
                        if not name or len(name) > 80 or not valid_user(user):
                            raise ValueError('Ungültiger Anzeigename oder RIST-Benutzername.')
                        if stream['user'] != user:
                            stop_stream(stream)
                            stream['user'] = user
                        stream['name'] = name
                        save(s)
                    else:
                        if not valid_password(get('password')):
                            raise ValueError('Passwort mindestens 12 Zeichen; nur A-Z, 0-9, _ und -.')
                        if stream['password'] != get('password'):
                            stop_stream(stream)
                            stream['password'] = get('password')
                            save(s)
                else:
                    return self.send(self.page('', 'Unbekannte Aktion.'), 404)
                return self.redirect()
            except (ValueError, DockerError, OSError) as e:
                return self.send(self.page('<p><a style="color:#77caff" href="/">Zurück</a></p>', str(e)), 400)


if __name__ == '__main__':
    print('Moo-RIST Single Manager listening on 0.0.0.0:3000', flush=True)
    ThreadingHTTPServer(('0.0.0.0', 3000), Handler).serve_forever()
