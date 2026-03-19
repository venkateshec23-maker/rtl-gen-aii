"""
Backup Script for RTL-Gen AI

Backs up cache, outputs, and database.

Usage: python scripts/backup.py [--restore BACKUP_FILE]
"""

import argparse
import tarfile
import shutil
from pathlib import Path
from datetime import datetime
import json


class BackupManager:
    """Manage backups and restores."""
    
    def __init__(self, backup_dir: str = 'backups'):
        """Initialize backup manager."""
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(self) -> Path:
        """
        Create full backup.
        
        Returns:
            Path: Backup file path
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'rtl_gen_ai_backup_{timestamp}.tar.gz'
        backup_path = self.backup_dir / backup_name
        
        print(f"Creating backup: {backup_path}")
        
        # Items to backup
        items_to_backup = [
            'cache',
            'outputs',
            '.env',
            'logs',
        ]
        
        with tarfile.open(backup_path, 'w:gz') as tar:
            for item in items_to_backup:
                item_path = Path(item)
                if item_path.exists():
                    print(f"  Adding: {item}")
                    tar.add(item, arcname=item)
                else:
                    print(f"  Skipping (not found): {item}")
        
        # Create manifest
        manifest = {
            'timestamp': timestamp,
            'items': items_to_backup,
            'size_bytes': backup_path.stat().st_size,
        }
        
        manifest_path = backup_path.with_suffix('.json')
        manifest_path.write_text(json.dumps(manifest, indent=2))
        
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        print(f"\n✓ Backup created: {backup_path}")
        print(f"  Size: {size_mb:.2f} MB")
        
        return backup_path
    
    def restore_backup(self, backup_file: str):
        """
        Restore from backup.
        
        Args:
            backup_file: Path to backup file
        """
        backup_path = Path(backup_file)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        print(f"Restoring backup: {backup_path}")
        
        # Extract backup
        with tarfile.open(backup_path, 'r:gz') as tar:
            members = tar.getmembers()
            
            print(f"  Extracting {len(members)} items...")
            
            for member in members:
                print(f"    {member.name}")
                tar.extract(member, path='.')
        
        print("\n✓ Backup restored successfully")
    
    def list_backups(self):
        """List available backups."""
        backups = sorted(self.backup_dir.glob('*.tar.gz'), reverse=True)
        
        if not backups:
            print("No backups found")
            return
        
        print("Available backups:")
        print("-" * 70)
        
        for backup in backups:
            size_mb = backup.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            
            print(f"{backup.name}")
            print(f"  Size: {size_mb:.2f} MB")
            print(f"  Created: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
    
    def cleanup_old_backups(self, keep_count: int = 5):
        """
        Remove old backups, keeping only the most recent.
        
        Args:
            keep_count: Number of backups to keep
        """
        backups = sorted(self.backup_dir.glob('*.tar.gz'), reverse=True)
        
        if len(backups) <= keep_count:
            print(f"No cleanup needed ({len(backups)} backups)")
            return
        
        to_remove = backups[keep_count:]
        
        print(f"Removing {len(to_remove)} old backups:")
        for backup in to_remove:
            print(f"  {backup.name}")
            backup.unlink()
            
            # Remove manifest if exists
            manifest = backup.with_suffix('.json')
            if manifest.exists():
                manifest.unlink()
        
        print(f"\n✓ Kept {keep_count} most recent backups")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='RTL-Gen AI Backup Manager')
    parser.add_argument('--restore', metavar='FILE', help='Restore from backup file')
    parser.add_argument('--list', action='store_true', help='List available backups')
    parser.add_argument('--cleanup', type=int, metavar='N', help='Keep only N most recent backups')
    
    args = parser.parse_args()
    
    manager = BackupManager()
    
    if args.restore:
        manager.restore_backup(args.restore)
    elif args.list:
        manager.list_backups()
    elif args.cleanup:
        manager.cleanup_old_backups(args.cleanup)
    else:
        # Default: create backup
        manager.create_backup()


if __name__ == "__main__":
    main()
