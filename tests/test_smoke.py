from importlib.machinery import SourceFileLoader
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "bcache-monitor"
bcache_monitor = SourceFileLoader("bcache_monitor", str(module_path)).load_module()


def test_version_string_validation_accepts_numeric_versions():
    assert bcache_monitor.is_valid_version_string("1.2.3")


def test_parse_sysfs_size_bytes_handles_mib_suffix():
    assert bcache_monitor.parse_sysfs_size_bytes("12MiB") == 12 * 1024 * 1024
