from unittest.mock import patch
import copy

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from todo_list.models import Todo


class TodoApiTests(APITestCase):
    """The REST API consumed by the React frontend (see todo_list/views.py)."""

    def setUp(self):
        self.list_url = reverse('todo-list')
        # The list endpoint caches its response, so no test may start with the
        # cache a previous one left behind.
        cache.clear()

    def test_list_is_empty_initially(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_create_task(self):
        response = self.client.post(self.list_url, {'title': 'Buy milk'}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['title'], 'Buy milk')
        self.assertEqual(Todo.objects.count(), 1)

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

    def test_csrf_endpoint_sets_the_cookie(self):
        response = self.client.get(reverse('api-csrf'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('csrftoken', response.cookies)

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


@override_settings(GEMINI_API_KEY='test-key')
class ChatApiTests(APITestCase):
    """POST /api/chat/ - the Gemini-backed assistant (Gemini calls are stubbed)."""

    def setUp(self):
        self.chat_url = reverse('api-chat')
        cache.clear()

    def test_chat_rejects_empty_message(self):
        response = self.client.post(self.chat_url, {'message': '  '}, format='json')

        self.assertEqual(response.status_code, 400)

    def test_chat_replies_without_tools(self):
        fake_reply = {'candidates': [{'content': {'parts': [{'text': 'Hello!'}]}}]}
        with patch('todo_list.agent._generate', return_value=fake_reply):
            response = self.client.post(self.chat_url, {'message': 'hi'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'reply': 'Hello!', 'actions': []})

    def test_chat_runs_create_tool_then_answers(self):
        first = {'candidates': [{'content': {'parts': [
            {'functionCall': {'name': 'create_task', 'args': {'title': 'Buy milk'}}},
        ]}}]}
        second = {'candidates': [{'content': {'parts': [
            {'text': 'Added "Buy milk" to your list.'},
        ]}}]}
        with patch('todo_list.agent._generate', side_effect=[first, second]):
            response = self.client.post(self.chat_url, {'message': 'add buy milk'}, format='json')

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['reply'], 'Added "Buy milk" to your list.')
        self.assertEqual(body['actions'][0]['tool'], 'create_task')
        self.assertEqual(Todo.objects.count(), 1)
        self.assertEqual(Todo.objects.get().title, 'Buy milk')

    def test_chat_runs_recommend_tool_for_what_next(self):
        Todo.objects.create(title='Oldest task')
        Todo.objects.create(title='Newest task')
        first = {'candidates': [{'content': {'parts': [
            {'functionCall': {'name': 'recommend_tasks', 'args': {}}},
        ]}}]}
        second = {'candidates': [{'content': {'parts': [
            {'text': 'Start with "Oldest task" - it has been waiting longest.'},
        ]}}]}
        with patch('todo_list.agent._generate', side_effect=[first, second]):
            response = self.client.post(
                self.chat_url, {'message': 'what should I do next?'}, format='json'
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['actions'][0]['tool'], 'recommend_tasks')
        self.assertEqual(body['actions'][0]['result']['total'], 2)
        self.assertEqual(body['actions'][0]['result']['focus_next'][0]['title'], 'Oldest task')

    def test_chat_without_key_reports_503(self):
        with override_settings(GEMINI_API_KEY=''):
            response = self.client.post(self.chat_url, {'message': 'hi'}, format='json')

        self.assertEqual(response.status_code, 503)
        self.assertIn('GEMINI_API_KEY', response.json()['detail'])


    def test_tool_results_are_sent_back_as_user_role(self):
        # Regression test: newer Gemini models reject role 'function' and only
        # accept user/model, so tool results must go back as 'user'.
        first = {'candidates': [{'content': {'parts': [
            {'functionCall': {'name': 'list_tasks', 'args': {}}},
        ]}}]}
        second = {'candidates': [{'content': {'parts': [{'text': 'Here you go.'}]}}]}
        seen_payloads = []

        def fake_generate(payload, api_key, model):
            seen_payloads.append(payload)
            return first if len(seen_payloads) == 1 else second

        with patch('todo_list.agent._generate', side_effect=fake_generate):
            response = self.client.post(self.chat_url, {'message': 'list my tasks'}, format='json')

        self.assertEqual(response.status_code, 200)
        tool_turn = seen_payloads[1]['contents'][-1]
        self.assertEqual(tool_turn['role'], 'user')
        self.assertIn('functionResponse', tool_turn['parts'][0])
        roles = {turn['role'] for turn in seen_payloads[1]['contents']}
        self.assertTrue(roles <= {'user', 'model'})
    def test_model_parts_are_echoed_verbatim_with_thought_signature(self):
        # Regression test: gemini-3.x rejects the follow-up call when the model's
        # thoughtSignature is dropped, so the model turn must echo the original
        # parts verbatim (including any free-standing text, which carries its own
        # signature coverage).
        first = {'candidates': [{'content': {'parts': [
            {'text': 'On it.'},
            {'functionCall': {'name': 'create_task', 'args': {'title': 'Buy milk'}},
             'thoughtSignature': 'sig-123'},
        ]}}]}
        second = {'candidates': [{'content': {'parts': [{'text': 'Added it.'}]}}]}
        seen_payloads = []

        def fake_generate(payload, api_key, model):
            seen_payloads.append(copy.deepcopy(payload))
            return first if len(seen_payloads) == 1 else second

        with patch('todo_list.agent._generate', side_effect=fake_generate):
            response = self.client.post(self.chat_url, {'message': 'add buy milk'}, format='json')

        self.assertEqual(response.status_code, 200)
        echo = seen_payloads[1]['contents'][1]
        self.assertEqual(echo['role'], 'model')
        call_part = next(p for p in echo['parts'] if 'functionCall' in p)
        self.assertEqual(call_part.get('thoughtSignature'), 'sig-123')
        self.assertTrue(any('text' in p for p in echo['parts']))

