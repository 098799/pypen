"""How it wrote: a verdict on each fill (README "How it wrote", verdicts.py)."""

from datetime import date, timedelta

from django.core import serializers
from django.test import Client, override_settings

from dpypen.items import pairing, verdicts
from dpypen.items.models import Ink, InviteCode, Usage
from dpypen.items.nextui import stats
from dpypen.items.tests import PLAIN_STATIC
from dpypen.items.tests_next import Seeded


def ended(pen, ink, nib, days_ago, length=20, **kw):
    end = date.today() - timedelta(days=days_ago)
    return Usage.objects.create(pen=pen, ink=ink, nib=nib, begin=end - timedelta(days=length), end=end, **kw)


@override_settings(STORAGES=PLAIN_STATIC)
class Finish(Seeded):
    def setUp(self):
        self.client.force_login(self.owner)

    def test_finish_says_how_it_wrote(self):
        r = self.client.post(f"/usages/{self.now.pk}/end/", {"next": "/dashboard/", "verdict": "loved", "note": "  wet,   lovely shading "})
        self.assertRedirects(r, "/dashboard/", fetch_redirect_response=False)
        self.now.refresh_from_db()
        self.assertEqual((self.now.end, self.now.verdict, self.now.note), (date.today(), "loved", "wet, lovely shading"))
        self.assertIsNotNone(self.now.verdict_at)
        toast = self.client.get("/dashboard/").content.decode()
        self.assertIn("Finished Pelikan M800 · Pelikan 4001 Blue: loved.", toast)

    def test_just_finish_says_nothing(self):
        self.client.post(f"/usages/{self.now.pk}/end/", {"verdict": ""})
        self.now.refresh_from_db()
        self.assertEqual((self.now.end, self.now.verdict, self.now.verdict_at), (date.today(), "", None))

    def test_a_word_it_does_not_know_is_no_word(self):
        self.client.post(f"/usages/{self.now.pk}/end/", {"verdict": "meh"})
        self.now.refresh_from_db()
        self.assertEqual((self.now.end, self.now.verdict), (date.today(), ""))

    def test_undo_takes_the_verdict_back_with_the_end(self):
        from dpypen.items import undo

        before = undo.snapshot(self.now)
        self.client.post(f"/usages/{self.now.pk}/end/", {"verdict": "never"})
        for obj in serializers.deserialize("json", before):
            obj.save()
        self.now.refresh_from_db()
        self.assertEqual((self.now.end, self.now.verdict), (None, ""))

    def test_the_finish_control_asks_on_every_screen_it_is_on(self):
        for url in ("/dashboard/", f"/pens/{self.pen.pk}/", "/usages/"):
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                self.assertIn('class="finish-d', html)
                self.assertIn('<p class="finish-q">How did it write?</p>', html)
                self.assertIn('<span class="fd-open">Not yet</span>', html)
                self.assertIn('name="verdict" value="never"', html)
                self.assertIn('data-new="verdicts"', html)


