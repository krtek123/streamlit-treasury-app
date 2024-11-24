import streamlit as st
import pandas as pd
from valuation import FixedBond

def display_fixed_rate_trade_form(selected_bond, yield_curves_df):
    st.subheader("Fixed Rate Principal at Maturity Bond")
    bond_emissions_file = "bond_emissions.csv"
    
    try:
        # Initialize session state variables if they do not exist
        if "trade_direction" not in st.session_state:
            st.session_state["trade_direction"] = "Buy"
        if "number_of_pieces" not in st.session_state:
            st.session_state["number_of_pieces"] = 1
        if "clean_price" not in st.session_state:
            st.session_state["clean_price"] = 100.0
        if "accrued_interest" not in st.session_state:
            st.session_state["accrued_interest"] = 0.0

        # Display the selected bond details in table format
        st.write("**Selected Bond Details:**")
        bond_details_table = pd.DataFrame([selected_bond]).rename(
            columns={
                "Issue Name": "Issue Name",
                "ISIN": "ISIN",
                "Maturity Date": "Maturity Date",
                "Nominal Value (1 unit)": "Nominal Value",
                "Nominal Value Currency": "Currency",
                "Fixed Rate/Spread [%]": "Coupon Rate (%)",
            }
        )
        st.table(bond_details_table[["Issue Name", "ISIN", "Maturity Date", "Nominal Value", "Currency", "Coupon Rate (%)"]])

        # Input fields for user parameters with dynamic updates
        trade_direction = st.selectbox("Trade Direction", ["Buy", "Sell"], key="trade_direction_input")
        st.session_state["trade_direction"] = trade_direction

        # Input number_of_pieces with condition to prevent invalid values
        if trade_direction == "Sell":
            # Forbid positive number for sell trades
            number_of_pieces = st.number_input(
                "Number of Pieces",
                min_value=-1000,  # Max negative value (change as needed)
                step=1,
                value=-abs(st.session_state["number_of_pieces"]),  # Set to negative
                key="pieces_input"
            )
            # Raise error if the number of pieces is positive (for "Sell" trade)
            if number_of_pieces > 0:
                st.error("Error: Number of pieces must be negative for 'Sell' trades.")
                return  # Exit the function early to prevent further calculation
        else:  # For "Buy" trade direction
            # Ensure that value is positive and >= 1 for buy trades
            number_of_pieces = st.number_input(
                "Number of Pieces",
                min_value=1,  # Ensure min value is 1
                step=1,
                value=abs(st.session_state["number_of_pieces"]),  # Set to positive
                key="pieces_input"
            )
            # Raise error if the number of pieces is negative (for "Buy" trade)
            if number_of_pieces < 0:
                st.error("Error: Number of pieces must be positive for 'Buy' trades.")
                return  # Exit the function early to prevent further calculation

        st.session_state["number_of_pieces"] = number_of_pieces

        clean_price = st.number_input(
            "Clean Price (% of Nominal)",
            min_value=0.0,
            step=0.01,
            value=st.session_state["clean_price"],
            key="clean_price_input"
        )
        st.session_state["clean_price"] = clean_price

        accrued_interest = st.number_input(
            "Accrued Interest (per piece)",
            min_value=0.0,
            step=0.01,
            value=st.session_state["accrued_interest"],
            key="accrued_interest_input"
        )
        st.session_state["accrued_interest"] = accrued_interest

        # Recalculate total price automatically whenever an input changes
        nominal_value = selected_bond["Nominal Value (1 unit)"]
        currency = selected_bond["Nominal Value Currency"]
        total_price = number_of_pieces * (nominal_value * clean_price / 100 + accrued_interest)

        # Display the recalculated total price dynamically
        st.write(f"**Total Price: {total_price:.2f} {currency}**")

        # Select trade date (not dependent on form submission)
        yield_dates = yield_curves_df["observation_date"].unique()
        trade_date = st.selectbox("Trade Date", yield_dates)

        # Add a slider to select the yield curve parallel shift value
        shift = st.slider(
            "Parallel Yield Curve Shift (%)",
            min_value=-5.0,  # Set as float
            max_value=5.0,   # Set as float
            value=0.0,       # Set as float
            step=0.1         # Keep step as float
        )

        # Solve button to trigger cash flow and NPV calculations
        if st.button("Solve"):
            # Initialize the FixedBond object with the bond details and yield curve data
            fixed_bond = FixedBond(
                selected_bond, 
                yield_curves_df, 
                trade_date, 
                selected_bond["Nominal Value Currency"], 
                selected_bond["Principal Payment Frequency"],
                number_of_pieces=number_of_pieces
            )

            # Get cash flows and NPV using the FixedBond class, passing the shift parameter
            cash_flows = fixed_bond.cash_flow(shift)
            npv = fixed_bond.npv(shift)

            # Display the calculated cash flows and NPV
            st.write("**Calculated Cash Flows**:")
            cf_df = pd.DataFrame(cash_flows)
            st.dataframe(cf_df)

            st.write(f"**Net Present Value (NPV by discounting with the yield curve): {npv:.2f} {selected_bond['Nominal Value Currency']}**")

            # Calculate Macauley Duration
            duration = fixed_bond.macauley_duration(shift)
            st.write(f"**Macauley Duration: {duration:.2f} years**")

            # Calculate Yield to Maturity (YTM)
            ytm = fixed_bond.yield_to_maturity(total_price, shift)
            st.write(f"**Yield to Maturity (YTM): {ytm:.2f}%**")

    except FileNotFoundError:
        st.warning(f"Bond emissions file {bond_emissions_file} not found. Please upload or check the file path.")