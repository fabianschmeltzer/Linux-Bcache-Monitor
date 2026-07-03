from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import sys
import pytest

module_path = Path(__file__).resolve().parents[1] / "bcache-monitor"
loader = SourceFileLoader("bcache_monitor", str(module_path))
spec = spec_from_loader(loader.name, loader)
bcache_monitor = module_from_spec(spec)
sys.modules[loader.name] = bcache_monitor
loader.exec_module(bcache_monitor)


def test_version_string_validation_accepts_numeric_versions():
    assert bcache_monitor.is_valid_version_string("1.2.3")


def test_parse_sysfs_size_bytes_handles_mib_suffix():
    assert bcache_monitor.parse_sysfs_size_bytes("12MiB") == 12 * 1024 * 1024


def test_parse_sysfs_size_bytes_handles_kernel_rate_and_large_units():
    assert bcache_monitor.parse_sysfs_size_bytes("4.0M/s") == 4 * 1024 ** 2
    assert bcache_monitor.parse_sysfs_size_bytes("1.5T") == int(1.5 * 1024 ** 4)
    assert bcache_monitor.parse_sysfs_size_bytes("2PiB") == 2 * 1024 ** 5


def test_parse_docker_block_io_pair_returns_read_and_write_totals():
    assert bcache_monitor.parse_docker_block_io_pair("1.5MiB / 2KiB") == (1572864, 2048)


def test_parse_docker_sizes_distinguishes_si_and_iec_units():
    assert bcache_monitor.parse_docker_size_bytes("4.11MB") == 4_110_000
    assert bcache_monitor.parse_docker_size_bytes("4.11MiB") == int(4.11 * 1024 ** 2)


def test_format_delta_pct_suppresses_zero_baseline_percentages():
    assert bcache_monitor.format_delta_pct(0, 0) == "n/a"


def test_format_cache_mode_shows_only_active_bracketed_mode():
    assert bcache_monitor.format_cache_mode("writethrough [writeback] writearound none") == "writeback"


def test_format_cache_mode_falls_back_to_raw_value():
    assert bcache_monitor.format_cache_mode("writethrough") == "writethrough"


def test_version_metadata_is_in_sync():
    repo_root = Path(__file__).resolve().parents[1]
    version = (repo_root / "VERSION").read_text().strip()
    readme = (repo_root / "README.md").read_text(encoding="utf-8")

    assert bcache_monitor.__version__ == version == "0.9.0"
    assert f"**Version:** {version}" in readme


def test_print_version_and_exit_for_cli_flag(capsys):
    assert bcache_monitor.print_version_and_exit_if_requested(["bcache-monitor", "--version"]) is True
    assert capsys.readouterr().out.strip() == "0.9.0"


def test_info_lines_include_bugreport_and_ai_notice():
    lines = "\n".join(bcache_monitor.info_lines({"language": "en"}))
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


def test_dashboard_layout_uses_minimal_stacked_and_split_profiles():
    minimal = bcache_monitor.dashboard_layout(12, 50)
    stacked = bcache_monitor.dashboard_layout(24, 63)
    split = bcache_monitor.dashboard_layout(38, 98)
    wide = bcache_monitor.dashboard_layout(62, 190)

    assert minimal.profile == "minimal"
    assert minimal.show_graph is False
    assert stacked.profile == "stacked"
    assert stacked.graph_x + stacked.graph_w < 63
    assert split.profile == "split"
    assert split.graph_x + split.graph_w < split.side_x
    assert split.side_x + split.side_w < 98
    assert wide.graph_w < 190 * 0.70


def test_pack_metric_rows_preserves_order_and_width():
    rows = bcache_monitor.pack_metric_rows(
        ["Modus: writeback", "Dirty: 12 MiB", "WB-Ziel: 4 MiB/s"],
        30,
    )

    assert all(len(row) <= 30 for row in rows)
    assert "Modus" in rows[0]
    assert "WB-Ziel" in rows[-1]


