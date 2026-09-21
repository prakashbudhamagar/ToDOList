from django.test import TestCase

from tasks.models import Todo


class TodoModelTests(TestCase):
    def test_str_returns_title(self):
        todo = Todo.objects.create(title='Buy milk')

        self.assertEqual(str(todo), 'Buy milk')

    def test_create_at_is_set_automatically(self):
        todo = Todo.objects.create(title='Buy milk')

        self.assertIsNotNone(todo.create_at)

    def test_priority_defaults_to_medium(self):
        todo = Todo.objects.create(title='Buy milk')

        self.assertEqual(todo.priority, Todo.Priority.MEDIUM)
        self.assertEqual(todo.get_priority_display(), 'Medium')

    def test_tasks_are_ordered_by_priority_then_age(self):
        Todo.objects.create(title='Someday', priority=Todo.Priority.LOW)
        Todo.objects.create(title='Today', priority=Todo.Priority.HIGH)
        Todo.objects.create(title='Soon', priority=Todo.Priority.MEDIUM)

        titles = [todo.title for todo in Todo.objects.all()]

        self.assertEqual(titles, ['Today', 'Soon', 'Someday'])

    def test_parse_priority_accepts_names_labels_and_numbers(self):
        for value in ('high', 'HIGH', 'High', '3', 3, Todo.Priority.HIGH):
            self.assertEqual(Todo.parse_priority(value), Todo.Priority.HIGH)

    def test_parse_priority_rejects_values_that_are_not_a_priority(self):
        # True is an int in Python but never means a priority.
        for value in ('urgent', 'lowest', '', None, 9, True, []):
            self.assertIsNone(Todo.parse_priority(value))