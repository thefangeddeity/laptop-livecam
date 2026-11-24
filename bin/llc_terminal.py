"""The viewer's terminal: a login shell on this node, in the browser.

Two locks, both required, and neither one is this file's own invention:

  1. WHO IS ASKING. The request must have arrived through `tailscale serve`,
     which proxies from loopback and stamps the tailnet identity of the person
     in the Tailscale-User-Login header (it strips any copy a client sends).
     A request from the plain LAN port reaches us from a LAN address and is
     refused before anything else is looked at -- the header means nothing
     there, because anyone can type it. The login must also be on the
     TERMINAL_USERS list in config.env; unset, the list is the one person who
     owns this machine on the tailnet. TERMINAL_USERS=off turns the card off.

  2. THE ACCOUNT PASSWORD. The pty runs `su - <user>`, so the password prompt
     is the system's own, checked by PAM against the node's account (Open
     Directory on macOS). The password goes from the keyboard to su through
     the pty; this code never parses, stores or logs it.

And it logs you out when you leave: the page's long-poll is the heartbeat,
and ~10 s without one kills the shell's whole process group. A tab closed,
a phone locked, a network gone -- all the same event. Fifteen minutes with
no keystroke ends it too.

No new dependencies: pty, threads and Flask's own long-poll.
"""

import base64, json, os, pty, pwd, re, secrets, select, signal, struct
import subprocess, sys, termios, threading, time, fcntl

HEARTBEAT_S   = 10        # no read for this long -> the page is gone
IDLE_S        = 15 * 60   # no keystroke for this long -> logged out
POLL_S        = 4.0       # long-poll hold; well inside HEARTBEAT_S
BUF_MAX       = 256 * 1024
MAX_SESSIONS  = 3
FAIL_WINDOW_S = 300       # three wrong passwords in five minutes...
FAIL_MAX      = 3
LOCK_S        = 300       # ...and the prompt is closed for five

_FAIL_MARKS = (b'Sorry', b'Authentication failure', b'incorrect')
_USER_RE = re.compile(r'^[a-z_][a-z0-9_.-]{0,31}$')
_LOOPBACK = ('127.0.0.1', '::1', '::ffff:127.0.0.1')

_lock = threading.Lock()
_sessions = {}            # sid -> _Session
_fails = []               # timestamps of failed logins
_locked_until = [0.0]
_owner = {'at': 0.0, 'login': ''}


def _log(msg):
    print(f'broadcast-api: terminal: {msg}', file=sys.stderr, flush=True)


class _Session:
    def __init__(self, sid, who, user, pid, fd):
        self.sid, self.who, self.user = sid, who, user
        self.pid, self.fd = pid, fd
        self.buf = bytearray()
        self.base = 0              # absolute offset of buf[0]
        self.cond = threading.Condition()
        self.alive = True
        self.reason = ''
        self.started = time.time()
        self.last_seen = time.time()
        self.last_input = time.time()
        self.authed = False        # su handed over to the user's shell
        self.prompted = False
        self.failed = False

    @property
    def end(self):
        return self.base + len(self.buf)

    def feed(self, data):
        with self.cond:
            self.buf += data
            if len(self.buf) > BUF_MAX:
                cut = len(self.buf) - BUF_MAX
                del self.buf[:cut]
                self.base += cut
            self.cond.notify_all()


# ── gate 1 ─────────────────────────────────────────────────────────────────

def _owner_login(tailscale):
    """The tailnet login that owns this machine, cached for a minute."""
    now = time.time()
    if now - _owner['at'] < 60:
        return _owner['login']
    login = ''
    try:
        r = tailscale(['status', '--json'], timeout=8)
        if r is not None and r.returncode == 0:
            j = json.loads(r.stdout)
            uid = str((j.get('Self') or {}).get('UserID', ''))
            login = ((j.get('User') or {}).get(uid) or {}).get('LoginName', '')
    except Exception as exc:
        _log(f'could not read the tailnet owner: {exc}')
    _owner.update(at=now, login=login)
    return login


def allowed_users(cfg, tailscale):
    raw = str(cfg.get('TERMINAL_USERS', '')).strip()
    if raw.lower() in ('off', '0', 'no', 'false', 'none'):
        return None                      # card off on this node
    if raw:
        return {u.strip().lower() for u in raw.split(',') if u.strip()}
    owner = _owner_login(tailscale)
    return {owner.lower()} if owner else set()


def gate(request, cfg, tailscale):
    """(login, None) when the caller may see a prompt, else (None, why)."""
    users = allowed_users(cfg, tailscale)
    if users is None:
        return None, 'off'
    if (request.remote_addr or '') not in _LOOPBACK:
        return None, 'tailnet-only'      # plain LAN port: the header is forgeable
    login = (request.headers.get('Tailscale-User-Login') or '').strip().lower()
    if not login:
        return None, 'tailnet-only'      # loopback, but not via tailscale serve
    if login not in users:
        return None, 'not-allowed'
    return login, None


