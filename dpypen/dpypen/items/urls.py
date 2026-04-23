from django.urls import path

from dpypen.items import crud, history, invite, notebook, public, pwa, records, search, share, views


urlpatterns = [
    path('', public.tease, name='home'),
    path('dashboard/', public.dashboard, name='dashboard'),
    path('history/', history.overview, name='history'),
    path('history/calendar/', history.calendar, name='history_calendar'),
    path('history/gantt/', history.gantt, name='history_gantt'),
    path('history/matrix/', history.matrix, name='history_matrix'),
    path('records/', records.records, name='records'),
    path('search/', search.search, name='search'),

    path('manifest.json', pwa.manifest, name='pwa_manifest'),
    path('sw.js', pwa.service_worker, name='pwa_sw'),
    path('icon.svg', pwa.icon, name='pwa_icon'),
    path('icon-maskable.svg', pwa.icon_maskable, name='pwa_icon_maskable'),
    path('i/leave/', invite.deactivate, name='invite_deactivate'),
    path('i/<str:token>/', invite.activate, name='invite_activate'),

    path('p/<str:token>/', share.pen_by_token, name='share_pen'),
    path('k/<str:token>/', share.ink_by_token, name='share_ink'),
    path('pub/inks/', share.inks_gallery, name='share_inks_gallery'),

    path('import/', notebook.upload, name='notebook_upload'),
    path('import/review/', notebook.review, name='notebook_review'),

    path('usages/', crud.usages_list, name='usages_list'),
    path('usages/add/', crud.usages_create, name='usages_create'),
    path('usages/<int:pk>/edit/', crud.usages_edit, name='usages_edit'),
    path('usages/<int:pk>/end/', crud.usages_end, name='usages_end'),
    path('usages/<int:pk>/delete/', crud.usages_delete, name='usages_delete'),
    path('usages/<int:pk>/samples/add/', crud.usages_sample_add, name='usages_sample_add'),
    path('samples/<int:pk>/extract/', crud.samples_extract, name='samples_extract'),
    path('samples/<int:pk>/delete/', crud.samples_delete, name='samples_delete'),

    path('pens/', crud.pens_list, name='pens_list'),
    path('pens/add/', crud.pens_create, name='pens_create'),
    path('pens/<int:pk>/', crud.pens_detail, name='pens_detail'),
    path('pens/<int:pk>/edit/', crud.pens_edit, name='pens_edit'),
    path('pens/<int:pk>/delete/', crud.pens_delete, name='pens_delete'),
    path('pens/<int:pk>/photos/add/', crud.pens_photo_add, name='pens_photo_add'),
    path('pens/<int:pk>/photos/<int:photo_pk>/', crud.pens_photo_edit, name='pens_photo_edit'),
    path('pens/<int:pk>/photos/<int:photo_pk>/delete/', crud.pens_photo_delete, name='pens_photo_delete'),
    path('pens/<int:pk>/photos/<int:photo_pk>/primary/', crud.pens_photo_primary, name='pens_photo_primary'),
    path('pens/<int:pk>/photos/<int:photo_pk>/rotate/', crud.pens_photo_rotate, name='pens_photo_rotate'),
    path('pens/<int:pk>/photos/<int:photo_pk>/enhance/', crud.pens_photo_enhance, name='pens_photo_enhance'),
    path('pens/<int:pk>/photos/<int:photo_pk>/unstyle/', crud.pens_photo_unstyle, name='pens_photo_unstyle'),

    path('inks/', crud.inks_list, name='inks_list'),
    path('inks/add/', crud.inks_create, name='inks_create'),
    path('inks/<int:pk>/', crud.inks_detail, name='inks_detail'),
    path('inks/<int:pk>/edit/', crud.inks_edit, name='inks_edit'),
    path('inks/<int:pk>/delete/', crud.inks_delete, name='inks_delete'),
    path('inks/<int:pk>/swatches/add/', crud.inks_swatch_add, name='inks_swatch_add'),
    path('swatches/<int:pk>/extract/', crud.swatches_extract, name='swatches_extract'),
    path('swatches/<int:pk>/delete/', crud.swatches_delete, name='swatches_delete'),

    path('supen', views.supen, dict(rotation=0, order=2)),
    path('supen/<int:rotation>', views.supen, dict(order=2)),
    path('supen/<int:rotation>/<int:order>', views.supen),
    path('suink', views.suink, dict(rotation=1, order=2)),
    path('suink/<int:rotation>', views.suink, dict(order=2)),
    path('suink/<int:rotation>/<int:order>', views.suink),
]
