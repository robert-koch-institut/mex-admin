# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changes

### Deprecated

### Removed

### Fixed

### Security

## [3.1.1] - 2026-07-22

## [3.1.0] - 2026-07-09

### Changes

- BREAKING: use MEX_EDITOR_USER_DATABASE instead of MEX_BACKEND_API_USER_DATABASE
- polish styling of consent page and ldap login page
- test search pages with appropriate reader user permissions

### Fixed

- disable buttons on consent page when clicking would have no effect

## [3.0.1] - 2026-07-06

### Fixed

- fix search page styling

## [3.0.0] - 2026-07-01

### Changes

- updated mex-backend to 4.0
- updated mex.common to version 3.0
- uses new backend endpoint for advanced reference filtering
- updated template to https://github.com/robert-koch-institut/mex-template/commit/1d816d
- change title to MEx Admin Editor to soft-launch admin renaming
- new template https://github.com/robert-koch-institut/mex-template/releases/tag/1.3.0
- updated template to https://github.com/robert-koch-institut/mex-template/commit/0d8c47

## [2.0.0] - 2026-06-30

### Changes

- replaced switch to toggle all primary sources with new workflow publish targets
- updated template to https://github.com/robert-koch-institut/mex-template/commit/11612b
- updated mex.common to version 2.0

### Fixed

- fix consent test submit failing
- fix cookiecutter permissions
- fix layout on create page

## [1.9.0] - 2026-04-02

### Added

- forbid users to change their consent status from positive to negative

### Changes

- update mex-backend to 1.8
- update mex-common to 1.18
- updated template to https://github.com/robert-koch-institut/mex-template/commit/43f715
- use merged items endpoint for consent site search

## [1.8.0] - 2026-03-25

### Added

- shows final fields in the mex editor
- added manually an EditorField for identifierInPrimarySource in _transform_model_to_editor_primary_sources
- added into InputConfig allow_subtractive and allow_preventive

### Changes

- update mex-common to 1.17
- update mex-backend to 1.7.2
- adapted tests because identifierInPrimarySource is not in MERGEABLE_FIELDS
- Updated uv to 0.10.11
- Text is truncated/wrapped based on model.yaml (edit with textarea -> wrap; otherwise truncate)
- Layout mostly flexing now (flex layout)
- edit_button is always visible for additives
- updated neo4j to 2026.02

## [1.7.1] - 2026-03-09

### Changes

- update lock file

### Fixed

- set build dir in docker file
- fix reflex build

## [1.7.0] - 2026-03-06

### Changes

- bump python to 3.14
- upgrade reflex to 0.8.27
- updated template to https://github.com/robert-koch-institut/mex-template/commit/0c16a6
- use dynamic primary source title for ingest tabs
- updated template to https://github.com/robert-koch-institut/mex-template/commit/81bc5b
- change the docker build to multi-stage build
- change primary source of rules from mex to mex-editor
- moved pytest rerun config from toml to makefile

### Removed

- disable reflex ssr
- get rid off nest-asyncio in tests

## [1.6.1] - 2026-03-05

### Changes

- make consent markdown path configurable via `MEX_EDITOR_ASSETS_DIR`

## [1.6.0] - 2026-03-04

### Added

- consent page filters items based on person

### Changes

- added supersededBy-backward fields in the edit page
- consent page UI clean up
- renamed 'locale' folder to 'i18n'
- change the docker build to multi-stage build
- change primary source of rules from mex to mex-editor
- moved pytest rerun config from toml to makefile

### Fixed

- fixed settings logging on startup and in tests
- fixed separate entrypoint configuration

## [1.5.1] - 2026-02-25

### Fixed

- fixed width of search and advanced-search result lists
- fixed redirect target after login screen interception

## [1.5.0] - 2026-02-24

### Added

- New page for advanced searching, including complex reference filter
- Translations for entity types
- Button on edit page to reset or delete rules
- Warn about unsaved changes when logging out
- pytest-retry since tests often failing on github (we belief due to low system/cpu performance in CI)

