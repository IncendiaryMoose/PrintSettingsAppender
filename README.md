# PrintSettingsAppender
A cura plugin that adds settings from other plugins into the settings menu. That is any files in a plugin that end with ".appendable.json". See example_settings.appendable.json for an example of some basic settings.
Click the toggle in the extension menu to make the example settings show up in cura (Requires a restart to take effect).

Some rules:
- All settings should start with their plugin name to prevent conflicts with other settings and to improve readability.
- All settings must be inside a category. This can be a copy of an existing category, in which case the settings inside will be added to the category, or it can be a new category.
- Settings files should not change after cura has finished loading plugins (Emitted pluginsLoaded signal). In most cases settings files should never change after starting cura, but if for some reason they have to, it must be before the pluginsLoaded signal in order for the changes to show up in cura.

For a complete list of existing settings and how they were implemented in cura see https://github.com/Ultimaker/Cura/blob/main/resources/definitions/fdmextruder.def.json and https://github.com/Ultimaker/Cura/blob/main/resources/definitions/fdmprinter.def.json