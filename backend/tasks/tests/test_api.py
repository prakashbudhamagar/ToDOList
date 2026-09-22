from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

from tasks.models import Todo


class TodoApiTests(APITestCase):
    """The REST API consumed by the React frontend (see tasks/views.py)."""

    def setUp(self):
        self.list_url = reverse('todo-list')
        # The list endpoint caches its response, so no test may start with the
        # cache a previous one left behind.
        cache.clear()

    def test_list_is_empty_initially(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_list_is_ordered_by_priority_then_age(self):
        Todo.objects.create(title='Someday', priority=Todo.Priority.LOW)
        Todo.objects.create(title='Today', priority=Todo.Priority.HIGH)
        Todo.objects.create(title='Soon', priority=Todo.Priority.MEDIUM)

        titles = [task['title'] for task in self.client.get(self.list_url).json()]

        self.assertEqual(titles, ['Today', 'Soon', 'Someday'])

    def test_create_task(self):
        response = self.client.post(self.list_url, {'title': 'Buy milk'}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['title'], 'Buy milk')
        self.assertEqual(Todo.objects.count(), 1)

    def test_create_task_defaults_to_medium_priority(self):
        response = self.client.post(self.list_url, {'title': 'Buy milk'}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['priority'], Todo.Priority.MEDIUM)
        self.assertEqual(response.json()['priority_label'], 'Medium')

    def test_create_task_with_a_priority(self):
        response = self.client.post(
            self.list_url, {'title': 'File the tax return', 'priority': Todo.Priority.HIGH}, format='json'
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['priority'], Todo.Priority.HIGH)
        self.assertEqual(response.json()['priority_label'], 'High')

    def test_create_rejects_a_priority_that_does_not_exist(self):
        response = self.client.post(self.list_url, {'title': 'Buy milk', 'priority': 9}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('priority', response.json())
        self.assertEqual(Todo.objects.count(), 0)

    def test_create_rejects_blank_title(self):
        response = self.client.post(self.list_url, {'title': ''}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'title': ['This field may not be blank.']})
        self.assertEqual(Todo.objects.count(), 0)

    def test_create_rejects_title_longer_than_100_characters(self):
        response = self.client.post(self.list_url, {'title': 'x' * 101}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Todo.objects.count(), 0)

    def test_retrieve_single_task(self):
        todo = Todo.objects.create(title='Buy milk')

        response = self.client.get(reverse('todo-detail', args=[todo.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['title'], 'Buy milk')

    def test_update_then_delete_task(self):
        todo = Todo.objects.create(title='Buy milk')
        detail_url = reverse('todo-detail', args=[todo.pk])

        response = self.client.patch(detail_url, {'title': 'Buy oat milk'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['title'], 'Buy oat milk')

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Todo.objects.count(), 0)

        # A 204 response has no body, so assertContains/assertNotContains can't be
        # used on it (they expect a 200 by default). Check the list instead.
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_patch_changes_the_priority_and_leaves_the_title_alone(self):
        todo = Todo.objects.create(title='Buy milk')
        detail_url = reverse('todo-detail', args=[todo.pk])

        response = self.client.patch(detail_url, {'priority': Todo.Priority.HIGH}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['title'], 'Buy milk')
        self.assertEqual(response.json()['priority'], Todo.Priority.HIGH)
        self.assertEqual(response.json()['priority_label'], 'High')

    def test_list_response_comes_from_the_cache(self):
        Todo.objects.create(title='Buy milk')

        self.assertEqual(len(self.client.get(self.list_url).json()), 1)

        # A write that bypasses the API stays invisible while the cached entry is
        # valid, which proves the second call did not hit the database.
        Todo.objects.create(title='Walk the dog')

        self.assertEqual(len(self.client.get(self.list_url).json()), 1)

    def test_create_clears_the_cached_list(self):
        self.client.get(self.list_url)
        self.client.post(self.list_url, {'title': 'Buy milk'}, format='json')

        self.assertEqual(len(self.client.get(self.list_url).json()), 1)

    def test_update_and_delete_clear_the_cached_list(self):
        todo = Todo.objects.create(title='Buy milk')
        detail_url = reverse('todo-detail', args=[todo.pk])
        self.client.get(self.list_url)

        self.client.patch(detail_url, {'title': 'Buy oat milk'}, format='json')
        self.assertEqual(self.client.get(self.list_url).json()[0]['title'], 'Buy oat milk')

        self.client.delete(detail_url)