@override_settings(STORAGES=PLAIN_STATIC)
class SayItLater(Seeded):
    def setUp(self):
        self.client.force_login(self.owner)
        self.recent = ended(self.due, self.ink, self.nib, 3)

    def test_the_desk_asks_about_a_fill_just_finished(self):
        html = self.client.get("/dashboard/").content.decode()
        self.assertIn(f'action="/usages/{self.recent.pk}/verdict/"', html)
        self.assertIn("How did it write?", html)

    def test_a_verdict_said_later_lands_back_where_it_was_said(self):
        r = self.client.post(f"/usages/{self.recent.pk}/verdict/", {"verdict": "fine", "next": "/dashboard/"})
        self.assertRedirects(r, "/dashboard/", fetch_redirect_response=False)
        self.recent.refresh_from_db()
        self.assertEqual(self.recent.verdict, "fine")
        html = self.client.get("/dashboard/").content.decode()
        self.assertNotIn(f'action="/usages/{self.recent.pk}/verdict/"', html)
        self.assertIn('class="vsaid is-fine"', html)

    def test_an_empty_word_clears_it_and_a_note_alone_keeps_it(self):
        self.client.post(f"/usages/{self.recent.pk}/verdict/", {"verdict": "loved"})
        self.client.post(f"/usages/{self.recent.pk}/verdict/", {"note": "smooth"})
        self.recent.refresh_from_db()
        self.assertEqual((self.recent.verdict, self.recent.note), ("loved", "smooth"))
        self.client.post(f"/usages/{self.recent.pk}/verdict/", {"verdict": ""})
        self.recent.refresh_from_db()
        self.assertEqual((self.recent.verdict, self.recent.note), ("", "smooth"))

    def test_nothing_sent_changes_nothing(self):
        r = self.client.post(f"/usages/{self.recent.pk}/verdict/", {"verdict": "bogus"})
        self.assertEqual(r.status_code, 302)
        self.recent.refresh_from_db()
        self.assertEqual((self.recent.verdict, self.recent.verdict_at), ("", None))

    def test_history_rows_ask_only_within_the_year(self):
        html = self.client.get(f"/pens/{self.due.pk}/").content.decode()
        self.assertIn(f'action="/usages/{self.recent.pk}/verdict/"', html)
        self.assertNotIn(f'action="/usages/{self.old.pk}/verdict/"', html)  # ended in 2024
        self.assertIn(f'href="/usages/{self.old.pk}/edit/"', html)  # its form still can

    def test_the_desk_does_not_ask_about_a_fill_long_gone(self):
        Usage.objects.filter(pk=self.recent.pk).update(end=date.today() - timedelta(days=400), begin=date.today() - timedelta(days=420))
        html = self.client.get("/dashboard/").content.decode()
        self.assertNotIn(f'action="/usages/{self.recent.pk}/verdict/"', html)
        self.assertNotIn("wait for a word", html)

    def test_the_desk_counts_the_rest_waiting(self):
        for i in range(6):
            ended(self.due, self.red, self.nib, 10 + i)
        ended(self.due, self.red, self.nib, 400)  # too old to ask about
        html = self.client.get("/dashboard/").content.decode()
        # 7 in the past year, 5 shown on the desk: 2 more (self.old ended in 2024).
        self.assertIn("2 more fills of the past year</a> wait for a word.", html)
        self.assertIn("/usages/?verdict=none", html)

    def test_a_guest_sees_the_word_but_no_buttons(self):
        self.recent.verdict = "loved"
        self.recent.save()
        ended(self.due, self.red, self.nib, 4)
        invite = InviteCode.objects.create(token="guest-token", label="friend")
        guest = Client()
        guest.post(f"/i/{invite.token}/")
        html = guest.get("/dashboard/").content.decode()
        self.assertIn('class="vsaid is-loved"', html)
        self.assertNotIn("/verdict/", html)
        self.assertNotIn('class="finish-d', html)
        self.assertEqual(guest.post(f"/usages/{self.recent.pk}/verdict/", {"verdict": "never"}).status_code, 302)
        self.recent.refresh_from_db()
        self.assertEqual(self.recent.verdict, "loved")


@override_settings(STORAGES=PLAIN_STATIC)
class TheForm(Seeded):
    def setUp(self):
        self.client.force_login(self.owner)

    def form(self, u, **more):
        return {"pen": u.pen_id, "nib": u.nib_id, "ink": u.ink_id, "begin": u.begin.isoformat(), "end": u.end.isoformat() if u.end else "", **more}

    def test_the_edit_form_says_and_shows_it(self):
        html = self.client.get(f"/usages/{self.old.pk}/edit/").content.decode()
        self.assertIn("How did it write?", html)
        self.assertIn('name="note"', html)
        self.client.post(f"/usages/{self.old.pk}/edit/", self.form(self.old, verdict="never", note="feathers"))
        self.old.refresh_from_db()
        self.assertEqual((self.old.verdict, self.old.note), ("never", "feathers"))
        self.assertIsNotNone(self.old.verdict_at)

    def test_a_new_inking_does_not_ask(self):
        html = self.client.get("/usages/add/").content.decode()
        self.assertNotIn("How did it write?", html)

    def test_the_old_versions_form_keeps_the_verdict(self):
        self.old.verdict, self.old.note = "loved", "smooth"
        self.old.save()
        self.client.post(f"/prev/usages/{self.old.pk}/edit/", self.form(self.old))
        self.old.refresh_from_db()
        self.assertEqual((self.old.verdict, self.old.note, self.old.verdict_at), ("loved", "smooth", None))


