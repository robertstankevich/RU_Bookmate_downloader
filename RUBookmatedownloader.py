import asyncio
import zipfile
import random
import os
import time
import re
import sys
import warnings
import json
import argparse
import shutil
import subprocess
import glob
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import httpx
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image

UA = {
    1: "Samsung/Galaxy_A51 Android/12 Bookmate/3.7.3",
    2: "Huawei/P40_Lite Android/11 Bookmate/3.7.3",
    3: "OnePlus/Nord_N10 Android/10 Bookmate/3.7.3"
    # 4: "Google/Pixel_4a Android/9 Bookmate/3.7.3",
    # 5: "Oppo/Reno_4 Android/8 Bookmate/3.7.3",
    # 6: "Xiaomi/Redmi_Note_9 Android/10 Bookmate/3.7.3",
    # 7: "Motorola/Moto_G_Power Android/10 Bookmate/3.7.3",
    # 8: "Sony/Xperia_10 Android/10 Bookmate/3.7.3",
    # 9: "LG/Velvet Android/10 Bookmate/3.7.3",
    # 10: "Realme/6_Pro Android/10 Bookmate/3.7.3",
}
HEADERS = {
    'app-user-agent': UA[random.randint(1, 3)],
    'mcc': '',
    'mnc': '',
    'imei': '',
    'subscription-country': '',
    'app-locale': '',
    'bookmate-version': '',
    'bookmate-websocket-version': '',
    'device-idfa': '',
    'onyx-preinstall': 'false',
    'auth-token': '',
    'accept-encoding': '',
    'user-agent': ''
}
BASE_URL = "https://api.bookmate.yandex.net/api/v5"
URLS = {
    "book": {
        "infoUrl": f"{BASE_URL}/books/{{uuid}}",
        "contentUrl": f"{BASE_URL}/books/{{uuid}}/content/v4"
    },
    "audiobook": {
        "infoUrl": f"{BASE_URL}/audiobooks/{{uuid}}",
        "contentUrl": f"{BASE_URL}/audiobooks/{{uuid}}/playlists.json"
    },
    "comicbook": {
        "infoUrl": f"{BASE_URL}/comicbooks/{{uuid}}",
        "contentUrl": f"{BASE_URL}/comicbooks/{{uuid}}/metadata.json"
    },
    "serial": {
        "infoUrl": f"{BASE_URL}/books/{{uuid}}",
        "contentUrl": f"{BASE_URL}/books/{{uuid}}/episodes"
    },
    "series": {
        "infoUrl": f"{BASE_URL}/series/{{uuid}}",
        "contentUrl": f"{BASE_URL}/series/{{uuid}}/parts"
    }
}


def get_auth_token():
    if os.path.isfile("token.txt"):
        with open("token.txt", encoding='utf-8') as file:
            return file.read()
    if HEADERS['auth-token']:
        return HEADERS['auth-token']
    auth_token = run_auth_webview()
    with open("token.txt", "w", encoding='utf-8') as file:
        file.write(auth_token)
    return auth_token


def run_auth_webview():
    import webview
    import urllib.parse

    def on_loaded(window):
        if "yx4483e97bab6e486a9822973109a14d05.oauth.yandex.ru" in urllib.parse.urlparse(window.get_current_url()).netloc:
            url = urllib.parse.urlparse(window.get_current_url())
            window.auth_token = urllib.parse.parse_qs(url.fragment)[
                'access_token'][0]
            window.destroy()

    window = webview.create_window(
        'Вход в аккаунт', 'https://oauth.yandex.ru/authorize?response_type=token&client_id=4483e97bab6e486a9822973109a14d05')
    window.events.loaded += on_loaded
    window.auth_token = None
    webview.start()
    return window.auth_token


def replace_forbidden_chars(filename):
    forbidden_chars = '\\/:*?"<>|'
    chars = re.escape(forbidden_chars)
    return re.sub(f'[{chars}]', '', filename)


