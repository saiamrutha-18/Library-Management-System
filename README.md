# Library Management System V2

## Description
The Library Management System -V2 is a web application that allows librarian to efficiently manage sections and books, including performing CRUD operations, granting and revoking books to users, and exporting data as CSV files. Users can request, read, and return books, as well as provide feedback.In all these search functionality is implemented. The system also automates email notifications, sending monthly activity reports and daily reminders to users. Additionally, caching is utilized in specific areas of the application to improve performance.


## Technologies used
- Flask backend for API.
- Vue.js for UIs.
- SQLite for database management.
- Redis for caching frequently accessed data.
- Redis and Celery for batch job processing.
- Bootstrap and CSS for responsive and visually appealing UI design.

## Running Tests Locally
Before running this project locally, ensure you have the following installed:
- Python (for Flask)
- SQLite (usually included with Python installations)
- Redis server
- Celery (Python library)


## Installation
1.Install dependencies

```
pip install -r requirements.txt
```

2.Start the Flask backend:

```
python app.py
```

3.Start Redis server:

```
redis-server
```

4.Start the Celery worker & beat:

```
celery -A app.celery beat --loglevel=info
celery -A app.celery worker -l info
```

5.Start Mailhog

```
mailhog
```

Finding your Inet value and Accessing Mailhog
```
ifconfig
```
Copy the inet value and paste as host and in your browser open  http://inet_value:8025/


6.Access the application in your browser at `http://127.0.0.1:5000/`.

