"""Finite-only tail reads; copied accepted flush with exactly two expressions changed."""
import hashlib,json
from decimal import localcontext
from owner_ledger import FINITE,exact

class FiniteTailRead:
    def _flush_account(self):
        raw=self.account.engine
        for row in list.__getitem__(raw.trades, slice(self._trade_cursor, None)):
            binding=self._fill_owner.get(row['fill_id'])
            if binding is None:raise AssertionError('NATIVE_FILL_HAS_NO_EXPLICIT_OWNER_BINDING')
            owner,index=binding
            self.owners.trade(row,owner)
            key=row['fill_id']+':'+row['leg']
            digest=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if key in self.processed_native_receipts and self.processed_native_receipts[key]!=digest:
                raise AssertionError('CONFLICTING_NATIVE_OWNER_RECEIPT_IDENTITY')
            self.processed_native_receipts[key]=digest
            if owner==FINITE:
                with localcontext() as ctx:
                    ctx.prec=40
                    self.program_budget.record_cost_event(row['fill_id']+':'+row['leg'],actual_fee=exact(row,'fee_amount'))
                if row['leg']=='OPEN':self.program.record_fill_receipt(raw,row['fill_id'],index)
        self._trade_cursor=len(raw.trades)
        for row in list.__getitem__(raw.funding, slice(self._funding_cursor, None)):
            allocated=self.owners.funding_event(row)
            with localcontext() as ctx:
                ctx.prec=40
                self.program_budget.record_cost_event('FUNDING:'+row['event_id'],signed_funding=allocated[FINITE])
        self._funding_cursor=len(raw.funding)
        self.owners.reconcile(raw)
        self._release_flat_retired()
