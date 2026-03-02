import streamlit as st
import pandas as pd
import os

# Import functions and constants from data_loaders.py
from data_loaders import (
    render_news_ticker,
    fetch_sofr_rate_fresh,
    read_excel_curves,
    read_excel_parameters
)

# Import run_model from financial_logic.py
from financial_logic import run_model

# Import database functions from database_manager.py
from database_manager import (
    init_db,
    save_scenario,
    load_scenarios,
    get_scenario,
    delete_scenario
)

# Import chart functions from chart_generator.py
from chart_generator import create_charts

st.set_page_config(page_title="Flobase Financial Model", layout="wide")

def main():
    init_db()
    
    if 'sofr_fetched' not in st.session_state:
        sofr_rate, sofr_date = fetch_sofr_rate_fresh()
        st.session_state.live_sofr = sofr_rate
        st.session_state.live_sofr_date = sofr_date
        st.session_state.sofr_fetched = True
    else:
        sofr_rate = st.session_state.live_sofr
        sofr_date = st.session_state.live_sofr_date
    
    st.title("Flobase IRR Calculator")
    ticker_html = render_news_ticker(sofr_rate, sofr_date)
    st.markdown(ticker_html, unsafe_allow_html=True)
    st.markdown("Standalone calculator with hardcoded base case curves. Adjust sliders to see instant IRR impact.")
    
    if 'params' not in st.session_state:
        st.session_state.params = {
            'advance_rate': 0.08,
            'preferred_return_factor': 1.3,
            'pre_preferred_fee_split': 0.80,
            'post_preferred_fee_split': 0.20,
            'sofr': sofr_rate,
            'spread': 0.105,
            'equity_contribution': 0.15,
            'debt_contribution': 0.85,
            'loan_term': 36,
            'vintage_term': 60,
            'enrolled_debt': 75000000,
            'earned_performance_fee': 0.27,
            'cancellation_rate': 0.49,
            'egl_accelerant': 0.0,
            'performance_guarantee': 1.0,
        }
    
    if 'customer_name' not in st.session_state:
        st.session_state.customer_name = "Default Customer"
    
    if 'sofr_date' not in st.session_state:
        st.session_state.sofr_date = sofr_date
    
    with st.sidebar:
        st.header("Standalone Calculator")
        st.caption("Adjust parameters to see instant IRR impact")
        
        st.markdown("---")
        st.subheader("Deal Inputs")
        
        st.session_state.params['enrolled_debt'] = st.slider(
            "Enrolled Debt ($M)",
            min_value=1,
            max_value=200,
            value=int(st.session_state.params['enrolled_debt'] / 1000000),
            step=1,
            help="Total enrolled debt in millions"
        ) * 1000000
        
        advance_rate_pct = st.slider(
            "Advance Rate (%)",
            min_value=4.0, max_value=15.0, 
            value=float(st.session_state.params['advance_rate']) * 100,
            step=0.25,
            help="Capital deployed as % of enrolled debt (determines Purchase Price)"
        )
        st.session_state.params['advance_rate'] = advance_rate_pct / 100
        
        perf_fee_pct = st.slider(
            "Performance Fee (%)",
            min_value=15.0, max_value=35.0,
            value=float(st.session_state.params['earned_performance_fee']) * 100,
            step=0.5,
            help="Fee earned on settled debt"
        )
        st.session_state.params['earned_performance_fee'] = perf_fee_pct / 100
        
        pre_pref_split_pct = st.slider(
            "Pre-Preferred Return Fee Split (%)",
            min_value=50.0, max_value=100.0,
            value=float(st.session_state.params['pre_preferred_fee_split']) * 100,
            step=1.0,
            help="Flobase share of gross fees until preferred return is met (default 80%)"
        )
        st.session_state.params['pre_preferred_fee_split'] = pre_pref_split_pct / 100
        
        post_pref_split_pct = st.slider(
            "Post-Preferred Return Fee Split (%)",
            min_value=10.0, max_value=100.0,
            value=float(st.session_state.params['post_preferred_fee_split']) * 100,
            step=5.0,
            help="Flobase share of fees after preferred return hurdle (e.g. 20%)"
        )
        st.session_state.params['post_preferred_fee_split'] = post_pref_split_pct / 100
        
        perf_guarantee_pct = st.slider(
            "Performance Guarantee (%)",
            min_value=50.0, max_value=150.0,
            value=float(st.session_state.params.get('performance_guarantee', 1.0)) * 100,
            step=5.0,
            help="Scales the settlement curve (100% = base case)"
        )
        st.session_state.params['performance_guarantee'] = perf_guarantee_pct / 100
        
        egl_accelerant_pct = st.number_input(
            "EGL Accelerant (%)",
            min_value=0.0, max_value=50.0,
            value=float(st.session_state.params.get('egl_accelerant', 0)) * 100,
            step=0.5,
            help="Early Graduation Loan as % of enrolled debt"
        )
        st.session_state.params['egl_accelerant'] = egl_accelerant_pct / 100
        
        st.markdown("---")
        st.subheader("Credit Facility")
        st.caption(f"Live SOFR from NY Fed ({st.session_state.sofr_date})")
        
        sofr_pct = st.number_input(
            "SOFR 90-Day Average (%)",
            min_value=0.0, max_value=8.0,
            value=round(float(st.session_state.params['sofr']) * 100, 2),
            step=0.01,
            format="%.2f",
            help="Base interest rate"
        )
        st.session_state.params['sofr'] = sofr_pct / 100
        
        if st.button("Refresh SOFR Rate"):
            fresh_sofr, fresh_date = fetch_sofr_rate_fresh()
            st.session_state.live_sofr = fresh_sofr
            st.session_state.live_sofr_date = fresh_date
            st.session_state.sofr_date = fresh_date
            st.session_state.params['sofr'] = fresh_sofr
            st.success(f"SOFR updated to {fresh_sofr*100:.2f}% ({fresh_date})")
            st.rerun()
        
        spread_pct = st.slider(
            "Spread over SOFR (%)",
            min_value=0.0, max_value=15.0,
            value=float(st.session_state.params['spread']) * 100,
            step=0.5,
            help="Additional spread over SOFR"
        )
        st.session_state.params['spread'] = spread_pct / 100
        
        equity_pct = st.slider(
            "Equity Contribution (%)",
            min_value=0.0, max_value=30.0,
            value=float(st.session_state.params['equity_contribution']) * 100,
            step=1.0,
            help="Equity capital as % of purchase price"
        )
        st.session_state.params['equity_contribution'] = equity_pct / 100
        st.session_state.params['debt_contribution'] = 1 - st.session_state.params['equity_contribution']
        
        st.markdown("---")
        st.subheader("Calculated Values")
        enrolled_debt = st.session_state.params['enrolled_debt']
        advance_rate = st.session_state.params['advance_rate']
        perf_fee = st.session_state.params['earned_performance_fee']
        egl_accelerant = st.session_state.params['egl_accelerant']
        purchase_price = enrolled_debt * advance_rate
        
        st.text(f"Purchase Price: ${purchase_price:,.0f}")
        st.text(f"Debt Amount: ${purchase_price * st.session_state.params['debt_contribution']:,.0f}")
        st.text(f"Equity Amount: ${purchase_price * st.session_state.params['equity_contribution']:,.0f}")
        st.text(f"Cost of Capital: {(st.session_state.params['sofr'] + st.session_state.params['spread'])*100:.2f}%")
        
        if egl_accelerant > 0:
            egl_loan_amount = enrolled_debt * egl_accelerant
            st.text(f"EGL Amount: ${egl_loan_amount:,.0f}")
        
        st.markdown("---")
        if st.button("Recalculate Model", type="primary"):
            st.rerun()
        
        st.markdown("---")
        st.header("Save/Load Scenarios")
        
        scenario_name = st.text_input("Scenario Name", value="")
        if st.button("Save Scenario", type="primary"):
            if scenario_name:
                results = run_model(st.session_state.params)
                results_serializable = {k: v if not isinstance(v, list) else v 
                                        for k, v in results.items()}
                save_scenario(
                    scenario_name,
                    st.session_state.customer_name,
                    st.session_state.params,
                    results_serializable
                )
                st.success(f"Scenario '{scenario_name}' saved!")
            else:
                st.warning("Please enter a scenario name")
        
        scenarios = load_scenarios()
        if scenarios:
            st.subheader("Saved Scenarios")
            for scenario in scenarios:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.text(f"{scenario[1]} ({scenario[2]})")
                with col2:
                    if st.button("Load", key=f"load_{scenario[0]}"):
                        params, _ = get_scenario(scenario[0])
                        if params:
                            st.session_state.params = params
                            st.rerun()
                with col3:
                    if st.button("Delete", key=f"del_{scenario[0]}"):
                        delete_scenario(scenario[0])
                        st.rerun()
    
    results = run_model(st.session_state.params)
    
    st.header("Performance Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Purchase Price",
            f"${results['purchase_price']:,.0f}"
        )
    with col2:
        st.metric(
            "MOIC",
            f"{results['moic']:.3f}x"
        )
    with col3:
        st.metric(
            "Unlevered IRR",
            f"{results['unlevered_irr']*100:.2f}%"
        )
    with col4:
        st.metric(
            "Levered IRR",
            f"{results['levered_irr']*100:.2f}%"
        )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Debt Amount",
            f"${results['debt_amount']:,.0f}"
        )
    with col2:
        st.metric(
            "Equity Amount",
            f"${results['equity_amount']:,.0f}"
        )
    with col3:
        st.metric(
            "Total Flobase Collections",
            f"${results['total_flobase_collections']:,.0f}"
        )
    
    st.markdown("---")
    st.header("Model Curves")
    
    fig1, fig2, fig3, fig4 = create_charts(results)
    
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig1, key="chart1")
    with col2:
        st.plotly_chart(fig2, key="chart2")
    
    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(fig3, key="chart3")
    with col4:
        st.plotly_chart(fig4, key="chart4")
    
    st.markdown("---")
    st.header("Sensitivity Analysis: Levered IRR")
    st.markdown("How your return changes based on Cancellation Rate vs. Cost of Capital")

    base_cancel = st.session_state.params['cancellation_rate']
    base_cost = st.session_state.params['sofr'] + st.session_state.params['spread']

    cancel_range = [base_cancel + (i * 0.05) for i in range(-2, 3)]
    cost_range = [base_cost + (i * 0.01) for i in range(-2, 3)]

    sensitivity_data = []

    for cost in cost_range:
        row = []
        for cancel in cancel_range:
            temp_params = st.session_state.params.copy()
            temp_params['cancellation_rate'] = cancel
            temp_params['spread'] = cost - temp_params['sofr']
            
            s_results = run_model(temp_params)
            row.append(f"{s_results['levered_irr']*100:.1f}%")
        sensitivity_data.append(row)

    df_sens = pd.DataFrame(
        sensitivity_data,
        index=[f"Cost: {c*100:.1f}%" for c in cost_range],
        columns=[f"Cancel: {r*100:.0f}%" for r in cancel_range]
    )

    st.table(df_sens)
    
    st.markdown("---")
    st.header("Vintage Analysis Tables")
    
    with st.expander("Active Debt Analysis", expanded=True):
        df_active = pd.DataFrame({
            'Month': results['months'],
            'BOP Active Debt': [f"${x:,.0f}" for x in results['active_debt']],
            'Cancelled Debt': [f"${x:,.0f}" for x in results['cancelled_debt']],
            'Settled Debt': [f"${x:,.0f}" for x in results['settled_debt']],
            'EOP Active Debt': [f"${x:,.0f}" for x in (results['active_debt'][1:] + [results['active_debt'][-1]])],
            'Cumulative Settlement (%)': [f"{x*100:.2f}%" for x in results['cumulative_settlement_rate']],
            'Cumulative Cancellation (%)': [f"{x*100:.2f}%" for x in results['cumulative_cancellation_rate']],
        })
        st.dataframe(df_active, hide_index=True, height=400)
    
    with st.expander("Receivable Fee Collection"):
        df_receivable = pd.DataFrame({
            'Month': results['months'],
            'BOP Receivable Balance': [f"${x:,.0f}" for x in results['receivable_balance']],
            'Cancellations': [f"${x:,.0f}" for x in results['receivable_cancellations']],
            'Payments': [f"${x:,.0f}" for x in results['receivable_payments']],
            'Cumulative Payment ($)': [f"${x:,.0f}" for x in results['cumulative_receivable_payment']],
            'Cumulative Payment (%)'
: [f"{x*100:.2f}%" for x in results['cumulative_receivable_pct']],
        })
        st.dataframe(df_receivable, hide_index=True, height=400)
    
    with st.expander("Out of Pocket Analysis"):
        df_oop = pd.DataFrame({
            'Month': results['months'],
            'BOP OOP Balance': [f"${x:,.0f}" for x in results['oop_balance']],
            'Cancellations': [f"${x:,.0f}" for x in results['oop_cancellations']],
            'Payments': [f"${x:,.0f}" for x in results['oop_payments']],
        })
        st.dataframe(df_oop, hide_index=True, height=400)
    
    with st.expander("Flobase Cash Flow"):
        df_cashflow = pd.DataFrame({
            'Month': results['months'],
            'Gross Fees': [f"${x:,.0f}" for x in results['gross_fees']],
            'FB Fee Split (%)': [f"{x*100:.0f}%" for x in results['fee_split_pct']],
            'FB Fees Earned': [f"${x:,.0f}" for x in results['flobase_fees']],
            'Cumulative FB Fees': [f"${x:,.0f}" for x in results['cumulative_flobase_fees']],
            'MAC Interest': [f"${x:,.0f}" for x in results['mac_interest']],
            'Debt Repayment': [f"${x:,.0f}" for x in results['debt_repayment']],
            'Net Cash Flow': [f"${x:,.0f}" for x in results['net_cash_flows']],
            'Cumulative CF': [f"${x:,.0f}" for x in results['cumulative_cash_flows']],
        })
        st.dataframe(df_cashflow, hide_index=True, height=400)
    
    with st.expander("Debt Balance Calculations"):
        df_debt = pd.DataFrame({
            'Month': results['months'],
            'Debt Balance': [f"${x:,.0f}" for x in results['debt_balance']],
            'Debt Repayment': [f"${x:,.0f}" for x in results['debt_repayment']],
        })
        st.dataframe(df_debt, hide_index=True, height=400)
    
    with st.expander("Collections Summary"):
        df_collections = pd.DataFrame({
            'Month': results['months'],
            'Flobase Collections (% PP)': [f"{x*100:.2f}%" for x in results['flobase_collections_pct']],
            'Total Collections (% PP)': [f"{x*100:.2f}%" for x in results['total_collections_pct']],
        })
        st.dataframe(df_collections, hide_index=True, height=400)

if __name__ == "__main__":
    main()