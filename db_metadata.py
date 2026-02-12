import mysql.connector
from mysql.connector import Error

# ----------------------------------
# USER → DB CREDENTIAL MAPPING
# ----------------------------------
USER_DB_MAPPING = {
    "ora_userA": {
        "user": "userA",
        "password": "App#Pass123!"
    },
    "ora_userB": {
        "user": "userC",
        "password": "App#Pass123!"
    }
}

DB_HOST = "10.0.1.110"
DB_PORT = 3306


def get_connection(app_user):
    creds = USER_DB_MAPPING[app_user]

    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=creds["user"],
        password=creds["password"],
        auth_plugin="caching_sha2_password",
        connection_timeout=10,
        autocommit=True
    )


# ----------------------------------
# Get databases user can access
# (RBAC-safe)
# ----------------------------------
def get_accessible_databases(app_user):
    conn = None
    cursor = None

    try:
        conn = get_connection(app_user)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT table_schema
            FROM information_schema.tables
            WHERE table_schema NOT IN (
                'mysql',
                'information_schema',
                'performance_schema',
                'sys'
            )
            ORDER BY table_schema;
        """)

        return [row[0] for row in cursor.fetchall()]

    except Error as e:
        raise RuntimeError(f"Failed to load databases: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()



# ----------------------------------
# Get tables user can access
# ----------------------------------
def get_accessible_tables(app_user,selected_db):
    conn = None
    cursor = None

    try:
        conn = get_connection(app_user)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
              AND table_schema = %s
              AND table_schema NOT IN (
                  'mysql',
                  'information_schema',
                  'performance_schema',
                  'sys'
              )
            ORDER BY table_schema, table_name;
        """,(selected_db,))

        return cursor.fetchall()

    except Error as e:
        raise RuntimeError(f"Failed to load tables: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()