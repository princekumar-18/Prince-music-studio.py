# =============================================================================
# 7. MAIN WINDOW: PRINCE MUSIC STUDIO
# =============================================================================

class PrinceMusicStudio(QMainWindow):
    """Spotify-inspired main desktop application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 PRINCE MUSIC STUDIO – Advanced Desktop Music Player")
        self.resize(1340, 820)

        self.db = DatabaseManager()
        self.engine = VLCAudioEngine()

        # State Variables
        self.current_view = "all"
        self.current_playlist_id = None
        self.displayed_tracks = []
        self.queue = []
        self.current_track = None
        self.current_index = -1
        self.is_shuffle = False
        self.repeat_mode = 0  # 0: Off, 1: Repeat All, 2: Repeat One
        self.is_dark_mode = True
        self.is_mini_mode = False
        self.is_seeking = False
        self.crossfade_sec = 0
        self.sleep_remaining_sec = 0

        self.build_ui()
        self.setup_shortcuts()
        self.apply_theme()
        self.refresh_playlists_sidebar()
        self.load_library_view("all")

        # Main UI & Visualizer Timer
        self.ui_timer = QTimer(self)
        self.ui_timer.setInterval(80)
        self.ui_timer.timeout.connect(self.on_timer_tick)
        self.ui_timer.start()

        # Sleep Countdown Timer
        self.sleep_timer = QTimer(self)
        self.sleep_timer.setInterval(1000)
        self.sleep_timer.timeout.connect(self.on_sleep_tick)
        self.sleep_timer.start()

    # -------------------------------------------------------------------------
    # UI CONSTRUCTION
    # -------------------------------------------------------------------------
    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 0)
        root_layout.setSpacing(8)

        # Top 3-Column Splitter (Left: Library/Playlists, Center: Hero+Tracks, Right: Queue/Lyrics/EQ)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(self.main_splitter, stretch=1)

        self.left_panel = self.create_left_sidebar()
        self.center_panel = self.create_center_panel()
        self.right_panel = self.create_right_sidebar()

        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(self.center_panel)
        self.main_splitter.addWidget(self.right_panel)
        self.main_splitter.setSizes([230, 740, 350])

        # Bottom Transport Control Bar
        self.transport_bar = self.create_transport_bar()
        root_layout.addWidget(self.transport_bar)

    def create_left_sidebar(self):
        frame = QFrame()
        frame.setObjectName("PanelCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        brand_lbl = QLabel("👑 PRINCE STUDIO")
        brand_lbl.setObjectName("HeroTitle")
        layout.addWidget(brand_lbl)

        nav_hdr = QLabel("LIBRARY & SMART VIEWS")
        nav_hdr.setObjectName("SectionHeader")
        layout.addWidget(nav_hdr)

        self.nav_list = QListWidget()
        self.nav_list.setFixedHeight(195)
        nav_items = [
            ("🎵  All Songs", "all"),
            ("❤️  Favorite Songs", "favorites"),
            ("🕒  Recently Played", "recent"),
            ("🔥  Most Played", "most_played"),
            ("✨  Smart Recommendations", "recommendations"),
            ("🌐  Internet Radio", "radio")
        ]
        for label, key in nav_items:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.nav_list.addItem(item)
        self.nav_list.setCurrentRow(0)
        self.nav_list.itemClicked.connect(self.on_nav_clicked)
        layout.addWidget(self.nav_list)

        # Custom Playlists Section
        pl_hdr_row = QHBoxLayout()
        pl_hdr = QLabel("CUSTOM PLAYLISTS")
        pl_hdr.setObjectName("SectionHeader")
        new_pl_btn = QPushButton("+ New")
        new_pl_btn.setFixedWidth(60)
        new_pl_btn.clicked.connect(self.create_new_playlist)
        pl_hdr_row.addWidget(pl_hdr)
        pl_hdr_row.addStretch()
        pl_hdr_row.addWidget(new_pl_btn)
        layout.addLayout(pl_hdr_row)

        self.playlist_list = QListWidget()
        self.playlist_list.itemClicked.connect(self.on_playlist_clicked)
        self.playlist_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_list.customContextMenuRequested.connect(self.on_playlist_context_menu)
        layout.addWidget(self.playlist_list, stretch=1)

        # Sleep Timer Box
        sleep_hdr = QLabel("⏰ SLEEP TIMER")
        sleep_hdr.setObjectName("SectionHeader")
        layout.addWidget(sleep_hdr)
        sleep_row = QHBoxLayout()
        self.sleep_combo = QComboBox()
        self.sleep_combo.addItems(["Off", "5 min", "15 min", "30 min", "60 min"])
        self.sleep_combo.currentIndexChanged.connect(self.on_sleep_timer_changed)
        self.sleep_status_lbl = QLabel("Off")
        sleep_row.addWidget(self.sleep_combo, stretch=1)
        sleep_row.addWidget(self.sleep_status_lbl)
        layout.addLayout(sleep_row)

        return frame

    def create_center_panel(self):
        frame = QFrame()
        frame.setObjectName("PanelCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Top Action Bar: Search, Sort, Add Files, Import Folder, Add Radio
        top_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search songs, artists, albums, or genres (Ctrl+F)...")
        self.search_input.textChanged.connect(self.refresh_current_table)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Title", "Artist", "Album", "Duration"])
        self.sort_combo.currentTextChanged.connect(self.refresh_current_table)

        add_files_btn = QPushButton("➕ Add Songs")
        add_files_btn.setObjectName("AccentBtn")
        add_files_btn.clicked.connect(self.add_songs_dialog)

        add_folder_btn = QPushButton("📁 Import Folder")
        add_folder_btn.clicked.connect(self.import_folder_dialog)

        add_radio_btn = QPushButton("📻 + Radio URL")
        add_radio_btn.clicked.connect(self.add_radio_dialog)

        top_bar.addWidget(self.search_input, stretch=1)
        top_bar.addWidget(QLabel("Sort:"))
        top_bar.addWidget(self.sort_combo)
        top_bar.addWidget(add_files_btn)
        top_bar.addWidget(add_folder_btn)
        top_bar.addWidget(add_radio_btn)
        layout.addLayout(top_bar)

        # Center Hero Section: Album Artwork + Song Info + Animated Visualizer
        hero_frame = QFrame()
        hero_layout = QHBoxLayout(hero_frame)
        hero_layout.setContentsMargins(4, 4, 4, 4)
        hero_layout.setSpacing(16)

        self.artwork_label = QLabel()
        self.artwork_label.setFixedSize(175, 175)
        self.artwork_label.setPixmap(
            MediaHelper.build_album_pixmap("Prince Studio", "Ready to Play", None, 175)
        )
        hero_layout.addWidget(self.artwork_label)

        info_vis_layout = QVBoxLayout()
        self.hero_title_lbl = QLabel("Welcome to Prince Music Studio")
        self.hero_title_lbl.setObjectName("TrackTitle")
        self.hero_artist_lbl = QLabel("Import songs or select an Internet Radio station to begin")
        self.hero_artist_lbl.setObjectName("TrackSub")
        self.hero_meta_lbl = QLabel("Formats: MP3 • WAV • FLAC • AAC • OGG • Live Streams")
        self.hero_meta_lbl.setObjectName("SectionHeader")

        info_vis_layout.addWidget(self.hero_title_lbl)
        info_vis_layout.addWidget(self.hero_artist_lbl)
        info_vis_layout.addWidget(self.hero_meta_lbl)

        self.visualizer = AudioVisualizerCanvas(self)
        info_vis_layout.addWidget(self.visualizer, stretch=1)
        hero_layout.addLayout(info_vis_layout, stretch=1)
        layout.addWidget(hero_frame)

        # Track Table Header
        self.view_title_lbl = QLabel("ALL SONGS")
        self.view_title_lbl.setObjectName("SectionHeader")
        layout.addWidget(self.view_title_lbl)

        # Library Songs Table
        self.track_table = QTableWidget(0, 6)
        self.track_table.setHorizontalHeaderLabels(
            ["♥", "Title", "Artist", "Album", "Duration", "Plays"]
        )
        self.track_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.track_table.setColumnWidth(0, 36)
        self.track_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.track_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.track_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.track_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.track_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.track_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.track_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.track_table.verticalHeader().setVisible(False)
        self.track_table.cellDoubleClicked.connect(self.on_table_double_clicked)
        self.track_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.track_table.customContextMenuRequested.connect(self.on_table_context_menu)
        layout.addWidget(self.track_table, stretch=1)

        return frame

    def create_right_sidebar(self):
        frame = QFrame()
        frame.setObjectName("PanelCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)

        self.right_tabs = QTabWidget()
        layout.addWidget(self.right_tabs)

        # TAB 1: Queue & Lyrics
        ql_widget = QWidget()
        ql_layout = QVBoxLayout(ql_widget)
        ql_layout.setContentsMargins(8, 8, 8, 8)

        q_hdr_row = QHBoxLayout()
        q_hdr = QLabel("UP NEXT QUEUE")
        q_hdr.setObjectName("SectionHeader")
        clear_q_btn = QPushButton("Clear")
        clear_q_btn.clicked.connect(self.clear_queue)
        q_hdr_row.addWidget(q_hdr)
        q_hdr_row.addStretch()
        q_hdr_row.addWidget(clear_q_btn)
        ql_layout.addLayout(q_hdr_row)

        self.queue_list = QListWidget()
        self.queue_list.setMaximumHeight(165)
        self.queue_list.itemDoubleClicked.connect(self.on_queue_item_double_clicked)
        ql_layout.addWidget(self.queue_list)

        lyr_hdr_row = QHBoxLayout()
        lyr_hdr = QLabel("SONG LYRICS")
        lyr_hdr.setObjectName("SectionHeader")
        fetch_lyr_btn = QPushButton("🌐 Auto-Fetch")
        fetch_lyr_btn.clicked.connect(self.fetch_lyrics_for_current)
        save_lyr_btn = QPushButton("💾 Save")
        save_lyr_btn.clicked.connect(self.save_current_lyrics)
        lyr_hdr_row.addWidget(lyr_hdr)
        lyr_hdr_row.addStretch()
        lyr_hdr_row.addWidget(fetch_lyr_btn)
        lyr_hdr_row.addWidget(save_lyr_btn)
        ql_layout.addLayout(lyr_hdr_row)

        self.lyrics_box = QTextEdit()
        self.lyrics_box.setPlaceholderText("Lyrics will appear here when available, or paste your own and click Save...")
        ql_layout.addWidget(self.lyrics_box, stretch=1)

        self.right_tabs.addTab(ql_widget, "Queue & Lyrics")

        # TAB 2: 10-Band Equalizer & Professional DSP Audio Controls
        eq_widget = QWidget()
        eq_layout = QVBoxLayout(eq_widget)
        eq_layout.setContentsMargins(8, 8, 8, 8)
        eq_layout.setSpacing(8)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset:"))
        self.eq_preset_combo = QComboBox()
        self.eq_preset_combo.addItems(list(EQ_PRESETS.keys()))
        self.eq_preset_combo.currentTextChanged.connect(self.apply_eq_preset)
        preset_row.addWidget(self.eq_preset_combo, stretch=1)
        eq_layout.addLayout(preset_row)

        # 10-Band Sliders
        bands_grid = QHBoxLayout()
        self.eq_sliders = []
        for idx, freq_label in enumerate(EQ_FREQUENCIES):
            col = QVBoxLayout()
            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(-20, 20)
            slider.setValue(0)
            slider.setMinimumHeight(130)
            slider.valueChanged.connect(lambda val, i=idx: self.engine.set_eq_band(i, val))
            self.eq_sliders.append(slider)
            lbl = QLabel(freq_label.replace("Hz", ""))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size: 10px;")
            col.addWidget(slider, alignment=Qt.AlignmentFlag.AlignHCenter)
            col.addWidget(lbl)
            bands_grid.addLayout(col)
        eq_layout.addLayout(bands_grid)

        # Bass Boost, Treble, Stereo Balance, Speed, Crossfade, Output Device
        dsp_form = QFormLayout()

        self.bass_slider = QSlider(Qt.Orientation.Horizontal)
        self.bass_slider.setRange(0, 15)
        self.bass_slider.valueChanged.connect(self.engine.set_bass_boost)
        dsp_form.addRow("Bass Boost:", self.bass_slider)

        self.treble_slider = QSlider(Qt.Orientation.Horizontal)
        self.treble_slider.setRange(-10, 15)
        self.treble_slider.valueChanged.connect(self.engine.set_treble_boost)
        dsp_form.addRow("Treble Adjust:", self.treble_slider)

        self.balance_slider = QSlider(Qt.Orientation.Horizontal)
        self.balance_slider.setRange(-100, 100)
        self.balance_slider.setValue(0)
        dsp_form.addRow("Stereo L/R:", self.balance_slider)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.currentTextChanged.connect(
            lambda s: self.engine.set_playback_rate(float(s.replace("x", "")))
        )
        dsp_form.addRow("Playback Speed:", self.speed_combo)

        self.crossfade_spin = QSpinBox()
        self.crossfade_spin.setRange(0, 12)
        self.crossfade_spin.setSuffix(" sec")
        self.crossfade_spin.valueChanged.connect(lambda v: setattr(self, "crossfade_sec", v))
        dsp_form.addRow("Crossfade:", self.crossfade_spin)

        self.device_combo = QComboBox()
        for dev_name, dev_id in self.engine.get_audio_devices():
            self.device_combo.addItem(dev_name, dev_id)
        self.device_combo.currentIndexChanged.connect(
            lambda idx: self.engine.set_audio_device(self.device_combo.itemData(idx))
        )
        dsp_form.addRow("Audio Output:", self.device_combo)

        eq_layout.addLayout(dsp_form)
        eq_layout.addStretch()
        self.right_tabs.addTab(eq_widget, "10-Band EQ & DSP")

        return frame

    def create_transport_bar(self):
        bar = QFrame()
        bar.setObjectName("TransportBar")
        bar.setFixedHeight(92)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(18)

        # Left: Current Track Mini Info & Favorite Heart
        left_box = QHBoxLayout()
        self.now_title_lbl = QLabel("No Track Playing")
        self.now_title_lbl.setObjectName("TrackTitle")
        self.now_artist_lbl = QLabel("Select a song")
        self.now_artist_lbl.setObjectName("TrackSub")
        text_col = QVBoxLayout()
        text_col.addWidget(self.now_title_lbl)
        text_col.addWidget(self.now_artist_lbl)
        left_box.addLayout(text_col)

        self.fav_btn = QPushButton("🤍")
        self.fav_btn.setFixedWidth(38)
        self.fav_btn.setToolTip("Toggle Favorite")
        self.fav_btn.clicked.connect(self.toggle_current_favorite)
        left_box.addWidget(self.fav_btn)
        layout.addLayout(left_box, stretch=2)

        # Center: Transport Buttons + Seek Bar
        center_col = QVBoxLayout()
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        self.shuffle_btn = QPushButton("🔀")
        self.shuffle_btn.setCheckable(True)
        self.shuffle_btn.setToolTip("Shuffle")
        self.shuffle_btn.clicked.connect(lambda c: setattr(self, "is_shuffle", c))

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.clicked.connect(self.play_previous)

        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("PlayBtn")
        self.play_btn.clicked.connect(self.toggle_play_pause)

        self.stop_btn = QPushButton("⏹")
        self.stop_btn.clicked.connect(self.stop_playback)

        self.next_btn = QPushButton("⏭")
        self.next_btn.clicked.connect(self.play_next)

        self.repeat_btn = QPushButton("🔁 Off")
        self.repeat_btn.clicked.connect(self.cycle_repeat_mode)

        for b in (self.shuffle_btn, self.prev_btn, self.play_btn, self.stop_btn, self.next_btn, self.repeat_btn):
            btn_row.addWidget(b)
        btn_row.addStretch()
        center_col.addLayout(btn_row)

        seek_row = QHBoxLayout()
        self.time_cur_lbl = QLabel("0:00")
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.sliderPressed.connect(lambda: setattr(self, "is_seeking", True))
        self.seek_slider.sliderReleased.connect(self.on_seek_released)
        self.time_tot_lbl = QLabel("0:00")
        seek_row.addWidget(self.time_cur_lbl)
        seek_row.addWidget(self.seek_slider, stretch=1)
        seek_row.addWidget(self.time_tot_lbl)
        center_col.addLayout(seek_row)
        layout.addLayout(center_col, stretch=4)

        # Right: Volume + Theme + Mini-Player + Fullscreen
        right_box = QHBoxLayout()
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setFixedWidth(36)
        self.mute_btn.clicked.connect(self.toggle_mute)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(100)
        self.vol_slider.valueChanged.connect(self.on_volume_changed)

        self.theme_btn = QPushButton("☀️ Light")
        self.theme_btn.clicked.connect(self.toggle_theme)

        self.mini_btn = QPushButton("🗕 Mini")
        self.mini_btn.clicked.connect(self.toggle_mini_player)

        self.full_btn = QPushButton("⛶ Full")
        self.full_btn.clicked.connect(self.toggle_fullscreen)

        right_box.addWidget(self.mute_btn)
        right_box.addWidget(self.vol_slider)
        right_box.addWidget(self.theme_btn)
        right_box.addWidget(self.mini_btn)
        right_box.addWidget(self.full_btn)
        layout.addLayout(right_box, stretch=2)

        return bar

    # -------------------------------------------------------------------------
    # KEYBOARD SHORTCUTS
    # -------------------------------------------------------------------------
    def setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, activated=self.toggle_play_pause)
        QShortcut(QKeySequence("Ctrl+Right"), self, activated=self.play_next)
        QShortcut(QKeySequence("Ctrl+Left"), self, activated=self.play_previous)
        QShortcut(QKeySequence("M"), self, activated=self.toggle_mute)
        QShortcut(QKeySequence("F"), self, activated=self.toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+M"), self, activated=self.toggle_mini_player)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self.add_songs_dialog)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: self.search_input.setFocus())
