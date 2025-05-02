from flask import Flask, request, jsonify, send_file, send_from_directory
import yt_dlp
from pytubefix import YouTube
import os
import time
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
DOWNLOAD_DIR = "Downloads"
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
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True
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
                'quiet': True
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
        # Handle common errors
        error_msg = str(e)
        if "Private video" in error_msg:
            return jsonify({'success': False, 'message': '❌ Video is private'}), 400
        elif "Unsupported URL" in error_msg:
            return jsonify({'success': False, 'message': '❌ Invalid YouTube URL'}), 400
        else:
            return jsonify({'success': False, 'message': f'❌ Download failed: {error_msg}'}), 500

# Serve downloaded files for user download
@app.route('/Downloads/<filename>')
def serve_file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    app.run()