def _dashboard_fixture():
    state = bcache_monitor.AppState(
        config={
            "language": "de",
            "docker_enabled": True,
            "containers": ["nextcloud_app", "immich-server"],
        },
        selected_containers=["nextcloud_app", "immich-server"],
    )
    state.device_name = "bcache0"
    state.device_source = "auto"
    state.sysfs_ok = True
    state.current_hits = 488_312
    state.current_misses = 183_697
    state.current_hps = 7
    state.current_mps = 1
    state.current_eff = 72.66
    state.hits.extend([0, 3, 7])
    state.miss.extend([0, 0, 1])
    state.miss_trend.extend([0, 0, 1])
    state.eff_history.extend([72.4, 72.5, 72.66])
    state.backing_write_rate_bytes = 11 * 1024
    state.docker_state = "OK"
    state.docker_cache = [
        ("nextcloud_app", 0.8, 12.0, "174.7MiB / 1GiB", "2MiB / 4MiB"),
        ("immich-server", 5.8, 45.0, "675.9MiB / 1GiB", "4MiB / 8MiB"),
    ]
    state.docker_io_rates = {
        "nextcloud_app": (1024, 2048),
        "immich-server": (4096, 8192),
    }
    details = bcache_monitor.empty_bcache_details()
    details.update({
        "cache_mode": "[writeback]",
        "cache_capacity": 512 * 1024 ** 3,
        "cache_available_percent": 93.0,
        "cache_available_bytes": 476 * 1024 ** 3,
        "dirty_bytes": 52 * 1024,
        "backing_size": 2 * 1024 ** 4,
        "fs_usage": {
            "total": 2 * 1024 ** 4,
            "used": 900 * 1024 ** 3,
            "free": 1_148 * 1024 ** 3,
        },
        "writeback_percent": "5",
        "writeback_rate_bytes": 4 * 1024 ** 2,
        "writeback_running": "1",
        "device_stat": {"read_sectors": 1, "write_sectors": 2},
        "_core_available": True,
    })
    smart = {
        **bcache_monitor.base_ssd_health(["sda"]),
        "life_remaining_percent": 47,
        "temperature_c": 36,
        "tbw_bytes": 20 * 1024 ** 4,
    }
    report = bcache_monitor.health_report(
        state.current_eff,
        details,
        smart,
        state.current_hps,
        state.current_mps,
    )
    recs = bcache_monitor.recommendations(state.current_eff, details, smart)
    flush_seconds = bcache_monitor.estimate_flush_seconds(
        details["dirty_bytes"],
        details["writeback_rate_bytes"],
    )
    return state, details, smart, report, recs, flush_seconds


@pytest.mark.parametrize("height,width", [(12, 50), (24, 63), (38, 98), (62, 190)])
def test_render_dashboard_keeps_core_metrics_in_bounds_at_common_sizes(height, width):
    screen = FakeScreen(height=height, width=width)
    state, details, smart, report, recs, flush_seconds = _dashboard_fixture()

    bcache_monitor.render_dashboard(
        screen,
        state,
        details,
        smart,
        report,
        recs,
        flush_seconds,
    )

    rendered = "\n".join(text for _, _, text, _ in screen.draws)
    assert "EFF 72.7%" in rendered
    assert "LIVE T 7/s" in rendered
    assert "Modus writeback" in rendered
    assert "CACHE-WERTE" in rendered
    assert any(row == height - 1 for row, _, _, _ in screen.draws)
    assert all(0 <= row < height and 0 <= col < width for row, col, _, _ in screen.draws)
    assert all(col + len(text) <= width for _, col, text, _ in screen.draws)


def test_split_dashboard_uses_side_panel_and_still_shows_containers():
    screen = FakeScreen(height=38, width=98)
    state, details, smart, report, recs, flush_seconds = _dashboard_fixture()

    bcache_monitor.render_dashboard(
        screen,
        state,
        details,
        smart,
        report,
        recs,
        flush_seconds,
    )

    layout = bcache_monitor.dashboard_layout(38, 98)
    assert any("CACHE-WERTE" in text and col == layout.side_x for _, col, text, _ in screen.draws)
    assert any("nextcloud_app" in text for _, _, text, _ in screen.draws)


