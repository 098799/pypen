"""The new version's addresses: /next/ plus what the old page has, one view for both.

A plain list, added to items/urls.py, so tests_doors walks every one of them as a
stranger and as a guest. Names start with `nx_`.
"""

from django.urls import path

from dpypen.items import crud, notebook, pairing, search
from dpypen.items.nextui import views
from dpypen.items.skin import rehome as r

urlpatterns = [
    path("next/", views.desk, name="nx_desk"),
    path("next/settings/", views.settings_page, name="nx_settings"),
    path("next/prefer/", views.prefer, name="nx_prefer"),
    path("next/pick/", r(pairing.next_inking), name="nx_pick"),
    path("next/search/", r(search.search), name="nx_search"),

    path("next/stats/", views.stats_overview, name="nx_stats"),
    path("next/stats/inkings/", views.stats_inkings, name="nx_stats_inkings"),
    path("next/stats/collection/", views.stats_collection, name="nx_stats_collection"),
    path("next/stats/cupboard/", views.stats_cupboard, name="nx_stats_cupboard"),
    path("next/stats/rotation/", views.stats_rotation, name="nx_stats_rotation"),
    path("next/stats/timeline/", views.stats_timeline, name="nx_stats_timeline"),
    path("next/stats/calendar/", views.stats_calendar, name="nx_stats_calendar"),
    path("next/stats/pairs/", views.stats_pairs, name="nx_stats_pairs"),
    path("next/stats/records/", views.records, name="nx_records"),

    path("next/import/", r(notebook.upload), name="nx_notebook_upload"),
    path("next/import/review/", r(notebook.review), name="nx_notebook_review"),

    path("next/usages/", r(crud.usages_list), name="nx_usages_list"),
    path("next/usages/add/", r(crud.usages_create), name="nx_usages_create"),
    path("next/usages/<int:pk>/edit/", r(crud.usages_edit), name="nx_usages_edit"),
    path("next/usages/<int:pk>/end/", r(crud.usages_end), name="nx_usages_end"),
    path("next/usages/<int:pk>/delete/", r(crud.usages_delete), name="nx_usages_delete"),
    path("next/usages/<int:pk>/samples/add/", r(crud.usages_sample_add), name="nx_usages_sample_add"),
    path("next/usages/samples/<int:pk>/extract/", r(crud.samples_extract), name="nx_samples_extract"),
    path("next/usages/samples/<int:pk>/delete/", r(crud.samples_delete), name="nx_samples_delete"),

    path("next/pens/", r(crud.pens_list), name="nx_pens_list"),
    path("next/pens/add/", r(crud.pens_create), name="nx_pens_create"),
    path("next/pens/needs-photos/", r(crud.pens_needs_photos), name="nx_pens_needs_photos"),
    path("next/pens/<int:pk>/", r(crud.pens_detail), name="nx_pens_detail"),
    path("next/pens/<int:pk>/edit/", r(crud.pens_edit), name="nx_pens_edit"),
    path("next/pens/<int:pk>/delete/", r(crud.pens_delete), name="nx_pens_delete"),
    path("next/pens/<int:pk>/photos/add/", r(crud.pens_photo_add), name="nx_pens_photo_add"),
    path("next/pens/<int:pk>/photos/<int:photo_pk>/", r(crud.pens_photo_edit), name="nx_pens_photo_edit"),
    path("next/pens/<int:pk>/photos/<int:photo_pk>/delete/", r(crud.pens_photo_delete), name="nx_pens_photo_delete"),
    path("next/pens/<int:pk>/photos/<int:photo_pk>/primary/", r(crud.pens_photo_primary), name="nx_pens_photo_primary"),
    path("next/pens/<int:pk>/photos/<int:photo_pk>/rotate/", r(crud.pens_photo_rotate), name="nx_pens_photo_rotate"),
    path("next/pens/<int:pk>/photos/<int:photo_pk>/enhance/", r(crud.pens_photo_enhance), name="nx_pens_photo_enhance"),
    path("next/pens/<int:pk>/photos/<int:photo_pk>/unstyle/", r(crud.pens_photo_unstyle), name="nx_pens_photo_unstyle"),

    path("next/inks/", r(crud.inks_list), name="nx_inks_list"),
    path("next/inks/add/", r(crud.inks_create), name="nx_inks_create"),
    path("next/inks/<int:pk>/", r(crud.inks_detail), name="nx_inks_detail"),
    path("next/inks/<int:pk>/edit/", r(crud.inks_edit), name="nx_inks_edit"),
    path("next/inks/<int:pk>/delete/", r(crud.inks_delete), name="nx_inks_delete"),
    path("next/inks/<int:pk>/swatches/add/", r(crud.inks_swatch_add), name="nx_inks_swatch_add"),
    path("next/inks/swatches/<int:pk>/extract/", r(crud.swatches_extract), name="nx_swatches_extract"),
    path("next/inks/swatches/<int:pk>/delete/", r(crud.swatches_delete), name="nx_swatches_delete"),
]
