import mysql.connector
from mysql.connector import Error


class DatabaseManager:
    def __init__(self, host="localhost", port=3306, user="root", password=""):
        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password
        self.connection = None

    # ── Koneksi ──────────────────────────────────────────────
    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host, port=self.port,
                user=self.user, password=self.password,
                connection_timeout=5, autocommit=False,
            )
            return True
        except Error as e:
            self.connection = None
            return str(e)

    def disconnect(self):
        try:
            if self.connection and self.connection.is_connected():
                self.connection.close()
        except Exception:
            pass
        self.connection = None

    def is_connected(self):
        try:
            return self.connection is not None and self.connection.is_connected()
        except Exception:
            return False

    def _cursor(self, dictionary=True):
        if not self.is_connected():
            self.connect()
        return self.connection.cursor(dictionary=dictionary)

    # ── Database ─────────────────────────────────────────────
    def get_databases(self):
        try:
            cur = self._cursor(dictionary=False)
            cur.execute("SHOW DATABASES")
            dbs = [r[0] for r in cur.fetchall()]
            cur.close()
            return dbs
        except Error:
            return []

    def create_database(self, db_name, charset="utf8mb4", collation="utf8mb4_general_ci"):
        try:
            cur = self._cursor(dictionary=False)
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET {charset} COLLATE {collation}")
            self.connection.commit()
            cur.close()
            return {"success": True, "message": f"Database '{db_name}' berhasil dibuat."}
        except Error as e:
            return {"success": False, "error": str(e)}

    def drop_database(self, db_name):
        try:
            cur = self._cursor(dictionary=False)
            cur.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
            self.connection.commit()
            cur.close()
            return {"success": True, "message": f"Database '{db_name}' berhasil dihapus."}
        except Error as e:
            return {"success": False, "error": str(e)}

    # ── Tabel ─────────────────────────────────────────────────
    def get_tables(self, database):
        try:
            cur = self._cursor(dictionary=False)
            cur.execute(f"USE `{database}`")
            cur.execute("SHOW TABLES")
            tables = [r[0] for r in cur.fetchall()]
            cur.close()
            return tables
        except Error:
            return []

    def get_table_columns(self, database, table):
        try:
            cur = self._cursor()
            cur.execute(f"SHOW FULL COLUMNS FROM `{database}`.`{table}`")
            cols = cur.fetchall()
            cur.close()
            return cols
        except Error:
            return []

    def get_table_data(self, database, table, limit=200, offset=0):
        try:
            cur = self._cursor()
            cur.execute(f"SELECT * FROM `{database}`.`{table}` LIMIT {limit} OFFSET {offset}")
            rows = cur.fetchall()
            cur.close()
            cur2 = self._cursor(dictionary=False)
            cur2.execute(f"SELECT COUNT(*) FROM `{database}`.`{table}`")
            total = cur2.fetchone()[0]
            cur2.close()
            return {"rows": rows, "total": total}
        except Error as e:
            return {"rows": [], "total": 0, "error": str(e)}

    def create_table(self, database, table_name, columns):
        col_defs = []
        pk_cols = []
        for col in columns:
            t = col["type"].upper()
            cd = f"`{col['name']}` {t}"
            if col.get("length"):
                cd += f"({col['length']})"
            if col.get("unsigned"):
                cd += " UNSIGNED"
            if not col.get("nullable", True):
                cd += " NOT NULL"
            if col.get("auto_increment"):
                cd += " AUTO_INCREMENT"
            if col.get("default") not in (None, ""):
                cd += f" DEFAULT '{col['default']}'"
            col_defs.append(cd)
            if col.get("primary_key"):
                pk_cols.append(col["name"])
            if col.get("unique") and not col.get("primary_key"):
                col_defs.append(f"UNIQUE KEY `uq_{col['name']}` (`{col['name']}`)")
        if pk_cols:
            col_defs.append("PRIMARY KEY (" + ", ".join(f"`{k}`" for k in pk_cols) + ")")
        sql = (f"CREATE TABLE IF NOT EXISTS `{database}`.`{table_name}` (\n  " +
               ",\n  ".join(col_defs) + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
        try:
            cur = self._cursor(dictionary=False)
            cur.execute(sql)
            self.connection.commit()
            cur.close()
            return {"success": True, "message": f"Tabel '{table_name}' berhasil dibuat.", "sql": sql}
        except Error as e:
            return {"success": False, "error": str(e), "sql": sql}

    def drop_table(self, database, table_name):
        try:
            cur = self._cursor(dictionary=False)
            cur.execute(f"DROP TABLE IF EXISTS `{database}`.`{table_name}`")
            self.connection.commit()
            cur.close()
            return {"success": True, "message": f"Tabel '{table_name}' berhasil dihapus."}
        except Error as e:
            return {"success": False, "error": str(e)}

    def truncate_table(self, database, table_name):
        try:
            cur = self._cursor(dictionary=False)
            cur.execute(f"TRUNCATE TABLE `{database}`.`{table_name}`")
            self.connection.commit()
            cur.close()
            return {"success": True, "message": f"Tabel '{table_name}' dikosongkan."}
        except Error as e:
            return {"success": False, "error": str(e)}

    def get_create_table_sql(self, database, table_name):
        try:
            cur = self._cursor(dictionary=False)
            cur.execute(f"SHOW CREATE TABLE `{database}`.`{table_name}`")
            row = cur.fetchone()
            cur.close()
            return row[1] if row else ""
        except Error:
            return ""

    # ── Row CRUD ─────────────────────────────────────────────
    def insert_row(self, database, table, data: dict):
        try:
            cols = ", ".join(f"`{k}`" for k in data)
            ph = ", ".join(["%s"] * len(data))
            sql = f"INSERT INTO `{database}`.`{table}` ({cols}) VALUES ({ph})"
            cur = self._cursor(dictionary=False)
            cur.execute(sql, list(data.values()))
            self.connection.commit()
            lid = cur.lastrowid
            cur.close()
            return {"success": True, "message": "Row ditambahkan.", "last_id": lid}
        except Error as e:
            self.connection.rollback()
            return {"success": False, "error": str(e)}

    def update_row(self, database, table, data: dict, where: dict):
        try:
            set_clause = ", ".join(f"`{k}` = %s" for k in data)
            where_clause = " AND ".join(f"`{k}` = %s" for k in where)
            sql = f"UPDATE `{database}`.`{table}` SET {set_clause} WHERE {where_clause}"
            cur = self._cursor(dictionary=False)
            cur.execute(sql, list(data.values()) + list(where.values()))
            self.connection.commit()
            affected = cur.rowcount
            cur.close()
            return {"success": True, "message": f"{affected} row diupdate."}
        except Error as e:
            self.connection.rollback()
            return {"success": False, "error": str(e)}

    def delete_row(self, database, table, where: dict):
        try:
            where_clause = " AND ".join(f"`{k}` = %s" for k in where)
            sql = f"DELETE FROM `{database}`.`{table}` WHERE {where_clause}"
            cur = self._cursor(dictionary=False)
            cur.execute(sql, list(where.values()))
            self.connection.commit()
            affected = cur.rowcount
            cur.close()
            return {"success": True, "message": f"{affected} row dihapus."}
        except Error as e:
            self.connection.rollback()
            return {"success": False, "error": str(e)}

    # ── SQL Query bebas ───────────────────────────────────────
    def execute_query(self, database, query):
        try:
            cur = self._cursor()
            if database:
                cur.execute(f"USE `{database}`")
            statements = [q.strip() for q in query.split(";") if q.strip()]
            last_result = None
            for stmt in statements:
                cur.execute(stmt)
                upper = stmt.upper().lstrip()
                if any(upper.startswith(k) for k in ("SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "DESC")):
                    cols = [d[0] for d in cur.description] if cur.description else []
                    rows = cur.fetchall()
                    last_result = {"rows": rows, "columns": cols}
                else:
                    self.connection.commit()
                    last_result = {"affected_rows": cur.rowcount, "message": "Query berhasil."}
            cur.close()
            return last_result or {"message": "Selesai."}
        except Error as e:
            try:
                self.connection.rollback()
            except Exception:
                pass
            return {"error": str(e)}

    def export_table_sql(self, database, table):
        try:
            create = self.get_create_table_sql(database, table)
            result = self.get_table_data(database, table, limit=50000)
            rows = result.get("rows", [])
            lines = [f"-- Dump tabel `{table}`",
                     f"DROP TABLE IF EXISTS `{table}`;",
                     create + ";", ""]
            if rows:
                cols = ", ".join(f"`{k}`" for k in rows[0].keys())
                for row in rows:
                    vals = ", ".join(
                        "NULL" if v is None
                        else f"'{str(v).replace(chr(39), chr(39)*2)}'"
                        for v in row.values()
                    )
                    lines.append(f"INSERT INTO `{table}` ({cols}) VALUES ({vals});")
            return "\n".join(lines)
        except Exception as e:
            return f"-- Error: {e}"
