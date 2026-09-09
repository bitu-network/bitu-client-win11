# file: src/cli/download/worldpop.py
import os
import time
import re
import logging
from pathlib import Path
import requests
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

WORLDPOP_API_BASE = "https://www.worldpop.org/rest/data/pop/wpgp"

def main():
    output_dir = Path("./worldpop_global_100m_unconstrained")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Querying WorldPop API root catalog...")
    response = requests.get(WORLDPOP_API_BASE, timeout=30)
    response.raise_for_status()
    catalog = response.json()
    
    entries = catalog.get('data', [])
    if not entries:
        logger.error("No entries found in WorldPop catalog response.")
        return
        
    logger.info(f"Retrieved {len(entries)} catalog records. Filtering for the latest year per country...")
    
    # Group by ISO3 to keep only the latest year per country
    country_latest = {}
    for entry in entries:
        iso3 = entry.get('iso3')
        if not iso3:
            continue
            
        year = entry.get('year')
        if not year:
            title = entry.get('title', '')
            match = re.search(r'\b(20\d{2}|19\d{2})\b', title)
            year = int(match.group(1)) if match else 0
        else:
            try:
                year = int(year)
            except ValueError:
                year = 0
                
        if iso3 not in country_latest or year > country_latest[iso3]['year_val']:
            country_latest[iso3] = {
                'entry': entry,
                'year_val': year
            }
            
    latest_entries = [val['entry'] for val in country_latest.values()]
    total_countries = len(latest_entries)
    logger.info(f"Identified latest year datasets for {total_countries} unique countries. Starting one-by-one sequential fetch & download...")
    
    success_count = 0
    fail_count = 0
    
    # One-by-one iterative loop: Fetch single metadata -> Download file immediately -> Next
    for idx, entry in enumerate(latest_entries, start=1):
        dataset_id = entry.get('id')
        iso3 = entry.get('iso3', 'GLOBAL')
        if not dataset_id:
            fail_count += 1
            continue
            
        detail_url = f"https://www.worldpop.org/rest/data/{dataset_id}"
        file_url = None
        
        # Step 1: Fetch metadata for this single country on-the-fly
        try:
            detail_resp = requests.get(detail_url, timeout=15)
            if detail_resp.status_code == 200:
                detail_json = detail_resp.json()
                detail_data = detail_json.get('data', {})
                
                # Extract files list or data_file
                files_list = detail_data.get('files', [])
                if isinstance(files_list, list) and files_list:
                    file_url = files_list[0]
                elif isinstance(files_list, str):
                    file_url = files_list
                
                if not file_url and detail_data.get('data_file'):
                    file_url = f"https://data.worldpop.org/{detail_data.get('data_file')}"
            
            # Small polite pause to avoid hammering the server
            time.sleep(0.05)
        except Exception as e:
            logger.warning(f"[{idx}/{total_countries}] [{iso3}] Metadata request failed: {e}")
            fail_count += 1
            continue
            
        if not file_url:
            logger.warning(f"[{idx}/{total_countries}] [{iso3}] No file URL found in detail response.")
            fail_count += 1
            continue
            
        if file_url.startswith('ftp://'):
            file_url = 'https://' + file_url[6:]
            
        file_name = os.path.basename(file_url)
        country_dir = output_dir / iso3
        output_path = country_dir / file_name
        
        # Skip if already downloaded
        if output_path.exists() and output_path.stat().st_size > 0:
            logger.info(f"[{idx}/{total_countries}] [{iso3}] Already exists, skipping: {file_name}")
            success_count += 1
            continue
            
        # Step 2: Download the file immediately right after getting its metadata
        logger.info(f"[{idx}/{total_countries}] [{iso3}] Downloading {file_name}...")
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            res = requests.get(file_url, stream=True, timeout=60)
            res.raise_for_status()
            
            total_size = int(res.headers.get('content-length', 0))
            
            with open(output_path, 'wb') as f, tqdm(
                total=total_size, unit='B', unit_scale=True, unit_divisor=1024, desc=file_name, leave=False
            ) as bar:
                for chunk in res.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))
                        
            success_count += 1
        except Exception as e:
            logger.error(f"[{idx}/{total_countries}] [{iso3}] Failed to download {file_name}: {e}")
            fail_count += 1
            
    logger.info(f"Pipeline finished! Successfully downloaded: {success_count} files (Failed: {fail_count})")

if __name__ == "__main__":
    main()