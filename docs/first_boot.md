## First boot mod folder prompt

On launch, the toolkit checks the `default_mod_folder` saved in `settings.yml`. A mod folder is considered valid when it contains a `levels` directory. If no folder is saved, or the saved one is no longer valid, a prompt asks for the mod folder right after the main window opens.

### Messages

- First run (no folder saved): a welcome message asking for the mod folder.
- Saved folder no longer valid: "The saved mod folder could not be found." followed by the old path.

### Buttons

- **Use detected folder**: only shown when the default Forgotten Hope 2 installation (`C:/Program Files (x86)/Forgotten Hope 2/mods/fh2`) exists and contains `levels`. This path is only a suggestion and is never saved unless the user picks it.
- **Browse...**: opens the folder picker, which rejects folders without a `levels` directory. The prompt keeps coming back until a valid folder is chosen or the user presses later.
- **Later**: closes the prompt. It shows again on the next launch, since the toolkit cannot do anything without a mod folder.

The mod folder can still be changed afterwards with the browse mod folder button, or in the settings menu.

### Implementation

All in [main.py](../main.py):

- `FH2_DEFAULT_MOD_FOLDER`: the suggested install path. The `default_mod_folder` setting itself now defaults to an empty string.
- `is_valid_mod_folder(path)`: checks for the `levels` directory.
- `BF2ModToolkitApp.prompt_for_mod_folder()`: the prompt loop, scheduled with `QTimer.singleShot(0, ...)` so it opens over the main window.
- `BF2ModToolkitApp.set_mod_folder(path)`: sets the active folder, saves it and lists its levels. It is shared by the prompt and `select_mod_folder()`.

### Testing

To see the prompt again, rename or delete `settings.yml` next to `main.py` and restart the toolkit. To see the "could not be found" message, point `default_mod_folder` at a folder that does not exist.
