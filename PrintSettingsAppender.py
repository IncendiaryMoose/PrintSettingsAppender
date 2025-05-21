# Developed by Incendiary Moose

from pathlib import Path
from json import load as json_load
from typing import Any

from UM.Logger import Logger
from UM.Extension import Extension
from UM.Settings.ContainerRegistry import ContainerRegistry
from UM.Settings.DefinitionContainer import DefinitionContainer
from UM.Settings.SettingRelation import SettingRelation, RelationType
from cura.CuraApplication import CuraApplication


class PrintSettingsAppender(Extension):
    """Extension type plugin that adds all .appendable.json files contained in plugins to cura"""
    # Extension was chosen over AdditionalSettingsAppender in order to disable the auto-renaming of settings and to allow easier appending of setting relations.

    def __init__(self) -> None:
        super().__init__()

        self.definition_file_paths: list[Path] = []
        self.all_settings: list[dict] = []
        self.relations: list[tuple[str, list[str]]] = []
        self._prefrences = CuraApplication.getInstance().getPreferences()
        self._prefrences.addPreference("printsettingappender/show_example", False)
        self._show_example = self._prefrences.getValue("printsettingappender/show_example")
        self.addMenuItem("Show Example", self._toggle_example)

        CuraApplication.getInstance().pluginsLoaded.connect(self._on_plugins_loaded)
        ContainerRegistry.getInstance().containerLoadComplete.connect(self._on_container_loaded)

    def _toggle_example(self) -> None:
        """Toggle state of show example setting"""
        self._show_example = not self._show_example
        self._prefrences.setValue("printsettingappender/show_example", self._show_example)
        Logger.debug(f"Show example is now {self._show_example}")

    def _on_plugins_loaded(self) -> None:
        """Initialization that should take place after all plugins are loaded"""
        # Wait until plugins are loaded before reading their settings (They could modify or generate them during __init__)

        # Search all plugins for .appendable.json files
        plugin_folders = Path(__file__).parents[2]
        for plugin_folder in plugin_folders.iterdir():
            plugin = plugin_folder.joinpath(plugin_folder.name)
            for settings_file in plugin.glob("*.appendable.json"):
                if settings_file.name == "example_settings.appendable.json" and not self._show_example:
                    continue
                Logger.debug(f"Settings found for {plugin_folder.name}: {settings_file}")
                self.definition_file_paths.append(settings_file)

        # Get all settings and setting relations
        for definition_file_path in self.definition_file_paths:
            settings: dict[str, dict[str, Any]] = {}

            with definition_file_path.open("r", encoding="utf-8") as settings_def:
                settings = json_load(settings_def)

            self.all_settings.append(settings)

            for plugin_key, plugin_category in settings.items():
                Logger.debug(f"Creating settings for: {plugin_key}")
                for setting_key, setting in plugin_category["children"].items():
                    self._get_all_children(setting_key, setting)

    def _on_container_loaded(self, container_id: str):
        container = ContainerRegistry.getInstance().findContainers(id=container_id)[0]

        if isinstance(container, DefinitionContainer) and container.getMetaDataEntry("type") == "machine":
            ##> container is a machine definition container
            Logger.debug(f"Appending settings to Machine: {container.getName()}")

            # Append all plugin settings to the machine definition
            # All profiles for the machine should inherit from this, so it is only required to add them once per machine
            for settings in self.all_settings:
                container.appendAdditionalSettingDefinitions(settings)

            # Append all setting relations to the containers
            # This is required for setting visibility to update without closing the menu
            for pair in self.relations:
                try:
                    child = container.findDefinitions(key=pair[0])[0]
                    for requirement in pair[1]:
                        parent = container.findDefinitions(key=requirement)[0]
                        req_by = SettingRelation(parent, child, RelationType.RequiredByTarget, "enabled")
                        req = SettingRelation(child, parent, RelationType.RequiresTarget, "enabled")
                        parent.relations.append(req_by)
                        child.relations.append(req)
                except Exception as e:
                    Logger.error(f"Failed to append {pair} due to {e}")

    def _get_all_children(self, key: str, setting: dict[str, str | dict[str, Any]]):
        """Find all "enabled" tags in a setting and its children and add the requirements for each setting to self.relations"""

        if "enabled" in setting:
            ##> Setting depends on another setting for visibility
            # Add all settings it depends on to self.relations
            requirements = setting["enabled"]
            requirements_list = requirements.replace(" and ", "|").replace(" or ", "|").split("|")  # type: ignore[union-attr]
            for index, requirement in enumerate(requirements_list):
                requirements_list[index] = requirement.removeprefix("not ")
            if not "False" in requirements:
                self.relations.append((key, requirements_list))

        if "children" in setting:
            ##> Setting has child settings
            # Search each child
            for child_key, child in setting["children"].items():  # type: ignore[union-attr]
                self._get_all_children(child_key, child)
