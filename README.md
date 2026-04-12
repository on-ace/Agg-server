# ⚡ Agg Server

**Local Web Server + MySQL Database Manager** — All in One Desktop App

Agg Server is a lightweight, modern desktop application that combines a simple **local HTTP server** and a powerful **MySQL database GUI manager** in a single clean interface.

Perfect for web developers, students, and anyone who needs a fast local development environment without installing heavy tools like XAMPP or Laragon.

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
	│   └── database.py          
	├── gui/
	│   └── main_window.py       
	├── server/
	│   ├── local_server.py      
	│   └── db_handler.py        
	├── www/                     
	│   └── index.html
	├── main.py                  
	├── requirements.txt
	└── README.md

## 🚀 Installation & Usage

### 1. Clone or Download the Project
	git clone https://github.com/yourusername/agg-server.git
	cd agg-server

### 2. Install Dependencies 
Using pip:
	pip install -r requirements.txt
Or manually:
	pip install PyQt5 mysql-connector-python

### 3. Run the Application
	python main.py

⚠️ Important Notes
- This app is designed for local development only
- Supports MySQL (compatible with MariaDB in most cases)
- For running PHP files, you still need a separate PHP server
- MySQL password is not saved to any file (only in memory while running)

📄 License
	This project is open for personal and educational use. You are free to modify and distribute it.

Built with ❤️ using Python & PyQt5
