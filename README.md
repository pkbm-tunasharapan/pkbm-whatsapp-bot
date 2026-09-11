# Bot WhatsApp PPDB - PKBM Tunas Harapan

Server webhook WhatsApp Cloud API yang menjawab pertanyaan PPDB secara
percakapan, memakai Claude (Anthropic) sebagai otak bot.

## Isi folder ini

- `app.py` - kode server (Flask). Info PPDB ada di bagian atas file, di
  dalam variabel `PPDB_INFO` - bisa diedit kapan saja tanpa perlu paham kode.
- `requirements.txt` - daftar library yang dibutuhkan.
- `Procfile` - perintah untuk menjalankan server di hosting (Render, dll).

## Langkah deploy (pakai Render.com, gratis, tanpa kartu kredit)

### 1. Unggah kode ini ke GitHub

1. Buka https://github.com dan buat akun kalau belum punya (gratis).
2. Klik tombol hijau **New** untuk membuat repository baru, beri nama
   misalnya `pkbm-whatsapp-bot`, biarkan "Public" atau "Private" (bebas),
   lalu klik **Create repository**.
3. Di halaman repository kosong itu, klik **uploading an existing file**,
   lalu drag & drop semua file di folder ini (`app.py`, `requirements.txt`,
   `Procfile`, `README.md`). Klik **Commit changes**.

### 2. Buat akun Render & deploy

1. Buka https://render.com, daftar (bisa langsung pakai akun GitHub yang
   tadi dibuat, lebih cepat).
2. Klik **New +** -> **Web Service**.
3. Pilih **Build and deploy from a Git repository**, hubungkan akun GitHub,
   lalu pilih repository `pkbm-whatsapp-bot` tadi.
4. Isi konfigurasi:
   - **Name**: bebas, misalnya `pkbm-tunas-harapan-bot`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: **Free**
5. Di bagian **Environment Variables**, tambahkan satu per satu:

   | Key | Value |
   |---|---|
   | `VERIFY_TOKEN` | bebas, buat sendiri string acak, misalnya `pkbmtunasharapan2026` |
   | `WHATSAPP_TOKEN` | access token dari App Dashboard Facebook (Step 2 Production setup / System User token) |
   | `PHONE_NUMBER_ID` | Phone Number ID dari App Dashboard Facebook |
   | `ANTHROPIC_API_KEY` | API key dari https://console.anthropic.com (menu API Keys) |

6. Klik **Create Web Service**. Tunggu beberapa menit sampai status jadi
   **Live**. Render akan memberi URL publik, misalnya:

   `https://pkbm-tunas-harapan-bot.onrender.com`

### 3. Sambungkan ke Facebook Developer

Kembali ke App Dashboard Facebook > Step 2. Production setup > Configure
Webhooks, lalu isi:

- **Callback URL**: `https://pkbm-tunas-harapan-bot.onrender.com/webhook`
  (URL dari Render tadi + `/webhook`)
- **Verify token**: harus SAMA PERSIS dengan nilai `VERIFY_TOKEN` yang
  diisi di Render tadi.

Klik **Verify and Save**. Kalau berhasil, server sudah tersambung.

## Catatan penting

- **Server gratis Render "tidur"** kalau tidak ada yang mengakses selama
  15 menit, dan perlu ~30-50 detik untuk "bangun" lagi saat ada pesan
  pertama masuk setelah tidur. Untuk volume tanya PPDB harian PKBM ini
  biasanya tidak masalah, tapi wajar kalau balasan pertama terasa agak
  lambat.
- **Riwayat percakapan** disimpan sementara di memori server, jadi akan
  hilang kalau server tidur/restart. Ini tidak masalah untuk obrolan
  singkat, tapi bukan riwayat permanen.
- **Isi PPDB_INFO di app.py** adalah satu-satunya sumber informasi yang
  dipakai bot untuk menjawab. Kalau ada info yang berubah (jadwal, syarat,
  biaya, dll), edit langsung di GitHub (klik file `app.py`, klik ikon
  pensil, ubah teksnya, commit) - Render akan otomatis deploy ulang.
- Jaga `WHATSAPP_TOKEN` dan `ANTHROPIC_API_KEY` tetap rahasia - jangan
  dibagikan ke siapa pun di luar tim pengelola.
