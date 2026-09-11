"""
Bot WhatsApp PPDB - PKBM Tunas Harapan
=======================================

Server webhook untuk WhatsApp Cloud API (Meta) yang menjawab pertanyaan calon
peserta didik/orang tua seputar PPDB secara percakapan natural, memakai Claude
(Anthropic API) sebagai "otak" bot.

Cara kerja singkat:
1. Meta mengirim GET ke /webhook saat verifikasi awal -> kita cocokkan VERIFY_TOKEN.
2. Meta mengirim POST ke /webhook setiap ada pesan WhatsApp masuk.
3. Kita ambil teks pesan, kirim ke Claude bersama info PPDB (lihat PPDB_INFO di
   bawah) supaya jawabannya akurat, lalu kirim balasan Claude itu balik ke
   pengirim lewat WhatsApp Cloud API.

Semua nilai rahasia (token WhatsApp, verify token, API key Claude) DIAMBIL DARI
ENVIRONMENT VARIABLE, bukan ditulis langsung di kode ini -- supaya aman dan
gampang diganti dari dashboard hosting tanpa deploy ulang.
"""

import os
import time
import logging

from flask import Flask, request, jsonify
import requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pkbm-bot")

app = Flask(__name__)

# ---------------------------------------------------------------------------
# 1) INFORMASI PPDB -- EDIT BAGIAN INI KAPAN SAJA SESUAI KEBUTUHAN
#    (tidak perlu paham kode, cukup ubah teks di dalam tanda kutip)
# ---------------------------------------------------------------------------
PPDB_INFO = """
Kamu adalah admin WhatsApp resmi PKBM Tunas Harapan Cirebon yang membantu
calon peserta didik dan orang tua/wali seputar Penerimaan Peserta Didik Baru
(PPDB). Jawab dengan ramah, singkat, jelas, dan dalam Bahasa Indonesia yang
sopan (gunakan sapaan "Bapak/Ibu" atau "Kakak" sesuai konteks). Jangan
mengaku sebagai AI/model bahasa -- posisikan diri sebagai admin PKBM.

INFORMASI RESMI PPDB PKBM TUNAS HARAPAN:

1. Jadwal pendaftaran: Pendaftaran dibuka SEPANJANG TAHUN, terbagi 2 gelombang:
   - Gelombang 1: Desember - Juli
   - Gelombang 2: Agustus - November

2. Program/paket yang tersedia: Paket A (setara SD), Paket B (setara SMP),
   dan Paket C (setara SMA).

3. Syarat pendaftaran (dokumen yang perlu dibawa/difotokopi):
   - Fotokopi KTP (jika calon peserta didik sudah punya KTP); jika belum
     punya KTP, gunakan fotokopi KTP orang tua/wali
   - Fotokopi Kartu Keluarga (KK)
   - Fotokopi Ijazah terakhir
   - Rapor terakhir (dipakai untuk proses Rekognisi Pembelajaran Lampau/RPL,
     supaya bisa lanjut dari jenjang yang sesuai)
   - Pas foto ukuran 4x6 sebanyak 3 lembar, dan 3x4 sebanyak 3 lembar
   - Materai Rp10.000 sebanyak 3 lembar

4. Biaya: GRATIS biaya pendidikan untuk peserta didik usia sekolah/usia
   belajar sesuai aturan pemerintah (tidak dipungut biaya).

5. Alamat PKBM: Keandra Living Sampiran, Jl. Living Raya No. 63.

6. Jika ada pertanyaan yang benar-benar di luar informasi di atas, atau perlu
   ditindaklanjuti manusia (misalnya kasus khusus, komplain, atau butuh
   konfirmasi berkas langsung), tetap jawab dengan sopan sebisamu dari
   informasi yang kamu punya, lalu sarankan untuk lanjut ke admin di nomor
   0852-2465-6996 kalau memang perlu penanganan langsung -- tapi jangan
   langsung melempar ke nomor itu untuk pertanyaan umum yang sebetulnya bisa
   kamu jawab sendiri dari info di atas.

Jaga jawaban tetap ringkas (idealnya 2-5 kalimat, atau poin singkat kalau
menjelaskan syarat/dokumen), jangan bertele-tele, dan akhiri dengan
menawarkan bantuan lanjutan bila relevan.
"""

# ---------------------------------------------------------------------------
# 2) KONFIGURASI DARI ENVIRONMENT VARIABLE (diisi di dashboard hosting)
# ---------------------------------------------------------------------------
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
WHATSAPP_API_VERSION = os.environ.get("WHATSAPP_API_VERSION", "v21.0")

# Riwayat percakapan sementara per nomor pengirim (disimpan di memori server).
# Catatan: ini akan kosong lagi kalau server tidur/restart (wajar di hosting
# gratis) -- untuk volume tanya-jawab PPDB harian ini biasanya tidak masalah.
CONVERSATIONS = {}
MAX_HISTORY_MESSAGES = 10
CONVERSATION_TTL_SECONDS = 60 * 60 * 6  # riwayat dianggap basi setelah 6 jam


def _get_history(sender):
    entry = CONVERSATIONS.get(sender)
    if entry and (time.time() - entry["updated_at"]) < CONVERSATION_TTL_SECONDS:
        return entry["messages"]
    return []


def _save_history(sender, messages):
    CONVERSATIONS[sender] = {
        "messages": messages[-MAX_HISTORY_MESSAGES:],
        "updated_at": time.time(),
    }


def ask_claude(sender, user_text):
    """Kirim pertanyaan ke Claude beserta konteks PPDB & riwayat obrolan."""
    history = _get_history(sender)
    messages = history + [{"role": "user", "content": user_text}]

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": 500,
            "system": PPDB_INFO,
            "messages": messages,
        },
        timeout=30,
    )

    if resp.status_code != 200:
        log.error("Anthropic API error %s: %s", resp.status_code, resp.text)
        return (
            "Maaf, admin sedang mengalami kendala teknis sebentar. "
            "Silakan coba lagi beberapa saat lagi, atau hubungi 0852-2465-6996."
        )

    data = resp.json()
    reply_text = "".join(
        block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
    ).strip()

    messages.append({"role": "assistant", "content": reply_text})
    _save_history(sender, messages)

    return reply_text or "Maaf, bisa diulangi pertanyaannya?"


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
    return "PKBM Tunas Harapan WhatsApp bot is running.", 200


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
            # Ini biasanya notifikasi status (terkirim/dibaca), bukan pesan baru.
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
                or "(pesan interaktif)"
            )
        else:
            user_text = f"(mengirim {msg_type}, mohon dibalas dengan teks ya)"

        reply_text = ask_claude(sender, user_text)
        send_whatsapp_message(sender, reply_text)

    except Exception:
        log.exception("Gagal memproses pesan masuk")

    # Selalu balas 200 ke Meta supaya tidak dianggap gagal & dikirim ulang terus.
    return jsonify(status="ok"), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
