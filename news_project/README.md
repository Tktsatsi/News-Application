# News Application - Django Project

A comprehensive news publishing platform with role-based access control, article approval workflow, and RESTful API for third-party integrations.

## Features

- **Role-Based Access Control**: Three user roles (Reader, Editor, Journalist) with specific permissions
- **Article Management**: Create, approve, and publish articles
- **Newsletter System**: Independent newsletter publishing
- **Subscription System**: Readers can subscribe to publishers and journalists
- **Email Notifications**: Automatic notifications when articles are approved
- **RESTful API**: Third-party API for retrieving articles based on subscriptions
- **Editorial Workflow**: Editor approval required before publication
- **Django Signals**: Post-approval notifications via signals

## Technology Stack

- **Framework**: Django 5.2.8
- **Database**: MariaDB
- **API**: Django REST Framework
- **Authentication**: Token-based authentication
- **Testing**: Django TestCase & pytest

## Installation

### Prerequisites

- Python 3.8 or higher
- MariaDB 10.5 or higher
- pip package manager

### Step 1: Set Up MariaDB Database

```bash
# Install MariaDB (Ubuntu/Debian)
sudo apt-get install mariadb-server mariadb-client

# Start MariaDB service
sudo systemctl start mariadb

# Secure MariaDB installation
sudo mysql_secure_installation

# Create database and user
sudo mysql -u root -p

# In MySQL prompt:
CREATE DATABASE news_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'news_user'@'localhost' IDENTIFIED BY 'news_password';
GRANT ALL PRIVILEGES ON news_db.* TO 'news_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 2: Install Python Dependencies

```bash
# Navigate to project directory
cd news_project

# Install required packages
pip install -r requirements.txt
```

### Step 3: Configure Settings

Update database credentials in `news_project/settings.py` if different:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'news_db',
        'USER': 'news_user',
        'PASSWORD': 'news_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### Step 4: Run Migrations

```bash
# Create migration files
python manage.py makemigrations

# Apply migrations to database
python manage.py migrate
```

### Step 5: Set Up User Groups and Permissions

```bash
# Run management command to create groups with permissions
python manage.py setup_groups
```

### Step 6: Create Superuser

```bash
# Create admin account
python manage.py createsuperuser
```

### Step 7: Run the Development Server

```bash
# Start the development server
python manage.py runserver
```

Visit http://127.0.0.1:8000/ in your browser.

## User Roles and Permissions

### Reader
- **Permissions**: View articles and newsletters
- **Features**: 
  - Subscribe to publishers and journalists
  - Receive email notifications on new publications
  - View approved articles

### Editor
- **Permissions**: View, update, delete articles and newsletters; approve articles
- **Features**:
  - Review pending articles
  - Approve/reject submissions
  - Trigger notifications on approval

### Journalist
- **Permissions**: Create, view, update, delete articles and newsletters
- **Features**:
  - Submit articles for approval
  - Publish independent newsletters
  - Track submission status

## Database Schema

### Models

1. **CustomUser**
   - Extends Django's AbstractUser
   - Role field (reader/editor/journalist)
   - Subscription fields for readers
   - Automatically assigned to groups

2. **Publisher**
   - Name, description, website
   - Many-to-many with editors and journalists
   - One-to-many with articles

3. **Article**
   - Title, content, summary
   - Foreign keys to author and publisher
   - Approval status and metadata
   - Published date tracking

4. **Newsletter**
   - Title, content
   - Foreign keys to author and publisher
   - Publication date tracking

## API Endpoints

### Authentication
All API endpoints require authentication via Token.

```bash
# Get authentication token
curl -X POST http://localhost:8000/api-auth/login/ \
  -d "username=youruser&password=yourpass"
