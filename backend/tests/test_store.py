"""JsonStore files must be readable by the non-root container user (mkstemp makes 0600 by default)."""
import stat

from app.ai.store import JsonStore


def test_saved_cache_is_world_readable_and_reloads(tmp_path):
    s = JsonStore(tmp_path / "c.json")
    s.put("k", {"input_hash": "h", "v": 1})
    assert s.save()
    mode = stat.S_IMODE((tmp_path / "c.json").stat().st_mode)
    assert mode & 0o044 == 0o044, oct(mode)  # group and other can read
    assert JsonStore(tmp_path / "c.json").get("k", "h") == {"input_hash": "h", "v": 1}