### Changes

- upgrade reflex to 0.8.15
- use pydantic v2 BaseModel instead of rx.Base
- other rerun lib for pytest
- updated mex-common to 1.16.0
- updated template to https://github.com/robert-koch-institut/mex-template/commit/81bc5b

### Removed

- all custom scripts due to reflex docs

## [1.4.1] - 2026-02-04

### Fixed

- fix uv export command

## [1.4.0] - 2026-02-04

### Added

- Component to display search results

### Changes

- use merged-person-from-login connector method
- updated template to https://github.com/robert-koch-institut/mex-template/commit/33ca3a
- bump python to 3.13
- updated template to https://github.com/robert-koch-institut/mex-template/commit/ad26e4
- bump common to 1.13.2
- switch package manager from pdm to uv

## [1.3.1] - 2026-01-14

### Changes

- update reflex env vars to use `REFLEX_` prefix in dockerfile

### Fixed

- fix application specifier for new uvicorn version

## [1.3.0] - 2026-01-14

### Added

- LocalStorage to store drafts and edits local on browser side.
- add cve scanning of frontend dependencies
- Dialog to search for entities by name and entity-type.
- Decorator for localized labels that creates a `ComputedVar[str]` that depends on
  `State.current_locale` and calls locale_service.get_text with a `label_id`
- Localized labels for every page, component and layout

### Changes

- upgrade reflex to version 0.7.14
- fix and/or evade type checking issues with reflex event handlers
- use pytest base_url plugin to make editor url configurable for testing
- updated template to https://github.com/robert-koch-institut/mex-template/commit/2039340
- updated template to https://github.com/robert-koch-institut/mex-template/commit/c5ff3e
- updated template to https://github.com/robert-koch-institut/mex-template/commit/7c3e75
- Using href navigation instead of navigation via code (`page.navigate()`).
- Refactored pagination into state mixin and component with options.
- Removed .mo files and converting .po files at runtime with polib
- tests:
  - Increased global expect timeout (to 10,000)
  - replaced all locators thats searched for localized strings with data_test_id searches
  - replaced localized string compares with regexs
- change failed login alert type from browser dialog to toast

### Removed

- Dialogs for navigating away while having changes on create or edit page.
- dropped npm support in favor of bun

### Fixed

- fixed bun cache options for windows
- fix broken unit tests and flaky additional title test

## [1.2.0] - 2025-11-28

### Added

- consent microsite with ldap auth to allow granting/revoking user info publishing
- CustomSelect-Component that has items with value and label instead of simple strings
- add caching for playwright browsers and node-modules to testing workflow

### Changes

- updated template to https://github.com/robert-koch-institut/mex-template/commit/a67c71
- updated template to https://github.com/robert-koch-institut/mex-template/commit/6009e2
- Field of the ReferenceFilter is now translated
- Initial language now picking from available languages instead of hard coded value
- updated template to https://github.com/robert-koch-institut/mex-template/commit/3c389d
- Increased global expect timeout (to 15,000) for tests
- Using the field label for new/remove additive value button
- renaming the field_name function to field_name_card
- editor tests use backend-testing entrypoint
- prefer using enum names over just raw strings in tests
- change external test marker to requires_rki_infrastructure

### Fixed

- Page numbers on search and ingest page

## [1.1.0] - 2025-10-10

### Added

- badge with '+ additional titles' if there is more than one title present
- allow to toggle all primary sources back on within the edit page
- ingest button of already imported items are always deactivated

### Changes

- run local test browser in headed mode with higher resolution
- update reflex to 0.7.3

### Removed

- removed warning when the create or edit browser window/tab is closed or navigated away

## [1.0.2] - 2025-10-07

### Fixed

- use locale files from mex-model

## [1.0.1] - 2025-10-07

### Changes

- bump mex-common to 1.5.1 and mex-model to 4.2.1

## [1.0.0] - 2025-10-06