@pytest.mark.parametrize("height,width", [(38, 98), (62, 190)])
def test_larger_dashboards_keep_eight_ranked_containers_visible(height, width):
    screen = FakeScreen(height=height, width=width)
    state, details, smart, report, recs, flush_seconds = _dashboard_fixture()
    original_rows = state.docker_cache * 4
    state.docker_cache = [
        (f"container-{index}", cpu, mem, mem_raw, io_raw)
        for index, (_name, cpu, mem, mem_raw, io_raw) in enumerate(original_rows, 1)
    ]
    state.docker_io_rates = {
        row[0]: (index * 1024, index * 2048)
        for index, row in enumerate(state.docker_cache, 1)
    }
    state.selected_containers = [row[0] for row in state.docker_cache]

    bcache_monitor.render_dashboard(
        screen,
        state,
        details,
        smart,
        report,
        recs,
        flush_seconds,
    )

    rendered = "\n".join(text for _, _, text, _ in screen.draws)
    assert all(f"container-{index}" in rendered for index in range(1, 9))
    assert any("DIAGNOSE / HINWEIS" in text for _, _, text, _ in screen.draws) == (height >= 62)


def test_compact_dashboard_prioritizes_top_io_containers_and_reserves_notice_row():
    screen = FakeScreen(height=24, width=63)
    state, details, smart, report, recs, flush_seconds = _dashboard_fixture()
    state.config_notice = "Configuration saved."
    original_rows = state.docker_cache * 4
    state.docker_cache = [
        (f"container-{index}", cpu, mem, mem_raw, io_raw)
        for index, (_name, cpu, mem, mem_raw, io_raw) in enumerate(original_rows, 1)
    ]
    state.docker_io_rates = {
        row[0]: (index * 1024, index * 2048)
        for index, row in enumerate(state.docker_cache, 1)
    }

    bcache_monitor.render_dashboard(
        screen,
        state,
        details,
        smart,
        report,
        recs,
        flush_seconds,
    )

    rendered = "\n".join(text for _, _, text, _ in screen.draws)
    assert "container-8" in rendered
    assert "container-7" in rendered
    assert "container-1" not in rendered
    assert {
        text for row, _, text, _ in screen.draws if row == screen.height - 2
    } == {"Configuration saved."}


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


def test_calculate_device_rates_rejects_counter_reset():
    prev = ({"read_sectors": 100, "write_sectors": 200}, 1.0)
    current = {"read_sectors": 10, "write_sectors": 20}

    assert bcache_monitor.calculate_device_rates(prev, current, 2.0) == (None, None)


def test_average_recent_io_rates_uses_recent_window():
    history = bcache_monitor.deque([
        (1.0, 100.0, 200.0),
        (8.0, 300.0, 600.0),
        (10.0, 0.0, 0.0),
    ])

    read_rate, write_rate = bcache_monitor.average_recent_io_rates(history, 10.0, window_seconds=5.0)

    assert read_rate == 150.0
    assert write_rate == 300.0
    assert list(history) == [(8.0, 300.0, 600.0), (10.0, 0.0, 0.0)]


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


def test_parse_smart_health_text_parses_ata_table_without_inventing_wear():
    raw = """
177 Wear_Leveling_Count     0x0013   091   091   000    Pre-fail  Always       -       123
194 Temperature_Celsius     0x0022   068   060   000    Old_age   Always       -       32
241 Total_LBAs_Written      0x0032   099   099   000    Old_age   Always       -       123456
"""
    health = bcache_monitor.parse_smart_health_text(raw)

    assert health["life_remaining_percent"] is None
    assert health["temperature_c"] == 32
    assert health["tbw_bytes"] == 123456 * 512


def test_parse_smart_health_json_parses_reliable_ata_fields():
    raw = """
{
  "temperature": {"current": 41},
  "logical_block_size": 4096,
  "ata_smart_attributes": {
    "table": [
      {"name": "Media_Wearout_Indicator", "value": 87, "raw": {"value": 123}},
      {"name": "Total_LBAs_Written", "value": 99, "raw": {"value": 1000}}
    ]
  }
}
"""
    health = bcache_monitor.parse_smart_health_json(raw)

    assert health["life_remaining_percent"] == 87
    assert health["temperature_c"] == 41
    assert health["tbw_bytes"] == 1000 * 4096


def test_smartctl_warning_exit_status_still_allows_metrics():
    result = {"returncode": 8, "stdout": "SMART warning", "status": "ERR:8"}

    assert bcache_monitor._smartctl_result_usable(result) is True


