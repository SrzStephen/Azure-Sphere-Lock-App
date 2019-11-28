import logging
from knobs import Knob
import pyodbc

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class UserClass():
    def __init__(self):
        self.dbuser = Knob(env_name="DATABASE_USER", default="", description="Database username")
        self.dbpass = Knob(env_name="DATABASE_PASSWORD", default="", description="Database password")
        self.server = Knob(env_name="DATABASE_SERVER", default="", description="Database server to connect to")
        self.database = Knob(env_name="DATABASE_DATABASE", default="", description="Database to connect to")
        self.table = Knob(env_name="DATABASE_TABLE", default="dbo.Users", description="Users table")
        if any([self.dbpass.get(), self.dbuser.get(), self.server.get(), self.database.get()]) is "":
            raise ValueError("Database Environment variables not set! Check .env to see whats needed.")

        self.connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.server.get()}' \
                                 f';DATABASE={self.database.get()};UID={self.dbuser.get()};PWD={self.dbpass.get()}'
        self.connection = pyodbc.connect(self.connection_string)

    def add_user(self, username, uid, device):
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            f"Insert INTO {self.table.get()} (card_UID,username,door_device) Values ('{uid}','{username}','{device}');")
        self.connection.commit()

    def remove_user(self, username, device):
        self.cursor = self.connection.cursor()
        self.cursor.execute(f"Delete FROM {self.table.get()} WHERE username='{username}' and door_device='{device}';")
        self.connection.commit()

    def user_exists(self, username, device):
        self.cursor = self.connection.cursor()
        self.cursor.execute(f"select * FROM {self.table.get()} WHERE username='{username}' and door_device='{device}';")
        return len(self.cursor.fetchall()) != 0

    def update_user(self, username, uid, device):
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            f"Update {self.table.get()} set card_UID='{uid}' WHERE username='{username}' and door_device='{device}';")
        self.connection.commit()

    def get_device_entries_as_list(self, device):
        self.cursor = self.connection.cursor()
        self.cursor.execute(f"select * FROM {self.table.get()} WHERE door_device='{device}';")
        results = self.cursor.fetchall()
        array = []
        for row in results:
            array.append({"card_id": row[0], "name": row[1]})
        return array


if __name__ == "__main__":
    UserClass().get_device_entries_as_list("test2")
