# =============================================================================
# 6. METADATA EDITOR & PYDUB AUDIO INSPECTOR DIALOGS
# =============================================================================

class MetadataEditorDialog(QDialog):
    """Dialog for editing track ID3/Vorbis tags and lyrics."""

    def __init__(self, track_dict, parent=None):
        super().__init__(parent)
        self.track = track_dict
        self.setWindowTitle("Edit Track Metadata & Lyrics")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.title_edit = QLineEdit(track_dict.get("title", ""))
        self.artist_edit = QLineEdit(track_dict.get("artist", ""))
        self.album_edit = QLineEdit(track_dict.get("album", ""))
        self.genre_edit = QLineEdit(track_dict.get("genre", ""))
        self.lyrics_edit = QTextEdit(track_dict.get("lyrics", ""))
        self.lyrics_edit.setMinimumHeight(120)

        form.addRow("Title:", self.title_edit)
        form.addRow("Artist:", self.artist_edit)
        form.addRow("Album:", self.album_edit)
        form.addRow("Genre:", self.genre_edit)
        form.addRow("Lyrics:", self.lyrics_edit)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save Metadata")
        save_btn.setObjectName("AccentBtn")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def get_values(self):
        return (
            self.title_edit.text().strip(),
            self.artist_edit.text().strip(),
            self.album_edit.text().strip(),
            self.genre_edit.text().strip(),
            self.lyrics_edit.toPlainText().strip()
        )
