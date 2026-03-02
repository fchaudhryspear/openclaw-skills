import numpy as np
import pyxirr
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Import constants (hardcoded curves) from data_loaders.py
from data_loaders import (
    BASE_SETTLEMENT_CURVE,
    BASE_SURVIVAL_CURVE,
    CANCELLATION_DISTRIBUTION,
    build_eop_active_curve
)

def run_model(params: dict) -> dict:
    """
    Core financial model to calculate IRR, cash flows, and debt schedule.
    
    BORROWING BASE LOGIC (Asset-Based Lending Algorithm)
    
    This model uses the corrected Excel-matching approach:
    1. Revenue = Enrolled_Debt × Settlement_Curve × Performance_Fee
    2. Flobase Share = Revenue × 80% (fixed fee split)
    3. Borrowing Base = EOP_Active_Enrolled_Debt × Advance_Rate × 85%
    4. Principal = MAX(0, Debt_BOP - Borrowing_Base)
    5. Interest = Debt_Balance × (SOFR + Spread) / 12
    6. Equity CF = Flobase Share - Interest - Principal
    """
    vintage_term = params['vintage_term']
    enrolled_debt = params['enrolled_debt']
    advance_rate = params['advance_rate']
    perf_fee = params['earned_performance_fee']
    equity_contribution = params['equity_contribution']
    debt_contribution = params['debt_contribution']
    loan_term = params['loan_term']
    cancellation_rate = params['cancellation_rate']
    egl_accelerant = params.get('egl_accelerant', 0)
    
    # Waterfall Fee Split (from Excel assumptions)
    pre_preferred_fee_split = params.get('pre_preferred_fee_split', 0.80)
    post_preferred_fee_split = params.get('post_preferred_fee_split', 0.20)
    
    # Performance Guarantee affects the HURDLE, not the settlement curve
    performance_guarantee = params.get('performance_guarantee', 1.30)
    
    purchase_price = enrolled_debt * advance_rate
    pref_hurdle = purchase_price * performance_guarantee  # Hurdle = Purchase × PG
    debt_amount = purchase_price * debt_contribution
    equity_amount = purchase_price * equity_contribution
    
    # Interest rate from SOFR + Spread (default: 4.28% + 10.5% = 14.78%)
    cost_of_capital = params['sofr'] + params['spread']
    monthly_interest_rate = cost_of_capital / 12
    
    months = list(range(vintage_term + 1))
    
    cancel_dist = (params.get('cancel_dist', CANCELLATION_DISTRIBUTION) + [0]*vintage_term)[:vintage_term]
    
    # Use uploaded settlement curve if provided, otherwise use base curve
    # Settlement curve is NOT scaled by performance guarantee (PG affects hurdle only)
    base_settle_curve = params.get('settle_curve', BASE_SETTLEMENT_CURVE)
    if base_settle_curve is None or len(base_settle_curve) == 0:
        base_settle_curve = BASE_SETTLEMENT_CURVE
    # Pad curve to ensure it has enough elements
    scaled_settlement_curve = (list(base_settle_curve) + [0.0] * (vintage_term + 1))[:vintage_term + 1]
    
    # Build EOP Active Enrolled Debt curve (collateral for borrowing base)
    # This is scaled proportionally if enrolled_debt differs from $75M base
    eop_active_curve = build_eop_active_curve(enrolled_debt, vintage_term)
    
    # Calculate the actual Borrowing Base limits (EOP Active × Advance Rate × 85%)
    borrowing_base_limits = [eop * advance_rate * 0.85 for eop in eop_active_curve]
    
    survival_curve_exact = BASE_SURVIVAL_CURVE.copy()
    
    # Legacy tracking arrays for charts (now using scaled settlement curve)
    active_debt = [enrolled_debt]
    settled_debt = [0.0]
    cancelled_debt = [0.0]
    cumulative_cancelled = [0]
    cumulative_settled = [0]
    monthly_cancel_rate = [0]
    monthly_settle_rate = [0]
    cumulative_cancel_rate = [0]
    cumulative_settle_rate = [0]
    
    for m in range(1, vintage_term + 1):
        prev_active = active_debt[-1]
        if m == 1 and egl_accelerant > 0:
            m_settled = enrolled_debt * egl_accelerant
            m_cancelled = 0
        else:
            m_cancelled = prev_active * (cancellation_rate * cancel_dist[m-1])
            # Use scaled settlement curve
            scaled_settle_pct = scaled_settlement_curve[m] if m < len(scaled_settlement_curve) else 0.0
            m_settled = (prev_active - m_cancelled) * scaled_settle_pct
        active_debt.append(max(0, prev_active - m_cancelled - m_settled))
        settled_debt.append(m_settled)
        cancelled_debt.append(m_cancelled)
        cumulative_cancelled.append(cumulative_cancelled[-1] + m_cancelled)
        cumulative_settled.append(cumulative_settled[-1] + m_settled)
        monthly_cancel_rate.append(m_cancelled / enrolled_debt)
        monthly_settle_rate.append(m_settled / enrolled_debt)
        cumulative_cancel_rate.append(cumulative_cancelled[-1] / enrolled_debt)
        cumulative_settle_rate.append(cumulative_settled[-1] / enrolled_debt)
    
    egl_loan_amount = enrolled_debt * egl_accelerant
    egl_month1_fee = egl_loan_amount * perf_fee
    
    # ============================================================
    # BORROWING BASE MONTHLY LOOP (Months 1-60)
    # Uses corrected Excel-matching logic with EOP Active Enrolled Debt
    # ============================================================
    
    gross_fees = [0.0]           # Gross revenue each month
    flobase_fees = [0.0]         # Flobase share (waterfall split)
    debt_balance = [debt_amount] # Start with initial debt
    interest_payments = [0.0]
    principal_payments = [0.0]
    equity_cfs = [-equity_amount]  # Month 0: equity outflow
    cumulative_gross_fees = [0.0]
    cumulative_flobase_fees = [0.0]
    fee_split_pct = [pre_preferred_fee_split]
    eop_active_debt_log = [enrolled_debt]  # Track EOP Active for debugging
    
    for m in range(1, vintage_term + 1):
        # --------------------------------------------------------
        # STEP A: Determine Revenue
        # Revenue = Enrolled_Debt × Settlement_Curve × Performance_Fee
        # Month 1: $0 revenue (no settlements yet), unless EGL is active
        # --------------------------------------------------------
        scaled_settle_pct = scaled_settlement_curve[m] if m < len(scaled_settlement_curve) else 0.0
        gross_settlement = enrolled_debt * scaled_settle_pct
        
        if m == 1:
            # Month 1: Only EGL fee if active, otherwise $0
            gross_revenue = egl_month1_fee
        else:
            # Months 2+: Settlement × Performance Fee
            gross_revenue = gross_settlement * perf_fee
        
        gross_fees.append(gross_revenue)
        
        # --------------------------------------------------------
        # STEP A2: Waterfall Fee Split
        # Pre-Preferred: 80% until cumulative FLOBASE collections >= 130% of purchase price
        # Post-Preferred: 20% after Flobase has collected their preferred return
        # The hurdle is $7.8M (130% × $6M) in cumulative Flobase fees
        # NOTE: No partial month split - entire month that crosses hurdle gets pre-preferred rate
        # --------------------------------------------------------
        prev_cum_flobase = cumulative_flobase_fees[-1]
        
        if prev_cum_flobase >= pref_hurdle:
            # Already past hurdle - use post-preferred split
            fb_share = gross_revenue * post_preferred_fee_split
            fee_split_pct.append(post_preferred_fee_split)
        else:
            # Still below hurdle (or will cross this month) - use pre-preferred split
            # The entire month gets 80% even if it crosses the hurdle
            fb_share = gross_revenue * pre_preferred_fee_split
            fee_split_pct.append(pre_preferred_fee_split)
        
        flobase_fees.append(fb_share)
        
        # --------------------------------------------------------
        # STEP B: Calculate Interest on Declining Balance
        # Interest = Debt_Balance_BOP × (Cost_of_Capital / 12)
        # --------------------------------------------------------
        bop_debt = debt_balance[-1]
        if bop_debt > 0:
            m_interest = bop_debt * monthly_interest_rate
        else:
            m_interest = 0
        interest_payments.append(m_interest)
        
        # --------------------------------------------------------
        # STEP C: Calculate Principal (BORROWING BASE FORMULA)
        # Borrowing_Base = EOP_Active_Enrolled_Debt × Advance_Rate × 85%
        # Principal = MAX(0, Debt_BOP - Borrowing_Base)
        # --------------------------------------------------------
        # Get EOP Active Enrolled Debt for this month (collateral)
        eop_active = eop_active_curve[m] if m < len(eop_active_curve) else 0
        eop_active_debt_log.append(eop_active)
        
        # Borrowing Base = Collateral × Advance Rate × 85%
        borrowing_base = eop_active * advance_rate * 0.85
        
        if bop_debt > 0:
            # Principal paydown = excess debt over borrowing base limit
            required_principal = max(0, bop_debt - borrowing_base)
            eop_debt = max(0, bop_debt - required_principal)
        else:
            required_principal = 0
            eop_debt = 0
        
        principal_payments.append(required_principal)
        debt_balance.append(eop_debt)
        
        # --------------------------------------------------------
        # STEP D: Equity Cash Flow
        # Equity_CF = Flobase_Share - Interest - Principal
        # Negative values in early months are capital calls
        # --------------------------------------------------------
        cumulative_gross_fees.append(cumulative_gross_fees[-1] + gross_revenue)
        cumulative_flobase_fees.append(cumulative_flobase_fees[-1] + fb_share)
        
        equity_cf = fb_share - m_interest - required_principal
        
        # Handle balloon payment at loan term end (only with EGL > 0)
        if m == loan_term and eop_debt > 0 and egl_accelerant > 0:
            balloon_amount = eop_debt
            equity_cf -= balloon_amount
            debt_balance[-1] = 0
        
        equity_cfs.append(equity_cf)

    start_date = datetime(2025, 10, 31)
    dates = [start_date + relativedelta(months=i) for i in range(vintage_term + 1)]
    
    try:
        unlevered_irr = pyxirr.xirr(dates, [-purchase_price] + flobase_fees[1:])
        if unlevered_irr is None:
            unlevered_irr = 0
    except Exception:
        unlevered_irr = 0
    
    try:
        levered_irr = pyxirr.xirr(dates, equity_cfs)
        if levered_irr is None:
            levered_irr = 0
    except Exception:
        levered_irr = 0

    total_flobase_collections = cumulative_flobase_fees[-1]
    moic = total_flobase_collections / purchase_price if purchase_price > 0 else 0
    
    flobase_collections_pct = [x/purchase_price for x in cumulative_flobase_fees]
    total_collections_pct = [sum(gross_fees[:i+1])/purchase_price for i in range(len(gross_fees))]
    
    egl_flobase_share = egl_month1_fee * pre_preferred_fee_split
    
    egl_adjusted_settle_rate = [0]
    for m in range(1, vintage_term + 1):
        base_settle = scaled_settlement_curve[m] if m < len(scaled_settlement_curve) else scaled_settlement_curve[-1]
        egl_adjusted_settle_rate.append(base_settle + egl_accelerant)
    
    receivable_balance = [0]
    receivable_cancellations = [0]
    receivable_payments = [0]
    cumulative_receivable_payment = [0]
    
    for month in range(1, vintage_term + 1):
        prev_receivable = receivable_balance[-1]
        new_receivable = settled_debt[month] * perf_fee
        month_cancel_receivable = prev_receivable * (cancel_dist[month - 1] if month <= len(cancel_dist) else 0)
        month_payment = gross_fees[month]
        
        receivable_balance.append(prev_receivable + new_receivable - month_cancel_receivable - month_payment)
        receivable_cancellations.append(month_cancel_receivable)
        receivable_payments.append(month_payment)
        cumulative_receivable_payment.append(cumulative_receivable_payment[-1] + month_payment)
    
    cumulative_receivable_pct = [x / (enrolled_debt * perf_fee) if enrolled_debt > 0 else 0 
                                  for x in cumulative_receivable_payment]
    
    oop_balance = [0]
    oop_cancellations = [0]
    oop_payments = [0]
    
    for month in range(1, vintage_term + 1):
        prev_oop = oop_balance[-1]
        new_oop = settled_debt[month] * 0.50 # This 0.50 seems like a magic number, consider making it a param
        month_cancel_oop = prev_oop * (cancel_dist[month - 1] if month <= len(cancel_dist) else 0)
        month_payment_oop = new_oop * 0.8 # This 0.8 seems like a magic number, consider making it a param
        
        oop_balance.append(prev_oop + new_oop - month_cancel_oop - month_payment_oop)
        oop_cancellations.append(month_cancel_oop)
        oop_payments.append(month_payment_oop)
    
    cumulative_cash_flows = [-purchase_price]
    for m in range(1, vintage_term + 1):
        cumulative_cash_flows.append(cumulative_cash_flows[-1] + equity_cfs[m])
    
    monthly_fees_sum = sum(flobase_fees[2:]) if len(flobase_fees) > 2 else 0
    egl_consistency_check = egl_flobase_share + monthly_fees_sum
    
    borrower_base = borrowing_base_limits[:vintage_term + 1]
    eop_active_enrolled = eop_active_debt_log[:vintage_term + 1]
    total_expected_fees = enrolled_debt * perf_fee
    
    # Debug prints removed - consider a proper logging solution
    
    results = {
        'months': months,
        'cumulative_settlement_rate': cumulative_settle_rate,
        'egl_adjusted_settle_rate': egl_adjusted_settle_rate,
        'cumulative_cancellation_rate': cumulative_cancel_rate,
        'flobase_collections_pct': flobase_collections_pct,
        'total_collections_pct': total_collections_pct,
        'purchase_price': purchase_price,
        'debt_amount': debt_amount,
        'equity_amount': equity_amount,
        'total_flobase_collections': total_flobase_collections,
        'moic': moic,
        'unlevered_irr': unlevered_irr,
        'levered_irr': levered_irr,
        'active_debt': active_debt,
        'cumulative_settled': cumulative_settled,
        'cumulative_cancelled': cumulative_cancelled,
        'cancelled_debt': cancelled_debt,
        'settled_debt': settled_debt,
        'monthly_cancel_rate': monthly_cancel_rate,
        'monthly_settle_rate': monthly_settle_rate,
        'receivable_balance': receivable_balance,
        'receivable_cancellations': receivable_cancellations,
        'receivable_payments': receivable_payments,
        'cumulative_receivable_payment': cumulative_receivable_payment,
        'cumulative_receivable_pct': cumulative_receivable_pct,
        'oop_balance': oop_balance,
        'oop_cancellations': oop_cancellations,
        'oop_payments': oop_payments,
        'gross_fees': gross_fees,
        'flobase_fees': flobase_fees,
        'fee_split_pct': fee_split_pct,
        'cumulative_flobase_fees': cumulative_flobase_fees,
        'mac_interest': interest_payments,
        'debt_balance': debt_balance,
        'debt_repayment': principal_payments,
        'net_cash_flows': equity_cfs,
        'cumulative_cash_flows': cumulative_cash_flows,
        'egl_loan_amount': egl_loan_amount,
        'egl_month1_fee': egl_month1_fee,
        'egl_flobase_share': egl_flobase_share,
        'total_expected_fees': total_expected_fees,
        'egl_consistency_check': egl_consistency_check,
        'borrower_base': borrower_base,
        'eop_active_enrolled': eop_active_enrolled,
        'principal_payments': principal_payments,
    }
    
    return results
