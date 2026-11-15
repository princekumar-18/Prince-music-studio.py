# =============================================================================
# 5. ANIMATED MATPLOTLIB AUDIO VISUALIZER
# =============================================================================

class AudioVisualizerCanvas(FigureCanvas):
    """Real-time animated 28-band spectrum & waveform canvas synced to EQ/playback."""

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(5, 1.8), dpi=90)
        self.fig.patch.set_facecolor("#181818")
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#181818")
        self.fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.08)

        self.num_bars = 28
        self.x_vals = np.arange(self.num_bars)
        self.heights = np.zeros(self.num_bars)
        self.phase = 0.0

        self.bars = self.ax.bar(
            self.x_vals, self.heights, width=0.72, color="#1DB954", alpha=0.88
        )
        (self.wave_line,) = self.ax.plot(
            np.linspace(0, self.num_bars - 1, 80),
            np.zeros(80),
            color="#00E5FF",
            linewidth=1.5,
            alpha=0.75
        )
        self.ax.set_ylim(0, 105)
        self.ax.set_xlim(-0.8, self.num_bars - 0.2)
        self.ax.axis("off")

    def set_theme_background(self, hex_color):
        self.fig.patch.set_facecolor(hex_color)
        self.ax.set_facecolor(hex_color)
        self.draw_idle()

    def update_spectrum(self, active, volume, eq_gains, bass_boost, treble_boost):
        if active and volume > 0:
            self.phase += 0.28
            vol_scale = max(0.15, volume / 100.0)
            new_heights = np.zeros(self.num_bars)
            for i in range(self.num_bars):
                eq_idx = min(9, int((i / self.num_bars) * 10))
                eq_factor = 1.0 + (eq_gains[eq_idx] / 25.0)
                if i < 6:
                    eq_factor += bass_boost / 20.0
                elif i > 20:
                    eq_factor += treble_boost / 20.0
                base = (
                    42.0 * math.sin(i * 0.35 + self.phase)
                    + 28.0 * math.cos(i * 0.7 - self.phase * 1.4)
                    + random.uniform(8, 34)
                )
                val = max(6.0, min(100.0, abs(base) * vol_scale * max(0.3, eq_factor)))
                new_heights[i] = 0.6 * self.heights[i] + 0.4 * val
            self.heights = new_heights

            x_dense = np.linspace(0, self.num_bars - 1, 80)
            wave = 50 + 28 * vol_scale * np.sin(x_dense * 0.55 - self.phase * 1.8)
            self.wave_line.set_ydata(wave)
        else:
            self.heights *= 0.72
            self.wave_line.set_ydata(np.zeros(80) + 4)

        for bar, h in zip(self.bars, self.heights):
            bar.set_height(h)
        self.draw_idle()

