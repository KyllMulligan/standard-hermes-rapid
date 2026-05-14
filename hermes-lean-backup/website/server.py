#!/usr/bin/env python3
import json
import ast
import os
import re
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
            ["hermes", "config"],
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
        proc = subprocess.run(
            ["hermes", "chat", "-q", message, "-Q"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
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

        super().do_GET()

    def do_POST(self):
        if self.path != "/hermes":
            self.send_error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"message": ""}

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
