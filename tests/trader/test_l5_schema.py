"""Tests for spec #7 Task 2: ExecutionState + FillEvent schema + back-compat."""
import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dataclasses import asdict
from tools._lib.current_trade import (
    ExecutionState, FillEvent, ListItem, _parse_list_item
)


class FillEventTest(unittest.TestCase):

    def test_fields(self):
        fe = FillEvent(ts="2026-04-24T09:12:00+07:00", lot=50, price=1855.0,
                       order_id="CR-12345", leg="entry")
        self.assertEqual(fe.ts, "2026-04-24T09:12:00+07:00")
        self.assertEqual(fe.lot, 50)
        self.assertEqual(fe.price, 1855.0)
        self.assertEqual(fe.order_id, "CR-12345")
        self.assertEqual(fe.leg, "entry")

    def test_roundtrip(self):
        fe = FillEvent(ts="2026-04-24T09:12:00+07:00", lot=50, price=1855.0,
                       order_id="CR-12345", leg="entry")
        fe2 = FillEvent(**asdict(fe))
        self.assertEqual(fe, fe2)


class ExecutionStateTest(unittest.TestCase):

    def test_defaults(self):
        ex = ExecutionState()
        self.assertEqual(ex.status, "pending")
        self.assertEqual(ex.path, "")
        self.assertIsNone(ex.entry_order_id)
        self.assertIsNone(ex.stop_order_id)
        self.assertIsNone(ex.tp1_order_id)
        self.assertIsNone(ex.tp2_order_id)
        self.assertEqual(ex.fills, [])
        self.assertEqual(ex.last_check, "")
        self.assertIsNone(ex.last_error)

    def test_placed(self):
        ex = ExecutionState(status="placed", path="pre_open",
                            entry_order_id="CR-12345",
                            last_check="2026-04-24T08:31:05+07:00")
        self.assertEqual(ex.status, "placed")
        self.assertEqual(ex.path, "pre_open")
        self.assertEqual(ex.entry_order_id, "CR-12345")

    def test_fills_isolated(self):
        ex1 = ExecutionState()
        ex2 = ExecutionState()
        ex1.fills.append(FillEvent(ts="t", lot=10, price=100.0,
                                   order_id="x", leg="entry"))
        self.assertEqual(ex2.fills, [])

    def test_all_statuses(self):
        for s in ("pending", "placed", "partial", "filled",
                  "cancelled", "failed", "closed"):
            ex = ExecutionState(status=s)
            self.assertEqual(ex.status, s)

    def test_all_paths(self):
        for p in ("pre_open", "intraday", "reconcile"):
            ex = ExecutionState(path=p)
            self.assertEqual(ex.path, p)

    def test_asdict_roundtrip(self):
        fe = FillEvent(ts="2026-04-24T09:12:00+07:00", lot=50, price=1855.0,
                       order_id="CR-12345", leg="entry")
        ex = ExecutionState(
            status="filled", path="pre_open",
            entry_order_id="CR-12345", stop_order_id="CR-12346",
            fills=[fe], last_check="2026-04-24T09:30:00+07:00"
        )
        d = asdict(ex)
        self.assertEqual(d["fills"][0]["leg"], "entry")
        self.assertEqual(d["status"], "filled")


class ListItemExecutionFieldTest(unittest.TestCase):

    def test_default_none(self):
        item = ListItem(ticker="ADMR", confidence=80)
        self.assertIsNone(item.execution)

    def test_set(self):
        ex = ExecutionState(status="placed", entry_order_id="CR-12345",
                            path="pre_open")
        item = ListItem(ticker="ADMR", confidence=80, execution=ex)
        self.assertEqual(item.execution.status, "placed")
        self.assertEqual(item.execution.entry_order_id, "CR-12345")


class ParseListItemExecutionTest(unittest.TestCase):

    def test_no_execution_key(self):
        item = _parse_list_item({"ticker": "ADMR", "confidence": 80})
        self.assertIsNone(item.execution)

    def test_execution_null(self):
        item = _parse_list_item({"ticker": "ADMR", "confidence": 80,
                                 "execution": None})
        self.assertIsNone(item.execution)

    def test_execution_placed(self):
        d = {
            "ticker": "ADMR", "confidence": 80,
            "execution": {
                "status": "placed", "path": "pre_open",
                "entry_order_id": "CR-12345",
                "stop_order_id": None, "tp1_order_id": None,
                "tp2_order_id": None, "fills": [],
                "last_check": "2026-04-24T08:31:05+07:00",
                "last_error": None,
            }
        }
        item = _parse_list_item(d)
        self.assertIsNotNone(item.execution)
        self.assertEqual(item.execution.status, "placed")
        self.assertEqual(item.execution.entry_order_id, "CR-12345")
        self.assertEqual(item.execution.fills, [])

    def test_execution_with_fills(self):
        d = {
            "ticker": "ADMR", "confidence": 80,
            "execution": {
                "status": "filled", "path": "pre_open",
                "entry_order_id": "CR-12345",
                "stop_order_id": "CR-12346",
                "tp1_order_id": "CR-12347",
                "tp2_order_id": None,
                "fills": [
                    {"ts": "2026-04-24T09:12:00+07:00", "lot": 50,
                     "price": 1855.0, "order_id": "CR-12345", "leg": "entry"}
                ],
                "last_check": "2026-04-24T09:30:00+07:00",
                "last_error": None,
            }
        }
        item = _parse_list_item(d)
        self.assertEqual(item.execution.status, "filled")
        self.assertEqual(len(item.execution.fills), 1)
        fill = item.execution.fills[0]
        self.assertEqual(fill.lot, 50)
        self.assertEqual(fill.leg, "entry")

    def test_execution_with_error(self):
        d = {
            "ticker": "ADMR", "confidence": 80,
            "execution": {
                "status": "failed", "path": "pre_open",
                "entry_order_id": None, "stop_order_id": None,
                "tp1_order_id": None, "tp2_order_id": None,
                "fills": [],
                "last_check": "2026-04-24T08:31:05+07:00",
                "last_error": "insufficient_funds",
            }
        }
        item = _parse_list_item(d)
        self.assertEqual(item.execution.status, "failed")
        self.assertEqual(item.execution.last_error, "insufficient_funds")

    def test_execution_missing_optional_fields(self):
        d = {
            "ticker": "ADMR", "confidence": 80,
            "execution": {
                "status": "placed", "path": "intraday",
                "entry_order_id": "CR-99",
            }
        }
        item = _parse_list_item(d)
        self.assertIsNone(item.execution.stop_order_id)
        self.assertEqual(item.execution.fills, [])
        self.assertEqual(item.execution.last_check, "")


if __name__ == "__main__":
    unittest.main()
