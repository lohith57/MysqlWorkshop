# 🔥 OCI MySQL HeatWave NL-SQL Assistant

This project is a Natural Language to SQL (NLSQL) chatbot built using **Streamlit** and **OCI MySQL HeatWave**. It allows users to query databases using plain English while enforcing **Role-Based Access Control (RBAC)** and maintaining conversational context.

---

## 🏗️ Step 1: Infrastructure Prerequisites

Before deploying the code, you must set up your OCI environment to allow secure communication between the application and the database.

1.  **VCN**: Create a Virtual Cloud Network (VCN) with at least two subnets.
2.  **HeatWave DB System**: Deploy a MySQL DB System with a HeatWave cluster enabled in a **Private Subnet**.
3.  **Compute VM**: Create a Linux VM (Oracle Linux 8 or 9) in the **Public Subnet** of the same VCN.
4.  **Network Security**:
    * **Security List (Private Subnet)**: Add an Ingress Rule for Port `3306` from the Public Subnet CIDR.
    * **Security List (Public Subnet)**: Add an Ingress Rule for Port `8501` to allow browser access to the Streamlit UI.



---

## 🔐 Step 2: RBAC & User Configuration

The application maps its users to actual MySQL users. This ensures the database handles security at the engine level. Log into your MySQL instance as `admin` and run the following:

###  Create Application Users
```sql
CREATE USER 'user_name'@'%' IDENTIFIED BY 'Strong#Password123';

### Provide Functional Grants

-- Grant data access (RBAC)
GRANT SELECT ON db_name.* TO 'user_name'@'%';

-- Grant access to run HeatWave GenAI routines (sys.ML_GENERATE & sys.NL_SQL)
GRANT EXECUTE ON sys.* TO 'user_name'@'%';

---Example Data sets:
data set :https://docs.oracle.com/en/cloud/paas/digital-assistant/tutorial-sql-dialogs/files/create_employee_db.txt

--- Maintain Conversation History
create database CONV_HISTORY
CREATE USER 'chat_history'@'%' IDENTIFIED BY 'Strong#Password123';

CREATE TABLE chat_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    user_question TEXT NOT NULL,          -- raw user input OR rewritten question
    generated_sql TEXT,                   -- HeatWave output
    answer TEXT NOT NULL,                 -- final assistant response
    app_user VARCHAR(64) NOT NULL,         -- ora_userA, etc
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


## 📦 Step 3: Install Dependencies
pip3 install -r requirements.txt

🐍 Step 4: Virtual Environment (Optional)
# Create the environment
python3 -m venv nlvnv

--Activate it
source nlvnv/bin/activate

-- Install requirements inside the venv
pip install -r requirements.txt

---
🚀 Step 5: Run the Streamlit App
Ensure NLSQL_Backend.py contains the Private IP of your HeatWave instance.

Launch the application:
streamlit run streamlit_app.py