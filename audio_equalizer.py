# =============================================================================
# 4. VLC AUDIO ENGINE (10-BAND EQ, BASS/TREBLE, BALANCE, SPEED, DEVICES)
# =============================================================================

class VLCAudioEngine:
    """Hardware-accelerated audio engine wrapping python-vlc with graceful fallback."""

    def __init__(self):
        self.has_vlc = False
        self.instance = None
        self.player = None
        self.equalizer = None
        self.is_playing_sim = False
        self.sim_position = 0.0
        self.sim_duration = 210.0
        self.volume = 80
        self.rate = 1.0
        self.balance = 0.0
        self.bass_boost = 0.0
        self.treble_boost = 0.0
        self.eq_gains = [0.0] * 10

        if HAS_VLC:
            try:
                self.instance = vlc.Instance("--no-video", "--quiet")
                self.player = self.instance.media_player_new()
                self.equalizer = vlc.AudioEqualizer()
                self.player.set_equalizer(self.equalizer)
                self.player.audio_set_volume(self.volume)
                self.has_vlc = True
            except Exception:
                self.has_vlc = False

    def load_and_play(self, source_path_or_url):
        if self.has_vlc:
            if source_path_or_url.startswith("http://") or source_path_or_url.startswith("https://"):
                media = self.instance.media_new(source_path_or_url)
            else:
                media = self.instance.media_new_path(os.path.abspath(source_path_or_url))
            self.player.set_media(media)
            self.player.play()
            self.player.set_rate(self.rate)
            self.apply_eq()
        else:
            self.sim_position = 0.0
            self.is_playing_sim = True

    def play(self):
        if self.has_vlc:
            self.player.play()
        else:
            self.is_playing_sim = True

    def pause(self):
        if self.has_vlc:
            self.player.pause()
        else:
            self.is_playing_sim = not self.is_playing_sim

    def stop(self):
        if self.has_vlc:
            self.player.stop()
        else:
            self.is_playing_sim = False
            self.sim_position = 0.0

    def is_playing(self):
        if self.has_vlc:
            return bool(self.player.is_playing())
        return self.is_playing_sim

    def set_volume(self, val):
        self.volume = max(0, min(100, int(val)))
        if self.has_vlc:
            self.player.audio_set_volume(self.volume)

    def get_time_sec(self):
        if self.has_vlc:
            ms = self.player.get_time()
            return max(0.0, ms / 1000.0) if ms >= 0 else 0.0
        return self.sim_position

    def get_length_sec(self):
        if self.has_vlc:
            ms = self.player.get_length()
            return max(0.0, ms / 1000.0) if ms > 0 else 0.0
        return self.sim_duration

    def set_position_ratio(self, ratio):
        ratio = max(0.0, min(1.0, float(ratio)))
        if self.has_vlc:
            self.player.set_position(ratio)
        else:
            self.sim_position = ratio * self.sim_duration

    def set_playback_rate(self, rate):
        self.rate = float(rate)
        if self.has_vlc:
            self.player.set_rate(self.rate)

    def set_eq_band(self, index, gain_db):
        if 0 <= index < 10:
            self.eq_gains[index] = float(gain_db)
            self.apply_eq()

    def set_bass_boost(self, gain_db):
        self.bass_boost = float(gain_db)
        self.apply_eq()

    def set_treble_boost(self, gain_db):
        self.treble_boost = float(gain_db)
        self.apply_eq()

    def apply_eq(self):
        if not self.has_vlc or not self.equalizer:
            return
        for i in range(10):
            total_gain = self.eq_gains[i]
            if i in (0, 1, 2):
                total_gain += self.bass_boost * (1.0 - i * 0.25)
            elif i in (7, 8, 9):
                total_gain += self.treble_boost * ((i - 6) * 0.3)
            clamped = max(-20.0, min(20.0, total_gain))
            self.equalizer.set_amp_at_index(clamped, i)
        self.player.set_equalizer(self.equalizer)

    def get_audio_devices(self):
        devices = [("Default System Output", "")]
        if not self.has_vlc:
            return devices
        try:
            mods = self.player.audio_output_device_enum()
            if mods:
                mod = mods
                while mod:
                    dev = mod.contents
                    name = dev.description.decode("utf-8", errors="ignore")
                    dev_id = dev.device.decode("utf-8", errors="ignore")
                    devices.append((name, dev_id))
                    mod = dev.next
                vlc.libvlc_audio_output_device_list_release(mods)
        except Exception:
            pass
        return devices

    def set_audio_device(self, device_id):
        if self.has_vlc and device_id:
            try:
                self.player.audio_output_device_set(None, device_id)
            except Exception:
                pass

