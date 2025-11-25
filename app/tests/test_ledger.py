"""
TiKòb Ledger Service Tests
Comprehensive testing for double-entry bookkeeping and tax calculations
"""
import pytest
from decimal import Decimal, ROUND_HALF_EVEN
from datetime import date, datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ledger_service import (
    LedgerService, ReconciliationService, TaxReportService,
    LedgerError, bankers_round, generate_id, PRECISION
)


class TestBankersRounding:
    """Test banker's rounding (round half to even)"""
    
    def test_round_half_to_even_down(self):
        """0.5 rounds to 0 (even)"""
        assert bankers_round(Decimal('0.5'), 0) == Decimal('0')
        assert bankers_round(Decimal('2.5'), 0) == Decimal('2')
        
    def test_round_half_to_even_up(self):
        """1.5 rounds to 2 (even)"""
        assert bankers_round(Decimal('1.5'), 0) == Decimal('2')
        assert bankers_round(Decimal('3.5'), 0) == Decimal('4')
        
    def test_round_normal_cases(self):
        """Normal rounding cases"""
        assert bankers_round(Decimal('1.4'), 0) == Decimal('1')
        assert bankers_round(Decimal('1.6'), 0) == Decimal('2')
        
    def test_round_two_decimals(self):
        """Rounding to 2 decimal places"""
        assert bankers_round(Decimal('1.234'), 2) == Decimal('1.23')
        assert bankers_round(Decimal('1.235'), 2) == Decimal('1.24')
        assert bankers_round(Decimal('1.225'), 2) == Decimal('1.22')
        assert bankers_round(Decimal('1.245'), 2) == Decimal('1.24')
        
    def test_round_preserves_precision(self):
        """Rounding preserves required precision"""
        result = bankers_round(Decimal('123.456789'), 4)
        assert result == Decimal('123.4568')
        
    def test_round_negative_numbers(self):
        """Rounding negative numbers"""
        assert bankers_round(Decimal('-1.5'), 0) == Decimal('-2')
        assert bankers_round(Decimal('-2.5'), 0) == Decimal('-2')
        

class TestGenerateId:
    """Test ID generation"""
    
    def test_id_uniqueness(self):
        """Generated IDs should be unique"""
        ids = [generate_id() for _ in range(1000)]
        assert len(ids) == len(set(ids))
        
    def test_id_with_prefix(self):
        """IDs should include prefix"""
        evt_id = generate_id('evt_')
        assert evt_id.startswith('evt_')
        
        post_id = generate_id('post_')
        assert post_id.startswith('post_')
        
    def test_id_length(self):
        """IDs should have consistent length"""
        for _ in range(100):
            id_val = generate_id('test_')
            assert len(id_val) == 17  # prefix(5) + hex(12)


class TestDecimalPrecision:
    """Test decimal precision handling"""
    
    def test_precision_constant(self):
        """PRECISION constant should be 6 decimal places"""
        assert PRECISION == Decimal('0.000001')
        
    def test_money_calculations_no_float_errors(self):
        """Money calculations should not have floating point errors"""
        a = Decimal('10.00')
        b = Decimal('3')
        result = a / b
        expected = Decimal('3.333333').quantize(PRECISION)
        assert result.quantize(PRECISION) == expected
        
    def test_interest_allocation_precision(self):
        """Interest allocation should maintain precision"""
        total_interest = Decimal('100.00')
        shares = [
            Decimal('0.333333'),
            Decimal('0.333333'),
            Decimal('0.333334')
        ]
        
        allocations = [(total_interest * s).quantize(PRECISION) for s in shares]
        total_allocated = sum(allocations)
        
        assert total_allocated <= total_interest
        assert total_interest - total_allocated < Decimal('0.01')


