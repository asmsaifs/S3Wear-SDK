"""Rules shared by `s3w check` and the docs checks: the manifest's, the store listing's (listing.json) and the content
policy's. Pure Python, no I/O."""
import json
import re

# The manifest's permission names (the app API's `@perm` tags use the same ones).
PERMISSIONS = {"storage", "imu", "audio.play", "audio.record", "health.read", "notify", "phone.http", "wifi.http",
               "location", "keep_screen_on", "background", "files", "gameboy"}
# Permissions that give an app access to the user's data or the network: a privacy policy is required (store policy).
PRIVACY_PERMISSIONS = {"phone.http", "wifi.http", "location", "audio.record", "health.read", "files"}
RESERVED_PREFIXES = ("dev.s3wear.", "s3w.", "com.s3wear.")
BUILTIN_FACE_IDS = {"digital", "analog", "modular", "minimal"}

MANIFEST_ID = re.compile(r"^[a-z0-9_-]+(\.[a-z0-9_-]+)+$")
SEMVER = re.compile(r"^\d{1,5}\.\d{1,5}\.\d{1,5}$")


def manifest_problems(m, api_level):
    """The manifest's rules: a list of strings, [] when it is fine."""
    out = []
    for key in ("id", "name", "version", "api_level", "ui_mode"):
        if key not in m:
            out.append(f"{key} missing")
    if out:
        return out
    if not (isinstance(m["id"], str) and MANIFEST_ID.match(m["id"]) and len(m["id"]) <= 47):
        out.append("id: reverse-DNS of [a-z0-9_-] parts, at most 47 bytes")
    if not (isinstance(m["name"], str) and 0 < len(m["name"].encode()) <= 31):
        out.append("name: 1..31 bytes")
    if not (isinstance(m["version"], str) and SEMVER.match(m["version"])):
        out.append("version: MAJOR.MINOR.PATCH")
    if not (isinstance(m["api_level"], int) and 1 <= m["api_level"] <= api_level):
        out.append(f"api_level: 1..{api_level}")
    if m["ui_mode"] not in ("widgets", "canvas"):
        out.append("ui_mode: widgets or canvas")
    perms = m.get("permissions", [])
    if not isinstance(perms, list):
        out.append("permissions: a list")
        perms = []
    for p in perms:
        if p not in PERMISSIONS:
            out.append(f"permissions: unknown '{p}'")
    if "memory_kb" in m and not (isinstance(m["memory_kb"], int) and 64 <= m["memory_kb"] <= 1024):
        out.append("memory_kb: 64..1024")
    if "storage_kb" in m and not (isinstance(m["storage_kb"], int) and m["storage_kb"] <= 4096 and "storage" in perms):
        out.append("storage_kb: at most 4096 and needs the storage permission")
    if "http_hosts" in m and not ({"phone.http", "wifi.http"} & set(perms)):
        out.append("http_hosts: needs phone.http or wifi.http")
    if m.get("category", "app") not in ("app", "game", "tool", "health"):
        out.append("category: app, game, tool or health")
    return out


# --- listing.json ---------------------------------------------------------------------------------------------------

URL = r"^https://[^\s/$.?#][^\s]*$"
LISTING_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "S3Wear store listing (listing.json)",
    "type": "object",
    "additionalProperties": False,
    "required": ["developer", "summary", "support_url", "source_url", "content_rating"],
    "properties": {
        "developer": {"type": "string", "pattern": r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$",
                      "description": "Your login in the store repository."},
        "summary": {"type": "string", "minLength": 1, "maxLength": 80, "description": "One line."},
        "support_url": {"type": "string", "pattern": URL, "maxLength": 200},
        "source_url": {"type": "string", "pattern": URL, "maxLength": 200},
        "privacy_url": {"type": "string", "pattern": URL, "maxLength": 200,
                        "description": "Required with phone.http, wifi.http, location, audio.record, health.read or files."},
        "donate_url": {"type": "string", "pattern": URL, "maxLength": 200, "description": "Optional link to donate."},
        "permission_reasons": {"type": "object", "additionalProperties": {"type": "string", "minLength": 1, "maxLength": 100},
                               "description": "A reason for every permission in the manifest."},
        "http_reasons": {"type": "object", "additionalProperties": {"type": "string", "minLength": 1, "maxLength": 100},
                         "description": "A reason for every host in http_hosts."},
        "content_rating": {"enum": ["everyone", "teen"]},
        "screenshot_captions": {"type": "array", "maxItems": 8, "items": {"type": "string", "minLength": 1, "maxLength": 60}},
    },
}


