# Media Cleanup Service for Unraid: A Complete Guide

Are you tired of managing storage space for your daily TV shows? Do you find yourself regularly having to clean up old episodes manually? The Media Cleanup Service container is here to help! This guide will walk you through setting up and using the service on your Unraid server, with various configuration scenarios to match your needs.

## ⚠️ IMPORTANT SAFETY WARNINGS

Before proceeding with the installation and use of this service, please read and understand these critical warnings:

1. **Data Loss Risk**: This service is designed to permanently delete media files. Once files are deleted, they CANNOT be recovered unless you have backups. The deletion is immediate and bypasses the recycle bin.

2. **No Built-in Recovery**: The service does not include any file recovery capabilities. Deleted files are permanently removed from your system.

3. **Verification Required**: Always run the service in dry-run mode first (`dry_run: true` in config) to verify what would be deleted before enabling actual deletions.

4. **Backup Critical**: Maintain regular backups of your important media files. This service should not be your only method of media management.

5. **Permission Issues**: Incorrect permissions can lead to unintended file access or failed deletions. Always verify PUID/PGID settings.

6. **Network Dependencies**: Service relies on network access to Plex/Sonarr. Network issues could cause synchronization problems.

7. **API Token Security**: Your Plex and Sonarr API tokens provide full access to these services. Keep them secure and never share configurations containing these tokens.

### Required Safety Precautions

Before running this service:

1. **Create Backups**: Set up a backup system for critical media files.
2. **Test in Isolation**: First test the service with a small, non-critical media collection.
3. **Verify Settings**: Double-check all paths and configuration settings.
4. **Monitor Logs**: Regularly check logs for unexpected behavior.
5. **Set Notifications**: Configure Unraid notifications to alert you of any issues.

### Recommended Safety Settings

```yaml
cleanup:
  dry_run: true  # Start with dry run enabled
  safety_threshold: 1000  # Maximum files to process in one run
  backup_enabled: true   # Enable backup checks
  notification_enabled: true  # Enable notifications
```

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
