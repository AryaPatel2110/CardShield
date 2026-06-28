from __future__ import annotations

import unittest

from cassandra_repository import SHARD_COUNT, transaction_shard


class RepositoryTests(unittest.TestCase):
    def test_transaction_shard_is_stable_and_bounded(self) -> None:
        first = transaction_shard("transaction-123")
        second = transaction_shard("transaction-123")

        self.assertEqual(first, second)
        self.assertGreaterEqual(first, 0)
        self.assertLess(first, SHARD_COUNT)


if __name__ == "__main__":
    unittest.main()
