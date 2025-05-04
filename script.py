from flask import Flask, request, jsonify, send_file, send_from_directory
import yt_dlp
from pytubefix import YouTube
import os
import time
import logging
import traceback

from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes and origins

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

cookies_dict = {}

# Handle cookies.txt gracefully
try:
    if os.path.exists("cookies.txt"):
        with open("cookies.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 7:
                    domain, _, path, secure, expiry, name, value = parts
                    cookies_dict[name] = value
    else:
        logger.warning("cookies.txt not found. Proceeding without cookies.")
except Exception as e:
    logger.error(f"Failed to read cookies.txt: {e}")
    logger.error(traceback.format_exc())

# Configuration
# DOWNLOAD_DIR = os.path.join(os.getcwd(), "Downloads")
DOWNLOAD_DIR = os.path.join(os.environ["USERPROFILE"], "Downloads")  # For Windows users
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/download', methods=['POST'])
def download():
    # Get request data
    data = request.get_json(silent=True) or {}
    url = data.get('url')
    format_type = data.get('format', 'video')  # Default to 'video'

    # Validate input
    if not url:
        return jsonify({
            'success': False,
            'message': '❌ URL is required'
        }), 400

    try:
        filename = None

        # VIDEO DOWNLOAD
        if format_type == 'video':
            ydl_opts = {
                'format': 'bestvideo[ext=mp4][height<=2160]+bestaudio[ext=m4a]/best[ext=mp4]',
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
                'cookiefile': os.path.abspath('cookies.txt') if os.path.exists('cookies.txt') else None,
                'geo_bypass': True,
                'nocheckcertificate': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.youtube.com/'
                },
                'logger': logger
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = f"{info.get('title', 'video')}.mp4"

        # AUDIO DOWNLOAD
        elif format_type == 'audio':
            yt = YouTube(url)
            audio = yt.streams.filter(only_audio=True).first()
            filename = f"{yt.title.replace('/', '_')}.mp3"  # Sanitize filename
            audio.download(output_path=DOWNLOAD_DIR, filename=filename)

        # PLAYLIST DOWNLOAD
        elif format_type == 'playlist':
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(playlist_title)s/%(title)s.%(ext)s'),
                'quiet': True,
                'cookiefile': os.path.abspath('cookies.txt') if os.path.exists('cookies.txt') else None,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.youtube.com/'
                }
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = f"{info.get('title', '')}.mp4"

        if filename:
            return jsonify({
                'success': True,
                'message': f"✅ Download complete!",
                'download_url': f"/Downloads/{filename}"
            })

    except Exception as e:
        logger.error(f"Download error: {e}")
        logger.error(traceback.format_exc())
        # Handle common errors
        error_msg = str(e)
        if "Private video" in error_msg:
            return jsonify({'success': False, 'message': '❌ Video is private'}), 400
        elif "Unsupported URL" in error_msg:
            return jsonify({'success': False, 'message': '❌ Invalid YouTube URL'}), 400
        elif "This video is not available" in error_msg or "This content isn’t available" in error_msg:
            return jsonify({'success': False, 'message': '❌ Video is unavailable (removed, region-restricted, or private)'}), 400
        else:
            return jsonify({'success': False, 'message': f'❌ Download failed: {error_msg}'}), 500

# Serve downloaded files for user download
@app.route('/Downloads/<filename>')
def serve_file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

@app.route('/')
def home():
    return send_file('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)