# ── the shell ──────────────────────────────────────────────────────────────

def _reader(s):
    while True:
        try:
            r, _, _ = select.select([s.fd], [], [], 1.0)
        except (OSError, ValueError):
            break
        if not s.alive:
            break
        if not r:
            continue
        try:
            data = os.read(s.fd, 65536)
        except OSError:
            data = b''
        if not data:
            break
        if not s.authed and s.end < 8192:
            # su (login(1) under root) prints a failure line and exits.
            # Anything else after the password prompt means a shell is up.
            tail = bytes(s.buf[-64:]) + data
            if any(m in tail for m in _FAIL_MARKS):
                s.failed = True
                with _lock:
                    _fails.append(time.time())
                _log(f'failed login as {s.user} from {s.who}')
                s.authed = None
            elif s.prompted and not data.lstrip().startswith((b'su', b'Login', b'login')) \
                    and data.strip(b'\r\n '):
                s.authed = True
                _log(f'{s.who} logged in as {s.user}')
            elif b'assword' in tail:
                s.prompted = True
        s.feed(data)
    _finish(s, 'login incorrect' if s.failed else 'exited')


def _session_pids(sid):
    """Every process still in the shell's session -- jobs a login shell put
    in their own process groups included, which killpg alone would miss."""
    try:
        out = subprocess.run(['ps', '-Ao', 'pid='], capture_output=True,
                             text=True, timeout=5).stdout.split()
    except Exception:
        return []
    pids = []
    for p in out:
        try:
            if int(p) != sid and os.getsid(int(p)) == sid:
                pids.append(int(p))
        except (ValueError, OSError):
            pass
    return pids


def _finish(s, reason):
    with s.cond:
        if not s.alive:
            return
        s.alive = False
        s.reason = s.reason or reason
        s.cond.notify_all()
    # Hang up the line, the way a closed terminal says goodbye: closing the
    # master sends SIGHUP to the session, and the shell passes it to its jobs.
    try:
        os.close(s.fd)
    except OSError:
        pass
    try:
        os.killpg(s.pid, signal.SIGHUP)
    except OSError:
        pass
    _log(f'session for {s.who} ({s.user}) ended: {s.reason}')

    def _reap():
        deadline = time.time() + 3
        while time.time() < deadline:
            try:
                if os.waitpid(s.pid, os.WNOHANG)[0]:
                    break
            except ChildProcessError:
                break
            time.sleep(0.2)
        # Whatever ignored the hangup goes now: the group, then anything
        # left anywhere in the session.
        for pid in [s.pid] + _session_pids(s.pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        try:
            os.waitpid(s.pid, 0)
        except (ChildProcessError, OSError):
            pass
        time.sleep(30)          # let the page read the reason, then forget
        with _lock:
            _sessions.pop(s.sid, None)
    threading.Thread(target=_reap, daemon=True).start()


def _set_size(fd, rows, cols):
    rows = max(2, min(int(rows), 500))
    cols = max(10, min(int(cols), 500))
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))


def _spawn(user, rows, cols):
    if os.geteuid() == 0:
        # Root's su asks nothing; login(1) as root still asks the password.
        argv = ['/bin/login', user] if os.path.exists('/bin/login') \
            else ['/usr/bin/login', user]
    else:
        argv = ['/usr/bin/su' if os.path.exists('/usr/bin/su') else '/bin/su',
                '-', user]
    pid, fd = pty.fork()
    if pid == 0:
        try:
            os.environ['TERM'] = 'xterm-256color'
            os.environ.pop('TMUX', None)
            os.chdir('/')
            os.execv(argv[0], argv)
        finally:
            os._exit(127)
    _set_size(fd, rows, cols)
    return pid, fd


def _watchdog():
    while True:
        time.sleep(1.0)
        now = time.time()
        with _lock:
            live = list(_sessions.values())
        for s in live:
            if not s.alive:
                continue
            if now - s.last_seen > HEARTBEAT_S:
                _finish(s, 'connection lost')
            elif now - s.last_input > IDLE_S:
                s.feed(b'\r\n\r\n[logged out: 15 minutes idle]\r\n')
                _finish(s, 'idle')


# ── routes ─────────────────────────────────────────────────────────────────

