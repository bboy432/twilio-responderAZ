# Admin Dashboard

The admin dashboard provides centralized monitoring and management of all Twilio responder branch instances.

## Features

- **Multi-Branch Monitoring**: View real-time status of TUC, POC, and REX branches
- **User Management**: Create and manage sub-accounts with granular permissions
- **Branch Control**: Enable/disable branches with confirmation dialogs
- **SMS Notifications**: Automatic notifications when branches are disabled/enabled
- **Session Management**: Secure authentication with session management
- **Permission System**: Control what users can view and manage

## Default Credentials

- **Username**: `axiomadmin`
- **Password**: `Dannyle44!`

⚠️ **IMPORTANT**: Change the default password immediately after first login!

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_SECRET_KEY` | Secret key for session management | `change-this-secret-key` |
| `ADMIN_USERNAME` | Default admin username | `axiomadmin` |
| `ADMIN_PASSWORD` | Default admin password | `Dannyle44!` |
| `NOTIFICATION_PHONE` | Phone number for SMS notifications | `+18017104034` |
| `TUC_URL` | Internal URL for Tucson branch | `http://twilio-app-tuc:5000` |
| `POC_URL` | Internal URL for Pocatello branch | `http://twilio-app-poc:5000` |
| `REX_URL` | Internal URL for Rexburg branch | `http://twilio-app-rex:5000` |
| `TWILIO_ACCOUNT_SID` | Twilio account SID for notifications | - |
| `TWILIO_AUTH_TOKEN` | Twilio auth token for notifications | - |
| `TWILIO_PHONE_NUMBER` | Phone number for sending notifications | - |
| `DATABASE_PATH` | Path to SQLite database | `/app/data/admin.db` |

## Database Schema

### Users Table
- `id` - Primary key
- `username` - Unique username
- `password_hash` - SHA-256 hashed password
- `is_admin` - Admin flag (1=admin, 0=regular user)
- `created_at` - Creation timestamp

### User Permissions Table
- `id` - Primary key
- `user_id` - Foreign key to users table
- `branch` - Branch name (tuc, poc, rex)
- `can_view` - View permission flag
- `can_trigger` - Trigger emergency permission flag
- `can_disable` - Enable/disable branch permission flag

### Branch Status Table
- `branch` - Primary key (tuc, poc, rex)
- `is_enabled` - Enable status flag
- `disabled_at` - Timestamp when disabled
- `disabled_by` - Username who disabled the branch
- `last_check` - Last status check timestamp

## User Types

### Admin Users
- Full access to all branches
- Can create and delete users
- Can modify user permissions
- Can enable/disable all branches
- Access to user management interface

### Regular Users
- Permissions controlled per branch
- Can view branches they have access to
- Can trigger emergencies if permitted
- Can enable/disable branches if permitted
- Cannot create or manage other users

## Permission Types

### View Permission
- Access to branch dashboard
- View branch status and logs
- See emergency timeline

### Trigger Permission
- Initiate emergency calls
- Send test notifications
- Access emergency trigger interface

### Disable Permission
- Enable/disable branch temporarily
- Receive confirmation dialogs
- Trigger SMS notifications on changes

## API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - Process login
- `GET /logout` - Logout and clear session

### Dashboard
- `GET /` - Main dashboard (requires login)
- `GET /branch/<branch>` - Individual branch dashboard

### Branch Management
- `GET /api/branch/<branch>/status` - Get branch status (JSON)
- `POST /api/branch/<branch>/disable` - Disable a branch
- `POST /api/branch/<branch>/enable` - Enable a branch

### User Management (Admin Only)
- `GET /users` - User management page
- `POST /users/create` - Create new user
- `POST /users/<id>/delete` - Delete user

## Security Features

1. **Password Hashing**: PBKDF2-SHA256 hashing with salt for all passwords (secure key derivation)
2. **Session Management**: Secure session cookies with configurable lifetime (12 hours)
3. **CSRF Protection**: Built-in Flask CSRF protection
4. **Permission Checking**: All actions validated against user permissions
5. **Confirmation Dialogs**: Double confirmation for critical actions (disable branch)

## SMS Notifications

When a branch is disabled or enabled, an SMS is sent to the configured `NOTIFICATION_PHONE`:

**Disable Example:**
```
ALERT: Tucson branch has been DISABLED by axiomadmin at 2025-10-21 15:30:00
```

**Enable Example:**
```
INFO: Tucson branch has been ENABLED by axiomadmin at 2025-10-21 15:35:00
```

## Auto-Refresh

The dashboard automatically refreshes branch statuses every 30 seconds to provide real-time monitoring without manual page refresh.

## Development

### Local Setup
```bash
cd admin-dashboard
pip install -r requirements.txt
export FLASK_SECRET_KEY=your-secret-key
export DATABASE_PATH=./admin.db
python app.py
```

Access at http://localhost:5000

### Docker Setup
```bash
docker build -t admin-dashboard .
docker run -p 5000:5000 \
  -e FLASK_SECRET_KEY=your-secret-key \
  -e TUC_URL=http://tuc:5000 \
  -e POC_URL=http://poc:5000 \
  -e REX_URL=http://rex:5000 \
  admin-dashboard
```

## Troubleshooting

### Cannot Login
- Verify database exists and is writable
- Check default credentials haven't been changed in environment
- Clear browser cookies and try again

### Branch Shows Offline
- Verify branch container is running
- Check network connectivity between containers
- Verify branch URL in environment variables

### Permissions Not Working
- Verify user has correct permissions in database
- Check if user is admin (admins bypass permission checks)
- Logout and login again to refresh session

### SMS Notifications Not Sending
- Verify Twilio credentials are correct
- Check Twilio account has SMS capability
- Verify phone number format: `+1XXXXXXXXXX`

## Database Backup

```bash
# Backup
docker cp twilio_responder_admin:/app/data/admin.db ./admin.db.backup

# Restore
docker cp ./admin.db.backup twilio_responder_admin:/app/data/admin.db
docker restart twilio_responder_admin
```

## Resetting Admin Password

If you lose the admin password, you can reset it by recreating the database:

```bash
docker exec -it twilio_responder_admin rm /app/data/admin.db
docker restart twilio_responder_admin
```

This will recreate the database with default credentials.
