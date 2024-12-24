Let's create a docker-compose file to make it easier to run the container:

# Media Cleanup Service

An automated service for managing media libraries in Plex and Sonarr, particularly focused on cleaning up older episodes from daily shows.

## Features

- Flexible configuration for Plex and/or Sonarr usage
- Automated cleanup of old media files based on configurable thresholds
- Support for parallel processing to handle large libraries efficiently
- Comprehensive logging and monitoring
- Docker support for easy deployment
- Automated testing and CI/CD pipeline

1. **Container Structure**: The container is built with security and best practices in mind:
   - Uses a slim Python base image to minimize size
   - Creates a non-root user for security
   - Includes proper healthchecks
   - Separates configuration, logs, and application code

2. **Configuration Management**: The setup provides flexible configuration handling:
   - Configuration files are mounted from the host system
   - Environment variables can override default settings
   - The entrypoint script validates configuration before starting

3. **Volume Management**: The docker-compose file sets up three main volumes:
   - `/config`: For configuration files (read-only)
   - `/logs`: For application logs
   - `/data`: For media files (read-only)

To use this containerized version:

1. First, create your directory structure:
```bash
mkdir -p media-cleanup/{config,logs}
```

2. Copy all the files into your directory:
```bash
# Copy your configuration
cp config.yaml media-cleanup/config/

# Copy application files
cp media_cleanup.py Dockerfile docker-compose.yml requirements.txt entrypoint.sh media-cleanup/
```

3. Build and run the container:
```bash
cd media-cleanup
docker-compose up -d
```

To run the cleanup on a schedule, you have several options:

1. Using host system's cron with docker command:
```bash
# Add to crontab
0 0 * * * docker-compose -f /path/to/docker-compose.yml up
```

2. Using a separate container scheduler like Ofelia:
```yaml
# Add to docker-compose.yml
  ofelia:
    image: mcuadros/ofelia:latest
    depends_on:
      - media-cleanup
    command: daemon --docker
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    labels:
      ofelia.job-run.cleanup.schedule: "0 0 * * *"
      ofelia.job-run.cleanup.container: media-cleanup
```

Some additional tips for using the containerized version:

1. Logging is handled through Docker's logging system, but also writes to the mounted logs directory:
```bash
# View logs
docker logs media-cleanup

# or from host
tail -f logs/media_cleanup.log
```

2. To update the configuration:
```bash
# Edit the config file
nano config/config.yaml

# Restart the container to apply changes
docker-compose restart media-cleanup
```

3. To update the container:
```bash
# Pull latest version and rebuild
docker-compose pull
docker-compose up -d --build
```

The containerized version provides several advantages:
- Isolated environment
- Easy deployment and updates
- Consistent behavior across systems
- Built-in logging and monitoring
- Security through isolation and least privilege