def register(app, cfg, tailscale, nocache):
    from flask import request, jsonify

    threading.Thread(target=_watchdog, daemon=True, name='term-watchdog').start()

    def _json(obj, code=200):
        return nocache(jsonify(obj)), code

    def _own(login):
        sid = (request.args.get('sid') or (request.get_json(silent=True) or {}).get('sid') or '')
        with _lock:
            s = _sessions.get(sid)
        if not s or s.who != login:
            return None
        s.last_seen = time.time()
        return s

    def _gated():
        # A custom header forces a CORS preflight, so no other origin can
        # drive this with a plain form post or an <img>.
        if request.method == 'POST' and request.headers.get('X-LLC-Term') != '1':
            return None, ('bad request', 400)
        login, why = gate(request, cfg, tailscale)
        if not login:
            return None, (why, 403)
        return login, None

    @app.route('/api/term/status', methods=['GET'])
    def term_status():
        login, why = gate(request, cfg, tailscale)
        try:
            me = pwd.getpwuid(os.getuid()).pw_name
        except KeyError:
            me = ''
        locked = max(0, int(_locked_until[0] - time.time()))
        return _json({'ok': bool(login), 'why': why or '', 'login': login or '',
                      'user': me, 'host': os.uname().nodename.split('.')[0],
                      'locked': locked, 'heartbeat': HEARTBEAT_S,
                      'idle': IDLE_S})

    @app.route('/api/term/open', methods=['POST'])
    def term_open():
        login, err = _gated()
        if err:
            return _json({'error': err[0]}, err[1])
        now = time.time()
        with _lock:
            _fails[:] = [t for t in _fails if now - t < FAIL_WINDOW_S]
            if len(_fails) >= FAIL_MAX:
                _locked_until[0] = max(_locked_until[0], _fails[-1] + LOCK_S)
                _fails.clear()
            if now < _locked_until[0]:
                return _json({'error': 'locked',
                              'locked': int(_locked_until[0] - now)}, 429)
            if sum(1 for s in _sessions.values() if s.alive) >= MAX_SESSIONS:
                return _json({'error': 'too many sessions'}, 429)
        body = request.get_json(silent=True) or {}
        user = str(body.get('user', '')).strip()
        if not _USER_RE.match(user):
            return _json({'error': 'bad user'}, 400)
        try:
            pwd.getpwnam(user)
        except KeyError:
            with _lock:
                _fails.append(time.time())
            time.sleep(2)
            return _json({'error': 'Login incorrect'}, 403)
        try:
            pid, fd = _spawn(user, body.get('rows', 24), body.get('cols', 80))
        except Exception as exc:
            _log(f'could not start a shell: {exc}')
            return _json({'error': 'spawn failed'}, 500)
        sid = secrets.token_urlsafe(24)
        s = _Session(sid, login, user, pid, fd)
        with _lock:
            _sessions[sid] = s
        threading.Thread(target=_reader, args=(s,), daemon=True,
                         name='term-' + sid[:6]).start()
        _log(f'{login} opened a login prompt for {user}')
        return _json({'sid': sid})

    @app.route('/api/term/read', methods=['GET'])
    def term_read():
        login, why = gate(request, cfg, tailscale)
        if not login:
            return _json({'error': why}, 403)
        s = _own(login)
        if not s:
            return _json({'alive': False, 'reason': 'no session'}, 404)
        try:
            off = int(request.args.get('off', '0'))
        except ValueError:
            off = 0
        deadline = time.time() + POLL_S
        with s.cond:
            while s.alive and off >= s.end and time.time() < deadline:
                s.cond.wait(max(0.05, deadline - time.time()))
            start = max(off, s.base)
            data = bytes(s.buf[start - s.base:])
            end = s.end
        s.last_seen = time.time()
        return _json({'data': base64.b64encode(data).decode('ascii'),
                      'off': end, 'alive': s.alive or bool(data),
                      'reason': '' if s.alive else s.reason})

    @app.route('/api/term/input', methods=['POST'])
    def term_input():
        login, err = _gated()
        if err:
            return _json({'error': err[0]}, err[1])
        s = _own(login)
        if not s or not s.alive:
            return _json({'error': 'no session'}, 404)
        body = request.get_json(silent=True) or {}
        data = str(body.get('data', '')).encode('utf-8', 'surrogateescape')
        if len(data) > 65536:
            return _json({'error': 'too long'}, 413)
        try:
            os.write(s.fd, data)
        except OSError:
            return _json({'error': 'closed'}, 410)
        s.last_input = time.time()
        return _json({'ok': True})

    @app.route('/api/term/resize', methods=['POST'])
    def term_resize():
        login, err = _gated()
        if err:
            return _json({'error': err[0]}, err[1])
        s = _own(login)
        if not s or not s.alive:
            return _json({'error': 'no session'}, 404)
        body = request.get_json(silent=True) or {}
        try:
            _set_size(s.fd, body.get('rows', 24), body.get('cols', 80))
            os.killpg(s.pid, signal.SIGWINCH)
        except (OSError, ValueError, TypeError):
            pass
        return _json({'ok': True})

    @app.route('/api/term/close', methods=['POST'])
    def term_close():
        login, err = _gated()
        if err:
            return _json({'error': err[0]}, err[1])
        s = _own(login)
        if s and s.alive:
            _finish(s, 'logged out')
        return _json({'ok': True})
