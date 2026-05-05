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


def test_info_lines_include_bugreport_and_ai_notice():
    lines = "\n".join(bcache_monitor.info_lines(None))
    assert "KI-Unterstützung" in lines
    assert "Linux-Bcache-Monitor/issues" in lines
