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


def test_version_metadata_is_in_sync():
    repo_root = Path(__file__).resolve().parents[1]
    version = (repo_root / "VERSION").read_text().strip()
    readme = (repo_root / "README.md").read_text()

    assert bcache_monitor.__version__ == version == "0.7.00"
    assert f"**Version:** {version}" in readme


def test_print_version_and_exit_for_cli_flag(capsys):
    assert bcache_monitor.print_version_and_exit_if_requested(["bcache-monitor", "--version"]) is True
    assert capsys.readouterr().out.strip() == "0.7.00"


def test_info_lines_include_bugreport_and_ai_notice():
    lines = "\n".join(bcache_monitor.info_lines(None))
    assert "AI assistance" in lines
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


def test_status_from_metrics_ignores_miss_trend_when_idle():
    status, _color, reason = bcache_monitor.status_from_metrics(52.0, 0, 0, [0, 0, 0, 10, 10, 10])

    assert status == "WARN"
    assert "historical" in reason
    assert "miss trend" not in reason


def test_status_from_metrics_keeps_live_miss_only_critical():
    status, _color, reason = bcache_monitor.status_from_metrics(90.0, 0, 5, [0, 0, 0, 5, 5, 5])

    assert status == "CRITICAL"
    assert "miss/hit" in reason


def test_format_delta_pct_for_display_suppresses_idle_minus_100():
    assert bcache_monitor.format_delta_pct_for_display(0, 0.5) == "n/a"


def test_calculate_docker_io_rates_returns_read_and_write_rates():
    prev = ((1024, 2048), 10.0)
    read_rate, write_rate, current = bcache_monitor.calculate_docker_io_rates(prev, 3072, 6144, 12.0)

    assert read_rate == 1024
    assert write_rate == 2048
    assert current == ((3072, 6144), 12.0)


def test_calculate_device_rates_uses_written_sectors():
    prev = ({"read_sectors": 10, "write_sectors": 20}, 1.0)
    current = {"read_sectors": 14, "write_sectors": 28}

    read_rate, write_rate = bcache_monitor.calculate_device_rates(prev, current, 3.0)

    assert read_rate == 1024
    assert write_rate == 2048


def test_parse_mountinfo_lines_matches_direct_device():
    lines = ["36 25 8:0 / /data rw,relatime - ext4 /dev/bcache0 rw\n"]

    assert bcache_monitor._parse_mountinfo_lines(lines, "bcache0") == [("/data", "/dev/bcache0")]



def test_efficiency_label_classifies_low_cache_benefit():
    assert bcache_monitor.efficiency_label(94) == "Sehr gut"
    assert bcache_monitor.efficiency_label(22) == "Cache bringt kaum Nutzen"


def test_estimate_flush_seconds_uses_dirty_data_and_rate():
    assert bcache_monitor.estimate_flush_seconds(12 * 1024 * 1024, 3 * 1024 * 1024) == 4
    assert bcache_monitor.format_duration(272) == "4m 32s"


def test_health_report_penalizes_hot_ssd_and_low_life():
    details = {"cache_mode": "[writeback]", "dirty_bytes": 0, "writeback_percent": "10"}
    smart = {"temperature_c": 72, "life_remaining_percent": 12}
    report = bcache_monitor.health_report(92, details, smart)

    assert report["score"] < 80
    assert report["status"] in {"WARNING", "CRITICAL", "FAILURE"}
    assert "SSD temperature critical" in report["warnings"]
    assert "Cache SSD life below 15%" in report["warnings"]


def test_prometheus_metrics_include_health_score_and_ssd_life():
    details = {"cache_mode": "[writeback]", "dirty_bytes": 1024, "cache_available_percent": 88.5}
    smart = {"life_remaining_percent": 77, "temperature_c": 43, "tbw_bytes": 1234}
    report = {"score": 91}

    output = bcache_monitor.prometheus_metrics("bcache0", 94.0, details, smart, report)

    assert 'bcache_hit_ratio{device="bcache0"} 0.940000' in output
    assert 'bcache_health_score{device="bcache0"} 91' in output
    assert 'bcache_ssd_life_remaining_percent{device="bcache0"} 77' in output


def test_parse_smart_health_text_parses_nvme_fields():
    raw = """
Percentage Used:                    12%
Data Units Written:                 1,000
Temperature:                        43 Celsius
"""
    health = bcache_monitor.parse_smart_health_text(raw)

    assert health["wear_used_percent"] == 12
    assert health["life_remaining_percent"] == 88
    assert health["temperature_c"] == 43
    assert health["tbw_bytes"] == 512000000