def test_read_ssd_health_aggregates_worst_temperature_and_life(monkeypatch):
    values = {
        "sda": {
            **bcache_monitor.empty_ssd_health_values(),
            "device": "/dev/sda",
            "source": "smartctl-json",
            "life_remaining_percent": 80,
            "temperature_c": 40,
            "tbw_bytes": 100,
            "attempts": [],
        },
        "sdb": {
            **bcache_monitor.empty_ssd_health_values(),
            "device": "/dev/sdb",
            "source": "smartctl-json",
            "life_remaining_percent": 65,
            "temperature_c": 52,
            "tbw_bytes": 200,
            "attempts": [],
        },
    }
    monkeypatch.setattr(bcache_monitor, "_read_one_ssd_health", lambda name: values[name])

    health = bcache_monitor.read_ssd_health(["sda", "sdb"])

    assert health["life_remaining_percent"] == 65
    assert health["temperature_c"] == 52
    assert health["tbw_bytes"] == 300


def test_smart_dependency_hint_recommends_nvme_cli_for_nvme_cache():
    assert "nvme-cli" in bcache_monitor.smart_dependency_hint(["nvme0n1"], ["nvme"], "NOT INSTALLED")


def test_dependency_warnings_include_missing_docker_cli_and_ssd_hint():
    smart = bcache_monitor.base_ssd_health(["sda"], dependency_hint="Install smartmontools (smartctl) to show SATA/SAS SSD health values.")
    warnings = bcache_monitor.dependency_warnings(smart, "NOT INSTALLED")

    assert any("smartmontools" in warning for warning in warnings)
    assert any("Docker CLI" in warning for warning in warnings)


def test_config_language_sanitizes_and_translates_labels():
    cfg = bcache_monitor._sanitize_config({"language": "en", "containers": [], "bcache_device": "bcache0", "docker_enabled": False})

    assert cfg["language"] == "en"
    assert cfg["docker_enabled"] is False
    assert bcache_monitor.tr(cfg, "settings") == "SETTINGS"
    assert bcache_monitor.tr({"language": "de"}, "docker_toggle") == "Docker-Statistiken:"


def test_docker_disabled_state_skips_container_stats():
    state = bcache_monitor.AppState(config={"language": "de", "docker_enabled": False})

    assert bcache_monitor.docker_enabled(state) is False
    assert bcache_monitor.list_container_stats_for_state(state) == ([], "DEAKTIVIERT")


def test_info_lines_are_localized_to_german():
    state = bcache_monitor.AppState(config={"language": "de"})
    lines = "\n".join(bcache_monitor.info_lines(state))

    assert "KI-Hinweis" in lines
    assert "Werte auf dem Hauptbildschirm" in lines


def test_dependency_summary_includes_direct_optional_command_checks(monkeypatch):
    monkeypatch.setattr(bcache_monitor.shutil, "which", lambda command: None)

    smart = bcache_monitor.base_ssd_health(["nvme0n1"], dependency_hint=bcache_monitor.missing_dependency_hint("nvme"))
    warnings = bcache_monitor.dependency_summary_lines(smart, "OK")

    assert any("Docker CLI" in warning for warning in warnings)
    assert any("nvme-cli" in warning for warning in warnings)
    assert not any("smartmontools" in warning for warning in warnings)


def test_dependency_summary_localizes_german_hints(monkeypatch):
    monkeypatch.setattr(bcache_monitor.shutil, "which", lambda command: None)

    warnings = bcache_monitor.dependency_summary_lines({}, "NOT INSTALLED", config_or_state={"language": "de"})

    assert any("installieren" in warning for warning in warnings)
    assert any("Docker" in warning for warning in warnings)


def test_missing_value_reasons_explain_unavailable_values():
    state = bcache_monitor.AppState(config={"language": "de"})
    details = {
        "writeback_rate_bytes": None,
        "writeback_percent": None,
        "writeback_running": None,
        "cache_capacity": None,
        "cache_available_percent": None,
        "backing_size": None,
        "fs_usage": None,
        "device_stat": None,
    }
    smart = bcache_monitor.base_ssd_health([], dependency_hint="No cache device found for SSD health values.")

    reasons = bcache_monitor.missing_value_reasons(state, details, smart, state, sysfs_ok=False)

    assert any("bcache-Zähler" in reason for reason in reasons)
    assert any("WB-Ziel" in reason for reason in reasons)
    assert any("SSD-Gesundheit" in reason for reason in reasons)


def test_automatic_diagnosis_recommends_sequential_cutoff_for_low_efficiency():
    details = {"cache_available_percent": 50, "dirty_bytes": 0, "cache_mode": "[writeback]"}

    diagnosis = bcache_monitor.automatic_diagnosis([92, 88, 41], 41, 1, 10, details, {}, {})

    assert diagnosis["problem"] is True
    assert "sequential_cutoff" in diagnosis["recommendation"]


