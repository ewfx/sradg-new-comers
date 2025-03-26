import os
import pandas as pd
import numpy as np
import joblib
import streamlit as st
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import GridSearchCV

# Import reconciliation logic
from ReconciliationReportAnomalyDetection import main as smarter_reconciliation
import JiraAnomalyTicketCreator  # Import Jira ticket creator module

MODEL_PATH = "isolation_forest_model.pkl"

def fn_tune_isolation_forest(X):
    param_grid = {
        'n_estimators': [100, 200, 300],
        'max_samples': ['auto', 0.5, 0.75],
        'contamination': [0.01, 0.03, 0.05],
        'max_features': [1.0, 0.8, 0.5]
    }
    
    model = IsolationForest(random_state=42)
    grid_search = GridSearchCV(model, param_grid, scoring='neg_mean_absolute_error', cv=3, n_jobs=-1)
    grid_search.fit(X)
    return grid_search.best_estimator_

def fn_train_model(history_df):
    model = fn_tune_isolation_forest(history_df["Balance_Difference"].values.reshape(-1, 1))
    joblib.dump(model, MODEL_PATH)
    return model

def fn_load_or_train_model(history_df):
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    else:
        return fn_train_model(history_df)

def fn_detect_anomalies(df, history_df, model):
    df["Balance_Difference"] = (df["GL_Balance"] - df["iHUB_Balance"]).round(2)
    df["Match_Status"] = df["Balance_Difference"].apply(lambda x: "Match" if x == 0 else "Break")
    df["Anomaly_status"] = "No"
    df["Comment"] = ""
    df["IsoForest_Score"] = model.predict(df[["Balance_Difference"]])

    account_variability = history_df.groupby("Account")["Balance_Difference"].agg(["mean", "std"]).reset_index()
    account_variability.rename(columns={"mean": "Historical_Mean", "std": "Historical_Std"}, inplace=True)
    df = df.merge(account_variability, on="Account", how="left")

    negative_threshold = df["Balance_Difference"].quantile(0.05)
    positive_threshold = df["Balance_Difference"].quantile(0.95)
    variability_threshold = 1.0

    df.loc[df["IsoForest_Score"] == -1, "Anomaly_status"] = "Yes"
    df.loc[df["Balance_Difference"] < negative_threshold, "Anomaly_status"] = "Yes"
    df.loc[df["Balance_Difference"] > positive_threshold, "Anomaly_status"] = "Yes"
    df.loc[
        ((df["Balance_Difference"] >= (df["Historical_Mean"] - variability_threshold * df["Historical_Std"])) &
         (df["Balance_Difference"] <= (df["Historical_Mean"] + variability_threshold * df["Historical_Std"]))),
        "Anomaly_status"
    ] = "No"

    df["Comment"] = "Balances match correctly. No action needed."
    df.loc[df["Anomaly_status"] == "Yes", "Comment"] = df.apply(
        lambda row: f"Anomaly detected: Balance mismatch of {row['Balance_Difference']}. Verify transactions.", axis=1
    )
    df.loc[(df["Anomaly_status"] == "No") & (df["Match_Status"] == "Break"), "Comment"] = "Balance mismatch detected but not classified as anomaly. Verify transaction history."
    df.drop(columns=["IsoForest_Score"], inplace=True)
    
    return df

# Streamlit UI
st.title("Reconciliation & Anomaly Detection App")
option = st.radio("Choose an option:", ["Anomaly Detection", "Smarter Reconciliation"])

if option == "Anomaly Detection":
    history_file = st.file_uploader("Upload Historical Data (Excel)", type=["xlsx"])
    test_file = st.file_uploader("Upload Test Data (Excel)", type=["xlsx"])

    if history_file and test_file:
        history_df = pd.read_excel(history_file, sheet_name="Sheet1")
        test_df = pd.read_excel(test_file, sheet_name="Sheet1")

        required_cols = {"GL_Balance", "iHUB_Balance", "Account"}
        if not required_cols.issubset(history_df.columns) or not required_cols.issubset(test_df.columns):
            st.error("Error: Files must contain 'GL_Balance', 'iHUB_Balance', and 'Account' columns.")
        else:
            model = fn_load_or_train_model(history_df)
            processed_df = fn_detect_anomalies(test_df, history_df, model)
            st.success("Anomaly detection completed!")
            st.dataframe(processed_df)
            
            output_file = "processed_test_data.xlsx"
            processed_df.to_excel(output_file, index=False)
            with open(output_file, "rb") as f:
                st.download_button("Download Processed Data", f, file_name="processed_test_data.xlsx")

elif option == "Smarter Reconciliation":
    smarter_reconciliation()
    st.success("Jira tickets created for anomalies.")
    JiraAnomalyTicketCreator.load_data()