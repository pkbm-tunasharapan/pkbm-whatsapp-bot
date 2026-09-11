"""
Bot WhatsApp PPDB - PKBM Tunas Harapan (versi CADANGAN, tanpa AI)
==================================================================

Versi ini TIDAK memakai Claude/AI apa pun -- semua balasan dicocokkan lewat
kata kunci (rule-based), jadi 100% GRATIS untuk dijalankan (tidak ada biaya
per pesan sama sekali). Cocok sebagai cadangan kalau bot versi AI (app.py di
folder pkbm-whatsapp-bot) sedang bermasalah, atau kalau memang tidak mau ada
biaya berlangganan sama sekali.

Cara kerja: setiap pesan masuk dicek kata kuncinya (jadwal, syarat, biaya,
dst) lalu dibalas dengan jawaban yang sudah disiapkan di bagian JAWABAN di
bawah. Kalau tidak ada kata kunci yang cocok, bot menampilkan menu topik
yang bisa ditanyakan.

Edit teks jawaban di bagian bawah kapan saja tanpa perlu paham kode.
"""

import os
import logging

from flask import Flask, request, jsonify
import requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pkbm-bot-no-ai")

app = Flask(__name__)

# ---------------------------------------------------------------------------
# KONFIGURASI DARI ENVIRONMENT VARIABLE (diisi di dashboard hosting)
# ---------------------------------------------------------------------------
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")
WHATSAPP_API_VERSION = os.environ.get("WHATSAPP_API_VERSION", "v21.0")

ADMIN_NUMBER = "0852-2465-6996"

# ---------------------------------------------------------------------------
# JAWABAN -- EDIT BAGIAN INI KAPAN SAJA SESUAI KEBUTUHAN
# ---------------------------------------------------------------------------
JAWABAN_JADWAL = (
    "Pendaftaran PPDB PKBM Tunas Harapan dibuka SEPANJANG TAHUN, terbagi "
    "2 gelombang:\n"
    "- Gelombang 1: Desember - Juli\n"
    "- Gelombang 2: Agustus - November\n\n"
    "Ada lagi yang mau ditanyakan (syarat, biaya, program, lokasi)?"
)

JAWABAN_SYARAT = (
    "Berkas yang perlu disiapkan untuk mendaftar:\n"
    "1. Fotokopi KTP (kalau belum punya KTP, pakai fotokopi KTP orang tua/wali)\n"
    "2. Fotokopi Kartu Keluarga (KK)\n"
    "3. Fotokopi ijazah terakhir\n"
    "4. Rapor terakhir (untuk proses Rekognisi Pembelajaran Lampau)\n"
    "5. Pas foto 4x6 (3 lembar) dan 3x4 (3 lembar)\n"
    "6. Materai Rp10.000 (3 lembar)\n\n"
    "Ada lagi yang mau ditanyakan?"
)

JAWABAN_PROGRAM = (
    "PKBM Tunas Harapan menyediakan Paket A (setara SD), Paket B (setara "
    "SMP), dan Paket C (setara SMA). Mau tanya soal jadwal, syarat, atau "
    "biaya pendaftarannya?"
)

JAWABAN_BIAYA = (
    "Pendidikan di PKBM Tunas Harapan GRATIS untuk peserta didik usia "
    "sekolah/usia belajar sesuai aturan pemerintah, tidak dipungut biaya.\n\n"
    "Ada lagi yang mau ditanyakan?"
)

JAWABAN_LOKASI = (
    "Alamat PKBM Tunas Harapan: Keandra Living Sampiran, Jl. Living Raya "
    "No. 63.\n\nAda lagi yang mau ditanyakan?"
)

JAWABAN_ADMIN = (
    f"Baik, untuk pertanyaan ini sebaiknya langsung dibantu admin kami di "
    f"{ADMIN_NUMBER} ya. Admin akan segera membalas."
)

JAWABAN_TERIMA_KASIH = "Sama-sama! Semoga lancar pendaftarannya. 🙏"

