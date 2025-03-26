import pandas as pd
import numpy as np
import streamlit as st

# Step 1: Load the reconciliation report
reconciliation_file = "Catalyst_data.csv"  # Replace with the path to your reconciliation report
data = pd.read_csv(reconciliation_file)

# Step 2: Define key and criteria columns
key_column = "TRADEID"
criteria_columns = ["PRICE", "QUANTITY", "INVENTORY", "CUSIP", "TRADEDATE", "SETTLEDATE", "BUYSELL"]

# Track missing columns
missing_columns = []

# Step 3: Add flags for mismatched columns and comments
mismatch_columns = []  # To hold mismatched column details
for column in criteria_columns:
    # Catalyst and Impact column names
    col_catalyst = f"Catalyst_{column}"
    col_impact = f"Impact_{column}"

    # Check if both required columns exist
    if col_catalyst not in data.columns or col_impact not in data.columns:
        missing_columns.append(col_catalyst if col_catalyst not in data.columns else col_impact)
        # Add default NaN column for missing data to prevent KeyError (optional)
        data[col_catalyst] = data.get(col_catalyst, np.nan)
        data[col_impact] = data.get(col_impact, np.nan)

    # Add mismatch flags for existing columns
    if col_catalyst in data.columns and col_impact in data.columns:
        data[f"{column}_mismatch"] = data[col_catalyst] != data[col_impact]
        mismatch_columns.append(column)
    else:
        # If columns are missing, add an entry in the mismatch columns list
        data[f"{column}_mismatch"] = False


# Step 4: Add an anomaly classifier with column-specific mismatch details
def classify_anomaly_with_comments(row):
    comments = []  # To store comments for row mismatches

    # Check for missing data in catalyst or impact columns
    for column in criteria_columns:
        col_catalyst = f"Catalyst_{column}"
        col_impact = f"Impact_{column}"

        if pd.isna(row.get(col_catalyst, np.nan)) and pd.isna(row.get(col_impact, np.nan)):
            comments.append(f"Both {col_catalyst} and {col_impact} are missing.")
        elif pd.isna(row.get(col_catalyst, np.nan)):
            comments.append(f"Missing {col_catalyst}.")
        elif pd.isna(row.get(col_impact, np.nan)):
            comments.append(f"Missing {col_impact}.")
        elif row.get(f"{column}_mismatch", False):  # Check if there's a mismatch
            comments.append(f"Mismatch in {column}")

    # Return the appropriate anomaly status and comments
    if comments:
        return "Anomaly Detected", "; ".join(comments)
    else:
        return "Matched", ""


# Apply classifier row-by-row
anomaly_results = data.apply(classify_anomaly_with_comments, axis=1)
data["anomaly_status"] = anomaly_results.apply(lambda x: x[0])  # First part of tuple is the status
data["mismatch_comments"] = anomaly_results.apply(lambda x: x[1])  # Second part is the comments

# Step 5: Statistical check for outliers (Z-Score method) on numerical columns
numerical_columns = ["PRICE_impact", "QUANTITY_impact"]

for column in numerical_columns:
    if column in data.columns:
        column_zscore = f"{column}_zscore"
        data[column_zscore] = (data[column] - data[column].mean()) / data[column].std()
        data[f"{column}_outlier"] = np.abs(data[column_zscore]) > 3
    else:
        print(f"Warning: Column `{column}` not found in the dataset for outlier detection.")

# Step 6: Save flagged anomalies for missing columns
anomalies = data[data["anomaly_status"] != "Matched"]
output_file = "reconciliation_report_detailed_anomalies.csv"
anomalies.to_csv(output_file, index=False)

# Display all anomalies (including missing columns and comments)
print("Anomalies detected (including explanations for mismatches):")
pd.set_option('display.max_columns', None)  # Show all columns in output
print(anomalies)
print(f"Anomalies saved to: {output_file}")

# Display missing columns as additional information
if missing_columns:
    print("\nWarning: The following columns were missing in the dataset:")
    print(missing_columns)
