import os
import shutil
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from config.settings import load_dotenv

# Resolved now, while the real environment is still intact: the tests below clear
# os.environ, which would otherwise make tempfile fall back to the current
# directory - and keep using it for the rest of the process.
TEMP_ROOT = tempfile.gettempdir()


class CsrfEndpointTests(APITestCase):
    """The shared /api/csrf/ endpoint the React API client calls before writes."""

    def test_csrf_endpoint_sets_the_cookie(self):
        response = self.client.get(reverse('api-csrf'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('csrftoken', response.cookies)


class LoadDotenvTests(SimpleTestCase):
    """The dependency-free .env reader in config/settings.py."""

    def make_temp_dir(self):
        """A throwaway directory that is deleted when the test finishes."""
        path = tempfile.mkdtemp(dir=TEMP_ROOT)
        self.addCleanup(shutil.rmtree, path, ignore_errors=True)
        return path

    def write_env(self, text):
        """A temporary .env file holding `text`."""
        path = os.path.join(self.make_temp_dir(), '.env')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        return path

    def test_reads_key_value_pairs(self):
        with patch.dict(os.environ, {}, clear=True):
            load_dotenv(self.write_env('GEMINI_API_KEY=abc123\n'))

            self.assertEqual(os.environ['GEMINI_API_KEY'], 'abc123')

    def test_real_environment_wins_over_the_file(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'from-env'}, clear=True):
            load_dotenv(self.write_env('GEMINI_API_KEY=from-file\n'))

            self.assertEqual(os.environ['GEMINI_API_KEY'], 'from-env')

    def test_blank_placeholder_does_not_hide_the_file_value(self):
        """Docker sets GEMINI_API_KEY="" when the host shell has no copy of it."""
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}, clear=True):
            load_dotenv(self.write_env('GEMINI_API_KEY=from-file\n'))

            self.assertEqual(os.environ['GEMINI_API_KEY'], 'from-file')

    def test_comments_quotes_and_blank_lines(self):
        with patch.dict(os.environ, {}, clear=True):
            load_dotenv(self.write_env(
                '# comment\n\nGEMINI_MODEL="gemini-3.6-flash"\nnot-a-pair\n'
            ))

            self.assertEqual(sorted(os.environ), ['GEMINI_MODEL'])
            self.assertEqual(os.environ['GEMINI_MODEL'], 'gemini-3.6-flash')

    def test_missing_file_is_not_an_error(self):
        with patch.dict(os.environ, {}, clear=True):
            load_dotenv(os.path.join(self.make_temp_dir(), 'missing.env'))

            self.assertEqual(os.environ, {})
