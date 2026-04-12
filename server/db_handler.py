import mysql.connector
from mysql.connector import Error

class DatabaseManager:
    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.connection = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password
            )
            return True
        except Error as e:
            return str(e)

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()

    def get_databases(self):
        cursor = self.connection.cursor()
        cursor.execute("SHOW DATABASES")
        dbs = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return dbs

    def get_tables(self, database):
        cursor = self.connection.cursor()
        cursor.execute(f"USE `{database}`")
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables

    def get_table_data(self, database, table, limit=100):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(f"USE `{database}`")
        cursor.execute(f"SELECT * FROM `{table}` LIMIT {limit}")
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def execute_query(self, database, query):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(f"USE `{database}`")
        cursor.execute(query)
        if query.strip().upper().startswith("SELECT"):
            result = cursor.fetchall()
        else:
            self.connection.commit()
            result = {"affected_rows": cursor.rowcount}
        cursor.close()
        return result

    # DDL Operations
    def create_database(self, db_name):
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
            self.connection.commit()
            cursor.close()
            return {"success": True, "message": f"Database '{db_name}' created."}
        except Error as e:
            return {"success": False, "error": str(e)}

    def drop_database(self, db_name):
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
            self.connection.commit()
            cursor.close()
            return {"success": True, "message": f"Database '{db_name}' dropped."}
        except Error as e:
            return {"success": False, "error": str(e)}

    def create_table(self, database, table_name, columns):
        # columns: list of dict [{"name":str, "type":str, "length":int/None, "nullable":bool, "primary_key":bool}]
        col_defs = []
        primary_keys = []
        for col in columns:
            col_def = f"`{col['name']}` {col['type']}"
            if col.get('length'):
                col_def += f"({col['length']})"
            if not col.get('nullable', True):
                col_def += " NOT NULL"
            if col.get('primary_key'):
                primary_keys.append(col['name'])
            col_defs.append(col_def)
        if primary_keys:
            col_defs.append(f"PRIMARY KEY ({', '.join(['`'+pk+'`' for pk in primary_keys])})")
        create_sql = f"CREATE TABLE IF NOT EXISTS `{database}`.`{table_name}` (\n  " + ",\n  ".join(col_defs) + "\n)"
        try:
            cursor = self.connection.cursor()
            cursor.execute(create_sql)
            self.connection.commit()
            cursor.close()
            return {"success": True, "message": f"Table '{table_name}' created."}
        except Error as e:
            return {"success": False, "error": str(e)}

    def drop_table(self, database, table_name):
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS `{database}`.`{table_name}`")
            self.connection.commit()
            cursor.close()
            return {"success": True, "message": f"Table '{table_name}' dropped."}
        except Error as e:
            return {"success": False, "error": str(e)}