def schema_problems(value, schema, path="listing"):
    """A small JSON Schema validator for what LISTING_SCHEMA uses: type, enum, pattern, minLength, maxLength, maxItems,
    items, properties, required, additionalProperties (false or a schema)."""
    out = []
    if "enum" in schema:
        if value not in schema["enum"]:
            out.append(f"{path}: one of {', '.join(map(str, schema['enum']))}")
        return out
    t = schema.get("type")
    kinds = {"object": dict, "array": list, "string": str}
    if t and not isinstance(value, kinds[t]):
        return [f"{path}: expected {t}"]
    if t == "string":
        if len(value) < schema.get("minLength", 0):
            out.append(f"{path}: empty")
        if len(value) > schema.get("maxLength", 10 ** 9):
            out.append(f"{path}: {len(value)} characters, at most {schema['maxLength']}")
        if "pattern" in schema and not re.match(schema["pattern"], value):
            out.append(f"{path}: does not look right" + (" (an https:// URL)" if schema["pattern"] == URL else ""))
    elif t == "array":
        if len(value) > schema.get("maxItems", 10 ** 9):
            out.append(f"{path}: {len(value)} items, at most {schema['maxItems']}")
        for i, item in enumerate(value):
            out += schema_problems(item, schema.get("items", {}), f"{path}[{i}]")
    elif t == "object":
        for key in schema.get("required", []):
            if key not in value:
                out.append(f"{path}.{key}: missing")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, v in value.items():
            if key in props:
                out += schema_problems(v, props[key], f"{path}.{key}")
            elif extra is False:
                out.append(f"{path}.{key}: not a listing field")
            elif isinstance(extra, dict):
                out += schema_problems(v, extra, f"{path}.{key}")
    return out


def listing_problems(listing, manifest=None):
    """The schema's rules plus the ones that depend on the manifest: a reason for every permission and host, a privacy
    policy for the permissions that need one. [] when fine. `manifest` is None for a face (no permissions)."""
    out = schema_problems(listing, LISTING_SCHEMA)
    if not isinstance(listing, dict):
        return out
    perms = list(manifest.get("permissions", [])) if manifest else []
    hosts = [h.strip() for h in re.split(r"[ ,]+", str(manifest.get("http_hosts", ""))) if h.strip()] if manifest else []
    reasons = listing.get("permission_reasons", {})
    http = listing.get("http_reasons", {})
    if isinstance(reasons, dict):
        out += [f"permission_reasons.{p}: missing (every permission needs a reason)" for p in perms if p not in reasons]
        out += [f"permission_reasons.{p}: '{p}' is not in the manifest's permissions" for p in reasons if p not in perms]
    if isinstance(http, dict):
        out += [f"http_reasons.{h}: missing (every host needs a reason)" for h in hosts if h not in http]
        out += [f"http_reasons.{h}: '{h}' is not in the manifest's http_hosts" for h in http if h not in hosts]
    needs = sorted(set(perms) & PRIVACY_PERMISSIONS)
    if needs and "privacy_url" not in listing:
        out.append(f"privacy_url: required with {', '.join(needs)}")
    return out


def listing_schema_json():
    return json.dumps(LISTING_SCHEMA, indent=2) + "\n"


# --- content policy ---------------------------------------------------------------------------------------------------

# Game and disc images and console firmware: the store never holds other people's games (store policy).
ROM_EXTENSIONS = {".gb", ".gbc", ".sgb", ".gba", ".nes", ".sfc", ".smc", ".smd", ".md", ".gen", ".n64", ".z64", ".v64",
                  ".nds", ".3ds", ".iso", ".cue", ".chd", ".rom"}
BIOS_WORDS = ("bios", "bootrom", "boot_rom")
# A console maker's or a game's name in a listing; matched as words, case-insensitive.
TRADEMARKS = ("game boy", "gameboy", "nintendo", "playstation", "sony computer", "sega", "atari", "pokemon", "pokémon",
              "zelda", "mario")
# Other names a listing may not borrow (a starting point; the reviewer applies the policy, and a file can extend this).
BRANDS = ("google", "android", "apple", "iphone", "samsung", "whatsapp", "facebook", "instagram", "tiktok", "youtube",
          "netflix", "spotify", "garmin", "fitbit", "pebble", "waveshare", "espressif")
OFFENSIVE = ("fuck", "shit", "cunt", "bitch", "porn", "nazi", "slut", "whore")
OWN_NAME = re.compile(r"^\s*s3\s*w(ear)?\b", re.I)


def file_problem(rel):
    """Why a file may not be in a submission: a game or disc image, console firmware. None when fine."""
    name = rel.rsplit("/", 1)[-1]
    dot = name.rfind(".")
    ext = name[dot:].lower() if dot > 0 else ""
    if ext in ROM_EXTENSIONS:
        return f"a game or disc image ({ext}): the store never holds other people's games"
    if any(w in name.lower() for w in BIOS_WORDS):
        return "a console's firmware: the store never holds it"
    return None


def _contains(text, word):
    return re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", text) is not None


def text_problems(label, text, extra=None):
    """Names the policy keeps out of a listing text. [] when fine."""
    t = text.lower()
    extra = extra or {}
    out = []
    for w in TRADEMARKS + tuple(extra.get("trademarks", [])):
        if _contains(t, w):
            out.append(f"{label}: '{w}' is a console maker's or a game's name: not in a listing")
    for w in BRANDS + tuple(extra.get("brands", [])):
        if _contains(t, w):
            out.append(f"{label}: '{w}' is someone else's brand: do not use it as a name or imply it is theirs")
    for w in OFFENSIVE + tuple(extra.get("offensive", [])):
        if _contains(t, w):
            out.append(f"{label}: '{w}' is not allowed in a listing")
    return out


def name_problems(label, name):
    """The S3Wear name rule: 'for S3Wear' is fine, a name that starts with S3Wear is the store's own."""
    return [f"{label}: a name that starts with S3Wear or S3W is kept for the store's own apps ('Snake for S3Wear' is fine)"] \
        if OWN_NAME.match(name) else []
