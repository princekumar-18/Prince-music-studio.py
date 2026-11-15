# =============================================================================
# 2. SQLITE DATABASE MANAGER
# =============================================================================

class DatabaseManager:
    """Manages persistent library, playlists, play history, favorites, and radio."""

    def __init__(self, db_path="prince_music_studio.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def init_schema(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE NOT NULL,
                title TEXT,
                artist TEXT,
                album TEXT,
                genre TEXT,
                duration REAL DEFAULT 0,
                play_count INTEGER DEFAULT 0,
                last_played TIMESTAMP,
                is_favorite INTEGER DEFAULT 0,
                lyrics TEXT DEFAULT ''
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                playlist_id INTEGER,
                track_id INTEGER,
                UNIQUE(playlist_id, track_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS radio_stations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                genre TEXT DEFAULT 'Stream'
            )
        """)
        # Seed default Internet Radio stations if empty
        cur.execute("SELECT COUNT(*) as cnt FROM radio_stations")
        if cur.fetchone()["cnt"] == 0:
            default_stations = [
                ("SomaFM Groove Salad (Ambient/Chill)", "http://ice1.somafm.com/groovesalad-128-mp3", "Ambient"),
                ("SomaFM Secret Agent (Lounge)", "http://ice1.somafm.com/secretagent-128-mp3", "Lounge"),
                ("SomaFM Def Con Radio (Electronic)", "http://ice1.somafm.com/defcon-128-mp3", "Electronic"),
                ("Radio Swiss Jazz", "http://stream.srg-ssr.ch/m/rsj/mp3_128", "Jazz"),
                ("Radio Swiss Classic", "http://stream.srg-ssr.ch/m/rsc_de/mp3_128", "Classical")
            ]
            cur.executemany(
                "INSERT INTO radio_stations (name, url, genre) VALUES (?, ?, ?)",
                default_stations
            )
        self.conn.commit()

    def upsert_track(self, filepath, title, artist, album, genre, duration, lyrics=""):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO tracks (filepath, title, artist, album, genre, duration, lyrics)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(filepath) DO UPDATE SET
                title=excluded.title,
                artist=excluded.artist,
                album=excluded.album,
                genre=excluded.genre,
                duration=excluded.duration
        """, (str(filepath), title, artist, album, genre, duration, lyrics))
        self.conn.commit()

    def get_all_tracks(self, sort_by="title", search_query=""):
        valid_sorts = {
            "Title": "title COLLATE NOCASE ASC",
            "Artist": "artist COLLATE NOCASE ASC",
            "Album": "album COLLATE NOCASE ASC",
            "Duration": "duration DESC"
        }
        order_clause = valid_sorts.get(sort_by, "title COLLATE NOCASE ASC")
        cur = self.conn.cursor()
        if search_query.strip():
            q = f"%{search_query.strip()}%"
            cur.execute(f"""
                SELECT * FROM tracks
                WHERE title LIKE ? OR artist LIKE ? OR album LIKE ? OR genre LIKE ?
                ORDER BY {order_clause}
            """, (q, q, q, q))
        else:
            cur.execute(f"SELECT * FROM tracks ORDER BY {order_clause}")
        return [dict(r) for r in cur.fetchall()]

    def get_favorites(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM tracks WHERE is_favorite = 1 ORDER BY title COLLATE NOCASE ASC")
        return [dict(r) for r in cur.fetchall()]

    def get_recently_played(self, limit=30):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM tracks
            WHERE last_played IS NOT NULL
            ORDER BY last_played DESC LIMIT ?
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]

    def get_most_played(self, limit=30):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM tracks
            WHERE play_count > 0
            ORDER BY play_count DESC, last_played DESC LIMIT ?
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]

    def get_recommendations(self, limit=20):
        """Smart Recommendation Engine based on favorite artists & genres."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT artist, genre FROM tracks
            WHERE is_favorite = 1 OR play_count > 0
            ORDER BY play_count DESC LIMIT 5
        """)
        seeds = cur.fetchall()
        if not seeds:
            cur.execute("SELECT * FROM tracks ORDER BY RANDOM() LIMIT ?", (limit,))
            return [dict(r) for r in cur.fetchall()]

        top_artists = [r["artist"] for r in seeds if r["artist"]]
        top_genres = [r["genre"] for r in seeds if r["genre"]]
        placeholders_a = ",".join(["?"] * len(top_artists)) if top_artists else "''"
        placeholders_g = ",".join(["?"] * len(top_genres)) if top_genres else "''"
        params = top_artists + top_genres + [limit]
        query = f"""
            SELECT * FROM tracks
            WHERE artist IN ({placeholders_a}) OR genre IN ({placeholders_g})
            ORDER BY is_favorite DESC, play_count ASC, RANDOM()
            LIMIT ?
        """
        cur.execute(query, params)
        results = [dict(r) for r in cur.fetchall()]
        if not results:
            cur.execute("SELECT * FROM tracks ORDER BY RANDOM() LIMIT ?", (limit,))
            results = [dict(r) for r in cur.fetchall()]
        return results

    def toggle_favorite(self, track_id):
        cur = self.conn.cursor()
        cur.execute("SELECT is_favorite FROM tracks WHERE id = ?", (track_id,))
        row = cur.fetchone()
        if not row:
            return False
        new_val = 0 if row["is_favorite"] else 1
        cur.execute("UPDATE tracks SET is_favorite = ? WHERE id = ?", (new_val, track_id))
        self.conn.commit()
        return bool(new_val)

    def record_play(self, track_id):
        now = datetime.datetime.now().isoformat( sep=" ", timespec="seconds")
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE tracks
            SET play_count = play_count + 1, last_played = ?
            WHERE id = ?
        """, (now, track_id))
        self.conn.commit()

    def update_metadata(self, track_id, title, artist, album, genre, lyrics):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE tracks
            SET title = ?, artist = ?, album = ?, genre = ?, lyrics = ?
            WHERE id = ?
        """, (title, artist, album, genre, lyrics, track_id))
        self.conn.commit()

    def create_playlist(self, name):
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO playlists (name) VALUES (?)", (name,))
        self.conn.commit()

    def delete_playlist(self, playlist_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,))
        cur.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        self.conn.commit()

    def get_playlists(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM playlists ORDER BY name COLLATE NOCASE ASC")
        return [dict(r) for r in cur.fetchall()]

    def add_track_to_playlist(self, playlist_id, track_id):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_id)
            VALUES (?, ?)
        """, (playlist_id, track_id))
        self.conn.commit()

    def get_playlist_tracks(self, playlist_id):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT t.* FROM tracks t
            JOIN playlist_tracks pt ON t.id = pt.track_id
            WHERE pt.playlist_id = ?
            ORDER BY t.title COLLATE NOCASE ASC
        """, (playlist_id,))
        return [dict(r) for r in cur.fetchall()]

    def get_radio_stations(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM radio_stations ORDER BY name ASC")
        return [dict(r) for r in cur.fetchall()]

    def add_radio_station(self, name, url, genre="Stream"):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO radio_stations (name, url, genre) VALUES (?, ?, ?)",
            (name, url, genre)
        )
        self.conn.commit()
