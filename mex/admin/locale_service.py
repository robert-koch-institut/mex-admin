import re
from collections.abc import Iterable
from gettext import GNUTranslations
from importlib.resources import files
from io import BytesIO
from pathlib import Path
from typing import Self, cast

import polib
from babel import Locale as BabelLocale
from pydantic import BaseModel

from mex.common.context import SingleSingletonStore
from mex.common.transform import camelcase_to_title

LOCALE_SERVICE_STORE = SingleSingletonStore["LocaleService"]()


class MExLocale(BaseModel):
    """Represents a locale with id and label."""

    id: str
    label: str
    language: str

    def values(self) -> Iterable[str]:
        """Expose locale values to avoid reflex bug."""
        return self.model_dump().values()  # sigh, don't ask


class LocaleService:
    """A service singleton to control the current locale used by the app."""

    @classmethod
    def get(cls) -> Self:
        """Get singleton instance of the LocaleService.

        Returns:
            The LocaleService singleton.
        """
        return cast("Self", LOCALE_SERVICE_STORE.load(cls))

    _admin_locale_path = cast("Path", (files("mex.admin") / "i18n"))
    _model_locale_path = cast("Path", (files("mex.model") / "i18n"))
    _available_locales: dict[str, MExLocale] = {}
    _translations: dict[str, GNUTranslations] = {}

    def __init__(self) -> None:
        """Initialize with all available locales in `_admin_locale_path`."""
        for po_file in self._admin_locale_path.glob("*.po"):
            locale = po_file.name.removesuffix(".po")
            language = re.split("[-_]", locale)[0]
            label = BabelLocale(language).get_language_name()
            self._available_locales[locale] = MExLocale(
                id=locale, label=label, language=language
            )

    def _ensure_translation(self, locale_id: str) -> GNUTranslations:
        if locale_id not in self._available_locales:
            error_msg = f"Given 'locale_id' ({locale_id}) is not valid. Valid values "
            f"are: {', '.join([loc.id for loc in self.get_available_locales()])}"
            raise ValueError(error_msg)

        if locale_id not in self._translations:
            filename = f"{locale_id}.po"
            model_po = polib.pofile(self._model_locale_path / filename)
            admin_po = polib.pofile(self._admin_locale_path / filename)
            admin_po.extend(model_po)
            self._translations[locale_id] = GNUTranslations(
                BytesIO(admin_po.to_binary())
            )
        return self._translations[locale_id]

    def get_available_locales(self) -> list[MExLocale]:
        """Get all available locales.

        Returns:
            All available locales.
        """
        return list(self._available_locales.values())

    def get_ui_label(self, locale_id: str, msg_id: str) -> str:
        """Get the text for a given locale_id and the msg_id.

        Args:
            locale_id (str): The locale to use.
            msg_id (str): The message id of the message to get the text for.

        Returns:
            The message of the msg_id for the given locale_id.
        """
        translation = self._ensure_translation(locale_id)
        return translation.gettext(msg_id)

    def get_field_label(  # noqa: PLR0911
        self, locale_id: str, stem_type: str, field_name: str, n: int = 1
    ) -> str:
        """Get the human readable form of the given field in a given language.

        Args:
            locale_id: The locale id of the language to use.
            stem_type: The entity type the field belongs to.
            field_name: The name of the field.
            n (optional): Number to pass to ngettext to determine if plural form is
            used. Defaults to 1.

        Returns:
            The human readable name of the field.
        """
        translation = self._ensure_translation(locale_id)
        msg_id_singular = f"{field_name}.singular"
        msg_id_plural = f"{field_name}.plural"

        if (
            stem_plural_singular_translation := translation.npgettext(
                stem_type, msg_id_singular, msg_id_plural, n
            )
        ) not in (msg_id_singular, msg_id_plural):
            return stem_plural_singular_translation

        if (
            plural_singular_translation := translation.ngettext(
                msg_id_singular, msg_id_plural, n
            )
        ) not in (
            msg_id_singular,
            msg_id_plural,
        ):
            return plural_singular_translation

        if (
            stem_fieldname_translation := translation.pgettext(stem_type, field_name)
        ) != field_name:
            return stem_fieldname_translation

        if (
            stem_singular_translation := translation.pgettext(
                stem_type, msg_id_singular
            )
        ) != msg_id_singular:
            return stem_singular_translation

        if (
            singular_translation := translation.gettext(msg_id_singular)
        ) != msg_id_singular:
            return singular_translation

        if (fieldname_translation := translation.gettext(field_name)) != field_name:
            return fieldname_translation

        return camelcase_to_title(field_name)

    def get_field_description(
        self, locale_id: str, stem_type: str, field_name: str
    ) -> str:
        """Get the description for a field in a given language.

        Args:
            locale_id: The locale id of the language to use.
            stem_type: The type the field belongs to.
            field_name: The name of the field.

        Returns:
            The description of the field.
        """
        translation = self._ensure_translation(locale_id)
        msg_id_description = f"{field_name}.description"
        if (
            description := translation.pgettext(stem_type, msg_id_description)
        ) != msg_id_description:
            return description

        if (
            description := translation.gettext(msg_id_description)
        ) != msg_id_description:
            return description

        return ""