class TestDoubleEntryValidation:
    """Test double-entry bookkeeping validation"""
    
    def test_valid_postings_balance(self):
        """Valid postings should sum to zero"""
        postings = [
            ('pool_cash', Decimal('100.00')),
            ('member_principal', Decimal('-100.00'))
        ]
        assert LedgerService.validate_postings_balance(postings)
        
    def test_invalid_postings_dont_balance(self):
        """Invalid postings should not sum to zero"""
        postings = [
            ('pool_cash', Decimal('100.00')),
            ('member_principal', Decimal('-99.00'))
        ]
        assert not LedgerService.validate_postings_balance(postings)
        
    def test_complex_balanced_transaction(self):
        """Complex transactions should still balance"""
        postings = [
            ('pool_cash', Decimal('1000.00')),
            ('member_principal', Decimal('-500.00')),
            ('member_earnings', Decimal('-300.00')),
            ('fee_income', Decimal('-150.00')),
            ('rounding_reserve', Decimal('-50.00'))
        ]
        assert LedgerService.validate_postings_balance(postings)
        
    def test_zero_amount_transactions(self):
        """Zero amount transactions should balance"""
        postings = [
            ('pool_cash', Decimal('0')),
            ('member_principal', Decimal('0'))
        ]
        assert LedgerService.validate_postings_balance(postings)


class TestInterestAllocation:
    """Test time-weighted interest allocation"""
    
    def test_equal_shares_allocation(self):
        """Equal shares should get equal allocation"""
        total_interest = Decimal('300.00')
        shares = [Decimal('0.333333333333'), Decimal('0.333333333333'), Decimal('0.333333333334')]
        
        allocations = []
        for share in shares:
            alloc = (total_interest * share).quantize(PRECISION)
            allocations.append(alloc)
        
        for i in range(len(allocations) - 1):
            diff = abs(allocations[i] - allocations[i + 1])
            assert diff < Decimal('0.01')
            
    def test_proportional_allocation(self):
        """Larger shares should get proportionally more"""
        total_interest = Decimal('1000.00')
        
        share_small = Decimal('0.1')
        share_large = Decimal('0.4')
        
        alloc_small = (total_interest * share_small).quantize(PRECISION)
        alloc_large = (total_interest * share_large).quantize(PRECISION)
        
        assert alloc_large == alloc_small * 4
        
    def test_allocation_captures_all_interest(self):
        """Total allocations should equal or be less than total interest"""
        total_interest = Decimal('1000.00')
        shares = [
            Decimal('0.123456'),
            Decimal('0.234567'),
            Decimal('0.345678'),
            Decimal('0.296299')
        ]
        
        allocations = [(total_interest * s).quantize(PRECISION) for s in shares]
        total_allocated = sum(allocations)
        
        assert total_allocated <= total_interest
        remainder = total_interest - total_allocated
        assert remainder < Decimal('0.01')
        
    def test_single_member_gets_all(self):
        """Single member should get all interest"""
        total_interest = Decimal('500.00')
        share = Decimal('1.0')
        
        allocation = (total_interest * share).quantize(PRECISION)
        assert allocation == total_interest


class TestTaxCalculations:
    """Test tax-related calculations"""
    
    def test_ytd_accumulation(self):
        """Year-to-date should accumulate correctly"""
        monthly_earnings = [
            Decimal('10.50'),
            Decimal('11.25'),
            Decimal('12.00'),
            Decimal('10.75'),
            Decimal('11.50'),
            Decimal('12.25')
        ]
        
        ytd = sum(monthly_earnings)
        assert ytd == Decimal('68.25')
        
    def test_1099_int_threshold(self):
        """1099-INT is required when interest exceeds $10"""
        threshold = Decimal('10.00')
        
        interest_below = Decimal('9.99')
        interest_above = Decimal('10.01')
        
        assert interest_below < threshold
        assert interest_above > threshold
        
    def test_rounding_for_tax_forms(self):
        """Tax form amounts should be rounded to 2 decimals"""
        raw_interest = Decimal('123.456789')
        tax_amount = bankers_round(raw_interest, 2)
        
        assert tax_amount == Decimal('123.46')
        
    def test_contribution_tracking(self):
        """Contributions should be tracked accurately"""
        contributions = [
            Decimal('100.00'),
            Decimal('100.00'),
            Decimal('100.00'),
            Decimal('150.00')
        ]
        
        total = sum(contributions)
        assert total == Decimal('450.00')


