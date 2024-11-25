import pandas as pd
from datetime import datetime
import numpy as np
import scipy.optimize as opt


class FixedBond:
    def __init__(self, bond_data, yield_curves_df, trade_date, currency_code, principal_payment_frequency="At Maturity", coupon_frequency="Annual", number_of_pieces=1):
        self.issue_name = bond_data["Issue Name"]
        self.isin = bond_data["ISIN"]
        #emission = pd.read_csv("bond_emissions.csv")
        #emission = emission[emission.ISIN == self.isin]
        self.maturity_date = pd.to_datetime(bond_data["Maturity Date"])
        self.nominal_value = bond_data["Nominal Value (1 unit)"]
        self.currency = bond_data["Nominal Value Currency"]
        self.coupon_rate = bond_data["Fixed Rate/Spread [%]"]
        self.emission_date = pd.to_datetime(bond_data["Issue Date"])
        self.yield_curve_df = yield_curves_df
        self.trade_date = pd.to_datetime(trade_date)
        self.currency_code = currency_code
        self.principal_payment_frequency = principal_payment_frequency
        self.coupon_frequency = coupon_frequency
        self.business_day_convention = bond_data["Business Day Convention"]
        self.day_count_convention = bond_data["Day Count Convention"]  # Added Day Count Convention
        self.number_of_pieces = number_of_pieces


    def apply_business_day_convention(self, date, convention="MODFOLLOWING"):
        if convention == "MODFOLLOWING":
            return pd.offsets.BusinessDay().rollforward(date)
        elif convention == "MODPRECEDING":
            return pd.offsets.BusinessDay().rollback(date)
        elif convention == "Following":
            return pd.offsets.BusinessDay().rollforward(date)
        else:
            raise ValueError(f"Unsupported convention: {convention}")

    def generate_dates(self, emission_date, maturity_date, convention="MODFOLLOWING"):
        """Generate a list of payment dates manually, including the maturity date."""
        payment_dates = []
        current_date = emission_date

        while current_date < maturity_date:
            # Generate the next unadjusted payment date based on coupon frequency
            if self.coupon_frequency == "Annual":
                next_payment_date = current_date.replace(year=current_date.year + 1)
            elif self.coupon_frequency == "Semi-Annual":
                next_payment_date = current_date + pd.DateOffset(months=6)
            elif self.coupon_frequency == "Quarterly":
                next_payment_date = current_date + pd.DateOffset(months=3)
            else:
                raise ValueError(f"Unsupported coupon frequency: {self.coupon_frequency}")

            # If the next payment date exceeds maturity, break the loop
            if next_payment_date >= maturity_date:
                break

            # Apply the business day convention to adjust the payment date
            adjusted_payment_date = self.apply_business_day_convention(next_payment_date, convention)

            # Append the adjusted date to the list
            payment_dates.append(adjusted_payment_date)

            # Move to the next period based on the **unadjusted date**
            current_date = next_payment_date
        payment_dates = [date for date in payment_dates if date <= maturity_date]
        # Always add the maturity date (unaltered by business day convention)
        if maturity_date not in payment_dates:
            payment_dates.append(maturity_date)

        return payment_dates


    def calculate_days(self, start_date, end_date, convention="ACT/360"):
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

        if convention == "ACT/360":
            return (end_date - start_date).days
        
        elif convention == "30/360":
            # Adjust the start and end day if they are 31
            start_day = 30 if start_date.day == 31 else start_date.day
            end_day = 30 if end_date.day == 31 else end_date.day
            
            # Adjust the end month and year if needed
            if end_day == 30 and start_date.month == 2 and start_date.year != end_date.year:
                end_day = 30
            
            # Calculate difference in years, months, and days
            year_diff = end_date.year - start_date.year
            month_diff = end_date.month - start_date.month
            day_diff = end_day - start_day

            # Convert everything into 360-day year and 30-day month
            days_30_360 = (year_diff * 360) + (month_diff * 30) + day_diff
            return days_30_360
        
        elif convention == "ACT/365":
            return (end_date - start_date).days
        
        else:
            raise ValueError(f"Unsupported convention: {convention}")

    def cash_flow(self, shift=0):
        cash_flows = []
        payment_dates = self.generate_dates(self.emission_date, self.maturity_date, convention=self.business_day_convention)
        remaining_principal = self.number_of_pieces * self.nominal_value
        cumulative_length_of_period = 0
    
        # Interpolate the entire yield curve for all tenors
        yield_curve_data = self.yield_curve_df[["currency", "observation_date", "tenor", "rate"]]
    
        # Filter the relevant yield curve for the currency and trade date
        relevant_curve = yield_curve_data[
            (yield_curve_data["currency"] == self.currency_code) &
            (pd.to_datetime(yield_curve_data["observation_date"]) == self.trade_date)
        ]
        
        if relevant_curve.empty:
            raise ValueError(f"No yield curve data available for the selected trade date and currency: {self.currency_code}")
        
        # Ensure the yield curve is sorted by tenor
        relevant_curve = relevant_curve.sort_values(by="tenor")
    
        # Extract tenors and rates from the yield curve
        tenors = relevant_curve["tenor"].values
        rates = relevant_curve["rate"].values
    
        # Interpolate the yield curve using numpy (handling the full curve)
        def interpolate_rate(length_in_years):
            return np.interp(length_in_years, tenors, rates, left=rates[0], right=rates[-1])
    
        # Define how much principal to pay at each period based on frequency
        def calculate_principal_payment(payment_date, first_payment_date, last_payment_date):
            if self.principal_payment_frequency == "Annual":
                return self.nominal_value / len(payment_dates)  # Equal payment each year
            elif self.principal_payment_frequency == "Semi-Annual":
                return self.nominal_value / (len(payment_dates))  # Equal semi-annual payment
            elif self.principal_payment_frequency == "Quarterly":
                return self.nominal_value / (len(payment_dates))  # Equal quarterly payment
            elif self.principal_payment_frequency == "Monthly":
                return self.nominal_value / (len(payment_dates))  # Equal monthly payment
            else:
                raise ValueError(f"Unsupported principal payment frequency: {self.principal_payment_frequency}")
    
        for i, date in enumerate(payment_dates):
            # Skip cash flows before the trade date
            if date < self.trade_date:
                continue  # Skip this iteration if the payment date is before the trade date
            
            coupon_payment = 0
            principal_repayment = 0
    
            if i == 0:
                length_of_period = self.calculate_days(self.emission_date, date, convention=self.day_count_convention)
            else:
                length_of_period = self.calculate_days(payment_dates[i - 1], date, convention=self.day_count_convention)
            
            # Convert length_of_period from days to years based on the day count convention
            if self.day_count_convention in ["ACT/360", "30/360"]:
                length_in_years = length_of_period / 360
            elif self.day_count_convention == "ACT/365":
                length_in_years = length_of_period / 365
            else:
                raise ValueError(f"Unsupported day count convention: {self.day_count_convention}")
            
            # Calculate coupon payment based on day count convention
            if self.day_count_convention in ["30/360", "ACT/360"]:
                coupon_payment = self.number_of_pieces * (self.nominal_value * self.coupon_rate / 100) * (length_of_period / 360)
            else:
                coupon_payment = self.number_of_pieces * (self.nominal_value * self.coupon_rate / 100) * (length_of_period / 365)
    
            cumulative_length_of_period += length_of_period
            
            # Use the interpolate_rate function to get the interpolated rate for the current period
            rate_interpolated = interpolate_rate(cumulative_length_of_period / 360)
    
            # Calculate the discounted coupon payment and principal repayment
            time_to_payment = cumulative_length_of_period / 360  # Time in years (since we've converted length_of_period to years)
            
            # Discount the coupon payment
            coupon_discount = coupon_payment / (1 + (rate_interpolated ) + (shift/100)) ** time_to_payment
            
            # Calculate principal repayment
            if self.principal_payment_frequency != "At Maturity" and (date != self.maturity_date):
                # If it's not the maturity date, we amortize the principal
                principal_repayment = calculate_principal_payment(date, payment_dates[0], payment_dates[-1])
                remaining_principal -= principal_repayment
            if date == self.maturity_date:
                # At maturity, the entire remaining principal is repaid
                principal_repayment = remaining_principal
                remaining_principal = 0  # Principal is fully paid off at maturity
            
            # Discount the principal repayment
            principal_discount = principal_repayment / (1 + (rate_interpolated ) + (shift/100)) ** time_to_payment
    
            # Append the cash flow details with new columns for Interpolated Rate and Discounted Payments
            cash_flows.append({
                "Date": date,
                "Coupon Payment": coupon_payment,
                "Principal Repayment": principal_repayment,
                "Length of Period": length_of_period,
                "Cumulative Length of Period": cumulative_length_of_period,
                "Remaining Principal": remaining_principal,
                "Interpolated Rate": rate_interpolated + shift/100,
                "Discounted Interest": coupon_discount,
                "Discounted Principal": principal_discount
            })
    
        # Safely print all the cash flows after all have been added
        for cash_flow in cash_flows:
            print(cash_flow)
    
        return cash_flows

    def npv(self, shift = 0):
        yield_curve = self.yield_curve_df[ 
            (self.yield_curve_df["currency"] == self.currency_code) & 
            (pd.to_datetime(self.yield_curve_df["observation_date"]) == self.trade_date)
        ]
        
        if yield_curve.empty:
            raise ValueError("No yield curve data available for the selected trade date and currency.")

        cash_flows = self.cash_flow(shift)
        npv = 0.0

        for cf in cash_flows:
            

            coupon_discount = cf["Discounted Interest"]
            principal_discount = cf["Discounted Principal"]
            npv += coupon_discount + principal_discount
        
        return npv
    def macauley_duration(self, shift = 0):
        cash_flows = self.cash_flow(shift)
        weighted_sum = 0.0
        total_cash_flow = 0.0
        
        for cf in cash_flows:
            time_to_payment = cf["Cumulative Length of Period"] / 360  # Convert to years
            discounted_cash_flow = cf["Discounted Interest"] + cf["Discounted Principal"]
            weighted_sum += time_to_payment * discounted_cash_flow
            total_cash_flow += discounted_cash_flow
    
        duration = weighted_sum / total_cash_flow
        return duration
    def yield_to_maturity(self, price, shift=0):
        def bond_price(rate, cash_flows, target_price, shift):
            """Calculate the price of the bond given a rate (YTM)."""
            price = 0.0
            for cf in cash_flows:
                time_to_payment = cf["Cumulative Length of Period"] / 360  # Convert to years
                discounted_coupon = cf["Coupon Payment"] / (1 + (rate + shift) / 100) ** time_to_payment
                discounted_principal = cf["Principal Repayment"] / (1 + (rate + shift) / 100) ** time_to_payment
                price += discounted_coupon + discounted_principal
            return price - target_price  # Return the difference from the target price
        
        
        
        # Get the bond's cash flows (including Coupon Payment and Principal Repayment)
        cash_flows = self.cash_flow(shift)
        
        # The target price should be passed here (not always 0.05%)
        target_price = price
        
        # Use scipy's Newton method to find the YTM (root of the bond price function)
        try:
            ytm = opt.newton(bond_price, x0=0.05, args=(cash_flows, target_price, shift))
        except RuntimeError:
            raise ValueError(f"Failed to converge to a YTM for the bond with price: {target_price}")
        
        return ytm


# Sample bond data for testing
bond_data = {
    "Issue Name": "Corporate Bond 1",
    "ISIN": "CZ1234567890",
    'Fixed Rate/Spread [%]': 3,
    "Maturity Date": "2033-01-15",
    "Nominal Value (1 unit)": 1000,
    "Nominal Value Currency": "CZK",
    "Coupon Rate/Spread [%]": 3.0,
    "Issue Date": "2022-01-15",
    "Business Day Convention": "Following",  # Convention set here
    "Day Count Convention":"30/360",  # Day count convention
}

yield_curve_df = pd.DataFrame({
    "currency": ["CZK", "CZK", "CZK"],
    "observation_date": [pd.Timestamp("2024-11-24")] * 3,
    "tenor": [1, 3, 5], 
    "rate": [2.0, 2.5, 3.0]
})

# Instantiate and calculate NPV
bond = FixedBond(bond_data, yield_curve_df, "2024-11-24", "CZK", coupon_frequency="Annual")
print(bond.npv())
