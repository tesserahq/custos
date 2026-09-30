"""Architecture guards for transaction ownership, provided by
tessera_sdk.testing.transaction_guards (see docs/managed-transactions.md in
tessera-sdk-py).

Rules with violations recorded in ``transaction_baseline.json`` may not
regress; a rule with no entry is fully enforced. Regenerate the baseline with
``UPDATE_TRANSACTION_BASELINE=1`` only after removing violations.
"""

from pathlib import Path

import pytest
from tessera_sdk.testing.transaction_guards import (
    DEFAULT_TRANSACTION_DIRS,
    RULE_NAMES,
    TransactionGuardConfig,
    assert_matches_baseline,
)

CONFIG = TransactionGuardConfig(
    app_root=Path(__file__).parents[2] / "app",
    baseline_path=Path(__file__).with_name("transaction_baseline.json"),
    transaction_dirs=(*DEFAULT_TRANSACTION_DIRS, "middleware", "core"),
    session_modules=("db.py", "services/sdk_user_service.py"),
    repository_base_modules=(),
    # Allowlisted top-level workflows that commit early around external I/O:
    # (path relative to app/, function name) -> reason.
    early_commit_allowlist={},
)


@pytest.mark.parametrize("rule", RULE_NAMES)
def test_transaction_rule_matches_baseline(rule):
    assert_matches_baseline(CONFIG, rule)
