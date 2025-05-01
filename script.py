from flask import Flask, request, jsonify
import yt_dlp
from pytubefix import YouTube
import os
import uuid
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
DOWNLOAD_DIR = "D:\\Harshil\\Python - Apna College\\downloaded videos"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/download', methods=['POST'])
def download():
    # Get request data
    data = request.get_json()
    url = data.get('url')
    format_type = data.get('format', 'video')  # Default to 'video'

    # Validate input
    if not url:
        return jsonify({
            'success': False,
            'message': '❌ URL is required'
        }), 400

    try:
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
                return jsonify({
                    'success': True,
                    'message': f"🎥 Downloaded: {info.get('title', 'your video')}"
                })

        # AUDIO DOWNLOAD
        elif format_type == 'audio':
            yt = YouTube(url)
            audio = yt.streams.filter(only_audio=True).first()
            filename = f"{yt.title.replace('/', '_')}.mp3"  # Sanitize filename
            audio.download(output_path=DOWNLOAD_DIR, filename=filename)
            return jsonify({
                'success': True,
                'message': f"🎧 Downloaded: {yt.title}"
            })

        # PLAYLIST DOWNLOAD
        elif format_type == 'playlist':
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(playlist_title)s/%(title)s.%(ext)s'),
                'quiet': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return jsonify({
                    'success': True,
                    'message': f"📂 Downloaded playlist: {info.get('title', '')} ({info.get('playlist_count', 0)} videos)"
                })

    except Exception as e:
        # Handle common errors
        error_msg = str(e)
        if "Private video" in error_msg:
            return jsonify({'success': False, 'message': '❌ Video is private'}), 400
        elif "Unsupported URL" in error_msg:
            return jsonify({'success': False, 'message': '❌ Invalid YouTube URL'}), 400
        else:
            return jsonify({
                'success': False,
                'message': f'❌ Download failed: {error_msg}'
            }), 500

if __name__ == '__main__':
    app.run(debug=True)