"""The watch's USB console (esp_console over USB-Serial-JTAG): install a package, stream logs.

The console echoes each line and prints "s3w> " when the command is done; the next command waits
for that prompt (lines sent while it is busy lose characters). Files go up as base64 lines with
`fs b64` (≤ 256 characters per command line)."""
import base64
import glob
import re
import sys
import time

PROMPT = "s3w> "
LINE_MAX = 250  # the console's 256-byte line, with a margin
STAGING = "/flash/apps/.staging"


class DeviceError(Exception):
    pass


def find_port(port=None):
    if port:
        return port
    ports = sorted(glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/ttyACM*"))
    if not ports:
        raise DeviceError("no watch found on USB (connect it, or pass --port)")
    if len(ports) > 1:
        raise DeviceError("several serial ports: pass --port (" + ", ".join(ports) + ")")
    return ports[0]


class Console:
    def __init__(self, port=None):
        try:
            import serial  # pyserial
        except ImportError:
            raise DeviceError("pyserial is missing: pip install pyserial (or pipx install the CLI)")
        self.port = find_port(port)
        try:
            self.s = serial.Serial(self.port, 115200, timeout=0.05)
        except serial.SerialException as e:
            raise DeviceError(f"{self.port}: {e} (is `idf.py monitor` or `s3w logs` running?)")
        self.cmd("", timeout=2)  # a fresh prompt

    def close(self):
        self.s.close()

    def cmd(self, line, timeout=10.0):
        """Runs one console command; returns its output (without echo and prompt)."""
        self.s.reset_input_buffer()
        self.s.write((line + "\r\n").encode())
        end = time.time() + timeout
        out = b""
        echo = line[:20]
        while time.time() < end:
            out += self.s.read(4096)
            text = out.decode(errors="replace")
            i = text.find(echo)
            if i >= 0 and PROMPT in text[i + len(echo):]:
                body = text[i + len(line):]
                body = body[: body.rfind(PROMPT)]
                return "\n".join(l for l in body.splitlines() if l.strip() not in ("", PROMPT.strip())).strip()
        raise DeviceError(f"no answer to `{line[:40]}` in {timeout:.0f} s")

    def upload(self, data, remote, progress=None):
        """Writes data to remote (replacing it)."""
        self.cmd(f"fs rm {remote}")
        prefix = f"fs b64 {remote} "
        chunk = (LINE_MAX - len(prefix)) // 4 * 3
        if chunk < 48:
            raise DeviceError(f"{remote}: path too long for the console")
        for i in range(0, len(data), chunk):
            part = data[i:i + chunk]
            r = self.cmd(prefix + base64.b64encode(part).decode())
            if f"+{len(part)}" not in r:
                raise DeviceError(f"upload failed at byte {i}: {r}")
            if progress:
                progress(min(i + chunk, len(data)), len(data))


def install(pkg_path, app_id, port=None, ask=True, trust_key=None):
    """Uploads a package to the staging folder and installs it (the watch asks unless ask=False)."""
    data = open(pkg_path, "rb").read()
    con = Console(port)
    try:
        if trust_key:
            print(con.cmd(f"app key add {trust_key}"))
        remote = f"{STAGING}/{app_id}.s3app"
        t0 = time.time()

        def progress(done, total):
            print(f"\ruploading {done}/{total} bytes", end="", flush=True)

        con.upload(data, remote, progress)
        print(f" ({time.time() - t0:.1f} s)")
        out = con.cmd(f"app install {remote}" + ("" if ask else " -y"), timeout=40)
        print(out)
        if "answer on the watch" in out:
            return True
        if "(ESP_OK)" not in out:
            if "unknown key" in out:
                print("the watch does not trust this key: rerun with --trust-key "
                      "(adds it on the watch), or `app key add <s3w key>` on the console", file=sys.stderr)
            if "not signed" in out:
                print("unsigned: sign it (s3w keygen) or turn on the developer option `settings set dev_unsigned 1`",
                      file=sys.stderr)
            return False
        return True
    finally:
        con.close()


LOG_TAGS = re.compile(r"^[IWED] \(\d+\) (app|app_rt|app_mgr):")


def logs(port=None, everything=False):
    """Prints the watch's log lines (app ones only unless everything) until Ctrl-C."""
    try:
        import serial
    except ImportError:
        raise DeviceError("pyserial is missing: pip install pyserial")
    port = find_port(port)
    s = serial.Serial(port, 115200, timeout=0.2)
    print(f"{port}: app logs (Ctrl-C ends)", file=sys.stderr)
    buf = b""
    try:
        while True:
            buf += s.read(4096)
            *lines, buf = buf.split(b"\n")
            for raw in lines:
                line = re.sub(r"\x1b\[[0-9;]*m", "", raw.decode(errors="replace")).rstrip("\r")
                if everything or LOG_TAGS.match(line):
                    print(line, flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        s.close()
