from django.urls import path
from django.views.generic import RedirectView

from dpypen.items.auth import login_or_guest_required

from dpypen.items.nextui import urls as nextui_urls
from dpypen.items import api_lists, crud, history, invite, kitshell, notebook, pairing, palette, public, pwa, records, search, share, undo, views


# The old version lives under /prev/ since the new one took the main addresses
# (Nov 2026). Its views and names are unchanged: `{% url 'pens_list' %}` is
# /prev/pens/, `{% url 'nx_pens_list' %}` is /pens/ (skin.py).
urlpatterns = [
    path('', public.landing, name='home'),
    path('prev/', login_or_guest_required(RedirectView.as_view(url='/prev/dashboard/')), name='prev'),
    path('robots.txt', public.robots, name='robots'),
    path('prev/dashboard/', public.dashboard, name='dashboard'),
    path('prev/history/', history.overview, name='history'),
    path('prev/history/inkings/', history.inkings, name='history_inkings'),
    path('prev/history/calendar/', history.calendar, name='history_calendar'),
    path('prev/history/gantt/', history.gantt, name='history_gantt'),
    path('prev/history/matrix/', history.matrix, name='history_matrix'),
    path('prev/records/', records.records, name='records'),
    path('prev/pick/', pairing.next_inking, name='next_inking'),
    path('prev/search/', search.search, name='search'),
    path('prev/settings/', public.settings_page, name='settings'),
    path('api/palette', palette.palette, name='api_palette'),
    path('api/pens', api_lists.pens, name='api_pens'),
    path('api/inks', api_lists.inks, name='api_inks'),
    path('api/usages', api_lists.usages, name='api_usages'),
    path('api/version', pwa.version, name='api_version'),
    path('whatsnew.json', pwa.whatsnew, name='whatsnew'),
    path('undo/<str:token>/', undo.undo, name='undo'),

    path('manifest.json', pwa.manifest, name='pwa_manifest'),
    path('sw.js', pwa.service_worker, name='pwa_sw'),
    # The kit's snippets as cached files (kitshell.py, kit README §5.9).
    path('kit/<str:name>', kitshell.serve, name='kit_shell'),
    path('icon.svg', pwa.icon, name='pwa_icon'),
    path('icon-maskable.svg', pwa.icon_maskable, name='pwa_icon_maskable'),
    path('i/leave/', invite.deactivate, name='invite_deactivate'),
    path('i/<str:token>/', invite.activate, name='invite_activate'),

    path('p/<str:token>/', share.pen_by_token, name='share_pen'),
    path('k/<str:token>/', share.ink_by_token, name='share_ink'),
    path('pub/inks/', share.inks_gallery, name='share_inks_gallery'),
    path('pub/inks/wall/', share.inks_wall, name='share_inks_wall'),
    path('pub/pens/wall/', share.pens_wall, name='share_pens_wall'),

    path('prev/import/', notebook.upload, name='notebook_upload'),
    path('prev/import/review/', notebook.review, name='notebook_review'),

    path('prev/usages/', crud.usages_list, name='usages_list'),
    path('prev/usages/add/', crud.usages_create, name='usages_create'),
    path('prev/usages/<int:pk>/edit/', crud.usages_edit, name='usages_edit'),
    path('prev/usages/<int:pk>/end/', crud.usages_end, name='usages_end'),
    path('prev/usages/<int:pk>/delete/', crud.usages_delete, name='usages_delete'),
    path('prev/usages/<int:pk>/samples/add/', crud.usages_sample_add, name='usages_sample_add'),
    path('prev/samples/<int:pk>/extract/', crud.samples_extract, name='samples_extract'),
    path('prev/samples/<int:pk>/delete/', crud.samples_delete, name='samples_delete'),

    path('prev/pens/', crud.pens_list, name='pens_list'),
    path('prev/pens/add/', crud.pens_create, name='pens_create'),
    path('prev/pens/needs-photos/', crud.pens_needs_photos, name='pens_needs_photos'),
    path('prev/pens/<int:pk>/', crud.pens_detail, name='pens_detail'),
    path('prev/pens/<int:pk>/edit/', crud.pens_edit, name='pens_edit'),
    path('prev/pens/<int:pk>/delete/', crud.pens_delete, name='pens_delete'),
    path('prev/pens/<int:pk>/photos/add/', crud.pens_photo_add, name='pens_photo_add'),
    path('prev/pens/<int:pk>/photos/<int:photo_pk>/', crud.pens_photo_edit, name='pens_photo_edit'),
    path('prev/pens/<int:pk>/photos/<int:photo_pk>/delete/', crud.pens_photo_delete, name='pens_photo_delete'),
    path('prev/pens/<int:pk>/photos/<int:photo_pk>/primary/', crud.pens_photo_primary, name='pens_photo_primary'),
    path('prev/pens/<int:pk>/photos/<int:photo_pk>/rotate/', crud.pens_photo_rotate, name='pens_photo_rotate'),
    path('prev/pens/<int:pk>/photos/<int:photo_pk>/enhance/', crud.pens_photo_enhance, name='pens_photo_enhance'),
    path('prev/pens/<int:pk>/photos/<int:photo_pk>/unstyle/', crud.pens_photo_unstyle, name='pens_photo_unstyle'),

    path('prev/inks/', crud.inks_list, name='inks_list'),
    path('prev/inks/add/', crud.inks_create, name='inks_create'),
    path('prev/inks/<int:pk>/', crud.inks_detail, name='inks_detail'),
    path('prev/inks/<int:pk>/edit/', crud.inks_edit, name='inks_edit'),
    path('prev/inks/<int:pk>/delete/', crud.inks_delete, name='inks_delete'),
    path('prev/inks/<int:pk>/swatches/add/', crud.inks_swatch_add, name='inks_swatch_add'),
    path('prev/swatches/<int:pk>/extract/', crud.swatches_extract, name='swatches_extract'),
    path('prev/swatches/<int:pk>/delete/', crud.swatches_delete, name='swatches_delete'),

    path('supen', views.supen, dict(rotation=0, order=2)),
    path('supen/<int:rotation>', views.supen, dict(order=2)),
    path('supen/<int:rotation>/<int:order>', views.supen),
    path('suink', views.suink, dict(rotation=1, order=2)),
    path('suink/<int:rotation>', views.suink, dict(order=2)),
    path('suink/<int:rotation>/<int:order>', views.suink),
]

# The new version (PYPEN-11), on the main addresses. In this list, so
# tests_doors walks it too.
urlpatterns += nextui_urls.urlpatterns
