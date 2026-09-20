from django.test import TestCase

from todo_list.models import Todo


class TodoModelTests(TestCase):
    def test_str_returns_title(self):
        todo = Todo.objects.create(title='Buy milk')

        self.assertEqual(str(todo), 'Buy milk')

    def test_create_at_is_set_automatically(self):
        todo = Todo.objects.create(title='Buy milk')

        self.assertIsNotNone(todo.create_at)
