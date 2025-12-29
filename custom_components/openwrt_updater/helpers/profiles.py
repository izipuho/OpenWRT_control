import logging
from homeassistant.core import HomeAssistant
from ..presets.const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _stringify_set(in_set: set[str]) -> str:
    """Stringify set with " " delimeter."""
    return " ".join(sorted(in_set))


class OpenWRTPackageList():
    """List of OpenWRT packages."""

    def __init__(self, hass: HomeAssistant, list_name: str) -> None:
        """Initialize list class."""
        self.hass = hass
        self.list_name = list_name
        self.include: set[str] = set()
        self.exclude: set[str] = set()
        self.get_packages()

    @property
    def include_str(self) -> str:
        """Stringify include set with " " delimeter."""
        if not self.include:
            return ""
        return _stringify_set(self.include)

    @property
    def exclude_str(self) -> str:
        """Stringify exclude set with " " delimeter."""
        if not self.exclude:
            return ""
        return _stringify_set(self.exclude)

    @property
    def packages(self) -> dict[str, set]:
        """Form packages dict for list."""
        return {"include": self.include, "exclude": self.exclude}

    def get_packages(self) -> None:
        """Get list from runtime."""
        packages = dict(self.hass.data[DOMAIN].get(
            "lists", {}).get(self.list_name, {}))
        _LOGGER.debug("Packages for %s: %s", self.list_name, packages)
        if packages:
            self.include = set(packages["include"])
            self.exclude = set(packages["exclude"])

    def mod_packages(self, include: str, exclude: str = "") -> None:
        """Manage packages fom list. Add or remove."""
        _include_set = set()
        _exclude_set = set()
        _LOGGER.debug("OLD:\nIncluded: %s\nExcluded: %s",
                      self.include, self.exclude)
        for pkg in include.strip().split(" "):
            _include_set.add(pkg)
        for pkg in exclude.strip().split(" "):
            _exclude_set.add(pkg)
        _LOGGER.debug("Including: %s;\n Excluding: %s",
                      _include_set, _exclude_set)
        self.include = set(_include_set)
        self.exclude = set(_exclude_set)


class OpenWRTProfile():
    """Profiles for OpenWRT device defining packages to build FW."""

    def __init__(self, hass: HomeAssistant, profile_name: str) -> None:
        """Initialize profile."""
        self.hass = hass
        self.profile_name = profile_name
        self.lists: set[str] = set()
        self.extra_include: set[str] = set()
        self.extra_exclude: set[str] = set()
        self.files: set[str] = set()
        self.get_profile()

    @property
    def profile(self) -> dict:
        """Gather profile."""
        return {
            "lists": list(self.lists),
            "extra_include": list(self.extra_include),
            "extra_exclude": list(self.extra_exclude),
            "files": list(self.files)}

    @property
    def extra_include_str(self) -> str:
        """Stringify include set with " " delimeter."""
        if not self.extra_include:
            return ""
        return _stringify_set(self.extra_include)

    @property
    def extra_exclude_str(self) -> str:
        """Stringify exclude set with " " delimeter."""
        if not self.extra_exclude:
            return ""
        return _stringify_set(self.extra_exclude)

    def get_profile(self):
        """Get profile from the runtime."""
        profile = self.hass.data[DOMAIN].get(
            "profiles", {}).get(self.profile_name, {})
        if profile:
            _LOGGER.debug("Profile %s is: %s", self.profile_name, profile)
            self.lists = profile.get("lists", set())
            self.extra_include = profile.get("extra_include", set())
            self.extra_exclude = profile.get("extra_exclude", set())
            self.files = profile.get("files", set())

    def mod_profile(self, lists: list[str], extra_include: str = "", extra_exclude: str = "", files: list[str] = []) -> None:
        """Add lists and extras to profile."""
        _include_set = set()
        _exclude_set = set()
        _LOGGER.debug("\nOLD:\n\tLists: %s\n\tIncl: %s\n\tExcl: %s",
                      self.lists, self.extra_include, self.extra_exclude)
        for pkg in extra_include.strip().split(" "):
            _include_set.add(pkg)
        for pkg in extra_exclude.strip().split(" "):
            _exclude_set.add(pkg)
        _LOGGER.debug("\nNEW:\n\tLists: %s\n\tIncl: %s\n\tExcl: %s",
                      lists, _include_set, _exclude_set)
        self.lists = set(lists)
        self.extra_include = set(_include_set)
        self.extra_exclude = set(_exclude_set)
        self.files = set(files)
