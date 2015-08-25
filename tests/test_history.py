from unittest import TestCase

import semantic_release
from semantic_release.history import (evaluate_version_bump, get_current_version, get_new_version,
                                      get_previous_version)
from semantic_release.history.logs import generate_changelog, markdown_changelog

from . import mock

MAJOR = 'feat(x): Add super-feature\n\nBREAKING CHANGE: Uses super-feature as default instead of ' \
        'dull-feature.'
MAJOR2 = 'feat(x): Add super-feature\n\nSome explanation\n\n' \
         'BREAKING CHANGE: Uses super-feature as default instead of ' \
         'dull-feature.'
MINOR = 'feat(x): Add non-breaking super-feature'
PATCH = 'fix(x): Fix bug in super-feature'
NO_TAG = 'docs(x): Add documentation for super-feature'
UNKNOWN_STYLE = 'random commits are the worst'

ALL_KINDS_OF_COMMIT_MESSAGES = [MINOR, MAJOR, MINOR, PATCH]
MINOR_AND_PATCH_COMMIT_MESSAGES = [MINOR, PATCH]
PATCH_COMMIT_MESSAGES = [PATCH, PATCH]
MAJOR_LAST_RELEASE_MINOR_AFTER = [MINOR, '1.1.0', MAJOR]


class EvaluateVersionBumpTest(TestCase):
    def test_major(self):
        with mock.patch('semantic_release.history.logs.get_commit_log',
                        lambda: ALL_KINDS_OF_COMMIT_MESSAGES):
            self.assertEqual(evaluate_version_bump('0.0.0'), 'major')

    def test_minor(self):
        with mock.patch('semantic_release.history.logs.get_commit_log',
                        lambda: MINOR_AND_PATCH_COMMIT_MESSAGES):
            self.assertEqual(evaluate_version_bump('0.0.0'), 'minor')

    def test_patch(self):
        with mock.patch('semantic_release.history.logs.get_commit_log',
                        lambda: PATCH_COMMIT_MESSAGES):
            self.assertEqual(evaluate_version_bump('0.0.0'), 'patch')

    def test_nothing_if_no_tag(self):
        with mock.patch('semantic_release.history.logs.get_commit_log', lambda: ['', '...']):
            self.assertIsNone(evaluate_version_bump('0.0.0'))

    def test_force(self):
        self.assertEqual(evaluate_version_bump('0.0.0', 'major'), 'major')
        self.assertEqual(evaluate_version_bump('0.0.0', 'minor'), 'minor')
        self.assertEqual(evaluate_version_bump('0.0.0', 'patch'), 'patch')

    def test_should_account_for_commits_earlier_than_last_commit(self):
        with mock.patch('semantic_release.history.logs.get_commit_log',
                        lambda: MAJOR_LAST_RELEASE_MINOR_AFTER):
            self.assertEqual(evaluate_version_bump('1.1.0'), 'minor')

    @mock.patch('semantic_release.history.config.getboolean', lambda *x: True)
    @mock.patch('semantic_release.history.logs.get_commit_log', lambda: [NO_TAG])
    def test_should_patch_without_tagged_commits(self):
        self.assertEqual(evaluate_version_bump('1.1.0'), 'patch')

    @mock.patch('semantic_release.history.config.getboolean', lambda *x: False)
    @mock.patch('semantic_release.history.logs.get_commit_log', lambda: [NO_TAG])
    def test_should_return_none_without_tagged_commits(self):
        self.assertIsNone(evaluate_version_bump('1.1.0'))

    @mock.patch('semantic_release.history.logs.get_commit_log', lambda: [])
    def test_should_return_none_without_commits(self):
        """
        Make sure that we do not release if there are no commits since last release.
        """
        with mock.patch('semantic_release.history.config.getboolean', lambda *x: True):
            self.assertIsNone(evaluate_version_bump('1.1.0'))

        with mock.patch('semantic_release.history.config.getboolean', lambda *x: False):
            self.assertIsNone(evaluate_version_bump('1.1.0'))


