from importlib.machinery import SourceFileLoader
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "bcache-monitor"
bcache_monitor = SourceFileLoader("bcache_monitor", str(module_path)).load_module()


def test_version_string_validation_accepts_numeric_versions():
    assert bcache_monitor.is_valid_version_string("1.2.3")


def test_parse_sysfs_size_bytes_handles_mib_suffix():
    assert bcache_monitor.parse_sysfs_size_bytes("12MiB") == 12 * 1024 * 1024


def test_parse_docker_block_io_pair_returns_read_and_write_totals():
    assert bcache_monitor.parse_docker_block_io_pair("1.5MiB / 2KiB") == (1572864, 2048)


def test_format_delta_pct_suppresses_zero_baseline_percentages():
    assert bcache_monitor.format_delta_pct(0, 0) == "n/a"


def test_format_cache_mode_shows_only_active_bracketed_mode():
    assert bcache_monitor.format_cache_mode("writethrough [writeback] writearound none") == "writeback"


def test_format_cache_mode_falls_back_to_raw_value():
    assert bcache_monitor.format_cache_mode("writethrough") == "writethrough"


def test_info_lines_include_bugreport_and_ai_notice():
    lines = "\n".join(bcache_monitor.info_lines(None))
    assert "KI-Unterstützung" in lines
    assert "Linux-Bcache-Monitor/issues" in lines


class FakeScreen:
    def __init__(self, height=30, width=80):
        self.height = height
        self.width = width
        self.draws = []

    def getmaxyx(self):
        return self.height, self.width

    def addstr(self, y, x, text, color=0):
        self.draws.append((y, x, text, color))


def test_graph_points_right_align_short_history_and_hide_zero_values():
    points = bcache_monitor._graph_points([0, 5, 0], y=2, x=10, w=8, h=5, maxv=10)

    assert [col for _, col, _ in points] == [15, 16, 17]
    assert points[0][0] is None
    assert points[2][0] is None


def test_draw_line_graph_does_not_draw_vertical_spike_bars_or_zero_baseline():
    screen = FakeScreen()
    bcache_monitor.draw_line_graph(screen, [0, 100, 0, 100, 0], y=2, x=10, w=8, h=6, color=2, maxv=100)
    drawn_text = "".join(text for _, _, text, _ in screen.draws)

    assert "┃" not in drawn_text
    assert "━" not in drawn_text
    assert all(row != 2 + 6 - 1 for row, _, _, _ in screen.draws)
