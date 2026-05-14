#!/usr/bin/env python3
import json
import ast
import os
import re
import shutil
import socket
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


def estimate_tokens(text: str) -> int:
    # lightweight approximation for UI display
    text = text or ""
    return max(1, round(len(text) / 4)) if text.strip() else 0


def detect_model_info() -> dict:
    provider = "unknown"
    model = "unknown"
    try:
        proc = subprocess.run(
            [HERMES_BIN, "config"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        cfg = proc.stdout or ""

        # Hermes config output commonly includes:
        #   Model: {'default': 'gpt-5.3-codex', 'provider': 'openai-codex', ...}
        m = re.search(r"Model:\s*(\{.*?\})", cfg)
        if m:
            try:
                obj = ast.literal_eval(m.group(1))
                if isinstance(obj, dict):
                    model = str(obj.get("default") or model)
                    provider = str(obj.get("provider") or provider)
            except Exception:
                pass

        # Fallback parsing
        for line in cfg.splitlines():
            s = line.strip()
            if s.startswith("provider:") and provider == "unknown":
                provider = s.split(":", 1)[1].strip() or provider
            if s.startswith("default:") and model == "unknown":
                model = s.split(":", 1)[1].strip().strip('"') or model
    except Exception:
        pass
    return {"provider": provider, "model": model}


HERMES_BIN = shutil.which("hermes") or "/home/rapiduser/.local/bin/hermes"


def read_config_section_value(section: str, key: str) -> str:
    cfg_path = os.path.expanduser("~/.hermes/config.yaml")
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return ""

    in_section = False
    key_re = re.compile(rf"^\s{{2}}{re.escape(key)}:\s*(.*)$")
    for raw in lines:
        line = raw.rstrip("\n")
        if not in_section:
            if re.match(rf"^{re.escape(section)}:\s*$", line):
                in_section = True
            continue

        if re.match(r"^[^\s].*:\s*$", line):
            break

        m = key_re.match(line)
        if m:
            value = m.group(1).strip().strip("\"'")
            return "" if value in ("", "null", "None") else value
    return ""


def delegation_api_key_from_config() -> str:
    return read_config_section_value("delegation", "api_key")


def model_api_key_from_config() -> str:
    return read_config_section_value("model", "api_key")


MODEL_OPTIONS = [
    {
        "id": "codex-main",
        "label": "GPT-5.3 Codex (openai-codex)",
        "provider": "openai-codex",
        "model": "gpt-5.3-codex",
        "api_key": os.environ.get("OPENAI_API_KEY") or model_api_key_from_config(),
    },
    {
        "id": "duke-litellm",
        "label": "Duke LiteLLM (delegated config)",
        "provider": "openrouter",
        "model": "gpt-5.3",
        "base_url": "https://litellm.oit.duke.edu/v1",
        "api_key": os.environ.get("DUKE_LITELLM_API_KEY") or delegation_api_key_from_config(),
    },
]

STATE = {
    **detect_model_info(),
    "calls": 0,
    "last_input_tokens": 0,
    "last_output_tokens": 0,
    "total_estimated_tokens": 0,
}


def ask_hermes(message: str) -> tuple[str, dict]:
    if not message:
        return "[error] empty message", dict(STATE)

    try:
        env = os.environ.copy()
        if STATE.get("provider") == "openrouter":
            mk = model_api_key_from_config()
            if mk:
                env.setdefault("OPENROUTER_API_KEY", mk)

        proc = subprocess.run(
            [HERMES_BIN, "chat", "-q", message, "-Q"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        reply = "[error] Hermes request timed out"
        in_tok = estimate_tokens(message)
        out_tok = estimate_tokens(reply)
        STATE["calls"] += 1
        STATE["last_input_tokens"] = in_tok
        STATE["last_output_tokens"] = out_tok
        STATE["total_estimated_tokens"] += in_tok + out_tok
        return reply, dict(STATE)
    except Exception as e:
        reply = f"[error] failed to call Hermes: {e}"
        in_tok = estimate_tokens(message)
        out_tok = estimate_tokens(reply)
        STATE["calls"] += 1
        STATE["last_input_tokens"] = in_tok
        STATE["last_output_tokens"] = out_tok
        STATE["total_estimated_tokens"] += in_tok + out_tok
        return reply, dict(STATE)

    if proc.returncode != 0:
        err = (proc.stderr or "").strip()
        out = f"[error] Hermes exited with code {proc.returncode}: {err or 'unknown error'}"
    else:
        out = (proc.stdout or "").strip() or "[warning] Hermes returned empty output"

    in_tok = estimate_tokens(message)
    out_tok = estimate_tokens(out)
    STATE["calls"] += 1
    STATE["last_input_tokens"] = in_tok
    STATE["last_output_tokens"] = out_tok
    STATE["total_estimated_tokens"] += in_tok + out_tok

    return out, dict(STATE)


def set_model_option(option_id: str, api_key_override: str = "") -> tuple[bool, str]:
    option = next((o for o in MODEL_OPTIONS if o["id"] == option_id), None)
    if not option:
        return False, "invalid model option"

    try:
        option = dict(option)
        if api_key_override and option.get("id") in ("duke-litellm", "codex-main"):
            option["api_key"] = api_key_override.strip()

        if option.get("id") == "duke-litellm" and option.get("base_url") and not option.get("api_key"):
            return False, "No API key found for Duke LiteLLM. Set DUKE_LITELLM_API_KEY in the server environment, put a key in delegation.api_key, or enter one in the website API key field."

        if option.get("id") == "codex-main" and not option.get("api_key"):
            return False, "No API key found for GPT-5.3 Codex. Set OPENAI_API_KEY in the server environment, set model.api_key, or enter one in the website API key field."

        p1 = subprocess.run(
            [HERMES_BIN, "config", "set", "model.provider", option["provider"]],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        p2 = subprocess.run(
            [HERMES_BIN, "config", "set", "model.default", option["model"]],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        p3 = None
        p4 = None
        if option.get("base_url"):
            p3 = subprocess.run(
                [HERMES_BIN, "config", "set", "model.base_url", option["base_url"]],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        if option.get("api_key"):
            p4 = subprocess.run(
                [HERMES_BIN, "config", "set", "model.api_key", option["api_key"]],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

        failures = [p for p in (p1, p2, p3, p4) if p is not None and p.returncode != 0]
        if failures:
            err = " ".join((p.stderr or "").strip() for p in failures).strip()
            return False, (err or "failed to set model/provider")

        STATE.update(detect_model_info())
        return True, "updated"
    except Exception as e:
        return False, str(e)


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/servername":
            name = os.environ.get("SERVER_NAME") or socket.gethostname()
            body = json.dumps({"servername": name}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/hermes-info":
            body = json.dumps(dict(STATE)).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/model-options":
            safe_options = [
                {k: v for k, v in o.items() if k != "api_key"}
                for o in MODEL_OPTIONS
            ]
            body = json.dumps({"options": safe_options, "current": {"provider": STATE.get("provider"), "model": STATE.get("model")}}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        super().do_GET()

    def do_POST(self):
        if self.path not in ("/hermes", "/set-model"):
            self.send_error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}

        if self.path == "/set-model":
            option_id = (data.get("option_id") or "").strip()
            api_key = (data.get("api_key") or "").strip()
            ok, msg = set_model_option(option_id, api_key_override=api_key)
            payload = {
                "ok": ok,
                "message": msg,
                "meta": dict(STATE),
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200 if ok else 400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        message = (data.get("message") or "").strip()
        reply, meta = ask_hermes(message)

        body = json.dumps({"reply": reply, "meta": meta}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    print("Serving on http://0.0.0.0:8080")
    server.serve_forever()
