def display_fixed_rate_trade_form(selected_bond, yield_curves_df):
    st.subheader("Fixed Rate Bond")
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

        # Input fields for user parameters
        trade_direction = st.selectbox("Trade Direction", ["Buy", "Sell"], key="trade_direction_input")
        st.session_state["trade_direction"] = trade_direction

        number_of_pieces = st.number_input(
            "Number of Pieces",
            min_value=1,
            step=1,
            value=st.session_state["number_of_pieces"],
            key="pieces_input"
        )
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

        # Calculate total price
        nominal_value = selected_bond["Nominal Value (1 unit)"]
        currency = selected_bond["Nominal Value Currency"]
        total_price = number_of_pieces * (nominal_value * clean_price / 100 + accrued_interest)

        st.write(f"**Total Price: {total_price:.2f} {currency}**")

        # Select trade date
        yield_dates = yield_curves_df["observation_date"].unique()
        trade_date = st.selectbox("Trade Date", yield_dates)

        # Add a slider for yield curve parallel shift
        shift = st.slider(
            "Parallel Yield Curve Shift (%)",
            min_value=-5.0,
            max_value=5.0,
            value=0.0,
            step=0.1
        )

        # Initialize FixedBond object
        fixed_bond = FixedBond(
            selected_bond,
            yield_curves_df,
            trade_date,
            selected_bond["Nominal Value Currency"],
            selected_bond["Principal Payment Frequency"],
            selected_bond["Coupon Frequency"],
            number_of_pieces=number_of_pieces
        )

        # Buttons for different calculations
        if st.button("Calculate Cash Flows and NPV"):
            cash_flows = fixed_bond.cash_flow(shift)
            npv = fixed_bond.npv(shift)

            st.write("**Calculated Cash Flows:**")
            cf_df = pd.DataFrame(cash_flows)
            st.dataframe(cf_df)

            if shift == 0:
                st.write(f"**Net Present Value (NPV BASE): {npv:.2f} {currency}**")
            else:
                st.write(f"**Net Present Value (NPV SCENARIO - shift {shift:.2f}%): {npv:.2f} {currency}**")

        if st.button("Calculate Duration"):
            duration = fixed_bond.macauley_duration(total_price)
            st.write(f"**Macaulay Duration: {duration:.2f} years**")

        if st.button("Calculate YTM"):
            ytm = fixed_bond.yield_to_maturity(total_price)
            st.write(f"**Yield to Maturity (YTM): {ytm:.2f}%**")

    except FileNotFoundError:
        st.warning(f"Bond emissions file {bond_emissions_file} not found. Please upload or check the file path.")
