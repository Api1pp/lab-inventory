import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

DATA_DIR = os.environ.get("DATA_DIR", "/var/lib/backend_data")
DATA_FILE = os.path.join(DATA_DIR, "inventory.json")
PORT = int(os.environ.get("PORT", "5000"))
VALID_STATUS = ("Tersedia", "Dipinjam", "Rusak")

lock = threading.Lock()


def load_data():
    """Baca daftar alat dari file JSON. Kalau belum ada, kembalikan list kosong."""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_data(items):
    """Simpan daftar alat ke file JSON (di dalam Named Volume)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_file = DATA_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, DATA_FILE)


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # GET /inventory -> daftar alat | GET /health -> cek server hidup
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self.send_json(200, {"status": "ok"})
        if path == "/inventory":
            with lock:
                return self.send_json(200, load_data())
        self.send_json(404, {"error": "Endpoint tidak ditemukan"})

    # POST /inventory -> tambah alat baru
    def do_POST(self):
        if urlparse(self.path).path != "/inventory":
            return self.send_json(404, {"error": "Endpoint tidak ditemukan"})

        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            return self.send_json(400, {"error": "Body harus berupa JSON yang valid"})

        if not isinstance(body, dict):
            return self.send_json(400, {"error": "Body harus berupa objek JSON"})

        name = str(body.get("name", "")).strip()
        if not name:
            return self.send_json(400, {"error": "Field 'name' wajib diisi"})

        try:
            quantity = int(body.get("quantity", 1))
        except (TypeError, ValueError):
            return self.send_json(400, {"error": "Field 'quantity' harus berupa angka"})
        if quantity < 0:
            return self.send_json(400, {"error": "Field 'quantity' tidak boleh negatif"})

        status = body.get("status", "Tersedia")
        if status not in VALID_STATUS:
            return self.send_json(
                400, {"error": "Field 'status' harus salah satu dari: " + ", ".join(VALID_STATUS)}
            )

        item = {
            "name": name,
            "category": str(body.get("category", "Lainnya")).strip() or "Lainnya",
            "quantity": quantity,
            "status": status,
            "borrower": str(body.get("borrower", "")).strip(),
        }

        with lock:
            items = load_data()
            items.append(item)
            save_data(items)
        self.send_json(201, item)

    # DELETE /inventory?index=X -> hapus alat urutan ke-X
    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path != "/inventory":
            return self.send_json(404, {"error": "Endpoint tidak ditemukan"})

        raw_index = parse_qs(parsed.query).get("index", [None])[0]
        if raw_index is None:
            return self.send_json(400, {"error": "Parameter 'index' wajib diisi"})
        try:
            index = int(raw_index)
        except ValueError:
            return self.send_json(400, {"error": "Parameter 'index' harus berupa angka"})

        with lock:
            items = load_data()
            if index < 0 or index >= len(items):
                return self.send_json(404, {"error": "Data dengan index tersebut tidak ada"})
            removed = items.pop(index)
            save_data(items)
        self.send_json(200, {"message": "Alat berhasil dihapus", "deleted": removed})


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Backend berjalan di port {PORT}, data di {DATA_FILE}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()