else:
    print("\nNo missing columns detected.")


# Step 1: Load the reconciliation file and simulate detected anomalies
#reconciliation_report_detailed_anomalies
def load_data():
    # Example dataset for anomalies
    reconciliation_file = "reconciliation_report_detailed_anomalies.csv"  # Replace with the path to your reconciliation report
    data = pd.read_csv(reconciliation_file)
    return pd.DataFrame(data)


# Step 2: Main Streamlit App to present anomalies and collect feedback
def main():
    st.title("Anomaly Reconciliation Tool")
    st.write("Detect anomalies, review mismatches, and provide resolutions.")

    # Load data
    data = load_data()
    anomalies = data[(data["PRICE_mismatch"] | data["QUANTITY_mismatch"])]

    # Placeholder DataFrame for storing feedback
    feedback = anomalies.copy()
    feedback["user_feedback"] = ""
    feedback["resolved_PRICE"] = feedback["Impact_PRICE"]
    feedback["resolved_QUANTITY"] = feedback["Impact_QUANTITY"]

    # Step 3: Review anomalies row by row
    for index, row in anomalies.iterrows():
        st.subheader(f"TRADE ID: {row['TRADEID']}")

        # Display mismatch details for each column
        if row["PRICE_mismatch"]:
            st.write(f"**PRICE Mismatch**: Catalyst = {row['Catalyst_PRICE']}, Impact = {row['Impact_PRICE']}")
            action_price = st.radio(
                f"Action for PRICE (TRADE ID {row['TRADEID']}):",
                ("No Action", "Replace with Catalyst Value", "Manual Resolution"),
                key=f"price_action_{index}"
            )

            if action_price == "Replace with Catalyst Value":
                feedback.at[index, "resolved_PRICE"] = row["Catalyst_PRICE"]
                feedback.at[index, "user_feedback"] += f"PRICE resolved with Catalyst value ({row['Catalyst_PRICE']}). "
            elif action_price == "Manual Resolution":
                manual_price = st.number_input(
                    f"Enter new PRICE value for TRADE ID {row['TRADEID']}:",
                    value=row["Impact_PRICE"] if row["Impact_PRICE"] else 0.0,
                    key=f"price_manual_{index}"
                )
                feedback.at[index, "resolved_PRICE"] = manual_price
                feedback.at[index, "user_feedback"] += f"PRICE manually resolved to {manual_price}. "

        if row["QUANTITY_mismatch"]:
            st.write(f"**QUANTITY Mismatch**: Catalyst = {row['Catalyst_QUANTITY']}, Impact = {row['Impact_QUANTITY']}")
            action_quantity = st.radio(
                f"Action for QUANTITY (TRADE ID {row['TRADEID']}):",
                ("No Action", "Replace with Catalyst Value", "Manual Resolution"),
                key=f"quantity_action_{index}"
            )

            if action_quantity == "Replace with Catalyst Value":
                feedback.at[index, "resolved_QUANTITY"] = row["Catalyst_QUANTITY"]
                feedback.at[
                    index, "user_feedback"] += f"QUANTITY resolved with Catalyst value ({row['Catalyst_QUANTITY']}). "
            elif action_quantity == "Manual Resolution":
                manual_quantity = st.number_input(
                    f"Enter new QUANTITY value for TRADE ID {row['TRADEID']}:",
                    value=row["Impact_QUANTITY"] if row["Impact_QUANTITY"] else 0.0,
                    key=f"quantity_manual_{index}"
                )
                feedback.at[index, "resolved_QUANTITY"] = manual_quantity
                feedback.at[index, "user_feedback"] += f"QUANTITY manually resolved to {manual_quantity}. "

    # Step 4: Save review and feedback
    if st.button("Save Feedback"):
        output_file = "reconciled_anomalies_with_feedback.csv"
        feedback.to_csv(output_file, index=False)
        st.success(f"Feedback saved to {output_file}")
        st.dataframe(feedback)  # Display resolved anomalies


# Run the application
if __name__ == "__main__":
    main()