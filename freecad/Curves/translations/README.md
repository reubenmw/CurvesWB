# Translations for CurvesWB

This folder contains translation files for the CurvesWB FreeCAD workbench, particularly the TrimFaceDialog feature.

## Overview

The translation system uses Qt's translation framework, which is integrated with FreeCAD. Translatable strings are marked in the Python code using `FreeCAD.Qt.translate()`.

## File Structure

```
translations/
├── README.md                    # This file
├── update_translations.py       # Script to generate/update .ts files
├── update_translations.bat      # Windows batch script
├── TrimFaceDialog.ts           # Master translation template (generated)
├── TrimFaceDialog_de.ts        # German translation (example)
├── TrimFaceDialog_fr.ts        # French translation (example)
└── *.qm                        # Compiled translations (auto-generated)
```

## For Developers: Adding New Translatable Strings

When adding new user-facing text to the code:

1. Import the translate function at the top of your file:
```python
translate = FreeCAD.Qt.translate
```

2. Wrap all user-facing strings:
```python
# Bad - not translatable
self.status_label.setText("Select an edge")

# Good - translatable
self.status_label.setText(translate('TrimFaceDialog', 'Select an edge'))
```

3. For strings with parameters, use `.format()`:
```python
message = translate('TrimFaceDialog', '{0} edges selected').format(count)
```

4. The first parameter (`'TrimFaceDialog'`) is the context - keep it consistent within a module.

5. After adding strings, regenerate the translation files:
```bash
python update_translations.py
# or on Windows:
update_translations.bat
```

## For Translators: Creating a New Translation

### Step 1: Get the Template

Get the master template file: `TrimFaceDialog.ts`

### Step 2: Create Language File

Copy the template and rename it with the appropriate language code:
- German: `TrimFaceDialog_de.ts`
- French: `TrimFaceDialog_fr.ts`
- Spanish: `TrimFaceDialog_es.ts`
- Japanese: `TrimFaceDialog_ja.ts`
- etc.

See [ISO 639-1 language codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes).

### Step 3: Translate

You can translate the `.ts` file using:

1. **Qt Linguist** (recommended - GUI tool):
   - Download from Qt website
   - Open the `.ts` file
   - Translate each string in the visual editor
   - Save when done

2. **Text editor** (for simple translations):
   - Open the `.ts` file in any text editor
   - Find blocks like:
   ```xml
   <message>
       <source>Select an edge</source>
       <translation type="unfinished"></translation>
   </message>
   ```
   - Fill in the translation:
   ```xml
   <message>
       <source>Select an edge</source>
       <translation>Kante auswählen</translation>
   </message>
   ```

### Step 4: Compile

Compile the translation file to `.qm` format:
```bash
lrelease TrimFaceDialog_de.ts
```

This creates `TrimFaceDialog_de.qm`, which FreeCAD will load automatically.

### Step 5: Test

1. Copy the `.qm` file to this `translations/` folder
2. Restart FreeCAD
3. Go to Edit → Preferences → General → Language
4. Select your language
5. Restart FreeCAD
6. Test the TrimFaceDialog feature

## Required Tools

### For Developers (generating .ts files):

- **lupdate** - Extracts strings from .ui files
- **pylupdate5/6** - Extracts strings from .py files
- **lconvert** - Merges translation files
- **lrelease** - Compiles .ts to .qm

Installation:
- **Ubuntu/Debian**: `sudo apt-get install qttools5-dev-tools python3-pyqt5.qttranslations`
- **Fedora**: `sudo dnf install qt5-linguist python3-qt5`
- **Windows**: Install Qt SDK and add `bin/` to PATH
- **macOS**: `brew install qt5` and add to PATH

### For Translators (translating):

- **Qt Linguist** (optional but recommended)
- **lrelease** - To compile your translations

Installation:
- Same as above, or download Qt Linguist standalone

## Translation Workflow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Developer adds translate() calls to source code     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Run update_translations.py to generate .ts template │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Send TrimFaceDialog.ts to translators               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Translators create TrimFaceDialog_XX.ts files      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Compile with lrelease to create .qm files          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 6. FreeCAD automatically loads .qm files from this dir │
└─────────────────────────────────────────────────────────┘
```

## Supported Languages

Any language supported by FreeCAD can be added. Common ones include:

- German (de)
- French (fr)
- Spanish (es)
- Italian (it)
- Portuguese (pt)
- Portuguese Brazil (pt-BR)
- Russian (ru)
- Chinese Simplified (zh-CN)
- Chinese Traditional (zh-TW)
- Japanese (ja)
- Korean (ko)
- Polish (pl)
- Dutch (nl)
- Swedish (sv)
- Czech (cs)
- Turkish (tr)

## Best Practices

### For Developers:

1. **Keep strings short and clear** - Easier to translate
2. **Use context consistently** - Same context for related strings
3. **Avoid concatenation** - Use format strings instead:
   ```python
   # Bad - hard to translate
   message = translate('TrimFaceDialog', 'Selected') + " " + str(count) + " " + translate('TrimFaceDialog', 'edges')

   # Good - translator sees full sentence
   message = translate('TrimFaceDialog', 'Selected {0} edges').format(count)
   ```
4. **Provide comments for complex strings**:
   ```python
   # QT_TRANSLATE_NOOP context for translator comments
   ```
5. **Don't translate technical terms** - Keep FreeCAD-specific terms in English
6. **Update .ts files regularly** - Run update script before each release

### For Translators:

1. **Keep formatting** - Preserve {0}, {1} placeholders
2. **Maintain capitalization style** - Match the original
3. **Test in context** - See how it looks in the UI
4. **Use consistent terminology** - Match FreeCAD's standard translations
5. **Ask if unclear** - Context matters for accurate translation

## Contributing Translations

If you've created a translation:

1. Fork the repository
2. Add your `.ts` and `.qm` files to this folder
3. Test thoroughly in FreeCAD
4. Submit a pull request
5. Include screenshots showing the translated UI

## Support

- FreeCAD Translation Wiki: https://wiki.freecad.org/Translating
- FreeCAD Forum Translation Section: https://forum.freecad.org/
- Issues: https://github.com/tomate44/CurvesWB/issues

## License

Translation files are licensed under the same license as CurvesWB (LGPL 2.1).
