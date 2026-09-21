from django.test import SimpleTestCase

from tasks.estimates import format_minutes, estimate_minutes


class EstimateMinutesTests(SimpleTestCase):
    """The heuristic behind the assistant's 'this should take about ...' answers."""

    def test_one_word_errand_is_quick(self):
        self.assertEqual(estimate_minutes('Groceries'), 15)

    def test_more_words_mean_more_scope(self):
        short = estimate_minutes('Groceries')
        longer = estimate_minutes('Repaint the hallway and the stairwell')

        self.assertGreater(longer, short)

    def test_quick_hint_caps_even_a_long_title(self):
        minutes = estimate_minutes('call the plumber about the leaking kitchen tap')

        self.assertEqual(minutes, 15)

    def test_deep_task_gets_at_least_a_working_session(self):
        self.assertGreaterEqual(estimate_minutes('write report'), 60)

    def test_estimate_never_exceeds_the_cap(self):
        minutes = estimate_minutes('write ' + 'very ' * 40 + 'long report')

        self.assertEqual(minutes, 240)

    def test_missing_title_still_gets_an_estimate(self):
        self.assertEqual(estimate_minutes(''), 15)
        self.assertEqual(estimate_minutes(None), 15)


class FormatMinutesTests(SimpleTestCase):
    """What the assistant reads out for a duration."""

    def test_under_an_hour(self):
        self.assertEqual(format_minutes(45), '~45 min')

    def test_whole_hours(self):
        self.assertEqual(format_minutes(120), '~2 h')

    def test_hours_and_minutes(self):
        self.assertEqual(format_minutes(90), '~1 h 30 min')