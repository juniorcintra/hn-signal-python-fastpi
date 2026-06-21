"""
Example client for the improved pipeline API.

This script demonstrates how to:
1. Start a pipeline job
2. Poll for completion
3. Retrieve results
"""

import os
import sys
import time
from typing import Optional

import httpx


class PipelineClient:
    """Client for interacting with the HN Article Enricher API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("API_KEY", "")
        self.headers = {"X-API-Key": self.api_key} if self.api_key else {}
    
    def start_pipeline(self) -> dict:
        """Start a new pipeline job."""
        url = f"{self.base_url}/api/v1/pipeline/run"
        
        with httpx.Client() as client:
            response = client.post(url, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
    
    def get_job_status(self, job_id: int) -> dict:
        """Get the status of a pipeline job."""
        url = f"{self.base_url}/api/v1/pipeline/jobs/{job_id}"
        
        with httpx.Client() as client:
            response = client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
    
    def wait_for_completion(self, job_id: int, poll_interval: int = 2, timeout: int = 300) -> dict:
        """
        Wait for a job to complete, polling at regular intervals.
        
        Args:
            job_id: The job ID to wait for
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait
        
        Returns:
            Final job status
        
        Raises:
            TimeoutError: If job doesn't complete within timeout
        """
        start_time = time.time()
        
        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")
            
            job = self.get_job_status(job_id)
            status = job["status"]
            
            if status in ["completed", "failed"]:
                return job
            
            print(f"Job {job_id} status: {status}, waiting {poll_interval}s...")
            time.sleep(poll_interval)
    
    def get_articles(self, page: int = 1, page_size: int = 10, **filters) -> dict:
        """Get articles with optional filters."""
        url = f"{self.base_url}/api/v1/articles"
        params = {"page": page, "page_size": page_size, **filters}
        
        with httpx.Client() as client:
            response = client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
    
    def test_llm_connection(self) -> dict:
        """Test the LLM connection."""
        url = f"{self.base_url}/api/v1/pipeline/test-llm"
        
        with httpx.Client() as client:
            response = client.get(url, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            return response.json()


def main():
    """Example usage of the pipeline client."""
    
    # Initialize client
    client = PipelineClient()
    
    print("=" * 60)
    print("HN Article Enricher - Pipeline Client Example")
    print("=" * 60)
    
    # Test LLM connection
    print("\n1. Testing LLM connection...")
    try:
        llm_test = client.test_llm_connection()
        print(f"   ✓ LLM Status: {llm_test['status']}")
        print(f"   Model: {llm_test['model']}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print("   ⚠ API key required. Set API_KEY environment variable.")
        else:
            print(f"   ✗ Error: {e}")
        sys.exit(1)
    
    # Start pipeline
    print("\n2. Starting pipeline job...")
    try:
        job_response = client.start_pipeline()
        job_id = job_response["job_id"]
        print(f"   ✓ Job started: ID={job_id}")
        print(f"   Status: {job_response['status']}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            print("   ⚠ Another pipeline job is already running")
            sys.exit(0)
        else:
            print(f"   ✗ Error: {e}")
            sys.exit(1)
    
    # Wait for completion
    print(f"\n3. Waiting for job {job_id} to complete...")
    try:
        final_job = client.wait_for_completion(job_id, poll_interval=3)
        
        print(f"\n   ✓ Job completed!")
        print(f"   Status: {final_job['status']}")
        print(f"   Scraped: {final_job['scraped']} articles")
        print(f"   New items: {final_job['new_items']}")
        print(f"   Enriched: {final_job['enriched']}")
        print(f"   Failed: {final_job['failed']}")
        
        if final_job.get('error_message'):
            print(f"   Error: {final_job['error_message']}")
        
        duration = None
        if final_job.get('started_at') and final_job.get('completed_at'):
            from datetime import datetime
            start = datetime.fromisoformat(final_job['started_at'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(final_job['completed_at'].replace('Z', '+00:00'))
            duration = (end - start).total_seconds()
            print(f"   Duration: {duration:.1f}s")
        
    except TimeoutError as e:
        print(f"   ✗ {e}")
        sys.exit(1)
    
    # Get enriched articles
    print("\n4. Fetching enriched articles...")
    articles_response = client.get_articles(
        page=1,
        page_size=5,
        enrichment_status="completed"
    )
    
    print(f"   Total enriched: {articles_response['total']}")
    print(f"\n   Recent articles:")
    
    for article in articles_response['items'][:3]:
        print(f"\n   • {article['title']}")
        print(f"     Category: {article['category']}")
        print(f"     Tags: {', '.join(article['tags'] or [])}")
        print(f"     Summary: {article['summary'][:100]}...")
    
    print("\n" + "=" * 60)
    print("✓ Pipeline execution completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