@override_settings(STORAGES=PLAIN_STATIC)
class OnThePages(Seeded):
    def setUp(self):
        self.client.force_login(self.owner)
        self.loved = ended(self.due, self.ink, self.nib, 100, verdict="loved", note="wet and dark")
        self.loved2 = ended(self.due, self.ink, self.nib, 40, verdict="loved")
        self.never = ended(self.due, self.red, self.nib, 20, verdict="never", note="dry")

    def test_the_pen_page_lists_what_it_loved_and_what_not(self):
        html = self.client.get(f"/pens/{self.due.pk}/").content.decode()
        self.assertIn("How it wrote", html)
        self.assertIn("Loved with", html)
        self.assertIn("Pelikan · 2×", html)
        self.assertIn("Not again with", html)
        self.assertIn("· dry", html)
        # A loved ink, the pen not inked: one tap inks it again.
        self.assertIn(f"/usages/add/?pen={self.due.pk}&amp;ink={self.ink.pk}", html)

    def test_the_ink_page_lists_the_pens(self):
        html = self.client.get(f"/inks/{self.ink.pk}/").content.decode()
        self.assertIn("How it wrote", html)
        self.assertIn("Loved 2 times", html)
        self.assertIn("Ink it again", html)
        html = self.client.get(f"/inks/{self.red.pk}/").content.decode()
        self.assertIn("Not again", html)

    def test_a_newer_word_wins(self):
        ended(self.due, self.red, self.nib, 5, verdict="loved")
        s = verdicts.shelf(list(Usage.objects.filter(pen=self.due).select_related("ink")), "ink")
        self.assertEqual([v["ink"].pk for v in s.loved], [self.ink.pk, self.red.pk])
        self.assertEqual(s.never, [])

    def test_a_page_with_no_word_has_no_section(self):
        html = self.client.get(f"/pens/{self.pen.pk}/").content.decode()
        self.assertNotIn('id="howItWrote"', html)


@override_settings(STORAGES=PLAIN_STATIC)
class TheInkings(Seeded):
    def setUp(self):
        self.client.force_login(self.owner)
        self.loved = ended(self.due, self.ink, self.nib, 100, verdict="loved", note="lovely shading")
        self.never = ended(self.due, self.red, self.nib, 20, verdict="never")

    def test_a_chip_per_word_with_its_count(self):
        html = self.client.get("/usages/").content.decode()
        self.assertIn('id="verdictChips"', html)
        self.assertIn('href="/usages/?verdict=loved"', html)
        self.assertIn("Loved <b>1</b>", html)
        self.assertIn("Not again <b>1</b>", html)
        self.assertIn("Not said <b>2</b>", html)  # self.old and self.now

    def test_a_chip_filters_and_turns_off(self):
        html = self.client.get("/usages/?verdict=loved").content.decode()
        self.assertIn("lovely shading", html)
        self.assertNotIn("Ruby", html.split('id="verdictChips"')[1].split("</nav>")[1])
        self.assertIn('href="/usages/" class="kit-chip is-loved" aria-current="true"', html)

    def test_not_said(self):
        r = self.client.get("/api/usages?verdict=none").json()
        self.assertEqual({i["id"] for i in r["items"]}, {self.old.pk, self.now.pk})

    def test_a_wrong_word_is_no_filter(self):
        self.assertEqual(self.client.get("/api/usages?verdict=bogus").json()["total"], 4)

    def test_the_search_finds_a_note_and_marks_it(self):
        html = self.client.get("/usages/?q=shading").content.decode()
        self.assertIn("lovely <mark>shading</mark>", html)
        self.assertEqual(self.client.get("/api/usages?q=shading").json()["total"], 1)

    def test_the_chips_keep_the_search_and_the_scope(self):
        html = self.client.get("/usages/?q=pelikan&color=Blue").content.decode()
        self.assertIn('href="/usages/?q=pelikan&amp;color=Blue&amp;verdict=loved"', html)

    def test_the_api_says_it(self):
        items = {i["id"]: i for i in self.client.get("/api/usages").json()["items"]}
        self.assertEqual((items[self.loved.pk]["verdict"], items[self.loved.pk]["note"]), ("loved", "lovely shading"))
        self.assertIsNone(items[self.old.pk]["verdict"])

    def test_nothing_matches(self):
        Usage.objects.filter(verdict="never").update(verdict="")
        html = self.client.get("/usages/?verdict=never").content.decode()
        self.assertIn("No inking matches not again", html)


