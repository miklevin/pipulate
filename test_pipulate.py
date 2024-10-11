import unittest
import requests
import sqlite3
import os
import json
from rich.console import Console
from rich.table import Table
from pyfiglet import Figlet
from bs4 import BeautifulSoup
import argparse

# Configurable constants for table names and endpoints
TODO = "task"
PROFILE = "profile"

# Get the folder name and create Figlet
folder_name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
f = Figlet(font='slant')
figlet_text = f.renderText(folder_name.capitalize())

# Print the Figlet
print(figlet_text)


class TestBotifythonApp(unittest.TestCase):
    # Server and Database Tests
    SERVER_RUNNING = {"section": "Server and Database", "endpoint": "/", "method": "GET", "description": "Check if the server is running", "test_func": 'test_server_running'}
    DATABASE_TABLES = {"section": "Server and Database", "endpoint": "Database", "method": "Check", "description": "Verify 'TODO' and 'PROFILE' tables exist", "test_func": 'test_database_tables'}
    
    # Todo Functionality Tests
    GET_TODOS = {"section": "Todo Functionality", "endpoint": f"/{TODO}", "method": "GET", "description": "Retrieve all todo items", "test_func": 'test_get_todos'}
    CREATE_TODO = {"section": "Todo Functionality", "endpoint": f"/{TODO}", "method": "POST", "description": "Create a new todo item", "test_func": 'test_create_todo'}
    UPDATE_TODO = {"section": "Todo Functionality", "endpoint": f"/{TODO}/update/{{todo_id}}", "method": "POST", "description": "Update an existing todo item", "test_func": 'test_update_todo'}
    TOGGLE_TODO = {"section": "Todo Functionality", "endpoint": f"/{TODO}/toggle/{{tid}}", "method": "POST", "description": "Toggle the completion status of a todo item", "test_func": 'test_toggle_todo'}
    SORT_TODOS = {"section": "Todo Functionality", "endpoint": f"/{TODO}_sort", "method": "POST", "description": "Sort todo items based on priority", "test_func": 'test_sort_todos'}
    DELETE_TODO = {"section": "Todo Functionality", "endpoint": f"/{TODO}/delete/{{tid}}", "method": "DELETE", "description": "Delete a todo item", "test_func": 'test_delete_todo'}
    
    # Profile Functionality Tests
    GET_PROFILES = {"section": "Profile Functionality", "endpoint": f"/{PROFILE}", "method": "GET", "description": "Retrieve all profiles", "test_func": 'test_get_profiles'}
    CREATE_PROFILE = {"section": "Profile Functionality", "endpoint": f"/{PROFILE}", "method": "POST", "description": "Create a new profile", "test_func": 'test_create_profile'}
    UPDATE_PROFILE = {"section": "Profile Functionality", "endpoint": f"/{PROFILE}/update/{{profile_id}}", "method": "POST", "description": "Update an existing profile", "test_func": 'test_update_profile'}
    TOGGLE_PROFILE = {"section": "Profile Functionality", "endpoint": f"/{PROFILE}/toggle/{{pid}}", "method": "POST", "description": "Toggle the active status of a profile", "test_func": 'test_toggle_profile'}
    SORT_PROFILES = {"section": "Profile Functionality", "endpoint": f"/{PROFILE}_sort", "method": "POST", "description": "Sort profiles based on priority", "test_func": 'test_sort_profiles'}
    DELETE_PROFILE = {"section": "Profile Functionality", "endpoint": f"/{PROFILE}/delete/{{profile_id}}", "method": "DELETE", "description": "Delete a profile", "test_func": 'test_delete_profile'}
    
    # Additional Endpoints Tests
    SEARCH = {"section": "Additional Endpoints", "endpoint": "/search", "method": "POST", "description": "Perform a search query", "test_func": 'test_search'}
    POKE_CHATBOT = {"section": "Additional Endpoints", "endpoint": "/poke", "method": "POST", "description": "Poke the chatbot to get a response", "test_func": 'test_poke_chatbot'}

    test_config = [
        SERVER_RUNNING, DATABASE_TABLES,
        GET_TODOS, CREATE_TODO, UPDATE_TODO, TOGGLE_TODO, SORT_TODOS, DELETE_TODO,
        GET_PROFILES, CREATE_PROFILE, UPDATE_PROFILE, TOGGLE_PROFILE, SORT_PROFILES, DELETE_PROFILE,
        SEARCH, POKE_CHATBOT
    ]

    @classmethod
    def setUpClass(cls):
        cls.base_url = "http://localhost:5001"
        cls.db_path = "data/data.db"
        cls.conn = sqlite3.connect(cls.db_path)
        cls.cursor = cls.conn.cursor()
        cls.test_results = []

    def setUp(self):
        self.test_todo_id = None
        self.test_profile_id = None

    def tearDown(self):
        pass  # Any necessary cleanup after each test

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.print_summary()

    def add_result(self, config_entry, status, message=""):
        self.test_results.append({
            "section": config_entry["section"],
            "endpoint": config_entry["endpoint"],
            "method": config_entry["method"],
            "status": status,
            "message": message
        })
        TestBotifythonApp.test_results.append({
            "section": config_entry["section"],
            "endpoint": config_entry["endpoint"],
            "method": config_entry["method"],
            "status": status,
            "message": message
        })

    @classmethod
    def print_summary(cls):
        console = Console()
        table = Table(title="Test Summary")

        table.add_column("Section", style="bold cyan")
        table.add_column("Method", style="green")
        table.add_column("Endpoint", style="magenta")
        table.add_column("Status", style="bold")
        table.add_column("Message", style="yellow")

        def style_endpoint(endpoint):
            # Split the endpoint by slashes and style each part
            parts = endpoint.split('/')
            styled_parts = [f"[magenta]{part}[/magenta]" if part else "" for part in parts]
            return "[white]/[/white]".join(styled_parts)

        previous_section = None
        for config_entry in cls.test_config:
            result = next((res for res in cls.test_results if res["endpoint"] == config_entry["endpoint"] and res["method"] == config_entry["method"]), None)
            if previous_section and previous_section != config_entry["section"]:
                # Add a separator line between different sections
                table.add_row("", "", "", "", "")  # Empty row for separation
            if result:
                status_color = "green" if result["status"] == "Success" else "red"
                table.add_row(
                    result["section"],
                    result["method"],
                    style_endpoint(result["endpoint"]),
                    f"[{status_color}]{result['status']}[/{status_color}]",
                    result["message"]
                )
            else:
                table.add_row(
                    config_entry["section"],
                    config_entry["method"],
                    style_endpoint(config_entry["endpoint"]),
                    "[yellow]Skipped[/yellow]",
                    "No result found or test not executed"
                )
            previous_section = config_entry["section"]

        console.print(table)

    def find_config_entry(self, test_func_name):
        return next(entry for entry in self.test_config if entry["test_func"] == test_func_name)

    def extract_profile_id(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        li_element = soup.find('li', id=lambda x: x and x.startswith('profile-'))
        if li_element:
            return li_element['id'].split('-')[1]
        return None

    # *******************************
    # Server and Database Tests
    # *******************************
    def test_server_running(self):
        response = requests.get(f"{self.base_url}/")
        status = "Success" if response.status_code == 200 else "Failure"
        self.add_result(self.find_config_entry("test_server_running"), status, "Server is running")
        self.assertEqual(response.status_code, 200)

    def test_database_tables(self):
        tables = ["TODO", "PROFILE"]  # Actual table names in the database
        for table_name in tables:
            self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            exists = self.cursor.fetchone()
            status = "Success" if exists else "Failure"
            self.add_result(self.find_config_entry("test_database_tables"), status, f"'{table_name}' table exists")
            self.assertTrue(exists, f"The '{table_name}' table does not exist")

    # *******************************
    # Todo Functionality Tests (CRUD + Get + Sort)
    # *******************************
    def test_create_todo(self):
        new_todo = {"title": "Test Todo Item"}
        response = requests.post(f"{self.base_url}/{TODO}", data=new_todo)
        status = "Success" if response.status_code == 200 else "Failure"
        self.add_result(self.find_config_entry("test_create_todo"), status, "Created new todo")
        self.assertEqual(response.status_code, 200)
        self.cursor.execute("SELECT id FROM TODO ORDER BY id DESC LIMIT 1")  # Use actual table name
        self.test_todo_id = self.cursor.fetchone()[0]

    def test_get_todos(self):
        response = requests.get(f"{self.base_url}/{TODO}")
        status = "Success" if response.status_code == 200 else "Failure"
        self.add_result(self.find_config_entry("test_get_todos"), status, "Fetched all todo items")
        self.assertEqual(response.status_code, 200)

    def test_update_todo(self):
        if not self.test_todo_id:
            self.test_create_todo()
        update_data = {"todo_title": "Updated Test Todo Item"}
        response = requests.post(f"{self.base_url}/{TODO}/update/{self.test_todo_id}", data=update_data)
        status = "Success" if response.status_code == 200 else "Failure"
        self.add_result(self.find_config_entry("test_update_todo"), status, "Updated todo")
        self.assertEqual(response.status_code, 200)

    def test_toggle_todo(self):
        if not self.test_todo_id:
            self.test_create_todo()
        response = requests.post(f"{self.base_url}/{TODO}/toggle/{self.test_todo_id}")
        status = "Success" if response.status_code == 200 else "Failure"
        self.add_result(self.find_config_entry("test_toggle_todo"), status, "Toggled todo status")
        self.assertEqual(response.status_code, 200)

    def test_delete_todo(self):
        if not self.test_todo_id:
            self.test_create_todo()
        response = requests.delete(f"{self.base_url}/{TODO}/delete/{self.test_todo_id}")
        status = "Success" if response.status_code == 200 else "Failure"
        self.add_result(self.find_config_entry("test_delete_todo"), status, "Deleted todo")
        self.assertEqual(response.status_code, 200)

    def test_sort_todos(self):
        sort_data = {"items": '[{"id": 1, "priority": 0}, {"id": 2, "priority": 1}]'}
        response = requests.post(f"{self.base_url}/{TODO}_sort", data=sort_data)
        status = "Success" if response.status_code == 200 else "Failure"
        self.add_result(self.find_config_entry("test_sort_todos"), status, "Sorted todo items by priority")
        self.assertEqual(response.status_code, 200)

    # *******************************
    # Profile Functionality Tests (CRUD + Get + Sort)
    # *******************************
    def test_create_profile(self):
        new_profile = {
            "profile_name": "Test Client",
            "profile_address": "123 Test St",
            "profile_code": "TEST001"
        }
        response = requests.post(f"{self.base_url}/{PROFILE}", data=new_profile)
        status = "Success" if response.status_code == 200 else "Failure"
        self.add_result(self.find_config_entry("test_create_profile"), status, "Created new profile")
        self.assertEqual(response.status_code, 200, f"Failed to create profile. Status: {response.status_code}, Response: {response.text}")
        self.test_profile_id = self.extract_profile_id(response.text)
        self.assertIsNotNone(self.test_profile_id, "Profile ID not found in response")

    def test_get_profiles(self):
        response = requests.get(f"{self.base_url}/{PROFILE}")
        status = "Success" if response.status_code == 200 else "Failure"
        self.add_result(self.find_config_entry("test_get_profiles"), status, "Fetched all profiles")
        self.assertEqual(response.status_code, 200)

    def test_update_profile(self):
        self.test_create_profile()  # Ensure a profile exists
        if hasattr(self, 'test_profile_id'):
            update_data = {"name": "Updated Client", "address": "456 Updated St", "code": "UPDATED001"}
            response = requests.post(f"{self.base_url}/{PROFILE}/update/{self.test_profile_id}", data=update_data)
            self.add_result(self.find_config_entry("test_update_profile"), "Success" if response.status_code == 200 else "Failure", "Updated profile")
            self.assertEqual(response.status_code, 200, f"Failed to update profile. Status: {response.status_code}, Response: {response.text}")
        else:
            self.fail("No profile ID available for testing")

    def test_toggle_profile(self):
        self.test_create_profile()  # Ensure a profile exists
        if hasattr(self, 'test_profile_id'):
            response = requests.post(f"{self.base_url}/{PROFILE}/toggle/{self.test_profile_id}")
            self.add_result(self.find_config_entry("test_toggle_profile"), "Success" if response.status_code == 200 else "Failure", "Toggled profile")
            self.assertEqual(response.status_code, 200, f"Failed to toggle profile. Status: {response.status_code}, Response: {response.text}")
        else:
            self.fail("No profile ID available for testing")

    def test_sort_profiles(self):
        sort_data = {"items": json.dumps([{"id": 1, "priority": 0}, {"id": 2, "priority": 1}])}
        response = requests.post(f"{self.base_url}/{PROFILE}_sort", data=sort_data)
        self.add_result(self.find_config_entry("test_sort_profiles"), "Success" if response.status_code == 200 else "Failure", "Sorted profiles")
        self.assertEqual(response.status_code, 200, f"Failed to sort profiles. Status: {response.status_code}, Response: {response.text}")

    def test_delete_profile(self):
        self.test_create_profile()  # Ensure a profile exists
        if hasattr(self, 'test_profile_id'):
            response = requests.delete(f"{self.base_url}/{PROFILE}/delete/{self.test_profile_id}")
            self.add_result(self.find_config_entry("test_delete_profile"), "Success" if response.status_code == 200 else "Failure", "Deleted profile")
            self.assertEqual(response.status_code, 200, f"Failed to delete profile. Status: {response.status_code}, Response: {response.text}")
        else:
            self.fail("No profile ID available for testing")

    # *******************************
    # Additional Endpoints Tests
    # *******************************
    def test_search(self):
        search_term = "Sample Search"
        response = requests.post(f"{self.base_url}/search", data={"nav_input": search_term})
        status = "Success" if response.status_code == 200 else "Failure"
        self.add_result(self.find_config_entry("test_search"), status, "Search request processed")
        self.assertEqual(response.status_code, 200)

    def test_poke_chatbot(self):
        response = requests.post(f"{self.base_url}/poke")
        status = "Success" if response.status_code == 200 else "Failure"
        self.add_result(self.find_config_entry("test_poke_chatbot"), status, "Poke request processed")
        self.assertEqual(response.status_code, 200)

    # *******************************
    # Dynamic Test Execution
    # *******************************
    def test_dynamic_execution(self):
        for config_entry in self.test_config:
            test_func_name = config_entry["test_func"]
            if hasattr(self, test_func_name):
                test_func = getattr(self, test_func_name)
                test_func()
            else:
                self.add_result(config_entry, "Skipped", f"Function '{test_func_name}' not found")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tests with optional verbosity.")
    parser.add_argument('-v', '--verbose', action='store_true', help="Increase output verbosity")
    args = parser.parse_args()

    # Run the tests with the specified verbosity
    verbosity_level = 2 if args.verbose else 1
    unittest.main(verbosity=verbosity_level, exit=False)

    # Print the test summary only if verbose mode is enabled
    if args.verbose:
        TestBotifythonApp.print_summary()

    # Summary of test results
    success_count = sum(1 for result in TestBotifythonApp.test_results if result["status"] == "Success")
    failure_count = sum(1 for result in TestBotifythonApp.test_results if result["status"] == "Failure")

    print(f"\nTotal Successes: {success_count}")
    print(f"Total Failures: {failure_count}")