```

### Endpoints

#### Articles
- `GET /api/articles/` - List all approved articles
- `POST /api/articles/` - Create article (journalists only)
- `GET /api/articles/<id>/` - Retrieve article details
- `PATCH /api/articles/<id>/` - Update article (editors only)
- `DELETE /api/articles/<id>/` - Delete article (editors only)

#### Publishers
- `GET /api/publishers/` - List all publishers
- `GET /api/publishers/<id>/` - Retrieve publisher details
- `GET /api/publishers/<id>/articles/` - Get publisher's articles

#### Journalists
- `GET /api/journalists/<id>/articles/` - Get journalist's articles

#### Subscriptions
- `GET /api/subscriptions/articles/` - Get articles based on user subscriptions

#### Newsletters
- `GET /api/newsletters/` - List all newsletters
- `POST /api/newsletters/` - Create newsletter (journalists only)
- `GET /api/newsletters/<id>/` - Retrieve newsletter details

### API Usage Examples

```bash
# List articles (requires authentication)
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/articles/

# Create article as journalist
curl -X POST \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"My Article","content":"Content here","publisher":1}' \
  http://localhost:8000/api/articles/

# Get subscription-based articles
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/subscriptions/articles/
```

## Testing

### Run All Tests

```bash
# Run all tests
python manage.py test

# Run specific test module
python manage.py test news_app.tests.test_api

# Run with coverage (if installed)
coverage run --source='.' manage.py test
coverage report
```

### Test Coverage

The test suite includes:
- Model tests (validation, relationships)
- API endpoint tests (CRUD operations)
- Permission tests (role-based access)
- Subscription-based article retrieval tests

## Postman Testing

Import the following endpoints into Postman:

1. Create a new collection "News API"
2. Set up environment variables:
   - `base_url`: http://localhost:8000
   - `token`: Your authentication token

3. Test endpoints:
   - GET {{base_url}}/api/articles/
   - POST {{base_url}}/api/articles/
   - GET {{base_url}}/api/subscriptions/articles/

## Web Interface

### Pages

- **Home**: Latest approved articles
- **Article Detail**: Full article view
- **Dashboard**: Role-specific dashboard
- **Pending Approvals**: Editor queue (editors only)
- **Approve Article**: Approval confirmation (editors only)

### Access Control

Access is automatically controlled based on user roles:
- Editors see pending approval queue
- Journalists see their submission stats
- Readers see subscriptions and latest articles

## Email Notifications

Email notifications are sent automatically when articles are approved:

1. Editor approves an article
2. Signal handler is triggered
3. All subscribers receive email notifications

### Email Configuration

For production, update settings.py:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

## Project Structure

```
news_project/
├── news_project/          # Project settings
│   ├── settings.py       # Configuration
│   ├── urls.py          # URL routing
│   └── wsgi.py          # WSGI config
├── news_app/            # Main application
│   ├── models.py        # Data models
│   ├── views.py         # View logic
│   ├── serializers.py   # API serializers
│   ├── signals.py       # Signal handlers
│   ├── permissions.py   # Custom permissions
│   ├── admin.py         # Admin configuration
│   ├── templates/       # HTML templates
│   ├── tests/          # Test suite
│   │   ├── test_models.py
│   │   └── test_api.py
│   └── management/     # Custom commands
│       └── commands/
│           └── setup_groups.py
├── requirements.txt     # Dependencies
└── README.md           # This file
```

## Admin Interface

Access the Django admin at http://127.0.0.1:8000/admin/

Features:
- User management with role assignment
- Article approval/management
- Publisher configuration
- Newsletter management

## Security Considerations

- CSRF protection enabled
- SQL injection prevention (Django ORM)
- XSS prevention (template escaping)
- Secure password hashing
- Token-based API authentication
- Role-based access control

## Troubleshooting

### Database Connection Issues

```bash
# Test database connection
python manage.py dbshell
```

### Migration Issues

```bash
# Reset migrations (development only)
python manage.py migrate news_app zero
python manage.py makemigrations
python manage.py migrate
```

### Permission Issues

```bash
# Re-run setup_groups command
python manage.py setup_groups
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow PEP 8 style guide
4. Write tests for new features
5. Submit pull request

## License

This project is for educational purposes.

## Contact

For questions or support, contact the development team.
