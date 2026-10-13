"""Prevent any account creation when original preservation reserve is short."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from native_wallet import admission
def test_admission_counts_two_publication_copies_and_original_case():
 case=82039556;packet=63204609;need=case+2*packet+1048576
 assert not admission(need-1,case,packet)
 assert admission(need,case,packet)