### Added

- submit button is disabled and contains a spinner while submitting
- localization (label and description only) for "de" and "en"
- warning when a page reflex navigates and there are still changes on the current page
- added a switch to toggle all primary sources and values in the edit page
- added textareas for fields listed in mex/editor/models.yaml
- warning when the create or edit browser window/tab is closed or navigated away
- new filter for reference field filtering
- tab to switch between new reference field filter and the old had primary source filter

### Changes

- bump cookiecutter template to b18156

### Fixed

- fix badge default for link and text
- fix title of edit page to be equal to search snippet

## [0.22.0] - 2025-07-31

### Added

- infobox to ingest page for "ldap" and "wikidata"
- new type for aux_provider instead of str
- 'None' as language selection for `Link` and `Text`
- add string input mask for `Resource.temporal` field

### Changes

- type of aux provider from `str` to `AuxProvider`
- prepare reflex update
- de-duplicate pagination component
- de-duplicate ingestion roundtrip tests

### Removed

- remove edit toggle button for non-identifier fields

### Fixed

- fix service readiness checks
- use more of the available space for rule input fields

## [0.21.0] - 2025-07-22

### Added

- entity type selection triggers search in merged view

### Changes

- resolve identifiers in merge view

### Fixed

- fix editing for link fields without a title value
- only show allowed precisions in temporal field drop-down

## [0.20.0] - 2025-07-08

### Added

- new page to search and select merged and extracted items
- highlight required fields in edit view with a red asterisk
- add support for logging-in with ENTER key

### Changes

- set is_loading to True on_load for search and ingest states

## [0.19.0] - 2025-06-25

### Added

- add ldap authentication

### Changes

- consent preview uses direct field isIndicatedAtTime as title

## [0.18.1] - 2025-06-19

### Changes

- rename aux-search component to ingest, matching naming in backend

### Fixed

- fix transparency of overlay containers

## [0.18.0] - 2025-06-17

### Changes

- install mex-common and mex-artificial from pypi

## [0.17.0] - 2025-06-16

### Added

- import artificial data helper and use in test
- page to create new rule-set in editor
- new rules module containing shared code of create and edit pages
- button for switching between rendered and input view for additive field values

## [0.16.0] - 2025-05-22

### Added

- allow editing for identifier fields

### Changes

- bump cookiecutter template to ed5deb
- BREAKING: set mex-backend compatibility to 0.37.1

## [0.15.0] - 2025-04-29

### Added

- import artificial data helper and use in test

### Changes

- update mex-common to 0.59.1

## [0.14.0] - 2025-04-15

### Added

- create InputConfig for all fields, not just mex primary source
- add `badge_default`, `badge_titles` and fine grained edit control to input config
- allow editing for vocabulary fields and harmonize with link/text language editing
- allow editing for integer fields
- show spinner while loading search results
- show validation errors in table format

### Changes

- update mex-common to 0.58.0

### Fixed

- fixed editing for temporal fields by showing select menu for precisions

## [0.13.0] - 2025-04-14

### Added

- search and import ldap persons
- resolve identifiers in search and edit view to their preferred title attributes
- resolve identifiers in primary source search filter to their preferred title attribute

### Changes

- apply ruff TC006 by quoting type expressions in `typing.cast` calls
- search initiation now requires hitting enter or clicking the search button

## [0.12.0] - 2025-03-13

### Added

- implement editing for text and link fields

## [0.11.2] - 2025-03-12

### Changes

- update mex-common to 0.54.2
- fix some styles

### Removed

- remove `merged` page boilerplate, for now

## [0.11.1] - 2025-03-12

### Added

- show mex-editor and mex-backend versions when hovering over logo

## [0.11.0] - 2025-03-05

### Added

- button to import and ingest wikidata organizations
- add color mode toggle to login screen
- added new/remove buttons for additive rules for string fields
- add event handlers for adding/removing additive value input cards
- added text input field for email, string and temporal fields
- add event handler for setting string input values
- filter for hadPrimarySource
- add new entrypoints `editor-api` and `editor-frontend` for prod mode
- add new settings for ports, hosts and paths for prod mode execution

