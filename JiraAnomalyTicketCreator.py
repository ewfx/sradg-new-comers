from jira import JIRA
import pandas as pd

# Step 1: Connect to the Jira server
# (Replace 'JIRA_URL', 'USERNAME', and 'API_TOKEN' with your Jira credentials)
JIRA_URL = "https://smartrecon.atlassian.net/"  # Replace with your Jira URL
USERNAME = "yasmeen_mca@yahoo.co.in"
API_TOKEN = "ATATT3xFfGF0TWq_IvqDiKEF8Bv84Y69jnvbRAr628HrphyCHj4KTvDS2UvOtKyOWRSa5wMo8A-EtRCjpHDDjB30xpFxo8RVNMbLy1aP4vWzsmBG6CJzVKHizgoB3iPi_p4hC-T4Fkacr6YcWTZo5ZUWCgoA9J1WsIkMnq62RpIZY_LFOlt1qrQ=C8766FFB"

jira_options = {"server": JIRA_URL}
jira = JIRA(options=jira_options, basic_auth=(USERNAME, API_TOKEN))


# Step 2: Load anomaly data
def load_data():
    # Example dataset for anomalies
    reconciliation_file = "reconciliation_report_detailed_anomalies.csv"  # Replace with the path to your reconciliation report
    data = pd.read_csv(reconciliation_file)
    return pd.DataFrame(data)


data = load_data()
anomalies = data[(data["PRICE_mismatch"] | data["QUANTITY_mismatch"])]

# Step 3: Create Jira tickets for anomalies
PROJECT_KEY = "NCSR"  # Replace with your Jira project key
summary_prefix = "Reconciliation Anomaly Detected"

# Placeholder for Jira ticket keys
data["Jira_Ticket"] = None

for index, row in anomalies.iterrows():
    # Construct ticket description
    description = f"""
    **TRADE ID:** {row['TRADEID']}
    **PRICE MISMATCH:** {row['PRICE_mismatch']}
    Catalyst: {row['Catalyst_PRICE']}
    Impact: {row['Impact_PRICE']}
    
    **QUANTITY MISMATCH:** {row['QUANTITY_mismatch']}
    Catalyst: {row['Catalyst_QUANTITY']}
    Impact: {row['Impact_QUANTITY']}
    
    Please review and provide feedback.
    """

    # Create Jira issue
    new_issue = jira.create_issue(
        project=PROJECT_KEY,
        summary=f"{summary_prefix} - TRADE ID {row['TRADEID']}",
        description=description,
        issuetype={"name": "Task"},  # Change to your issue type, e.g., Bug, Story, etc.
    )

    # Log ticket key to dataframe
    data.at[index, "Jira_Ticket"] = new_issue.key

print("Jira Tickets Created for Anomalies")
print(data)

# Step 4: Save Jira-linked anomalies to CSV for review
output_file = "anomalies_with_jira_links.csv"
data.to_csv(output_file, index=False)