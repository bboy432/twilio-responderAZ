FROM nginx:alpine

# Copy dashboard files to nginx html directory
COPY index.html /usr/share/nginx/html/
COPY static/ /usr/share/nginx/html/static/

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
