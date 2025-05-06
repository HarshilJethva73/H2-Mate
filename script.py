from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import traceback
import logging
from pathlib import Path
import platform
import tempfile
import shutil
import zipfile

app = Flask(__name__)
CORS(app)

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Download location (cross-platform)
DOWNLOAD_DIR = Path.home() / "Downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/')
def home():
    return "🎬 YouTube Downloader Backend is running."

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json(force=True)
    url = data.get('url')
    format_type = data.get('format', 'video')

    if not url:
        return jsonify({'success': False, 'message': '❌ URL is required'}), 400

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'geo_bypass': True,
                'nocheckcertificate': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0',
                    'Referer': 'https://www.youtube.com/'
                },
                'logger': logger
            }

            if os.path.exists("cookies.txt"):
                ydl_opts['cookiefile'] = os.path.abspath("cookies.txt")

            if format_type == 'video':
                ydl_opts['format'] = 'bestvideo[ext=mp4][height<=2160]+bestaudio[ext=m4a]/best[ext=mp4]'
            elif format_type == 'audio':
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'
                }]
            elif format_type == 'playlist':
                ydl_opts['format'] = 'bestvideo+bestaudio/best'
            else:
                return jsonify({'success': False, 'message': '❌ Invalid format'}), 400

            ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title)s.%(ext)s')
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            files = os.listdir(tmpdir)
            if not files:
                raise Exception("Download failed: No files found.")

            if format_type == 'playlist':
                zip_filename = f"{info.get('title') or info.get('playlist_title') or 'playlist'}.zip"
                zip_path = os.path.join(tmpdir, zip_filename)
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for f in files:
                        zipf.write(os.path.join(tmpdir, f), arcname=f)
                shutil.move(zip_path, os.path.join(DOWNLOAD_DIR, zip_filename))
                return jsonify({'success': True, 'message': '✅ Playlist zipped and saved.', 'download_url': f'/Downloads/{zip_filename}'})

            for f in files:
                if format_type == 'audio' and f.endswith('.mp3'):
                    final_file = f
                    break
            else:
                final_file = files[0]

            shutil.move(os.path.join(tmpdir, final_file), os.path.join(DOWNLOAD_DIR, final_file))
            return jsonify({'success': True, 'message': '✅ Download complete!', 'download_url': f'/Downloads/{final_file}'})

    except Exception as e:
        logger.error("Error occurred during download", exc_info=True)
        msg = str(e)
        if "Private video" in msg:
            return jsonify({'success': False, 'message': '❌ This video is private.'}), 400
        elif "Unsupported URL" in msg:
            return jsonify({'success': False, 'message': '❌ Invalid or unsupported URL.'}), 400
        return jsonify({'success': False, 'message': f'❌ Unexpected error: {msg}'}), 500

@app.route('/Downloads/<filename>')
def serve_download(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