### Changes

- update mex-common to version 0.54.0
- combine EditState.editor_fields and EditState.fields
- update transformation logic to handle strings from additive rules
- BREAKING: change default ports to 8030/8031 for dockerfile

### Fixed

- fix redirect bug on 404 pages, by side-stepping add_page

## [0.10.0] - 2025-02-18

### Changes

- update mex-common to version 0.51.1
- pin mex-backend container version to 0.30.1
- update url parameters when search options change
- load url parameters on page load (i.e. when a link/bookmark is clicked)
- search parameters as state vars when switching editor components

## [0.9.0] - 2025-02-13

### Added

- aux extractor search for wikidata

### Changes

- update mex-common to version 0.49.3
- BREAKING: you must start the local dev mode simply with `pdm run editor` (no 2nd run)
- BREAKING: rename postfix_badge to render_badge (for consistency)
- simplify some styles and update look and feel to be more inline with mex-drop
- use more idiomatic variables for styling elements with colors or spacing

### Removed

- remove BackendIdentityProvider in favor of mex-common version
- remove identity_provider from EditorSettings in favor of mex-common setting
- remove EditorIdentityProvider enum in favor of mex-common enum
- remove dependency to reflex-chakra, use default checkboxes instead

### Fixed

- decorate state handlers with `@rx.event` to satisfy new reflex versions
- explicitly define cache strategies for vars with `@rx.var(cache=False)`

## [0.8.0] - 2025-01-22

### Added

- add toggles for preventive and subtractive rules
- add functionality to edit component for submitting rules
- add utility function to escalate errors to all consoles
- temporarily add BackendIdentityProvider (stop-gap MX-1763)

### Changes

- bump cookiecutter template to 57e9b7
- rename FixedX and EditableX classes to EditorX for consistency

### Removed

- drop dev-dependency to mex-backend, use the flush endpoint instead
- temporarily removed localization of temporals entity output

## [0.7.1] - 2025-01-15

- update mex-backend docker tag

## [0.7.0] - 2025-01-15

### Added

- redirect to original URL after login
- add icon identifiers to models.yaml and ModelConfig

## [0.6.0] - 2024-11-19

### Changes

- upgrade mex-common and model dependencies to v3
- overhaul and simplify margins and spaces
- move transform_models_to_fields from State to transform module
- use dedicated backend connector methods for edit and search
- use same rendering components for edit and search pages
- pop toasts when backend connector encounters errors
- scroll to top when pagination is triggered
- update dependency versions

### Fixed

- fix routing issues by moving the refresh handlers section from `on_mount` to `page.on_load`

## [0.5.0] - 2024-09-19

### Added

- implement simple search with pagination and entity type filtration

### Changes

- set fastapi, starlette and pydantic versions explicitly and update mex-common

## [0.4.0] - 2024-08-07

### Added

- implement a basic item view which will be expanded into the editing mode
- add model config YAML to store which fields to use for titles and previews
- add basic rendering functions for arbitrary models and types
- configure CI integration tests running against real backend and database
- implement integration tests for all four major pages in the editor

### Changes

- rework navigation bar to work with states instead of passing through literals
- update layout and styling on login form, merge page stub and search view

## [0.3.0] - 2024-07-29

### Added

- add login component and form
- add user menu in navbar with logout button
- setup authentication against locally configured users

### Changes

- re-organize state classes into individual modules

### Removed

- remove unused `mex.editor.transform.to_primitive`

## [0.2.1] - 2024-07-12

### Changes

- update dependency versions

## [0.2.0] - 2024-07-12

### Added

- add health check route to api

### Changes

- use production mode in dockerfile
- change default ports to 8030/8040

## [0.1.0] - 2024-06-14

### Changes

- switch tech stack to python, pydantic, fastapi and reflex
