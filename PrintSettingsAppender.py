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
    """Adds all .appendable.json files contained in plugins to cura"""

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
        self._show_example = not self._show_example
        self._prefrences.setValue("printsettingappender/show_example", self._show_example)
        Logger.debug(f"Show example is now {self._show_example}")

    def _on_plugins_loaded(self) -> None:

        # Search all plugins for .appendable.json files
        plugin_folders = Path(__file__).parents[2]
        for plugin_folder in plugin_folders.iterdir():
            plugin = plugin_folder.joinpath(plugin_folder.name)
            for settings_file in plugin.glob("*.appendable.json"):
                if settings_file.name == "example_settings.appendable.json" and not self._show_example:
                    continue
                Logger.debug(f"Settings : {settings_file}")
                self.definition_file_paths.append(settings_file)

        # Get all settings and setting relations
        for definition_file_path in self.definition_file_paths:
            settings: dict[str, dict[str, Any]] = {}

            with definition_file_path.open("r") as settings_def:
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
            Logger.debug(f"Appending settings to Machine {container.getName()}")

            # Append all plugin settings
            for settings in self.all_settings:
                container.appendAdditionalSettingDefinitions(settings)

            # Append all setting relations
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
        if "enabled" in setting:
            ##> Setting depends on another setting for visibility
            requirements = setting["enabled"]
            requirements_list = requirements.replace(" and ", "|").replace(" or ", "|").split("|") # type: ignore[union-attr]
            for index, requirement in enumerate(requirements_list):
                requirements_list[index] = requirement.removeprefix("not ")
            if not "False" in requirements:
                self.relations.append((key, requirements_list))

        if "children" in setting:
            ##> Setting has child settings
            for child_key, child in setting["children"].items(): # type: ignore[union-attr]
                self._get_all_children(child_key, child)
