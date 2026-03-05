# Build customizations
# Change this file instead of sconstruct or manifest files, whenever possible.

from site_scons.site_tools.NVDATool.typings import AddonInfo, BrailleTables, SymbolDictionaries

# Since some strings in `addon_info` are translatable,
# we need to include them in the .po files.
# Gettext recognizes only strings given as parameters to the `_` function.
# To avoid initializing translations in this module we simply import a "fake" `_` function
# which returns whatever is given to it as an argument.
from site_scons.site_tools.NVDATool.utils import _


# Add-on information variables
addon_info = AddonInfo(
	# add-on Name/identifier, internal for NVDA
	addon_name="Open_Bible",
	# Add-on summary/title, usually the user visible name of the add-on
	# Translators: Summary/title for this add-on
	# to be shown on installation and add-on information found in add-on store
	addon_summary=_("Open Bible"),
	# Add-on description
	# Translators: Long description to be shown for this add-on on add-on information from add-on store
	addon_description=_(
		"""Este add-on permite a leitura da Bíblia Sagrada no NVDA em várias versões (arquivos JSON).
		Você pode navegar por livro, capítulo e versículo, pesquisar, favoritar, anotar e copiar/compartilhar versículos."""
	),
	# version
	addon_version="2026.03.05",
	# Brief changelog for this version
	# Translators: what's new content for the add-on version to be shown in the add-on store
	addon_changelog=_(
		"""Seguinda versão publicada.
		Apenas melhorias internas no código."""
	),
	# Author(s)
	addon_author="Leandro Souza",
	# URL for the add-on documentation support
	addon_url="https://github.com/leandro-sds/Open-Bible",
	# URL for the add-on repository where the source code can be found
	addon_sourceURL="https://github.com/leandro-sds/Open-Bible",
	# Documentation file name
	addon_docFileName="readme.html",
	# Minimum NVDA version supported (e.g. "2019.3.0", minor version is optional)
	addon_minimumNVDAVersion="2024.1",
	# Last NVDA version supported/tested (e.g. "2024.4.0", ideally more recent than minimum version)
	addon_lastTestedNVDAVersion="2025.3.3",
	# Add-on update channel (default is None, denoting stable releases, and for development releases, use "dev".)
	# Do not change unless you know what you are doing!
	addon_updateChannel=None,
	# Add-on license such as GPL 2
	addon_license="GPL-2.0-only",
	# URL for the license document the ad-on is licensed under
	addon_licenseURL=None,
)

# Define the python files that are the sources of your add-on.
# Paths are relative to the repository root. Use "/" as separator.
pythonSources: list[str] = [
	"addon/globalPlugins/open_bible.py",
]

# Files that contain strings for translation. Usually your python sources
i18nSources: list[str] = pythonSources + ["buildVars.py"]

# Files that will be ignored when building the nvda-addon file
# Paths are relative to the addon directory, not to the root directory of your addon sources.
excludedFiles: list[str] = []

# Base language for the NVDA add-on
baseLanguage: str = "pt"

# Markdown extensions for add-on documentation
markdownExtensions: list[str] = []

# Custom braille translation tables
brailleTables: BrailleTables = {}

# Custom braille translation tables: display names
brailleTableDisplayNames: dict[str, str] = {}

# Custom symbol dictionaries
symbolDictionaries: SymbolDictionaries = {}

# Custom symbol dictionaries: display names
symbolDictionaryDisplayNames: dict[str, str] = {}
