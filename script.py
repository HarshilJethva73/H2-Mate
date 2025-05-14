# script.py
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
CORS(app)  # Enable CORS for all routes

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ...existing code...
# Determine download directory based on OS/environment
if "RAILWAY_STATIC_URL" in os.environ or os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"):
    DOWNLOAD_DIR = Path("/tmp")
elif platform.system() == "Windows":
    DOWNLOAD_DIR = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
else:
    DOWNLOAD_DIR = Path.home() / "Downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
# ...existing code...

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json(force=True) or {}
    url = data.get('url')
    format_type = data.get('format', 'video')

    # Validate URL input
    if not url:
        return jsonify({'success': False, 'message': '❌ URL is required'}), 400

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Common yt_dlp options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'geo_bypass': True,
                'nocheckcertificate': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.youtube.com/'
                },
                'logger': logger
            }
            # Use cookies if available
            # Check if the cookies file exists and is being used
            cookies_path = os.path.abspath('cookies.txt')
            if os.path.exists(cookies_path):
                logger.info(f"Using cookies from: {cookies_path}")
                ydl_opts['cookiefile'] = cookies_path
            else:
                logger.warning("No cookies file found, will proceed without cookies.")


            # Handle different formats
            if format_type == 'video':
                # Download video (highest quality mp4 up to 2160p)
                ydl_opts['format'] = 'bestvideo[ext=mp4][height<=2160]+bestaudio[ext=m4a]/best[ext=mp4]'
                ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title)s.%(ext)s')
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                # Move downloaded file to DOWNLOAD_DIR
                files = os.listdir(tmpdir)
                if not files:
                    raise Exception("Download failed: no file found")
                # Assuming first file is the video
                filename = files[0]
                filepath = os.path.join(tmpdir, filename)
                dest_path = os.path.join(DOWNLOAD_DIR, filename)
                shutil.move(filepath, dest_path)
                download_url = f"/Downloads/{filename}"
                return jsonify({'success': True, 'message': '✅ Download complete!', 'download_url': download_url})

            elif format_type == 'audio':
                # Download best available audio (prefer lossless if available)
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title)s.%(ext)s')
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',  # or 'wav'/'flac' for lossless
                    'preferredquality': '320'   # '0' = best quality in ffmpeg
                }]
            
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                files = os.listdir(tmpdir)
                if not files:
                    raise Exception("Download failed: no file found")
                filename = None
                # Find .mp3 file if postprocessor changed extension
                for f in files:
                    if f.lower().endswith('.mp3'):
                        filename = f
                        break
                # Fallback to any file
                if not filename:
                    filename = files[0]
                filepath = os.path.join(tmpdir, filename)
                dest_path = os.path.join(DOWNLOAD_DIR, filename)
                shutil.move(filepath, dest_path)
                download_url = f"/Downloads/{filename}"
                return jsonify({'success': True, 'message': '✅ Download complete!', 'download_url': download_url})

            elif format_type == 'playlist':
                # Download entire playlist (videos with best quality)
                ydl_opts['format'] = 'bestvideo[ext=mp4][height<=2160]+bestaudio[ext=m4a]/best[ext=mp4]'
                ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title)s.%(ext)s')
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                files = os.listdir(tmpdir)
                if not files:
                    raise Exception("Download failed: no files found")
                # Create a zip of all files
                playlist_title = info.get('title') or info.get('playlist_title') or 'playlist'
                zip_filename = f"{playlist_title}.zip"
                zip_path = os.path.join(tmpdir, zip_filename)
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for f in files:
                        file_path = os.path.join(tmpdir, f)
                        zipf.write(file_path, arcname=f)
                dest_path = os.path.join(DOWNLOAD_DIR, zip_filename)
                shutil.move(zip_path, dest_path)
                download_url = f"/Downloads/{zip_filename}"
                return jsonify({'success': True, 'message': '✅ Download complete!', 'download_url': download_url})

            else:
                return jsonify({'success': False, 'message': '❌ Invalid format selected'}), 400

    except Exception as e:
        logger.error(f"Download error: {e}")
        logger.error(traceback.format_exc())
        error_msg = str(e)
        if "Private video" in error_msg:
            return jsonify({'success': False, 'message': '❌ Video is private'}), 400
        elif "Unsupported URL" in error_msg:
            return jsonify({'success': False, 'message': '❌ Invalid YouTube URL'}), 400
        elif "This video is not available" in error_msg or "This content isn't available" in error_msg:
            return jsonify({'success': False, 'message': '❌ Video is unavailable (removed, region-restricted, or private)'}), 400
        elif error_msg:
            # Generic catch-all for unexpected errors (HTTP 500)
            return jsonify({'success': False, 'message': '❌ An unexpected error occurred. Please try again later.'}), 500

@app.route('/Downloads/<path:filename>')
def serve_file(filename):
    # Serve files from the DOWNLOAD_DIR
    return send_from_directory(str(DOWNLOAD_DIR), filename, as_attachment=True)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    # app.run(host='0.0.0.0', port=port)
    # app.run(debug=True)  # Uncomment for debugging