async def download_file(url, file_path):
    is_download = False
    count = 0
    while not is_download:
        async with httpx.AsyncClient(http2=True, verify=False) as client:
            response = await client.get(url, headers=HEADERS, timeout=None)
            if response.status_code == 200:
                is_download = True
                with open(file_path, 'wb') as file:
                    file.write(response.content)
                print(f"File downloaded successfully to {file_path}")
            elif response.is_redirect:
                response = await client.get(response.next_request.url)
                if response.status_code == 200:
                    is_download = True
                    with open(file_path, 'wb') as file:
                        file.write(response.content)
                    print(f"File downloaded successfully to {file_path}")
            else:
                print(
                    f"Failed to download file. Status code: {response.status_code}")
                count += 1
                if count == 3:
                    print(
                        "Failed to download the file check if the id is correct or try again later")
                    sys.exit()
                time.sleep(5)


async def send_request(url):
    is_download = False
    count = 0
    while not is_download:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=HEADERS, timeout=None)
            if response.status_code == 200:
                is_download = True
                return response
            else:
                print(
                    f"Failed to send request. Status code: {response.status_code}")
                count += 1
                if count == 3:
                    print(
                        "Failed to download the file check if the id is correct or try again later")
                    sys.exit()
                time.sleep(5)


def create_pdf_from_images(images_folder, output_pdf):
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter

    images = filter(lambda file: file.endswith(".jpeg"), os.listdir(images_folder))

    for image in images:
        img_path = os.path.join(images_folder, image)
        with Image.open(img_path):
            c.drawImage(img_path, 0, 0, width, height)
            c.showPage()
        os.remove(img_path)
    c.save()
    print(f"File downloaded successfully to {output_pdf}")


