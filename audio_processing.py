# =============================================================================
# 3. METADATA, ARTWORK (PILLOW) & AUDIO PROCESSING (MUTAGEN + PYDUB)
# =============================================================================

class MediaHelper:
    """Handles tag extraction, tag writing, cover art rendering, and online lookups."""

    @staticmethod
    def extract_metadata(filepath):
        path_obj = Path(filepath)
        meta = {
            "title": path_obj.stem,
            "artist": "Unknown Artist",
            "album": "Unknown Album",
            "genre": "Pop",
            "duration": 0.0,
            "lyrics": "",
            "cover_bytes": None
        }
        if not HAS_MUTAGEN or not path_obj.exists():
            return meta

        try:
            audio = mutagen.File(filepath)
            if audio is None:
                return meta
            if hasattr(audio, "info") and hasattr(audio.info, "length"):
                meta["duration"] = float(audio.info.length)

            # Easy tag fallback
            easy = mutagen.File(filepath, easy=True)
            if easy and easy.tags:
                meta["title"] = easy.tags.get("title", [meta["title"]])[0]
                meta["artist"] = easy.tags.get("artist", [meta["artist"]])[0]
                meta["album"] = easy.tags.get("album", [meta["album"]])[0]
                meta["genre"] = easy.tags.get("genre", [meta["genre"]])[0]

            # Extract embedded cover art & unsynced lyrics
            if hasattr(audio, "tags") and audio.tags:
                for key, val in audio.tags.items():
                    if key.startswith("APIC"):
                        meta["cover_bytes"] = val.data
                    elif key.startswith("USLT"):
                        meta["lyrics"] = str(val.text)
                    elif key == "covr" and val:
                        meta["cover_bytes"] = bytes(val[0])
            if isinstance(audio, FLAC) and audio.pictures:
                meta["cover_bytes"] = audio.pictures[0].data
        except Exception:
            pass
        return meta

    @staticmethod
    def write_file_tags(filepath, title, artist, album, genre):
        if not HAS_MUTAGEN or not os.path.exists(filepath):
            return False
        try:
            easy = mutagen.File(filepath, easy=True)
            if easy is not None:
                easy["title"] = title
                easy["artist"] = artist
                easy["album"] = album
                easy["genre"] = genre
                easy.save()
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def build_album_pixmap(title, artist, cover_bytes=None, size=220):
        """Uses Pillow to render rounded album art or generate a custom vinyl cover."""
        try:
            if cover_bytes:
                img = Image.open(io.BytesIO(cover_bytes)).convert("RGBA")
                img = img.resize((size, size), Image.Resampling.LANCZOS)
            else:
                img = Image.new("RGBA", (size, size), (24, 24, 24, 255))
                draw = ImageDraw.Draw(img)
                # Dynamic color palette seeded by title
                seed = sum(ord(c) for c in (title or "Prince"))
                r = 30 + (seed * 37) % 140
                g = 60 + (seed * 73) % 160
                b = 90 + (seed * 53) % 150
                for y in range(size):
                    ratio = y / float(size)
                    col = (
                        int(r * (1 - ratio * 0.5)),
                        int(g * (1 - ratio * 0.3)),
                        int(b * (1 - ratio * 0.4)),
                        255
                    )
                    draw.line([(0, y), (size, y)], fill=col)

                # Draw stylized vinyl rings
                cx, cy = size // 2, size // 2
                for radius in range(35, size // 2 - 12, 14):
                    draw.ellipse(
                        [cx - radius, cy - radius, cx + radius, cy + radius],
                        outline=(255, 255, 255, 45), width=2
                    )
                draw.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=(29, 185, 84, 230))
                draw.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=(18, 18, 18, 255))

                # Overlay Title & Artist text
                short_title = (title or "Prince Studio")[:20]
                short_artist = (artist or "Unknown Artist")[:24]
                draw.text((16, size - 46), short_title, fill=(255, 255, 255, 245))
                draw.text((16, size - 26), short_artist, fill=(220, 220, 220, 200))

            # Apply rounded mask
            mask = Image.new("L", (size, size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([0, 0, size, size], radius=16, fill=255)
            output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            output.paste(img, (0, 0), mask=mask)

            raw_data = output.tobytes("raw", "RGBA")
            qimg = QImage(raw_data, size, size, QImage.Format.Format_RGBA8888)
            return QPixmap.fromImage(qimg)
        except Exception:
            pix = QPixmap(size, size)
            pix.fill(QColor("#1DB954"))
            return pix

    @staticmethod
    def fetch_online_artwork(artist, album):
        """Fetches legal album artwork from the public iTunes Search API."""
        if not artist or artist == "Unknown Artist":
            return None
        try:
            term = urllib.parse.quote(f"{artist} {album}")
            url = f"https://itunes.apple.com/search?term={term}&entity=song&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "PrinceMusicStudio/1.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("resultCount", 0) > 0:
                    art_url = data["results"][0].get("artworkUrl100", "")
                    if art_url:
                        hi_res = art_url.replace("100x100bb", "400x400bb")
                        with urllib.request.urlopen(hi_res, timeout=3.5) as img_resp:
                            return img_resp.read()
        except Exception:
            pass
        return None

    @staticmethod
    def fetch_online_lyrics(artist, title):
        """Queries public lyrics.ovh API where legally available."""
        if not artist or not title or artist == "Unknown Artist":
            return ""
        try:
            a = urllib.parse.quote(artist)
            t = urllib.parse.quote(title)
            url = f"https://api.lyrics.ovh/v1/{a}/{t}"
            req = urllib.request.Request(url, headers={"User-Agent": "PrinceMusicStudio/1.0"})
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("lyrics", "").strip()
        except Exception:
            return ""

    @staticmethod
    def inspect_audio_with_pydub(filepath):
        """Uses pydub to analyze audio properties (dBFS, sample rate, channels)."""
        if not HAS_PYDUB or not os.path.exists(filepath):
            return None
        try:
            seg = AudioSegment.from_file(filepath)
            return {
                "duration_sec": round(len(seg) / 1000.0, 2),
                "channels": seg.channels,
                "frame_rate": seg.frame_rate,
                "sample_width_bits": seg.sample_width * 8,
                "dBFS": round(seg.dBFS, 2),
                "max_dBFS": round(seg.max_dBFS, 2)
            }
        except Exception:
            return None
