"""Options flow for OpenWRT Updater: add devices via UI."""

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .presets.const import DOMAIN
from .helpers.helpers import (
    build_device_schema,
    build_global_options_schema,
    upsert_device,
)
from .helpers.profiles import OpenWRTPackageList, OpenWRTProfile

_LOGGER = logging.getLogger(__name__)


class OpenWRTOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for an existing config entry."""

    def __init__(self) -> None:
        """Initialize Options Flow handler."""
        # Current entry state
        self._data = {}
        self._devices = {}
        self._list_name: str | None = None
        self._lists: dict[str, dict] = {}
        self._lists_to_delete: list[str] | None = None
        self._profile_name: str | None = None
        self._profiles: dict[str, list] = {}

    def get_fresh_data(self):
        """Get fresh data all the time."""
        return dict(self.hass.data[DOMAIN]["config"])

    async def async_step_init(self, user_input=None):
        """Entry point."""
        # _LOGGER.debug("Options flow: init")
        self._data = dict(self.config_entry.data)
        self._devices = dict(self.config_entry.options.get("devices", {}))
        if self.config_entry.unique_id == "__global__":
            self._lists = dict(self.config_entry.options.get("lists", {}))
            self._profiles = dict(
                self.config_entry.options.get("profiles", {}))
            return await self.async_step_global_menu()
        return await self.async_step_device_menu()

    async def async_step_global_menu(self, user_input=None):
        """Global entity menu."""
        return self.async_show_menu(
            step_id="global_menu",
            menu_options=["global", "lists_menu", "profiles_menu"],
        )

    async def async_step_device_menu(self, user_input=None):
        """Device enity menu."""
        if not self._devices:
            return await self.async_step_add_device()
        return self.async_show_menu(
            step_id="device_menu",
            menu_options=["device_add", "device_remove"],
        )

    async def async_step_global(self, user_input=None):
        """Global options step."""
        if user_input is not None:
            _LOGGER.debug("Saving data to global entry: %s", user_input)
            options = dict(self.config_entry.options)
            options.update(user_input)
            return self.async_create_entry(title="", data=options)
        saved_options = self.get_fresh_data()
        schema = await self.hass.async_add_executor_job(
            build_global_options_schema, self.hass, saved_options
        )
        return self.async_show_form(step_id="global", data_schema=schema)

    async def async_step_lists_menu(self, user_input=None):
        """Global lists menu."""
        return self.async_show_menu(
            step_id="lists_menu",
            menu_options=["list_add", "list_edit_pick", "lists_delete_pick"],
        )

    async def async_step_list_add(self, user_input=None):
        """Add new package list."""
        errors: dict[str, str] = {}

        if user_input is not None:
            list_name = user_input.get("list_id", "").strip()
            if list_name in self._lists:
                errors["list_id"] = "list_id_exists"
            else:
                pack_list = OpenWRTPackageList(self.hass, list_name)
                pack_list.add_packages(user_input.get(
                    "include", ""), user_input("exclude", ""))
                options = dict(self.config_entry.options)
                options["lists"] = pack_list.packages
                if user_input["add_another"]:
                    return await self.async_step_list_add()
                return self.async_create_entry(title="", data=options)

        schema = vol.Schema(
            {
                vol.Required("list_id"): str,
                vol.Optional("include", default=""): str,
                vol.Optional("exclude", default=""): str,
                vol.Optional("add_another", default=False): bool,
            }
        )
        return self.async_show_form(
            step_id="list_add", data_schema=schema, errors=errors
        )

    async def async_step_list_edit_pick(self, user_input=None):
        """Edit package list."""
        options = dict(self.config_entry.options)
        pack_lists = options.get("lists", {})

        if not pack_lists:
            return self.async_abort(reason="no_lists")

        if user_input is not None:
            self._list_name = user_input["list_id"]
            return await self.async_step_list_edit()

        return self.async_show_form(
            step_id="list_edit_pick",
            data_schema=vol.Schema(
                {vol.Required("list_id"): vol.In(sorted(pack_lists.keys()))}
            ),
        )

    async def async_step_list_edit(self, user_input=None):
        """Edit selected list."""
        options = dict(self.config_entry.options)
        # pack_lists = dict(options.get("lists", {}))

        # if not pack_lists:
        #    return self.async_abort(reason="no_lists")
        # if not self._list_name or self._list_name not in pack_lists:
        #    return self.async_abort(reason="list_not_found")

        current = OpenWRTPackageList(self.hass, self._list_name)

        if user_input is not None:
            current.mod_packages(user_input.get(
                "include", ""), user_input.get("exclude", ""))
            options["lists"][self._list_name].update(current.packages)
            self._lists = options["lists"]
            _LOGGER.debug("Saved packages: %s", current.packages)
            return self.async_create_entry(title="", data=options)

        schema = vol.Schema(
            {
                vol.Optional(
                    "include",
                    description={"suggested_value": current.include_str},
                ): str,
                vol.Optional(
                    "exclude",
                    description={"suggested_value": current.exclude_str},
                ): str,
            }
        )

        return self.async_show_form(step_id="list_edit", data_schema=schema)

    async def async_step_lists_delete_pick(self, user_input=None):
        """Pick list to delete."""
        options = dict(self.config_entry.options)
        pack_lists = options.get("lists", {})

        if not pack_lists:
            return self.async_abort(reason="no_lists")

        if user_input is not None:
            selected = user_input.get("lists", [])
            to_delete = list(selected)

            for list_id in to_delete:
                pack_lists.pop(list_id, None)

            options["lists"] = pack_lists
            return self.async_create_entry(title="", data=options)

        schema = vol.Schema(
            {
                vol.Required("lists"): cv.multi_select(
                    {list_id: list_id for list_id in sorted(pack_lists.keys())}
                )
            }
        )
        return self.async_show_form(step_id="lists_delete_pick", data_schema=schema)

    async def async_step_add_device(self, user_input=None):
        """Add device step."""
        if user_input is not None:
            upsert_device(self._devices, user_input)

            if user_input.get("add_another"):
                return await self.async_step_add_device()

            return self.async_create_entry(
                title="",
                data={"devices": self._devices},
            )

        defaults: dict = {"ip": f"{self._data.get('place_ipmask', '')}."}
        schema = await self.hass.async_add_executor_job(
            build_device_schema, self.hass, defaults
        )
        return self.async_show_form(step_id="add_device", data_schema=schema)

    async def async_step_remove_device(self, user_input=None):
        """Step to choose device for removal."""
        if not self._devices:
            return self.async_abort(reason="no_devices")

        if user_input is not None:
            remove_ip = user_input["ip"]
            _LOGGER.debug("Remove %s", remove_ip)
            self._devices.pop(remove_ip, None)

            new_options = dict(self.config_entry.options)
            new_options["devices"] = self._devices

            device_registry = dr.async_get(self.hass)
            device_entry = device_registry.async_get_device(
                identifiers={(DOMAIN, remove_ip)}
            )
            if device_entry is not None:
                device_registry.async_remove_device(device_entry.id)

            return self.async_create_entry(
                title="",
                data=new_options,
            )

        return self.async_show_form(
            step_id="remove_device",
            data_schema=vol.Schema(
                {vol.Required("ip"): vol.In(list(self._devices.keys()))}
            ),
        )

    async def async_step_profiles_menu(self, user_input=None):
        """Global profiles menu."""
        return self.async_show_menu(
            step_id="profiles_menu",
            menu_options=["profile_add",
                          "profile_edit_pick", "profiles_delete_pick"],
        )

    async def async_step_profile_add(self, user_input=None):
        """Add new profile."""
        errors: dict[str, str] = {}

        options = dict(self.config_entry.options)
        profiles = dict(options.get("profiles", {}))
        pack_lists = dict(options.get("lists", {}))

        if not pack_lists:
            return self.async_abort(reason="no_lists")

        if user_input is not None:
            profile_name = user_input["profile_name"].strip()
            if profile_name in profiles:
                errors["profile_name"] = "profile_exists"
            else:
                # profiles[profile_name] = {"lists": list(selected_lists)}
                profile = OpenWRTProfile(self.hass, profile_name)
                profile.mod_profile(user_input.get("lists", set()), user_input.get(
                    "extra_include", ""), user_input.get("extra_exclude", ""))
                options["profiles"][profile_name] = {
                    "lists": profile.lists, "extra_include": profile.extra_include, "extra_exclude": profile.extra_exclude}
                if user_input["add_another"]:
                    return await self.async_step_profile_add()
                return self.async_create_entry(title="", data=options)

        schema = vol.Schema(
            {
                vol.Required("profile_name"): str,
                vol.Required("lists"): cv.multi_select(
                    {list_id: list_id for list_id in sorted(pack_lists.keys())}
                ),
                vol.Optional("extra_include", default=""): str,
                vol.Optional("extra_exclude", default=""): str,
                vol.Optional("add_another", default=False): bool,
            }
        )
        return self.async_show_form(
            step_id="profile_add", data_schema=schema, errors=errors
        )

    async def async_step_profile_edit_pick(self, user_input=None):
        """Pick profile to edit."""
        options = dict(self.config_entry.options)
        profiles = dict(options.get("profiles", {}))

        if not profiles:
            return self.async_abort(reason="no_profiles")

        if user_input is not None:
            self._profile_name = user_input["profile_name"]
            return await self.async_step_profile_edit()

        return self.async_show_form(
            step_id="profile_edit_pick",
            data_schema=vol.Schema(
                {vol.Required("profile_name"): vol.In(sorted(profiles.keys()))}
            ),
        )

    async def async_step_profile_edit(self, user_input=None):
        """Edit selected profile."""
        options = dict(self.config_entry.options)
        profiles = dict(options.get("profiles", {}))
        lists = dict(options.get("lists", {}))

        if not lists:
            return self.async_abort(reason="no_lists")

        # profile_name = self._profile_name
        # if not profile_name or profile_name not in profiles:
        #    return self.async_abort(reason="profile_not_found")

        current = OpenWRTProfile(self.hass, self._profile_name)

        if user_input is not None:
            current.mod_profile(
                set(user_input.get("lists", set())),
                user_input.get("extra_include", ""),
                user_input.get("extra_exclude", "")
            )
            profiles[self._profile_name] = dict(current.profile)
            options["profiles"] = profiles
            return self.async_create_entry(title="", data=options)

        schema = vol.Schema(
            {
                vol.Optional(
                    "lists",
                    description={"suggested_value": list(current.lists)},
                ): cv.multi_select(
                    {list_id: list_id for list_id in sorted(lists.keys())}
                ),
                vol.Optional("extra_include", description={"suggested_value": current.extra_include_str}, ): str,
                vol.Optional("extra_exclude", description={"suggested_value": current.extra_exclude_str}, ): str,
            }
        )
        return self.async_show_form(step_id="profile_edit", data_schema=schema)

    async def async_step_profiles_delete_pick(self, user_input=None):
        """Pick profiles to delete (bulk)."""
        options = dict(self.config_entry.options)
        profiles = dict(options.get("profiles", {}))

        if not profiles:
            return self.async_abort(reason="no_profiles")

        if user_input is not None:
            selected = user_input.get("profiles") or []
            for profile_name in selected:
                profiles.pop(profile_name, None)

            options["profiles"] = profiles
            return self.async_create_entry(title="", data=options)

        schema = vol.Schema(
            {
                vol.Required("profiles"): cv.multi_select(
                    {profile_name: profile_name for profile_name in sorted(
                        profiles.keys())}
                )
            }
        )
        return self.async_show_form(step_id="profiles_delete_pick", data_schema=schema)
