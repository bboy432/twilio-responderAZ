# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the local requirements file to the container
# This is done first to leverage Docker's layer caching
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
# The .dockerignore file will prevent config and logs from being copied
COPY . .

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define the command to run your app using gunicorn (a production-ready server)
# This will run the 'app' object from your 'app.py' file
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]

