import streamlit as st

import pandas as pd
from PIL import Image


from bonds import display_fixed_rate_trade_form  # Your custom bond form function

bond_emissions_file = "bond_emissions.csv"
# Initialize session state variables
if "active_pane" not in st.session_state:
    st.session_state["active_pane"] = None  # No active pane initially
if "show_currency" not in st.session_state:
    st.session_state["show_currency"] = False  # Flag to control currency table visibility
if "show_yield_curve" not in st.session_state:
    st.session_state["show_yield_curve"] = False  # Flag for yield curve visibility
if "show_bond_emissions" not in st.session_state:
    st.session_state["show_bond_emissions"] = False  # Flag for bond emissions visibility

# Set page configuration
st.set_page_config(page_title="Treasury Management", layout="wide")

# Load CSV files into Pandas DataFrames
currencies_df = pd.read_csv("currencies.csv")  # Make sure this file exists
yield_curves_df = pd.read_csv("yieldCurves.csv")  # Make sure this file exists
bond_emissions_df = pd.read_csv("bond_emissions.csv")  # Load bond emissions data

# CSS for styling buttons and centering the image
st.markdown(
    """
    <style>
    .nav-button {
        font-size: 18px;
        padding: 15px;
        margin: 5px;
        border-radius: 10px;
        border: none;
        cursor: pointer;
        transition: background-color 0.3s, color 0.3s, box-shadow 0.3s;
    }
    .nav-button:hover {
        background-color: #45a049; /* Hover effect */
        color: white;
    }
    .button-container {
        display: flex;
        justify-content: center;
        gap: 10px;
        margin-top: 10px;
    }
    .image-container {
        display: flex;
        justify-content: center;
        margin-bottom: 20px;
        align-items: center;
    }
    .header-container {
        display: flex;
        justify-content: center;
        font-size: 20px;
        margin-bottom: 20px;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Display logo
img = Image.open("logo.PNG")  # Ensure this image exists and is in the correct path
st.markdown('<div class="image-container">', unsafe_allow_html=True)
st.image(img, width=100)  # Adjust image size if needed
st.markdown('</div>', unsafe_allow_html=True)

# Heading for Menu Options
if st.session_state.get("active_pane") is None:
    st.markdown('<div class="header-container">Select a Menu Option</div>', unsafe_allow_html=True)

# Navigation Buttons
nav_buttons = st.container()
with nav_buttons:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.button(
            "Settings",  # Static button text
            key="settings",
            use_container_width=True,
            on_click=lambda: st.session_state.update({"active_pane": "Settings"})
        )
    with col2:
        st.button(
            "Trade",  # Static button text
            key="trade",
            use_container_width=True,
            on_click=lambda: st.session_state.update({"active_pane": "Trade"})
        )

# Function to display content for the Settings pane
def display_settings():
    st.header("Settings")

    # Submenu under Settings
    st.subheader("Lists")
    button_container = st.container()
    with button_container:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Yield Curves", key="yield_curves"):
                st.session_state["show_currency"] = False
                st.session_state["show_yield_curve"] = True
                st.session_state["show_bond_emissions"] = False
        with col2:
            if st.button("Currencies", key="currencies"):
                st.session_state["show_currency"] = True
                st.session_state["show_yield_curve"] = False
                st.session_state["show_bond_emissions"] = False
        with col3:
            if st.button("Bond Emissions", key="bond_emissions"):
                st.session_state["show_currency"] = False
                st.session_state["show_yield_curve"] = False
                st.session_state["show_bond_emissions"] = True

    # Show currency table
    if st.session_state["show_currency"]:
        st.write("**Currencies Table:**")
        st.dataframe(currencies_df)

    # Show yield curve section
    if st.session_state["show_yield_curve"]:
        st.write("**Yield Curves:**")
        selected_currency = st.selectbox(
            "Select Currency",
            currencies_df["currency_name"].unique()
        )
        if selected_currency:
            selected_currency_code = currencies_df.loc[
                currencies_df["currency_name"] == selected_currency, "currency_code"
            ].iloc[0]
            filtered_curves = yield_curves_df[yield_curves_df["currency"] == selected_currency_code]
            available_dates = filtered_curves["observation_date"].unique()
            selected_date = st.selectbox("Select Date", available_dates)
            if selected_date:
                curve_data = filtered_curves[filtered_curves["observation_date"] == selected_date]
                if not curve_data.empty:
                    transposed_curve_data = curve_data.pivot(
                        index="observation_date", columns="tenor", values="rate"
                    )
                    st.write("**Transposed Yield Curve Data:**")
                    st.dataframe(transposed_curve_data)
                    st.write("**Yield Curve Line Chart:**")
                    st.line_chart(curve_data.set_index("tenor")["rate"])
                else:
                    st.warning("No yield curve data available for the selected date.")
            else:
                st.info("Please select a date to view the yield curve.")
        else:
            st.info("Please select a currency.")

    # Bond Emissions Section
    if st.session_state["show_bond_emissions"]:
        st.write("**Bond Emissions:**")
        bond_emissions_file = "bond_emissions.csv"
        try:
            bond_emissions_df = pd.read_csv(bond_emissions_file)
            st.write("**Bond Emissions Data:**")
            st.dataframe(bond_emissions_df)
        except FileNotFoundError:
            st.warning(f"Bond emissions file `{bond_emissions_file}` not found. Please upload or check the file path.")

# Function to display content for the Trade pane
def display_trade():
    try:
        # Filter bonds based on the criteria (Fixed and Nominal Frequency 'At Maturity')
        fixed_bonds = bond_emissions_df[
            bond_emissions_df['Reference Rate Code'].isna() 
        ]
        
        # Create a list of bond names (e.g., "Corporate Bond 1", "Gov Bond 2")
        bond_options = [
            f"{row['Issue Name']} ({row['ISIN']})" for _, row in fixed_bonds.iterrows()
        ]
        
        # Allow the user to select a bond
        selected_bond_display = st.selectbox(
            "Select Bond",
            bond_options
        )
        selected_bond_index = bond_options.index(selected_bond_display)
        selected_bond = fixed_bonds.iloc[selected_bond_index]

        # Pass the selected bond to the trade form
        display_fixed_rate_trade_form(selected_bond, yield_curves_df)  # Pass selected bond

    except FileNotFoundError:
        st.warning(f"Bond emissions file `{bond_emissions_file}` not found. Please upload or check the file path.")

# Determine which pane to display based on the active pane state
if st.session_state["active_pane"] == "Settings":
    display_settings()
elif st.session_state["active_pane"] == "Trade":
    display_trade()