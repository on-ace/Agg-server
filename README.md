# Agg-server
⚡ Agg Server — Local Web Server + MySQL GUI Manager  A clean, modern desktop app to run a local HTTP server and manage MySQL databases visually. Built with Python and PyQt5.  Features: Local Server, Database CRUD, SQL Editor, Table Structure, SQL Export, Dark Theme.

![Agg Server Preview](https://via.placeholder.com/800x450/0f172a/22d3ee?text=Agg+Server+Screenshot)

## ✨ Key Features

### 🌐 Server Tab
- Start and stop local web server with one click
- Custom port (default: 8000)
- Serves all files from the `www/` directory
- Real-time status indicator
- "Open in Browser" button

### 🗄️ Database Manager
- Connect to any MySQL server
- Tree view of all databases and tables
- Browse table data with pagination
- Full **CRUD** operations (Insert, Edit, Delete rows)
- Built-in **SQL Query Editor** with result table
- View table structure and `SHOW CREATE TABLE` SQL
- Export table to `.sql` dump file

### 🛠️ Database Tools
- Create / Drop Database
- Create Table using visual dialog (supports Primary Key, Auto Increment, NOT NULL, Default, etc.)
- Drop or Truncate Table
- Execute multiple SQL statements
- Clean dark modern UI

## 🛠️ Technologies

- Python 3
- PyQt5 (GUI)
- mysql-connector-python
- Built-in `http.server` + threading

## 📁 Project Structure

Agg-Server/
├── db/
│   └── database.py          # MySQL core manager
├── gui/
│   └── main_window.py       # Main window and UI logic
├── server/
│   ├── local_server.py      # HTTP server thread
│   └── db_handler.py        # Legacy handler
├── www/                     # Web root folder
│   └── index.html
├── main.py                  # Application launcher
├── requirements.txt
└── README.md

## 🚀 Installation & Usage

### 1. Clone or Download the Project
	```bash
	git clone https://github.com/yourusername/agg-server.git
	cd agg-server

### 2. Install Dependencies 
Using pip:
	```bash
    pip install -r requirements.txt
Or manually:
	```bash
	pip install PyQt5 mysql-connector-python

### 3. Run the Application
	```bash
	python main.py

⚠️ Important Notes

	- This app is designed for local development only
	- Supports MySQL (compatible with MariaDB in most cases)
	- For running PHP files, you still need a separate PHP server
	- MySQL password is not saved to any file (only in memory while running)

📄 License
	This project is open for personal and educational use. You are free to modify and distribute it.

Built with ❤️ using Python & PyQt5
