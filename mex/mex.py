import reflex as rx
from reflex.components.radix import themes

from mex.admin.advanced_search.main import index as advanced_search_index
from mex.admin.advanced_search.state import AdvancedSearchState
from mex.admin.api.main import api as admin_api
from mex.admin.create.main import index as create_index
from mex.admin.create.state import CreateState
from mex.admin.edit.main import index as edit_index
from mex.admin.edit.state import EditState
from mex.admin.home.main import index as home_index
from mex.admin.ingest.main import index as ingest_index
from mex.admin.ingest.state import IngestState
from mex.admin.login.main import mex_login as login_mex_index
from mex.admin.merge.main import index as merge_index
from mex.admin.merge.state import MergeState
from mex.admin.rules.state import RuleState
from mex.admin.search.main import index as search_index
from mex.admin.search.state import SearchState
from mex.admin.state import State
from mex.admin.utils import load_settings

app = rx.App(
    theme=themes.theme(
        accent_color="blue",
        has_background=False,
        appearance="light",
    ),
    style={
        ">a": {"opacity": "0"},
        ".truncate": {
            "overflow": "hidden",
            "text-overflow": "ellipsis",
            "white-space": "nowrap",
        },
    },
    api_transformer=admin_api,
)
app.add_page(
    home_index,
    route="/",
    title="MEx Admin",
    on_load=[
        State.check_mex_login,
        State.load_nav,
    ],
)
app.add_page(
    search_index,
    route="/search",
    title="MEx Admin | Search",
    on_load=[
        State.check_mex_login,
        State.load_nav,
        SearchState.get_available_primary_sources,
        SearchState.load_search_params,
        SearchState.refresh,
        SearchState.resolve_identifiers,
    ],
)
app.add_page(
    advanced_search_index,
    route="/advanced-search",
    title="MEx Admin | Advanced Search",
    on_load=[
        State.check_mex_login,
        State.load_nav,
        AdvancedSearchState.search,
        AdvancedSearchState.resolve_identifiers,
    ],
)
app.add_page(
    merge_index,
    route="/merge",
    title="MEx Admin | Merge",
    on_load=[
        State.check_mex_login,
        State.load_nav,
        MergeState.reset_stem_type,
        MergeState.refresh,
        MergeState.resolve_identifiers,
    ],
)
app.add_page(
    create_index,
    route="/create/[draft_id]",
    title="MEx Admin | Create",
    on_load=[
        State.check_mex_login,
        State.load_nav,
        RuleState.refresh,
        RuleState.resolve_identifiers,
    ],
)
app.add_page(
    create_index,
    route="/create",
    title="MEx Admin | Create",
    on_load=[
        State.check_mex_login,
        State.load_nav,
        CreateState.reset_stem_type,
        RuleState.refresh,
        RuleState.resolve_identifiers,
    ],
)
app.add_page(
    edit_index,
    route="/item/[item_id]",
    title="MEx Admin | Edit",
    on_load=[
        State.check_mex_login,
        State.load_nav,
        RuleState.refresh,
        EditState.show_submit_success_toast_on_redirect,
        RuleState.resolve_identifiers,
        EditState.resolve_superseded_by_backward,
    ],
)
app.add_page(
    ingest_index,
    route="/ingest",
    title="MEx Admin | Ingest",
    on_load=[
        State.check_mex_login,
        State.load_nav,
        IngestState.refresh,
        IngestState.resolve_identifiers,
        IngestState.flag_ingested_items,
        IngestState.resolve_primary_source_titles,
    ],
)
app.add_page(
    login_mex_index,
    route="/login",
    title="MEx Admin | Login",
)
app.register_lifespan_task(
    load_settings,
)
