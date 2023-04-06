# Calendly Clone (Limited to Google)
Built as a showcase for Apexive. <br>
Aim is to build somthing close to Calendly. <br>

Allows users to schedule an event with availability. 
Availabilty is converted to slots based on event duration.
Slots are sent by mail to invitees who can pick a slot.
Selected slots are created on the event owner's Google Calendar as a Calendar-Event with Meet Link.
Webhooks are automatically activated for the Calendar-Event which helps keep the data consistent with Google Calendar

This is a brief description of the project.


## Getting Started
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Docker
- Docker Compose

### Installing
1. Clone the repository:
```
git clone https://github.com/beni1028/calendly_clone.git

```
2. Change into the project directory:

3. Build and start the Docker containers:
```
docker-compose up -d --build
````

### Django Migrations

To make migrations and migrate the Django application:

1. SSH into the Django container:
```
docker exec -it apexive_demo /bin/sh
```
2. Make migrations:
```
python manage.py makemigrations
```
3. Migrate the database:
```
python manage.py migrate
```
The Django application should now be set up and ready to use.

## Usage
Currently, to access the application the user needs use login via Google OAuth.
This is required to help get access to Google Calendar

# Available APIs

The following APIs are available in this project:

| Method| API | Description | 
| --- | --- | --- |
| GET|`/accounts/event-slots/<slug>` | Retrieves available slots to book a meeting |
| POST|`/accounts/event-slots/<slug>` | Send selected slot to book |
| POST|`/accounts/oauth2callback/` | Send activation code from front-end to verify and login user. Returns a token |

##TODO
- Add barebone UI using react
- Auto-creating backups of dB
- Logging 
 