def epub_to_fb2(epub_path, fb2_path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        book = epub.read_epub(epub_path)

    fb2_content = '<?xml version="1.0" encoding="UTF-8"?>\n<fb2 xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">\n<body>'
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_content()
            soup = BeautifulSoup(content, 'html.parser')
            text_content = soup.get_text()
            fb2_content += f'<p>{text_content}</p>'

    fb2_content += '</body>\n</fb2>'

    with open(fb2_path, 'w', encoding='utf-8') as fb2_file:
        fb2_file.write(fb2_content)

    print(f"fb2 file save to {fb2_path}")


def get_resource_info(resource_type, uuid, series=''):
    info_url = URLS[resource_type]['infoUrl'].format(uuid=uuid)
    info = asyncio.run(send_request(info_url)).json()
    if info:
        picture_url = info[resource_type]["cover"]["large"]
        name = info[resource_type]["title"]
        name = replace_forbidden_chars(name)
        download_dir = f"mybooks/{'series' if series else resource_type}/{series}{name}/"
        path = f'{download_dir}{name}'
        os.makedirs(os.path.dirname(download_dir), exist_ok=True)
        asyncio.run(download_file(picture_url, f'{path}.jpeg'))
        with open(f"{path}.json", 'w', encoding='utf-8') as file:
            file.write(json.dumps(info, ensure_ascii=False))
        print(f"File downloaded successfully to {path}.json")
    return path


def get_resource_json(resource_type, uuid):
    url = URLS[resource_type]['contentUrl'].format(uuid=uuid)
    return asyncio.run(send_request(url)).json()


def download_book(uuid, series='', serial_path=None):
    path = serial_path if serial_path else get_resource_info(
        'book', uuid, series)
    asyncio.run(download_file(
        URLS['book']['contentUrl'].format(uuid=uuid), f'{path}.epub'))
    epub_to_fb2(f"{path}.epub", f"{path}.fb2")


def merge_audiobook_chapters_ffmpeg(audiobook_dir, output_file, metadata=None, cleanup_chapters=True):
    """
    Merge all M4A chapter files in a directory into a single audiobook using ffmpeg
    
    Args:
        audiobook_dir: Path to the directory containing chapter files
        output_file: Path for the merged output file
        metadata: Dictionary of metadata to embed
        cleanup_chapters: Whether to remove individual chapter files after successful merge
    """
    from pathlib import Path
    import subprocess
    
    audiobook_path = Path(audiobook_dir)
    
    # Find all M4A files and sort them naturally
    chapter_files = sorted([f for f in audiobook_path.glob("*.m4a") if "Глава_" in f.name], 
                          key=lambda x: int(x.stem.split('_')[1]))
    
    if not chapter_files:
        print(f"No chapter files found in {audiobook_path}")
        return False
    
    print(f"Found {len(chapter_files)} chapters, merging with ffmpeg...")
    
    # Look for cover image
    cover_image = None
    for ext in ['.jpeg', '.jpg', '.png']:
        potential_cover = audiobook_path / f"{audiobook_path.name}{ext}"
        if potential_cover.exists():
            cover_image = potential_cover
            break
    
    # Create a temporary file list for ffmpeg
    filelist_path = audiobook_path / "chapters_list.txt"
    
    # Create chapter metadata file
    chapters_metadata_path = audiobook_path / "chapters_metadata.txt"
    
    try:
        # Get chapter durations first
        print("📊 Analyzing chapter durations...")
        chapter_durations = []
        current_time = 0.0
        
        for chapter_file in chapter_files:
            # Get duration of each chapter using ffprobe
            duration_cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', str(chapter_file)
            ]
            duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
            
            if duration_result.returncode == 0:
                duration = float(duration_result.stdout.strip())
                chapter_durations.append((current_time, current_time + duration, chapter_file))
                current_time += duration
            else:
                print(f"⚠️ Could not get duration for {chapter_file.name}")
                chapter_durations.append((current_time, current_time + 180, chapter_file))  # Fallback: 3 minutes
                current_time += 180
        
        # Write file list for ffmpeg concat
        with open(filelist_path, 'w', encoding='utf-8') as f:
            for chapter_file in chapter_files:
                # Use absolute path and escape single quotes for ffmpeg
                abs_path = str(chapter_file.absolute()).replace("'", "'\"'\"'")
                f.write(f"file '{abs_path}'\n")
        
        # Create chapters metadata file
        with open(chapters_metadata_path, 'w', encoding='utf-8') as f:
            f.write(";FFMETADATA1\n")
            
            # Add global metadata
            if metadata:
                for key, value in metadata.items():
                    if value:
                        # Escape special characters for ffmetadata
                        escaped_value = str(value).replace('=', '\\=').replace(';', '\\;').replace('#', '\\#').replace('\\', '\\\\')
                        f.write(f"{key.upper()}={escaped_value}\n")
            
            # Add chapter markers
            for i, (start_time, end_time, chapter_file) in enumerate(chapter_durations):
                chapter_num = i + 1
                chapter_title = f"Глава {chapter_num}"
                
                f.write("\n[CHAPTER]\n")
                f.write("TIMEBASE=1/1000\n")  # Milliseconds
                f.write(f"START={int(start_time * 1000)}\n")
                f.write(f"END={int(end_time * 1000)}\n")
                f.write(f"title={chapter_title}\n")
        
        # FFmpeg command to concatenate files
        cmd = [
            'ffmpeg', '-y',  # -y to overwrite output file
            '-f', 'concat',
            '-safe', '0',
            '-i', str(filelist_path),
            '-i', str(chapters_metadata_path),  # Chapter metadata
        ]
        
        # Add cover image if available
        if cover_image:
            cmd.extend(['-i', str(cover_image)])
            cmd.extend(['-c:v', 'copy'])  # Copy video/image stream
            cmd.extend(['-c:a', 'copy'])  # Copy audio stream
            cmd.extend(['-disposition:v:0', 'attached_pic'])  # Mark image as cover
            cmd.extend(['-map_metadata', '1'])  # Use metadata from chapters file
        else:
            cmd.extend(['-c', 'copy'])  # Copy without re-encoding
            cmd.extend(['-map_metadata', '1'])  # Use metadata from chapters file
        
        # Add metadata if available (this will override the metadata file if needed)
        if metadata:
            for key, value in metadata.items():
                if value:  # Only add non-empty values
                    cmd.extend(['-metadata', f'{key}={value}'])
        else:
            # Fallback metadata
            cmd.extend(['-metadata', f'title={audiobook_path.name}'])
            cmd.extend(['-metadata', 'genre=Audiobook'])
            cmd.extend(['-metadata', 'media_type=2'])
        
        cmd.append(str(output_file))
        
        # Run ffmpeg
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        if result.returncode == 0:
            print(f"✅ Successfully merged audiobook: {output_file}")
            # Get file size
            size_mb = Path(output_file).stat().st_size / (1024 * 1024)
            print(f"Output file size: {size_mb:.1f} MB")
            if cover_image:
                print(f"📷 Cover image embedded: {cover_image.name}")
            print(f"📑 Chapter markers added: {len(chapter_files)} chapters")
            
            # Clean up individual chapter files after successful merge (if requested)
            if cleanup_chapters:
                print("🧹 Cleaning up chapter files...")
                for chapter_file in chapter_files:
                    try:
                        chapter_file.unlink()
                        print(f"   Removed: {chapter_file.name}")
                    except OSError as e:
                        print(f"   ⚠️ Could not remove {chapter_file.name}: {e}")
                
                print(f"✨ Cleanup complete. Merged audiobook ready: {Path(output_file).name}")
            else:
                print(f"📁 Chapter files preserved. Merged audiobook ready: {Path(output_file).name}")
            
            return True
        else:
            print(f"❌ Error merging audiobook with ffmpeg:")
            print(result.stderr)
            return False
            
    finally:
        # Clean up temporary files
        if filelist_path.exists():
            filelist_path.unlink()
        if chapters_metadata_path.exists():
            chapters_metadata_path.unlink()


