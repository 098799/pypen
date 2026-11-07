"""The new version's addresses: the main ones since Nov 2026 (it lived under
/next/ while it was tried; the old version is under /prev/ now). One view for
both faces.

A plain list, added to items/urls.py, so tests_doors walks every one of them as a
stranger and as a guest. Names start with `nx_`.
"""

from django.urls import path

from dpypen.items import crud, notebook, pairing, search
from dpypen.items.nextui import photocheck, views
from dpypen.items.skin import rehome as r

urlpatterns = [
    # Bookmarks and home-screen tiles from the weeks under /next/.
    path("next/", views.from_next, name="nx_from_next"),
    path("next/<path:rest>", views.from_next),
    path("dashboard/", views.desk, name="nx_desk"),
    path("settings/", views.settings_page, name="nx_settings"),
    path("pick/", r(pairing.next_inking), name="nx_pick"),
    path("search/", r(search.search), name="nx_search"),
    path("supen/", views.turns_pens, name="nx_supen"),
    path("suink/", views.turns_inks, name="nx_suink"),

    path("stats/", views.stats_overview, name="nx_stats"),
    path("stats/inkings/", views.stats_inkings, name="nx_stats_inkings"),
    path("stats/collection/", views.stats_collection, name="nx_stats_collection"),
    path("stats/cupboard/", views.stats_cupboard, name="nx_stats_cupboard"),
    path("stats/rotation/", views.stats_rotation, name="nx_stats_rotation"),
    path("stats/timeline/", views.stats_timeline, name="nx_stats_timeline"),
    path("stats/calendar/", views.stats_calendar, name="nx_stats_calendar"),
    path("stats/pairs/", views.stats_pairs, name="nx_stats_pairs"),
    path("stats/records/", views.records, name="nx_records"),

    path("import/", r(notebook.upload), name="nx_notebook_upload"),
    path("import/review/", r(notebook.review), name="nx_notebook_review"),

    path("usages/", r(crud.usages_list), name="nx_usages_list"),
    path("usages/add/", r(crud.usages_create), name="nx_usages_create"),
    path("usages/<int:pk>/edit/", r(crud.usages_edit), name="nx_usages_edit"),
    path("usages/<int:pk>/end/", r(crud.usages_end), name="nx_usages_end"),
    path("usages/<int:pk>/delete/", r(crud.usages_delete), name="nx_usages_delete"),
    path("usages/<int:pk>/samples/add/", r(crud.usages_sample_add), name="nx_usages_sample_add"),
    path("usages/samples/<int:pk>/extract/", r(crud.samples_extract), name="nx_samples_extract"),
    path("usages/samples/<int:pk>/delete/", r(crud.samples_delete), name="nx_samples_delete"),

    path("pens/", r(crud.pens_list), name="nx_pens_list"),
    path("pens/add/", r(crud.pens_create), name="nx_pens_create"),
    path("pens/needs-photos/", r(crud.pens_needs_photos), name="nx_pens_needs_photos"),
    path("pens/photos/check/", photocheck.check, name="nx_pens_photo_check"),
    path("pens/<int:pk>/photos/<int:photo_pk>/verdict/", photocheck.verdict, name="nx_pens_photo_verdict"),
    path("pens/<int:pk>/", r(crud.pens_detail), name="nx_pens_detail"),
    path("pens/<int:pk>/edit/", r(crud.pens_edit), name="nx_pens_edit"),
    path("pens/<int:pk>/delete/", r(crud.pens_delete), name="nx_pens_delete"),
    path("pens/<int:pk>/photos/add/", r(crud.pens_photo_add), name="nx_pens_photo_add"),
    path("pens/<int:pk>/photos/<int:photo_pk>/", r(crud.pens_photo_edit), name="nx_pens_photo_edit"),
    path("pens/<int:pk>/photos/<int:photo_pk>/delete/", r(crud.pens_photo_delete), name="nx_pens_photo_delete"),
    path("pens/<int:pk>/photos/<int:photo_pk>/primary/", r(crud.pens_photo_primary), name="nx_pens_photo_primary"),
    path("pens/<int:pk>/photos/<int:photo_pk>/rotate/", r(crud.pens_photo_rotate), name="nx_pens_photo_rotate"),
    path("pens/<int:pk>/photos/<int:photo_pk>/enhance/", r(crud.pens_photo_enhance), name="nx_pens_photo_enhance"),
    path("pens/<int:pk>/photos/<int:photo_pk>/unstyle/", r(crud.pens_photo_unstyle), name="nx_pens_photo_unstyle"),

    path("inks/", r(crud.inks_list), name="nx_inks_list"),
    path("inks/add/", r(crud.inks_create), name="nx_inks_create"),
    path("inks/<int:pk>/", r(crud.inks_detail), name="nx_inks_detail"),
    path("inks/<int:pk>/edit/", r(crud.inks_edit), name="nx_inks_edit"),
    path("inks/<int:pk>/delete/", r(crud.inks_delete), name="nx_inks_delete"),
    path("inks/<int:pk>/swatches/add/", r(crud.inks_swatch_add), name="nx_inks_swatch_add"),
    path("inks/swatches/<int:pk>/extract/", r(crud.swatches_extract), name="nx_swatches_extract"),
    path("inks/swatches/<int:pk>/delete/", r(crud.swatches_delete), name="nx_swatches_delete"),
]
