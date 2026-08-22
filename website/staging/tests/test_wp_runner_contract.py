from __future__ import annotations

import re
import unittest
from pathlib import Path


RUNNER = Path(__file__).resolve().parents[1] / "p1-7-wp-runner.sh"


class WordPressRunnerContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = RUNNER.read_text(encoding="utf-8")

    def test_dry_run_is_default(self) -> None:
        self.assertIn('execute=0', self.source)
        self.assertRegex(self.source, r'if \[\[ "\$execute" != 1 \]\]; then')

    def test_production_host_is_forbidden(self) -> None:
        self.assertIn('FORBIDDEN_PRODUCTION_HOST="theobserverofmultiverses.info"', self.source)
        self.assertIn('Refusing to target the production/Gravatar domain.', self.source)
        self.assertIn('EXPECTED_STAGING_SUFFIX=".wpcomstaging.com"', self.source)
        self.assertIn('staging-*"$EXPECTED_STAGING_SUFFIX"', self.source)

    def test_execute_requires_external_restore_and_access_evidence(self) -> None:
        mutation = self.source.index('wp plugin install "$plugin_zip"')
        for marker in ('restore_proof_id', 'access_proof_id', 'Mutation mode requires sanitized'):
            with self.subTest(marker=marker):
                self.assertLess(self.source.index(marker), mutation)

    def test_all_guards_precede_first_mutation(self) -> None:
        mutation = self.source.index('wp plugin install "$plugin_zip"')
        required_before_mutation = (
            'actual_plugin_sha=',
            'wp_get_environment_type',
            'actual_home=',
            'actual_siteurl=',
            'is_multisite()',
            'blog_public',
            'wp plugin is-installed observer-research-registry',
            'p1-7-environment-probe.php',
            'if [[ "$execute" != 1 ]]',
        )
        for marker in required_before_mutation:
            with self.subTest(marker=marker):
                self.assertLess(self.source.index(marker), mutation)

    def test_runner_never_publishes_or_changes_domain(self) -> None:
        forbidden_commands = (
            "wp post update",
            "--post_status=publish",
            "wp option update home",
            "wp option update siteurl",
            "wp rewrite structure",
            "wp search-replace",
        )
        for command in forbidden_commands:
            with self.subTest(command=command):
                self.assertNotIn(command, self.source)

    def test_exact_release_hash_is_bound(self) -> None:
        hashes = re.findall(r"[0-9a-f]{64}", self.source)
        self.assertIn(
            "0d29a680f9aa478d2da3167b64bdbd0570839b2fd7cf9168159e8d4317e3e3d7",
            hashes,
        )

    def test_both_sync_results_are_asserted(self) -> None:
        self.assertIn('assert_status_actions "$evidence_dir/registry-status-before.json" create', self.source)
        self.assertIn('assert_sync_counts "$evidence_dir/registry-sync-first.log" 5 0 0', self.source)
        self.assertIn('assert_sync_counts "$evidence_dir/registry-sync-second.log" 0 0 5', self.source)
        self.assertEqual(2, self.source.count('assert_status_actions "$evidence_dir/registry-status-after-'))


if __name__ == "__main__":
    unittest.main()