def download_audiobook(uuid, series='', max_bitrate=False, merge_chapters=True, cleanup_chapters=True):
    path = get_resource_info('audiobook', uuid, series)
    resp = get_resource_json('audiobook', uuid)
    metadata = None
    
    # Extract metadata from the JSON file if it exists
    json_file = f"{path}.json"
    metadata = None
    if os.path.exists(json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            info = json.load(f)
            if 'audiobook' in info:
                book_info = info['audiobook']
                
                # Extract author name
                author_name = 'Unknown Author'
                if 'authors' in book_info and book_info['authors']:
                    author_name = book_info['authors'][0].get('name', 'Unknown Author')
                
                # Extract narrator name
                narrator_name = ''
                if 'narrators' in book_info and book_info['narrators']:
                    narrator_names = [n.get('name', '') for n in book_info['narrators']]
                    narrator_name = ', '.join(filter(None, narrator_names))
                
                # Extract publisher name
                publisher_name = ''
                if 'publishers' in book_info and book_info['publishers']:
                    publisher_name = book_info['publishers'][0].get('name', '')
                
                metadata = {
                    'title': book_info.get('title', os.path.basename(path)),
                    'artist': author_name,
                    'album': book_info.get('title', os.path.basename(path)),
                    'album_artist': author_name,
                    'composer': author_name,
                    'genre': 'Audiobook',
                    'media_type': '2',
                    'comment': book_info.get('annotation', ''),
                    'publisher': publisher_name,
                    'language': book_info.get('language', 'ru'),
                }
                
                # Add narrator if available
                if narrator_name:
                    metadata['performer'] = narrator_name
                
                # Remove empty values
                metadata = {k: v for k, v in metadata.items() if v}
    
    if resp:
        bitrate = 'max_bit_rate' if max_bitrate else 'min_bit_rate'
        json_data = resp['tracks']
        files = os.listdir(os.path.dirname(path))
        for track in json_data:
            name = f'Глава_{track["number"]+1}.m4a'
            if name not in files:
                download_url = track['offline'][bitrate]['url'].replace(".m3u8", ".m4a")
                asyncio.run(download_file(
                    download_url, f'{os.path.dirname(path)}/{name}'))
    
    # Skip merging if requested
    if not merge_chapters:
        print(f"📁 Audiobook chapters saved separately in: {os.path.dirname(path)}")
        return
    
    # Try ffmpeg first, fallback to pydub if ffmpeg fails
    output_file = f"{path}_complete.m4a"
    audiobook_dir = os.path.dirname(path)
    
    # Check if ffmpeg is available and try to merge
    try:
        success = merge_audiobook_chapters_ffmpeg(audiobook_dir, output_file, metadata, cleanup_chapters=cleanup_chapters)
        if success:
            print(f"Merged audiobook saved to {output_file}")
            return
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"ffmpeg not available or failed: {e}")
        print("Falling back to pydub method...")
    
    # Fallback to original pydub method
    audio_files = sorted(
        glob.glob(os.path.join(os.path.dirname(path), "Глава_*.m4a")),
        key=lambda x: int(re.search(r'Глава_(\d+)\.m4a', x).group(1))
    )
    if audio_files:
        from pydub import AudioSegment
        merged = AudioSegment.empty()
        for file in audio_files:
            merged += AudioSegment.from_file(file)
        merged.export(f"{path}.m4a", format="mp4")
        print(f"Merged audiobook saved to {path}.m4a")


