import logging
from importlib import resources
from homeassistant.core import HomeAssistant

_lists_DIR = "custom_components.openwrt_updater.presets"
_LOGGER = logging.getLogger(__name__)

def _read_preset_lists_sync() -> dict[str, dict[str, str]]:
    """Read preset lists."""
    lists: dict[str, dict[str, dir]] = {}
    lists_dir = resources.files(_lists_DIR) / "lists"

    for lst in lists_dir.iterdir():
        include: list[str] = []
        exclude: list[str] = []
        if lst.is_file():
            list_name = lst.stem # .name maybe?
            _LOGGER.debug("Parse list: %s", list_name)
            list_raw = lst.read_text(encoding="utf-8")
            lists[list_name] = {}

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
                    exclude.append(package[1:])
                    lists[list_name]["exclude"] = package[1:]
                else:
                    include.append(package)
                    lists[list_name]["include"] = package
            

            lists[list_name] = {"include": " ".join(include), "exclude": " ".join(exclude)}
            #_LOGGER.debug("Lists are: %s", lists)
    return lists

async def read_preset_lists(hass: HomeAssistant) -> dict:
    """Non-blocking read preset lists."""
    return await hass.async_add_executor_job(_read_preset_lists_sync)