class GenerateChangelogTests(TestCase):
    def test_should_generate_all_sections(self):
        with mock.patch('semantic_release.history.logs.get_commit_log',
                        lambda: ALL_KINDS_OF_COMMIT_MESSAGES + [MAJOR2, UNKNOWN_STYLE]):
            changelog = generate_changelog('0.0.0')
            self.assertIn('feature', changelog)
            self.assertIn('fix', changelog)
            self.assertIn('documentation', changelog)
            self.assertIn('breaking', changelog)
            self.assertGreater(len(changelog['feature']), 0)
            self.assertGreater(len(changelog['fix']), 0)
            self.assertGreater(len(changelog['breaking']), 0)

    def test_should_only_read_until_given_version(self):
        with mock.patch('semantic_release.history.logs.get_commit_log',
                        lambda: MAJOR_LAST_RELEASE_MINOR_AFTER):
            changelog = generate_changelog('1.1.0')
            self.assertGreater(len(changelog['feature']), 0)
            self.assertEqual(len(changelog['fix']), 0)
            self.assertEqual(len(changelog['documentation']), 0)
            self.assertEqual(len(changelog['breaking']), 0)

    def test_should_skip_style_changes(self):
        with mock.patch('semantic_release.history.logs.get_commit_log',
                        lambda: PATCH_COMMIT_MESSAGES + ['style(x): change x']):
            changelog = generate_changelog('0.0.0')
            self.assertNotIn('style', changelog)

    def test_should_skip_chore_changes(self):
        with mock.patch('semantic_release.history.logs.get_commit_log',
                        lambda: PATCH_COMMIT_MESSAGES + ['chore(x): change x']):
            changelog = generate_changelog('0.0.0')
            self.assertNotIn('chore', changelog)


def test_current_version_should_return_correct_version():
    self.assertEqual(get_current_version(), semantic_release.__version__)


class GetPreviousVersionTests(TestCase):

    @mock.patch('semantic_release.history.get_commit_log', lambda: ['0.10.0', '0.9.0'])
    def test_should_return_correct_version(self):
        self.assertEqual(get_previous_version('0.10.0'), '0.9.0')

    @mock.patch('semantic_release.history.get_commit_log', lambda: ['v0.10.0', 'v0.9.0'])
    def test_should_return_correct_version_with_v(self):
        self.assertEqual(get_previous_version('0.10.0'), '0.9.0')


class GetNewVersionTests(TestCase):
    def test_major_bump(self):
        self.assertEqual(get_new_version('0.0.0', 'major'), '1.0.0')
        self.assertEqual(get_new_version('0.1.0', 'major'), '1.0.0')
        self.assertEqual(get_new_version('0.1.9', 'major'), '1.0.0')
        self.assertEqual(get_new_version('10.1.0', 'major'), '11.0.0')

    def test_minor_bump(self):
        self.assertEqual(get_new_version('0.0.0', 'minor'), '0.1.0')
        self.assertEqual(get_new_version('1.2.0', 'minor'), '1.3.0')
        self.assertEqual(get_new_version('1.2.1', 'minor'), '1.3.0')
        self.assertEqual(get_new_version('10.1.0', 'minor'), '10.2.0')

    def test_patch_bump(self):
        self.assertEqual(get_new_version('0.0.0', 'patch'), '0.0.1')
        self.assertEqual(get_new_version('0.1.0', 'patch'), '0.1.1')
        self.assertEqual(get_new_version('10.0.9', 'patch'), '10.0.10')

    def test_none_bump(self):
        self.assertEqual(get_new_version('1.0.0', None), '1.0.0')


class MarkdownChangelogTests(TestCase):
    def test_should_output_all_sections(self):
        markdown = markdown_changelog('0', {
            'refactor': ['Refactor super-feature'],
            'breaking': ['Uses super-feature as default instead of dull-feature.'],
            'feature': ['Add non-breaking super-feature', 'Add super-feature'],
            'fix': ['Fix bug in super-feature'],
            'documentation': ['Document super-feature']
        })
        self.assertEqual(
            markdown,
            '\n'
            '### Feature\n'
            '* Add non-breaking super-feature\n'
            '* Add super-feature\n'
            '\n'
            '### Fix\n'
            '* Fix bug in super-feature\n'
            '\n'
            '### Breaking\n'
            '* Uses super-feature as default instead of dull-feature.\n'
            '\n'
            '### Documentation\n'
            '* Document super-feature\n'
        )

    def test_should_not_include_empty_sections(self):
        self.assertEqual(
            markdown_changelog(
                '1.0.1',
                {'refactor': [], 'breaking': [], 'feature': [], 'fix': [], 'documentation': []},
            ),
            ''
        )

    def test_should_output_heading(self):
        self.assertIn(
            '## v1.0.1\n',
            markdown_changelog(
                '1.0.1',
                {'refactor': [], 'breaking': [], 'feature': [], 'fix': [], 'documentation': []},
                header=True
            )
        )

    def test_should_not_output_heading(self):
        self.assertNotIn(
            'v1.0.1',
            markdown_changelog(
                '1.0.1',
                {'refactor': [], 'breaking': [], 'feature': [], 'fix': [], 'documentation': []},
            )
        )
