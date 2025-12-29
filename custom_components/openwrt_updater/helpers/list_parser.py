import logging
from importlib import resources
from homeassistant.core import HomeAssistant
from .profiles import OpenWRTPackageList
from ..presets.const import PRESETS_DIR

_LOGGER = logging.getLogger(__name__)


def _read_preset_lists_sync(hass: HomeAssistant) -> dict[str, dict[str, str]]:
    """Read preset lists."""
    lists: dict[str, dict[str, dir]] = {}
    lists_dir = resources.files(PRESETS_DIR) / "lists"

    for lst in lists_dir.iterdir():
        include: set[str] = set()
        exclude: set[str] = set()
        if lst.is_file():
            list_name = lst.stem  # .name maybe?
            _LOGGER.debug("Parse list: %s", list_name)
            list_raw = lst.read_text(encoding="utf-8")
            lists[list_name] = {}
            pack_list = OpenWRTPackageList(hass, list_name)

            for line in list_raw.splitlines():
                package = line.strip()

                if not package or package.startswith("#"):
                    continue
                if len(package) == 1:
                    continue

                if "#" in package:
                    package = package.split("#", 1)[0].strip()

                _LOGGER.debug("  Package: %s", package)
                if package[0] == "-":
                    exclude.add(package[1:])
                else:
                    include.add(package)

            pack_list.mod_packages(" ".join(include), " ".join(exclude))
            lists[list_name] = dict(pack_list.packages)
    return lists


async def read_preset_lists(hass: HomeAssistant) -> dict:
    """Non-blocking read preset lists."""
    return await hass.async_add_executor_job(_read_preset_lists_sync, hass)