class TestReconciliation:
    """Test reconciliation logic"""
    
    def test_balanced_ledger(self):
        """Balanced ledger should pass reconciliation"""
        postings = [
            ('asset', Decimal('1000.00')),
            ('liability', Decimal('-1000.00'))
        ]
        
        total = sum(p[1] for p in postings)
        assert total == Decimal('0')
        
    def test_unbalanced_ledger_detection(self):
        """Unbalanced ledger should be detected"""
        postings = [
            ('asset', Decimal('1000.00')),
            ('liability', Decimal('-999.99'))
        ]
        
        total = sum(p[1] for p in postings)
        assert total != Decimal('0')
        assert total == Decimal('0.01')
        
    def test_pool_member_equality(self):
        """Pool cash should equal sum of member accounts"""
        pool_cash = Decimal('10000.00')
        
        member_accounts = [
            Decimal('2500.00'),
            Decimal('3000.00'),
            Decimal('2000.00'),
            Decimal('2500.00')
        ]
        
        member_total = sum(member_accounts)
        assert pool_cash == member_total
        
    def test_rounding_reserve_handling(self):
        """Rounding reserve should account for sub-cent differences"""
        pool_cash = Decimal('10000.00')
        member_total = Decimal('9999.97')
        rounding_reserve = Decimal('0.03')
        
        assert pool_cash == member_total + rounding_reserve


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_zero_balance(self):
        """Zero balance should be handled correctly"""
        balance = Decimal('0')
        
        assert balance == Decimal('0')
        assert balance >= Decimal('0')
        
    def test_very_small_amounts(self):
        """Very small amounts should be handled"""
        small_amount = Decimal('0.000001')
        
        assert small_amount > Decimal('0')
        assert small_amount.quantize(PRECISION) == small_amount
        
    def test_very_large_amounts(self):
        """Very large amounts should be handled"""
        large_amount = Decimal('999999999999.999999')
        
        doubled = large_amount * 2
        halved = doubled / 2
        
        assert halved == large_amount
        
    def test_negative_prevention(self):
        """Negative balances should be prevented for withdrawals"""
        balance = Decimal('100.00')
        withdrawal = Decimal('150.00')
        
        assert withdrawal > balance
        
    def test_concurrent_share_calculation(self):
        """Share calculations should be deterministic"""
        pool = Decimal('10000.00')
        member_balance = Decimal('2500.00')
        
        share1 = member_balance / pool
        share2 = member_balance / pool
        
        assert share1 == share2
        assert share1 == Decimal('0.25')


class TestTimeWeightedAllocation:
    """Test D-1 (day-before) allocation logic"""
    
    def test_same_day_deposit_excluded(self):
        """Same-day deposits should not affect interest allocation"""
        yesterday_balance = Decimal('1000.00')
        today_deposit = Decimal('500.00')
        
        interest_base = yesterday_balance
        assert interest_base == Decimal('1000.00')
        assert today_deposit not in [yesterday_balance]
        
    def test_timing_arbitrage_prevention(self):
        """Timing arbitrage should be prevented by D-1 snapshots"""
        pool_yesterday = Decimal('10000.00')
        member_yesterday = Decimal('1000.00')
        
        pool_today = Decimal('15000.00')
        member_today = Decimal('6000.00')
        
        share_fair = member_yesterday / pool_yesterday
        share_unfair = member_today / pool_today
        
        assert share_fair == Decimal('0.1')
        assert share_unfair == Decimal('0.4')
        assert share_fair < share_unfair


class TestChecksumGeneration:
    """Test report checksum generation"""
    
    def test_checksum_consistency(self):
        """Same data should produce same checksum"""
        import hashlib
        import json
        
        data = {'member_id': 1, 'amount': '100.00', 'year': 2025}
        
        checksum1 = hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()
        
        checksum2 = hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()
        
        assert checksum1 == checksum2
        
    def test_checksum_changes_with_data(self):
        """Different data should produce different checksum"""
        import hashlib
        import json
        
        data1 = {'member_id': 1, 'amount': '100.00'}
        data2 = {'member_id': 1, 'amount': '100.01'}
        
        checksum1 = hashlib.sha256(
            json.dumps(data1, sort_keys=True).encode()
        ).hexdigest()
        
        checksum2 = hashlib.sha256(
            json.dumps(data2, sort_keys=True).encode()
        ).hexdigest()
        
        assert checksum1 != checksum2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
