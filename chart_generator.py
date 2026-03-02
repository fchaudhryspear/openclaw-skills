import plotly.graph_objects as go

def create_charts(results):
    months = results['months']
    
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=months,
        y=[x * 100 for x in results['cumulative_settlement_rate']],
        mode='lines',
        name='Cumulative Settlement',
        line=dict(color='#2ecc71', width=3)
    ))
    fig1.add_trace(go.Scatter(
        x=months,
        y=[x * 100 for x in results['cumulative_cancellation_rate']],
        mode='lines',
        name='Cumulative Cancellation',
        line=dict(color='#e74c3c', width=3, dash='dot')
    ))
    fig1.update_layout(
        title='Portfolio Performance (Settlement vs. Cancellation)',
        xaxis_title='Month',
        yaxis_title='% of Enrolled Debt',
        template='plotly_white',
        hovermode='x unified'
    )
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=months,
        y=[x * 100 for x in results['flobase_collections_pct']],
        mode='lines',
        name='Flobase Recovery (Net)',
        fill='tozeroy',
        line=dict(color='#3498db', width=2)
    ))
    fig2.add_shape(
        type="line", line=dict(dash="dash", color="gray"),
        x0=0, x1=max(months), y0=130, y1=130
    )
    fig2.update_layout(
        title='Cumulative Flobase Collections (% of Purchase Price)',
        xaxis_title='Month',
        yaxis_title='% of Investment recovered',
        template='plotly_white'
    )

    fig3 = go.Figure()
    cfs = results['net_cash_flows']
    colors = ['#e74c3c' if x < 0 else '#2ecc71' for x in cfs]
    
    fig3.add_trace(go.Bar(
        x=months,
        y=cfs,
        marker_color=colors,
        name='Net Cash Flow'
    ))
    fig3.update_layout(
        title='Monthly Net Cash Flow (After Debt Service)',
        xaxis_title='Month',
        yaxis_title='Cash ($)',
        template='plotly_white'
    )

    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        x=months,
        y=results['debt_balance'],
        name='Debt Balance',
        fill='tozeroy',
        line=dict(color='#95a5a6')
    ))
    fig4.update_layout(
        title='Debt Paydown Schedule',
        xaxis_title='Month',
        yaxis_title='Outstanding Debt ($)',
        template='plotly_white'
    )
    
    return fig1, fig2, fig3, fig4
