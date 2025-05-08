import os
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
import yt_dlp
import zipfile
import shutil

app = Flask(__name__)

# Determine Downloads directory based on OS
if os.name == 'nt':
    download_dir = Path(os.environ.get('USERPROFILE', Path.home())) / 'Downloads'
else:
    download_dir = Path.home() / 'Downloads'
download_dir.mkdir(parents=True, exist_ok=True)

# Path to cookies.txt in same directory as this script
script_dir = Path(__file__).resolve().parent
cookies_file = script_dir / 'cookies.txt'

@app.route('/')
def index():
    return send_from_directory(script_dir, 'index.html')

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json() or request.form
    url = data.get('url')
    fmt = data.get('format')
    if not url or not fmt:
        return jsonify(success=False, message="❌ Invalid YouTube URL")
    fmt = fmt.lower()
    ydl_opts = {
        'cookiefile': str(cookies_file),
        'quiet': True
    }
    file_paths = []
    def hook(d):
        if d.get('status') == 'finished':
            file_paths.append(d.get('filename'))
    if fmt == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'outtmpl': str(download_dir / '%(title)s.%(ext)s'),
            'noplaylist': True
        })
    elif fmt == 'video':
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4][height<=2160]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': str(download_dir / '%(title)s.%(ext)s'),
            'noplaylist': True
        })
    elif fmt == 'playlist':
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4][height<=2160]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': str(download_dir / '%(playlist_title)s' / '%(playlist_index)s - %(title)s.%(ext)s')
        })
    else:
        return jsonify(success=False, message="❌ Invalid format")
    ydl_opts['progress_hooks'] = [hook]
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        err_msg = str(e).lower()
        if 'private' in err_msg:
            return jsonify(success=False, message="❌ Video is private")
        elif any(x in err_msg for x in ['unavailable', 'region-restricted', 'removed']):
            return jsonify(success=False, message="❌ Video is unavailable (removed, region-restricted, or private)")
        elif any(x in err_msg for x in ['unsupported url', 'invalid url', 'url does not exist']):
            return jsonify(success=False, message="❌ Invalid YouTube URL")
        else:
            return jsonify(success=False, message="❌ An unknown error occurred.")
    except Exception:
        return jsonify(success=False, message="❌ An unexpected error occurred. Please try again later.")
    if fmt == 'playlist':
        if not file_paths:
            return jsonify(success=False, message="❌ An unknown error occurred.")
        first_path = Path(file_paths[0])
        playlist_folder = first_path.parent
        playlist_name = playlist_folder.name
        zip_path = download_dir / f"{playlist_name}.zip"
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in playlist_folder.iterdir():
                    if file.is_file():
                        zipf.write(file, arcname=file.name)
            shutil.rmtree(playlist_folder)
        except Exception:
            return jsonify(success=False, message="❌ An unexpected error occurred. Please try again later.")
        filename = f"{playlist_name}.zip"
    else:
        if not file_paths:
            return jsonify(success=False, message="❌ An unknown error occurred.")
        filename = Path(file_paths[-1]).name
    download_url = request.host_url.rstrip('/') + '/Downloads/' + filename
    return jsonify(success=True, message="Download ready.", download_url=download_url)

@app.route('/Downloads/<path:filename>')
def serve_download(filename):
    return send_from_directory(str(download_dir), filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
