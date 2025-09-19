# Multi-stage build to reduce context
FROM alpine:latest AS file-copier

# Create directory structure
RUN mkdir -p /app/public

# Copy HTML and assets (include background images)
COPY public/*.html /app/public/
COPY public/*Background.jpg /app/public/
COPY public/scripts/ /app/public/scripts/
COPY public/styles/ /app/public/styles/
COPY public/favicon.ico /app/public/
COPY public/fonts/ /app/public/fonts/
COPY public/icons/ /app/public/icons/

# Final stage with nginx
FROM nginx:alpine

# Remove default nginx files
RUN rm -rf /usr/share/nginx/html/*

# Copy files from previous stage
COPY --from=file-copier /app/public/ /usr/share/nginx/html/

# Fix permissions for all files
RUN chmod -R 644 /usr/share/nginx/html/
RUN find /usr/share/nginx/html/ -type d -exec chmod 755 {} \;

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 3000

# Start nginx
CMD ["nginx", "-g", "daemon off;"]