class ThePicker(Seeded):
    def test_loved_comes_up_and_not_again_goes_down(self):
        third = Ink.objects.create(
            brand=self.ink.brand, name="Olive", color="Green", obtained_from="shop", how="Bought", volume=50, rotation=self.rot, used_up=False
        )
        today = date.today()
        usages = list(Usage.objects.all())
        before = {s.ink.pk: s.score for s in pairing.suggest_inks(self.due, today, usages)}
        ended(self.due, third, self.nib, 300, verdict="loved")
        ended(self.due, self.red, self.nib, 400, verdict="never")
        usages = list(Usage.objects.all())
        ranked = pairing.suggest_inks(self.due, today, usages)
        by = {s.ink.pk: s for s in ranked}
        self.assertGreater(by[third.pk].score, before[third.pk])
        self.assertEqual(ranked[0].ink.pk, third.pk)
        self.assertEqual(ranked[-1].ink.pk, self.red.pk)
        self.assertTrue(any("loved in this pen" in t for _, t in by[third.pk].reasons))
        self.assertIn(("warn", f"✕ not again in this pen, {by[self.red.pk].last_paired:%b %Y}"), by[self.red.pk].reasons)

    def test_other_pens_count_a_little(self):
        ended(self.pen, self.red, self.nib, 300, verdict="loved")
        by = {s.ink.pk: s for s in pairing.suggest_inks(self.due, date.today(), list(Usage.objects.all()))}
        self.assertIn(("good", "loved in 1 other pen"), by[self.red.pk].reasons)

    def test_one_query_for_the_verdicts(self):
        usages = list(Usage.objects.only("pen_id", "ink_id", "begin", "end"))
        ended(self.due, self.red, self.nib, 400, verdict="never")
        with self.assertNumQueries(2):  # the bottles, the verdicts
            pairing.suggest_inks(self.due, date.today(), usages)


@override_settings(STORAGES=PLAIN_STATIC)
class TheStats(Seeded):
    def setUp(self):
        self.client.force_login(self.owner)

    def test_the_plate_asks_while_nothing_is_said(self):
        html = self.client.get("/stats/pairs/").content.decode()
        self.assertIn("How they wrote", html)
        self.assertIn("No fill says yet how it wrote", html)

    def test_a_word_shows_at_once(self):
        self.client.get("/stats/pairs/")
        self.client.post(f"/usages/{self.old.pk}/verdict/", {"verdict": "loved"})
        html = self.client.get("/stats/pairs/").content.decode()
        self.assertIn("<b>1</b> of 1 fills say how they wrote", html)
        self.assertIn("Loved <b>1</b>", html)

    def test_the_numbers(self):
        ended(self.due, self.red, self.nib, 30, verdict="loved")
        ended(self.due, self.red, self.nib, 10, verdict="never")
        ended(self.pen, self.ink, self.nib, 50, verdict="loved")
        s = stats.said_pairs()
        self.assertEqual((s["n"], s["ended"]), (3, 4))
        self.assertEqual([w["n"] for w in s["words"]], [2, 0, 1])
        # The red pairing's newest word is Not again: it leaves the loved list.
        self.assertEqual([(i["pen"].pk, i["ink"].pk) for i in s["loved"]], [(self.pen.pk, self.ink.pk)])
        self.assertEqual([(i["pen"].pk, i["ink"].pk) for i in s["never"]], [(self.due.pk, self.red.pk)])
