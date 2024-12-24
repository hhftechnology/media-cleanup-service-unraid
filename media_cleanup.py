#!/usr/bin/env python3

import os
import sys
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

# Only import PlexAPI if Plex functionality is enabled
try:
    from plexapi.server import PlexServer
    PLEX_AVAILABLE = True
except ImportError:
    PLEX_AVAILABLE = False

@dataclass
class Config:
    """Configuration class that supports optional Plex or Sonarr settings."""
    days_threshold: int
    media_root: str
    delete_empty_dirs: bool
    parallel_processing: bool
    max_workers: int
    dry_run: bool
    # Optional Sonarr configuration
    sonarr_enabled: bool = False
    sonarr_api_key: Optional[str] = None
    sonarr_host: Optional[str] = None
    # Optional Plex configuration
    plex_enabled: bool = False
    plex_url: Optional[str] = None
    plex_token: Optional[str] = None

class SonarrManager:
    """Handles all Sonarr-related operations."""
    
    def __init__(self, api_key: str, host: str, logger: logging.Logger):
        self.api_key = api_key
        self.host = host
        self.logger = logger

    def _get_headers(self) -> Dict[str, str]:
        return {
            'X-Api-Key': self.api_key,
            'Accept': 'application/json'
        }

    def get_daily_series(self) -> List[Dict]:
        """Fetch daily series from Sonarr."""
        try:
            response = requests.get(
                f"{self.host}/api/v3/series",
                headers=self._get_headers()
            )
            response.raise_for_status()
            series = response.json()
            return [s for s in series if s['seriesType'] == 'daily']
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch series from Sonarr: {str(e)}")
            return []

    def get_episodes_to_delete(self, series_id: int, threshold_date: datetime) -> List[Dict]:
        """Get episodes older than the threshold date."""
        try:
            response = requests.get(
                f"{self.host}/api/v3/episode",
                params={'seriesId': series_id},
                headers=self._get_headers()
            )
            response.raise_for_status()
            episodes = response.json()
            
            return [
                episode for episode in episodes
                if datetime.strptime(episode['airDateUtc'], '%Y-%m-%dT%H:%M:%SZ') < threshold_date
                and episode.get('hasFile', False)
            ]
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch episodes for series {series_id}: {str(e)}")
            return []

    def process_episode(self, episode: Dict, dry_run: bool) -> bool:
        """Process a single episode in Sonarr."""
        try:
            if not dry_run:
                # Unmonitor episode
                episode['monitored'] = False
                requests.put(
                    f"{self.host}/api/v3/episode/{episode['id']}",
                    headers=self._get_headers(),
                    json=episode
                )

                # Delete episode file
                requests.delete(
                    f"{self.host}/api/v3/episodefile/{episode['episodeFileId']}",
                    headers=self._get_headers()
                )

            self.logger.info(f"Processed Sonarr episode: {episode.get('title', 'Unknown')} " +
                           f"({'Dry run' if dry_run else 'Deleted'})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to process Sonarr episode {episode.get('id')}: {str(e)}")
            return False

class PlexManager:
    """Handles all Plex-related operations."""
    
    def __init__(self, url: str, token: str, logger: logging.Logger):
        if not PLEX_AVAILABLE:
            raise ImportError("PlexAPI is not installed. Install it with: pip install plexapi")
        self.server = PlexServer(url, token)
        self.logger = logger

    def refresh_libraries(self, dry_run: bool):
        """Refresh all TV show libraries in Plex."""
        try:
            if not dry_run:
                for section in self.server.library.sections():
                    if section.type == 'show':
                        section.update()
                        self.logger.info(f"Refreshed Plex library: {section.title}")
        except Exception as e:
            self.logger.error(f"Failed to refresh Plex libraries: {str(e)}")

class MediaCleaner:
    """Main class that orchestrates the cleanup process."""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize managers based on configuration
        self.sonarr = (SonarrManager(self.config.sonarr_api_key, 
                                    self.config.sonarr_host, 
                                    self.logger) 
                      if self.config.sonarr_enabled else None)
        
        self.plex = (PlexManager(self.config.plex_url, 
                                self.config.plex_token, 
                                self.logger) 
                    if self.config.plex_enabled and PLEX_AVAILABLE else None)

    def _load_config(self, config_path: str) -> Config:
        """Load and validate configuration from YAML file."""
        import yaml
        
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
            
            # Create base config
            config = Config(
                days_threshold=data['cleanup']['days_threshold'],
                media_root=data['cleanup']['media_root'],
                delete_empty_dirs=data['cleanup'].get('delete_empty_dirs', True),
                parallel_processing=data['performance'].get('parallel_processing', True),
                max_workers=data['performance'].get('max_workers', 4),
                dry_run=data['cleanup'].get('dry_run', False)
            )
            
            # Add Sonarr config if present
            if 'sonarr' in data:
                config.sonarr_enabled = True
                config.sonarr_api_key = data['sonarr']['api_key']
                config.sonarr_host = data['sonarr']['host']
            
            # Add Plex config if present
            if 'plex' in data:
                config.plex_enabled = True
                config.plex_url = data['plex']['url']
                config.plex_token = data['plex']['token']
            
            if not (config.sonarr_enabled or config.plex_enabled):
                raise ValueError("Neither Sonarr nor Plex is configured")
            
            return config
            
        except Exception as e:
            sys.exit(f"Failed to load configuration: {str(e)}")

    def _setup_logging(self):
        """Configure logging system."""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'media_cleanup.log'),
                logging.StreamHandler()
            ]
        )

    def cleanup_empty_directories(self):
        """Remove empty directories if configured to do so."""
        if not self.config.delete_empty_dirs or self.config.dry_run:
            return

        try:
            for root, dirs, files in os.walk(self.config.media_root, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        self.logger.info(f"Removed empty directory: {dir_path}")
        except Exception as e:
            self.logger.error(f"Failed to cleanup empty directories: {str(e)}")

    def run(self):
        """Main execution method that coordinates the cleanup process."""
        self.logger.info("Starting media cleanup process...")
        threshold_date = datetime.now() - timedelta(days=self.config.days_threshold)
        total_processed = 0

        # Process Sonarr content if enabled
        if self.config.sonarr_enabled:
            self.logger.info("Processing Sonarr content...")
            series = self.sonarr.get_daily_series()
            
            for serie in series:
                episodes = self.sonarr.get_episodes_to_delete(serie['id'], threshold_date)
                if not episodes:
                    continue

                self.logger.info(f"Processing {len(episodes)} episodes for '{serie['title']}'")
                
                if self.config.parallel_processing:
                    with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                        results = list(executor.map(
                            lambda ep: self.sonarr.process_episode(ep, self.config.dry_run), 
                            episodes
                        ))
                    total_processed += sum(1 for r in results if r)
                else:
                    for episode in episodes:
                        if self.sonarr.process_episode(episode, self.config.dry_run):
                            total_processed += 1

        # Refresh Plex libraries if enabled
        if self.config.plex_enabled:
            self.logger.info("Refreshing Plex libraries...")
            self.plex.refresh_libraries(self.config.dry_run)

        # Clean up empty directories if configured
        if self.config.delete_empty_dirs:
            self.cleanup_empty_directories()

        self.logger.info(f"Cleanup complete. Processed {total_processed} episodes " +
                        f"({'Dry run' if self.config.dry_run else 'Actual run'})")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python media_cleanup.py config.yaml")
        sys.exit(1)

    cleaner = MediaCleaner(sys.argv[1])
    cleaner.run()