def download_comicbook(uuid, series=''):
    path = get_resource_info('comicbook', uuid, series)
    resp = get_resource_json('comicbook', uuid)
    if resp:
        download_url = resp["uris"]["zip"]
        asyncio.run(download_file(download_url, f'{path}.cbr'))
        with zipfile.ZipFile(f'{path}.cbr', 'r') as zip_ref:
            zip_ref.extractall(os.path.dirname(path))
        shutil.rmtree(os.path.dirname(path)+"/preview",
                      ignore_errors=False, onerror=None)
        create_pdf_from_images(os.path.dirname(path), f"{path}.pdf")


def download_serial(uuid):
    path = get_resource_info('book', uuid)
    resp = get_resource_json('serial', uuid)
    if resp:
        for episode_index, episode in enumerate(resp["episodes"]):
            name = f"{episode_index+1}. {episode['title']}"
            download_dir = f'{os.path.dirname(path)}/{name}'
            os.makedirs(download_dir, exist_ok=True)
            download_book(episode['uuid'],
                          serial_path=f'{download_dir}/{name}')


def download_series(uuid):
    path = get_resource_info('series', uuid)
    resp = get_resource_json('series', uuid)
    name = os.path.basename(path)
    print(name)
    for part_index, part in enumerate(resp['parts']):
        print(part['resource_type'], part['resource']['uuid'])
        func = FUNCTION_MAP[part['resource_type']]
        func(part['resource']['uuid'], f"{name}/{part_index+1}. ")


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("command", choices=FUNCTION_MAP.keys())
    argparser.add_argument("uuid")
    argparser.add_argument("--max_bitrate", action='store_false', help="Use maximum bitrate for audiobooks")
    argparser.add_argument("--no-merge", action='store_true', help="Keep audiobook chapters as separate files (don't merge)")
    argparser.add_argument("--keep-chapters", action='store_true', help="Keep individual chapter files after merging")
    args = argparser.parse_args()

    HEADERS['auth-token'] = get_auth_token()

    func = FUNCTION_MAP[args.command]
    if args.command == 'audiobook':
        func(args.uuid, max_bitrate=args.max_bitrate, merge_chapters=not args.no_merge, cleanup_chapters=not args.keep_chapters)
    else:
        func(args.uuid)


FUNCTION_MAP = {
    'book': download_book,
    'audiobook': download_audiobook,
    'comicbook': download_comicbook,
    'serial': download_serial,
    'series': download_series
}

if __name__ == "__main__":
    main()
