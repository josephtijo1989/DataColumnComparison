import pandas as pd
import numpy as np

def generate_preset_datasets():
    # Preset 1: Customer Directory (Databricks Delta Lake vs SQL Server Production DB)
    np.random.seed(42)
    
    # 500 Customers in Databricks
    cust_ids = [f"CUST-{1000 + i}" for i in range(500)]
    names_first = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Riley", "Dakota", "Reese"]
    names_last = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    tiers = ["Bronze", "Silver", "Gold", "Platinum"]
    
    data_a = []
    for i, cid in enumerate(cust_ids):
        fn = names_first[i % len(names_first)]
        ln = names_last[(i * 3) % len(names_last)]
        email = f"{fn.lower()}.{ln.lower()}{i}@example.com"
        tier = tiers[i % len(tiers)]
        spend = float(round(150.0 + (i * 12.5) % 3500.0, 2))
        score = 600 + (i * 7) % 250
        status = "Active" if i % 12 != 0 else "Inactive"
        data_a.append({
            "customer_id": cid,
            "first_name": fn,
            "last_name": ln,
            "email": email,
            "loyalty_tier": tier,
            "total_spend": spend,
            "credit_score": score,
            "account_status": status
        })
        
    df_a = pd.DataFrame(data_a)
    
    # SQL Server dataset (Source B) - 480 customers (some missing, some mismatched spend/tier/email case)
    data_b = []
    for i, row in enumerate(data_a):
        if i % 25 == 0:
            # Missing in SQL Server
            continue
            
        cid = row["customer_id"]
        fn = row["first_name"]
        ln = row["last_name"]
        email = row["email"]
        tier = row["loyalty_tier"]
        spend = row["total_spend"]
        score = row["credit_score"]
        status = row["account_status"]
        
        # Introduce deliberate diffs for testing compare engine
        if i % 15 == 0:
            # Mismatched spend (e.g. pending sync)
            spend = round(spend + 49.99, 2)
        elif i % 18 == 0:
            # Mismatched loyalty tier
            tier = "Platinum" if tier != "Platinum" else "Gold"
        elif i % 22 == 0:
            # Case difference in email
            email = email.upper()
        elif i % 30 == 0:
            # Status difference
            status = "Pending" if status == "Active" else "Active"
            
        data_b.append({
            "customer_id": cid,
            "first_name": fn,
            "last_name": ln,
            "email": email,
            "loyalty_tier": tier,
            "total_spend": spend,
            "credit_score": score,
            "account_status": status
        })
        
    # Add 15 extra records present only in SQL Server (Source B)
    for j in range(15):
        cid = f"CUST-SQL-{9000 + j}"
        data_b.append({
            "customer_id": cid,
            "first_name": "Legacy",
            "last_name": f"User_{j}",
            "email": f"legacy.user{j}@sqlserver-db.internal",
            "loyalty_tier": "Bronze",
            "total_spend": 99.00,
            "credit_score": 650,
            "account_status": "Active"
        })
        
    df_b = pd.DataFrame(data_b)
    
    # Preset 2: Financial Transactions
    tx_ids = [f"TXN-2026-{10000 + i}" for i in range(300)]
    tx_a = []
    for i, tid in enumerate(tx_ids):
        tx_a.append({
            "txn_id": tid,
            "account_id": f"ACC-{5000 + (i % 50)}",
            "amount": float(round(10.0 + (i * 23.4) % 1200, 2)),
            "currency": "USD" if i % 10 != 0 else "EUR",
            "merchant": f"Store_{i % 20}",
            "status": "SETTLED" if i % 8 != 0 else "PENDING"
        })
    df_tx_a = pd.DataFrame(tx_a)
    
    tx_b = []
    for i, row in enumerate(tx_a):
        if i % 20 == 0:
            continue
        r = dict(row)
        if i % 7 == 0:
            r["amount"] = round(r["amount"] + 0.50, 2)
        if i % 11 == 0:
            r["status"] = "FAILED"
        tx_b.append(r)
    df_tx_b = pd.DataFrame(tx_b)
    
    return {
        "customers": {
            "title": "E-Commerce Customers (Databricks Delta vs SQL Server Production)",
            "description": "Compare customer profile attributes, total spend, and loyalty status across Databricks Analytics Lakehouse and SQL Server OLTP database.",
            "source_a_name": "Databricks Delta Lake (silver.customers)",
            "source_b_name": "SQL Server (Production.Customers)",
            "df_a": df_a,
            "df_b": df_b,
            "default_key": "customer_id",
            "default_compare": ["total_spend", "loyalty_tier", "email", "account_status", "credit_score"]
        },
        "financial_transactions": {
            "title": "Financial Transactions (Databricks Ledger vs SQL Server Core Banking)",
            "description": "Validate daily transactional amounts, status codes, and currencies between analytical ledger and core banking database.",
            "source_a_name": "Databricks Ledger (finance.daily_txns)",
            "source_b_name": "SQL Server (dbo.CoreTransactions)",
            "df_a": df_tx_a,
            "df_b": df_tx_b,
            "default_key": "txn_id",
            "default_compare": ["amount", "status", "currency", "merchant"]
        }
    }
