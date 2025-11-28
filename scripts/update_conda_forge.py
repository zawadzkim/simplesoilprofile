#!/usr/bin/env python3
"""
Update conda-forge feedstock with new package version.

This script automatically creates a pull request to a conda-forge feedstock
repository with updated package version and source information from PyPI.
"""
import os
import sys
import argparse
import logging
from typing import Optional, Dict, Any
import requests
import yaml
import base64
from urllib.request import urlopen


class CondaForgeUpdater:
    """Handle conda-forge feedstock updates."""
    
    def __init__(self, github_token: str):
        """Initialize with GitHub token."""
        self.github_token = github_token
        self.headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
        self.logger = logging.getLogger(__name__)
    
    def get_pypi_info(self, package_name: str, version: str) -> tuple[str, str]:
        """Get PyPI source URL and SHA256 for a package version."""
        self.logger.info(f"Fetching PyPI info for {package_name} v{version}")
        
        pypi_url = f"https://pypi.org/pypi/{package_name}/json"
        response = requests.get(pypi_url)
        response.raise_for_status()
        pypi_data = response.json()
        
        # Find source distribution
        for file_info in pypi_data['urls']:
            if file_info['packagetype'] == 'sdist':
                source_url = file_info['url']
                source_sha256 = file_info['digests']['sha256']
                self.logger.info(f"Found source: {source_url}")
                self.logger.info(f"SHA256: {source_sha256}")
                return source_url, source_sha256
        
        raise ValueError(f"No source distribution found for {package_name} on PyPI")
    
    def get_feedstock_meta(self, feedstock_repo: str) -> tuple[str, str]:
        """Get current meta.yaml content and SHA from feedstock."""
        base_url = f"https://api.github.com/repos/conda-forge/{feedstock_repo}"
        
        try:
            meta_response = requests.get(f"{base_url}/contents/recipe/meta.yaml", 
                                       headers=self.headers)
            meta_response.raise_for_status()
            meta_content = base64.b64decode(meta_response.json()['content']).decode()
            meta_sha = meta_response.json()['sha']
            return meta_content, meta_sha
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(
                    f"Feedstock {feedstock_repo} not found. "
                    "Please create it first via conda-forge/staged-recipes"
                )
            raise
    
    def update_meta_yaml(self, meta_content: str, version: str, 
                        source_url: str, source_sha256: str) -> str:
        """Update meta.yaml with new version and source info."""
        meta_data = yaml.safe_load(meta_content)
        
        # Update version
        if 'package' in meta_data and 'version' in meta_data['package']:
            meta_data['package']['version'] = version
        
        # Update source
        if 'source' in meta_data:
            meta_data['source']['url'] = source_url
            meta_data['source']['sha256'] = source_sha256
        
        return yaml.dump(meta_data, default_flow_style=False, sort_keys=False)
    
    def create_branch(self, feedstock_repo: str, branch_name: str) -> bool:
        """Create a new branch in the feedstock repository."""
        base_url = f"https://api.github.com/repos/conda-forge/{feedstock_repo}"
        
        try:
            # Get main branch SHA
            main_ref = requests.get(f"{base_url}/git/refs/heads/main", 
                                  headers=self.headers)
            main_ref.raise_for_status()
            main_sha = main_ref.json()['object']['sha']
            
            # Create new branch
            branch_data = {
                'ref': f'refs/heads/{branch_name}',
                'sha': main_sha
            }
            response = requests.post(f"{base_url}/git/refs", 
                                   json=branch_data, headers=self.headers)
            
            if response.status_code == 201:
                self.logger.info(f"Created branch: {branch_name}")
                return True
            else:
                self.logger.warning(f"Branch {branch_name} may already exist")
                return False
        except Exception as e:
            self.logger.warning(f"Branch creation issue: {e}")
            return False
    
    def update_meta_file(self, feedstock_repo: str, branch_name: str,
                        updated_meta: str, meta_sha: str, version: str):
        """Update the meta.yaml file in the feedstock repository."""
        base_url = f"https://api.github.com/repos/conda-forge/{feedstock_repo}"
        
        update_data = {
            'message': f'Update to version {version}',
            'content': base64.b64encode(updated_meta.encode()).decode(),
            'sha': meta_sha,
            'branch': branch_name
        }
        
        response = requests.put(f"{base_url}/contents/recipe/meta.yaml", 
                              json=update_data, headers=self.headers)
        response.raise_for_status()
        self.logger.info("Updated meta.yaml")
    
    def create_pull_request(self, feedstock_repo: str, branch_name: str,
                           package_name: str, version: str) -> str:
        """Create a pull request for the update."""
        base_url = f"https://api.github.com/repos/conda-forge/{feedstock_repo}"
        
        pr_data = {
            'title': f'Update to version {version}',
            'head': branch_name,
            'base': 'main',
            'body': f'''Update {package_name} to version {version}

- Updated version to {version}
- Updated source URL and SHA256

Auto-generated by release workflow.
'''
        }
        
        response = requests.post(f"{base_url}/pulls", json=pr_data, 
                               headers=self.headers)
        
        if response.status_code == 201:
            pr_url = response.json()['html_url']
            self.logger.info(f"✅ Created conda-forge PR: {pr_url}")
            return pr_url
        else:
            error_msg = f"Failed to create PR: {response.status_code}\n{response.text}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def update_feedstock(self, package_name: str, version: str,
                        feedstock_repo: str, branch_name: str) -> str:
        """Complete feedstock update process."""
        if not feedstock_repo:
            self.logger.info("No conda-forge feedstock specified, skipping update")
            return ""
        
        self.logger.info(f"Creating conda-forge update for {package_name} v{version}")
        
        # Get PyPI package info
        source_url, source_sha256 = self.get_pypi_info(package_name, version)
        
        # Get current meta.yaml
        meta_content, meta_sha = self.get_feedstock_meta(feedstock_repo)
        
        # Update meta.yaml content
        updated_meta = self.update_meta_yaml(meta_content, version, 
                                           source_url, source_sha256)
        
        # Create branch
        self.create_branch(feedstock_repo, branch_name)
        
        # Update file
        self.update_meta_file(feedstock_repo, branch_name, updated_meta, 
                             meta_sha, version)
        
        # Create PR
        pr_url = self.create_pull_request(feedstock_repo, branch_name, 
                                        package_name, version)
        
        return pr_url


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Update conda-forge feedstock")
    parser.add_argument("--package-name", required=True,
                       help="Name of the package to update")
    parser.add_argument("--version", required=True,
                       help="New version to update to")
    parser.add_argument("--feedstock-repo", required=True,
                       help="conda-forge feedstock repository name")
    parser.add_argument("--branch-name", required=True,
                       help="Branch name for the update")
    parser.add_argument("--github-token", 
                       default=os.environ.get('GITHUB_TOKEN'),
                       help="GitHub token (or use GITHUB_TOKEN env var)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    if not args.github_token:
        logging.error("GitHub token required (--github-token or GITHUB_TOKEN env var)")
        sys.exit(1)
    
    try:
        updater = CondaForgeUpdater(args.github_token)
        pr_url = updater.update_feedstock(
            package_name=args.package_name,
            version=args.version,
            feedstock_repo=args.feedstock_repo,
            branch_name=args.branch_name
        )
        
        if pr_url:
            print(f"SUCCESS: Created PR at {pr_url}")
        else:
            print("SKIPPED: No feedstock specified")
            
    except Exception as e:
        logging.error(f"Failed to update conda-forge: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