JAWABAN_SAPAAN = (
    "Assalamu'alaikum, selamat datang di layanan info PPDB PKBM Tunas "
    "Harapan! 😊\n\n"
    "Bapak/Ibu bisa tanya seputar:\n"
    "- *Jadwal* pendaftaran\n"
    "- *Syarat/berkas* pendaftaran\n"
    "- *Program* (Paket A/B/C)\n"
    "- *Biaya*\n"
    "- *Lokasi/alamat*\n\n"
    "Silakan ketik pertanyaannya langsung, ya."
)

JAWABAN_TIDAK_MENGERTI = (
    "Maaf, admin belum bisa memahami pertanyaan itu secara otomatis. "
    "Bapak/Ibu bisa tanya soal *jadwal*, *syarat*, *program*, *biaya*, "
    "atau *lokasi* pendaftaran. Kalau butuh dibantu langsung, silakan "
    f"hubungi admin di {ADMIN_NUMBER}."
)

# Urutan penting: kata kunci yang lebih spesifik ditaruh lebih dulu.
# Format: (daftar kata kunci, jawaban)
ATURAN = [
    (["jadwal", "kapan", "buka pendaftaran", "tanggal daftar", "gelombang"], JAWABAN_JADWAL),
    (["syarat", "berkas", "dokumen", "persyaratan", "bawa apa", "kelengkapan"], JAWABAN_SYARAT),
    (["paket a", "paket b", "paket c", "program", "setara sd", "setara smp", "setara sma", "kejar paket"], JAWABAN_PROGRAM),
    (["biaya", "bayar", "gratis", "spp", "harga", "uang pendaftaran"], JAWABAN_BIAYA),
    (["alamat", "lokasi", "dimana", "di mana", "tempat"], JAWABAN_LOKASI),
    (["admin", "cs", "manusia", "operator", "komplain", "keluhan", "bicara dengan orang"], JAWABAN_ADMIN),
    (["terima kasih", "makasih", "thanks", "trims"], JAWABAN_TERIMA_KASIH),
    (["halo", "hai", "assalamualaikum", "assalamu'alaikum", "permisi", "selamat pagi", "selamat siang", "selamat sore", "selamat malam"], JAWABAN_SAPAAN),
]


def cari_jawaban(teks_masuk: str) -> str:
    teks = teks_masuk.lower()
    for kata_kunci_list, jawaban in ATURAN:
        for kata_kunci in kata_kunci_list:
            if kata_kunci in teks:
                return jawaban
    return JAWABAN_TIDAK_MENGERTI


def send_whatsapp_message(to, text):
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        },
        timeout=30,
    )
    if resp.status_code >= 300:
        log.error("Gagal kirim pesan WhatsApp: %s %s", resp.status_code, resp.text)
    return resp


@app.get("/")
def health():
    return "PKBM Tunas Harapan WhatsApp bot (versi tanpa AI) is running.", 200


@app.get("/webhook")
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        log.info("Webhook berhasil diverifikasi.")
        return challenge, 200

    log.warning("Verifikasi webhook gagal (token tidak cocok).")
    return "Verification failed", 403


@app.post("/webhook")
def receive_message():
    payload = request.get_json(silent=True) or {}
    log.info("Payload masuk: %s", payload)

    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]["value"]
        messages = change.get("messages")

        if not messages:
            return jsonify(status="ignored"), 200

        message = messages[0]
        sender = message["from"]
        msg_type = message.get("type")

        if msg_type == "text":
            user_text = message["text"]["body"]
        elif msg_type == "interactive":
            interactive = message.get("interactive", {})
            user_text = (
                interactive.get("button_reply", {}).get("title")
                or interactive.get("list_reply", {}).get("title")
                or ""
            )
        else:
            user_text = ""

        reply_text = cari_jawaban(user_text) if user_text else JAWABAN_TIDAK_MENGERTI
        send_whatsapp_message(sender, reply_text)

    except Exception:
        log.exception("Gagal memproses psan masuk")

    return jsonify(status="ok"), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