def test_health_report_suppresses_score_when_core_data_is_incomplete():
    report = bcache_monitor.health_report(None, {"_core_available": False}, {})

    assert report["score"] is None
    assert report["status"] == "DATA INCOMPLETE"


def test_docker_top_io_calculates_largest_share():
    rates = {"immich": (100, 900), "postgres": (0, 100)}

    top = bcache_monitor.docker_top_io(rates, 1)[0]

    assert top["name"] == "immich"
    assert round(top["share_percent"]) == 91


def _fake_bcache_sysfs(tmp_path, monkeypatch):
    sysroot = tmp_path / "sys"
    backing_partition = sysroot / "devices" / "pci0" / "block" / "sdb" / "sdb1"
    cache_disk = sysroot / "devices" / "pci0" / "block" / "sda"
    cache_partition = cache_disk / "sda1"
    backing_bcache = backing_partition / "bcache"
    cache_bcache = cache_partition / "bcache"
    backing_bcache.mkdir(parents=True)
    cache_bcache.mkdir(parents=True)
    (cache_partition / "partition").write_text("1\n")
    (backing_partition / "partition").write_text("1\n")

    cache_set = sysroot / "fs" / "bcache" / "test-uuid"
    cache_set.mkdir(parents=True)
    try:
        (backing_bcache / "cache").symlink_to(cache_set, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks are not available: {exc}")
    (cache_set / "cache0").symlink_to(cache_bcache, target_is_directory=True)

    block_root = sysroot / "block" / "bcache0"
    block_root.mkdir(parents=True)
    (block_root / "bcache").symlink_to(backing_bcache, target_is_directory=True)

    class_block = sysroot / "class" / "block"
    class_block.mkdir(parents=True)
    (class_block / "sda").symlink_to(cache_disk, target_is_directory=True)
    (class_block / "sda1").symlink_to(cache_partition, target_is_directory=True)
    (class_block / "sdb1").symlink_to(backing_partition, target_is_directory=True)
    bcache_class = class_block / "bcache0"
    bcache_class.mkdir()
    (bcache_class / "size").write_text("4096\n")
    (backing_partition / "stat").write_text("1 0 8 0 2 0 16 0 0 0 0\n")

    (backing_bcache / "backing_dev_name").write_text("sdb1\n")
    (backing_bcache / "dirty_data").write_text("12.0M\n")
    (backing_bcache / "cache_mode").write_text("writethrough [writeback] writearound none\n")
    (backing_bcache / "writeback_percent").write_text("10\n")
    (backing_bcache / "writeback_running").write_text("1\n")
    (backing_bcache / "writeback_rate").write_text("4.0M\n")
    stats_total = backing_bcache / "stats_total"
    stats_total.mkdir()
    (stats_total / "cache_hits").write_text("49644\n")
    (stats_total / "cache_misses").write_text("375\n")
    (cache_bcache / "bucket_size").write_text("512K\n")
    (cache_bcache / "nbuckets").write_text("100\n")
    (cache_set / "cache_available_percent").write_text("88\n")

    monkeypatch.setattr(bcache_monitor, "SYSFS_ROOT", str(sysroot))
    return block_root / "bcache"


def test_topology_resolves_partition_cache_and_physical_health_device(tmp_path, monkeypatch):
    bcache_path = _fake_bcache_sysfs(tmp_path, monkeypatch)

    topology = bcache_monitor.discover_bcache_topology("bcache0", str(bcache_path))

    assert topology.status == "ok"
    assert topology.backing_device == "sdb1"
    assert topology.cache_block_devices == ["sda1"]
    assert topology.health_devices == ["sda"]


def test_read_bcache_details_parses_writeback_bytes_and_backing_stat(tmp_path, monkeypatch):
    bcache_path = _fake_bcache_sysfs(tmp_path, monkeypatch)

    details = bcache_monitor.read_bcache_details("bcache0", str(bcache_path))

    assert details["writeback_rate_bytes"] == 4 * 1024 ** 2
    assert details["cache_capacity"] == 512 * 1024 * 100
    assert details["cache_devices"] == ["sda"]
    assert details["device_stat"] == {"read_sectors": 8, "write_sectors": 16}
    assert details["_metrics"]["writeback_rate_bytes"].status == "ok"


def test_prometheus_omits_unknown_values_and_exposes_collector_status():
    details = bcache_monitor.empty_bcache_details()
    report = {"score": None}
    smart = bcache_monitor.base_ssd_health([])

    output = bcache_monitor.prometheus_metrics(
        "bcache0",
        None,
        details,
        smart,
        report,
        {"sysfs": False, "topology": False, "smart": False},
    )

    assert "bcache_hit_ratio" not in output
    assert "bcache_dirty_bytes" not in output
    assert "bcache_cache_available_percent" not in output
    assert 'collector="sysfs"} 0' in output


def test_diagnostic_payload_has_stable_schema_and_no_smart_raw_output(tmp_path, monkeypatch):
    _fake_bcache_sysfs(tmp_path, monkeypatch)
    smart = {
        **bcache_monitor.base_ssd_health(["sda"]),
        "device": "/dev/sda",
        "source": "smartctl-json",
        "life_remaining_percent": 90,
        "temperature_c": 40,
        "tbw_bytes": 1234,
    }
    monkeypatch.setattr(bcache_monitor, "read_ssd_health", lambda _devices: smart)

    snapshot = bcache_monitor.collect_monitor_snapshot({
        "bcache_device": "bcache0",
        "containers": [],
        "language": "de",
        "docker_enabled": False,
    })
    payload = bcache_monitor.diagnostic_payload(snapshot)

    assert payload["schema_version"] == 1
    assert payload["status"] == "degraded"
    assert payload["topology"]["health_devices"] == ["sda"]
    assert "serial" not in str(payload).lower()


def test_diagnostic_payload_handles_missing_bcache_device():
    snapshot = {
        "details": bcache_monitor.empty_bcache_details(),
        "hits": None,
        "misses": None,
        "efficiency": None,
        "resolution": {"device": None, "path": None, "source": "none", "warning": "missing"},
        "smart_health": bcache_monitor.base_ssd_health([]),
        "collector_status": {"sysfs": False, "topology": False, "smart": False},
        "status": "failed",
    }

    payload = bcache_monitor.diagnostic_payload(snapshot)

    assert payload["status"] == "failed"
    assert payload["metrics"]["cache_hits"]["value"] is None


def test_update_validation_rejects_syntax_error():
    script = b'#!/usr/bin/env python3\n__version__ = "0.9.1"\nif True print("broken")\n' + b"# pad\n" * 300

    content, error = bcache_monitor.validate_update_script(script)

    assert content is None
    assert "syntax" in error


def test_self_update_uses_script_version_when_version_file_is_stale(monkeypatch, tmp_path):
    installed = tmp_path / "bcache-monitor"
    installed.write_text("#!/usr/bin/env python3\n__version__ = \"0.8.3\"\n" + "# old\n" * 300)
    installed.chmod(0o755)
    remote_script = "#!/usr/bin/env python3\n__version__ = \"0.8.4\"\n" + "# new\n" * 300
    exec_args = {}

    monkeypatch.delenv(bcache_monitor.UPDATE_FAIL_COUNT_ENV, raising=False)
    monkeypatch.delenv("BCACHE_MONITOR_UPDATED_TO", raising=False)
    monkeypatch.setattr(bcache_monitor, "__version__", "0.8.3")
    monkeypatch.setattr(bcache_monitor, "__file__", str(installed))
    monkeypatch.setattr(bcache_monitor, "read_remote_text", lambda _url: "0.8.3")
    monkeypatch.setattr(bcache_monitor, "read_remote_bytes", lambda _url: remote_script.encode("utf-8"))
    monkeypatch.setattr(bcache_monitor.time, "sleep", lambda _seconds: None)

    def fake_execv(executable, args):
        exec_args["executable"] = executable
        exec_args["args"] = args
        raise SystemExit

    monkeypatch.setattr(bcache_monitor.os, "execv", fake_execv)

    try:
        bcache_monitor.self_update_if_needed()
    except SystemExit:
        pass

    assert installed.read_text() == remote_script
    assert bcache_monitor.os.environ["BCACHE_MONITOR_UPDATED_FROM"] == "0.8.3"
    assert bcache_monitor.os.environ["BCACHE_MONITOR_UPDATED_TO"] == "0.8.4"
    assert exec_args["args"][1] == str(installed)
