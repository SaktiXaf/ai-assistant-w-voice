#  AI
Assistant

Jarvis adalah MVP personal voice AI assistant desktop untuk Windows. Assistant bisa menerima perintah suara atau teks, memahami intent sederhana, menjalankan aksi komputer, memberi respons suara, dan mencatat log lokal.

## Fitur MVP

- Voice input Bahasa Indonesia via `SpeechRecognition`
- Text-to-speech offline via `pyttsx3`
- Rule-based command parser
- Gemini parser opsional sebagai fallback untuk command natural language
- Buka aplikasi dari `config/apps.json`
- Buka website dari `config/websites.json`
- Buka domain bebas seperti `buka detik.com`
- Cari di website tertentu seperti `cari bohemian rhapsody di spotify`
- Ingat website terakhir, jadi setelah `buka website spotify`, command `cari bohemian rhapsody` akan mencari di Spotify
- Google Search
- Buat catatan `.txt` di `data/notes`
- Ketik teks ke window aktif via `pyautogui`
- Baca waktu
- Safety confirmation untuk aksi sensitif
- Log lokal di `data/logs/assistant.log`
- Wake phrase `hei jarvis` / `hey jarvis` / `hei jervis`

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Kalau `SpeechRecognition` meminta PyAudio dan gagal install di Windows, jalankan:

```powershell
pip install pipwin
pipwin install pyaudio
```

## Konfigurasi

Edit file:

- `config/apps.json` untuk daftar aplikasi
- `config/websites.json` untuk daftar website
- `config/settings.json` untuk bahasa, TTS, safety, dan AI parser
- `.env` untuk `GEMINI_API_KEY` dan `GEMINI_MODEL`

Catatan: jika memakai Gemini parser, teks command akan dikirim ke Gemini API. Matikan dengan mengubah `use_ai_parser` menjadi `false` di `config/settings.json`.

## Menjalankan

Mode suara:

```powershell
python main.py
```

Mode teks:

```powershell
python main.py --text
```

Sekali jalan untuk test:

```powershell
python main.py --once "open youtube" --no-voice
```

## Contoh Command

- `hey jarvis`
- `hey jarvis open spotify`
- `hey jarvis please open youtube`
- `hey jarvis open detik.com`
- `hey jarvis open website detik`
- `hey jarvis search tutorial python`
- `hey jarvis search for bohemian rhapsody on spotify`
- `hey jarvis play bohemian rhapsody`
- `hey jarvis create note study database at 8`
- `hey jarvis type hello world`
- `hey jarvis what time is it`
- `hey jarvis what can you do`
- `who are you`
- `thank you`
- `terima kasih`
- `hey jarvis shut down`

Jika kamu hanya memanggil `hey jarvis`, assistant menjawab `what do you need sir`.
Jika kamu memberi perintah seperti `hey jarvis open spotify`, assistant menjawab `as your command` sebelum menjalankan action.
Perintah utama dibuat English-only, tapi small talk sederhana seperti `terima kasih` tetap dijawab.

## Safety

Assistant akan meminta konfirmasi sebelum:

- Menutup aplikasi
- Mengetik teks panjang
- Membuka website yang tidak dikenal
- Menjalankan aksi yang ditandai sensitif

Format konfirmasi: jawab `ya`, `lanjut`, atau `ya lanjut`.
