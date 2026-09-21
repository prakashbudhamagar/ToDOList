import copy
from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from tasks.models import Todo


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
        with patch('chat.agent._generate', return_value=fake_reply):
            response = self.client.post(self.chat_url, {'message': 'hi'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['reply'], 'Hello!')
        self.assertEqual(response.json()['actions'], [])

    def test_chat_creates_a_task(self):
        first = {'candidates': [{'content': {'parts': [
            {'functionCall': {'name': 'create_task', 'args': {'title': 'Buy milk'}}},
        ]}}]}
        second = {'candidates': [{'content': {'parts': [
            {'text': 'Added "Buy milk" to your list.'},
        ]}}]}
        with patch('chat.agent._generate', side_effect=[first, second]):
            response = self.client.post(self.chat_url, {'message': 'add buy milk'}, format='json')

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['actions'][0]['tool'], 'create_task')
        self.assertEqual(body['actions'][0]['result']['title'], 'Buy milk')

    def test_chat_recommends_tasks_with_estimates(self):
        Todo.objects.create(title='Oldest task')
        Todo.objects.create(title='Newer task')
        first = {'candidates': [{'content': {'parts': [
            {'functionCall': {'name': 'recommend_tasks', 'args': {}}},
        ]}}]}
        second = {'candidates': [{'content': {'parts': [
            {'text': 'Start with "Oldest task" - it has been waiting longest.'},
        ]}}]}
        with patch('chat.agent._generate', side_effect=[first, second]):
            response = self.client.post(
                self.chat_url, {'message': 'what should I do next?'}, format='json'
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['actions'][0]['tool'], 'recommend_tasks')
        self.assertEqual(body['actions'][0]['result']['total'], 2)
        focus = body['actions'][0]['result']['focus_next']
        self.assertEqual([task['title'] for task in focus], ['Oldest task', 'Newer task'])
        # Every recommendation carries the priority and how long it may take.
        self.assertEqual(focus[0]['priority'], 'Medium')
        self.assertEqual(focus[0]['estimate_minutes'], 25)
        self.assertEqual(focus[0]['estimate'], '~25 min')

    def test_chat_recommends_urgent_tasks_first_with_longer_estimates(self):
        Todo.objects.create(title='Reply to the landlord', priority=Todo.Priority.LOW)
        Todo.objects.create(title='Write the project report', priority=Todo.Priority.HIGH)
        first = {'candidates': [{'content': {'parts': [
            {'functionCall': {'name': 'recommend_tasks', 'args': {}}},
        ]}}]}
        second = {'candidates': [{'content': {'parts': [
            {'text': 'Do the report first - about an hour - then the reply.'},
        ]}}]}
        with patch('chat.agent._generate', side_effect=[first, second]):
            response = self.client.post(
                self.chat_url, {'message': 'what should I do next?'}, format='json'
            )

        focus = response.json()['actions'][0]['result']['focus_next']
        self.assertEqual(
            [task['title'] for task in focus],
            ['Write the project report', 'Reply to the landlord'],
        )
        self.assertEqual(focus[0]['priority'], 'High')
        self.assertEqual(focus[0]['estimate'], '~1 h')
        self.assertEqual(focus[1]['estimate'], '~15 min')

    def test_chat_creates_a_task_with_a_priority(self):
        first = {'candidates': [{'content': {'parts': [
            {'functionCall': {
                'name': 'create_task',
                'args': {'title': 'File taxes', 'priority': 'high'},
            }},
        ]}}]}
        second = {'candidates': [{'content': {'parts': [
            {'text': 'Added "File taxes" as a high priority task.'},
        ]}}]}
        with patch('chat.agent._generate', side_effect=[first, second]):
            response = self.client.post(
                self.chat_url, {'message': 'add file taxes, high priority'}, format='json'
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['actions'][0]['result']['priority'], 'High')
        self.assertEqual(Todo.objects.get().priority, Todo.Priority.HIGH)

    def test_chat_reports_a_priority_it_does_not_understand(self):
        first = {'candidates': [{'content': {'parts': [
            {'functionCall': {
                'name': 'create_task',
                'args': {'title': 'Buy milk', 'priority': 'urgent'},
            }},
        ]}}]}
        second = {'candidates': [{'content': {'parts': [{'text': 'Let me try again.'}]}}]}
        with patch('chat.agent._generate', side_effect=[first, second]):
            response = self.client.post(
                self.chat_url, {'message': 'add buy milk as urgent'}, format='json'
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn('priority', response.json()['actions'][0]['result']['error'])
        self.assertEqual(Todo.objects.count(), 0)

    def test_chat_updates_only_the_priority(self):
        todo = Todo.objects.create(title='Buy milk')
        first = {'candidates': [{'content': {'parts': [
            {'functionCall': {
                'name': 'update_task',
                'args': {'id': todo.pk, 'priority': 'high'},
            }},
        ]}}]}
        second = {'candidates': [{'content': {'parts': [
            {'text': 'Bumped "Buy milk" to high priority.'},
        ]}}]}
        with patch('chat.agent._generate', side_effect=[first, second]):
            response = self.client.post(
                self.chat_url, {'message': 'make buy milk high priority'}, format='json'
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['actions'][0]['result']['priority'], 'High')
        todo.refresh_from_db()
        self.assertEqual(todo.title, 'Buy milk')
        self.assertEqual(todo.priority, Todo.Priority.HIGH)

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

        with patch('chat.agent._generate', side_effect=fake_generate):
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

        with patch('chat.agent._generate', side_effect=fake_generate):
            response = self.client.post(self.chat_url, {'message': 'add buy milk'}, format='json')

        self.assertEqual(response.status_code, 200)
        echo = seen_payloads[1]['contents'][1]
        self.assertEqual(echo['role'], 'model')
        call_part = next(p for p in echo['parts'] if 'functionCall' in p)
        self.assertEqual(call_part.get('thoughtSignature'), 'sig-123')
        self.assertTrue(any('text' in p for p in echo['parts']))