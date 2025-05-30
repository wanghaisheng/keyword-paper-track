# scholar_scraper.py (or your existing Python file)

from scholarly import scholarly
from scholarly import ProxyGenerator
from scholarly.lib.exceptions import MaxTriesExceededException # Import the specific exception

import pandas as pd
import time
import random
import os # Import os to read environment variables
import sys # Import sys to exit with an error code if needed

# --- (Keep your setup_proxy, search_scholar, and save_to_csv functions as they are,
#      or use the improved versions from the previous response for better stability) ---

# Improved setup_proxy function (from previous response)
def setup_proxy():
    pg = ProxyGenerator()
    print("Attempting to set up free proxies...")
    if pg.FreeProxies():
        scholarly.use_proxy(pg)
        print("Proxy setup successful using FreeProxies.")
        return True
    else:
        print("Failed to set up free proxies. Trying Tor (if installed and running locally)...")
        try:
            # Note: Tor might not be available in a standard GitHub Actions runner
            # without additional setup. FreeProxies is usually the first attempt.
            scholarly.use_tor(tor_proxy="socks5://127.0.0.1:9050", tor_data_dir=None)
            print("Proxy setup successful using Tor.")
            return True
        except Exception as e:
            print(f"Failed to set up Tor proxy: {e}. No working proxy could be set up.")
            return False

# Improved search_scholar function (from previous response)
def search_scholar(keywords, start_year, end_year, max_retries=5, max_results=None):
    results = []
    current_scholarly_index = 0
    current_collected_count = 0
    
    attempts = 0
    while attempts <= max_retries:
        try:
            print(f"\n--- Attempt {attempts + 1}/{max_retries + 1}: Searching for '{keywords}' (year {start_year}-{end_year}) from scholarly index {current_scholarly_index} ---")
            
            search_query_generator = scholarly.search_pubs(
                keywords,
                year_low=start_year,
                year_high=end_year,
                start_index=current_scholarly_index
            )

            while True:
                try:
                    result = next(search_query_generator)
                    time.sleep(random.uniform(2, 5))

                    pub_year = result.get('bib', {}).get('pub_year', 0)
                    try:
                        pub_year = int(pub_year)
                        if start_year <= pub_year <= end_year:
                            data = {
                                'title': result.get('bib', {}).get('title', ''),
                                'doi': result.get('bib', {}).get('doi', ''),
                                'authors': ', '.join(result.get('bib', {}).get('author', [])),
                                'year': pub_year,
                                'month': result.get('bib', {}).get('pub_month', ''),
                                'abstract': result.get('bib', {}).get('abstract', ''),
                                'citation': result.get('num_citations', 0),
                                'publication': result.get('bib', {}).get('journal', '')
                            }
                            results.append(data)
                            current_collected_count += 1
                            if current_collected_count % 10 == 0:
                                print(f"Fetched {current_collected_count} results so far...")
                            
                            if max_results and current_collected_count >= max_results:
                                print(f"Reached maximum requested results ({max_results}). Stopping search.")
                                return results

                        current_scholarly_index += 1

                    except ValueError:
                        print(f"Skipping entry due to invalid publication year format: {result.get('bib',{}).get('pub_year')}")
                        current_scholarly_index += 1
                        continue

                except StopIteration:
                    print("No more results from Google Scholar for this query.")
                    return results
                
        except MaxTriesExceededException as e:
            print(f"Caught MaxTriesExceededException on attempt {attempts + 1}: {e}")
            print(f"Proxy failed at scholarly index {current_scholarly_index}. Retrying with new proxy setup.")
            attempts += 1
            if attempts > max_retries:
                print("Max retries exceeded. Could not complete search.")
                break
            
            if not setup_proxy():
                print("Failed to set up new proxy after an error. Cannot continue with further attempts.")
                break
            time.sleep(random.uniform(5, 15))

        except Exception as e:
            print(f"An unexpected error occurred on attempt {attempts + 1}: {e}")
            print("Stopping search due to unhandled error.")
            break

    return results

def save_to_csv(data, filename):
    if not data:
        print("No data to save or data collection failed.")
        return
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"Data saved to {filename}")

if __name__ == "__main__":
    # Read parameters from environment variables (set by GitHub Actions)
    # Provide default values for local testing or if not set by GA
    
    # Environment variables are typically prefixed with 'INPUT_' for workflow_dispatch
    # and are strings. Convert to int where necessary.
    keywords = os.getenv('INPUT_KEYWORDS', 'triatomine United States')
    
    try:
        start_year = int(os.getenv('INPUT_START_YEAR', '2022'))
    except ValueError:
        print("Warning: INPUT_START_YEAR is not a valid integer. Using default 2022.")
        start_year = 2022
    
    try:
        end_year = int(os.getenv('INPUT_END_YEAR', '2024'))
    except ValueError:
        print("Warning: INPUT_END_YEAR is not a valid integer. Using default 2024.")
        end_year = 2024
        
    # The output filename path should be relative to the GitHub Actions workspace
    # or a generic path that works in the runner.
    # The original path '/Users/liting/...' will not exist in the GitHub Actions runner.
    # Assuming your Python script is in the same directory as 'north_america_triatomine',
    # or that 'north_america_triatomine' is a subdirectory of your repo root.
    filename = os.getenv('INPUT_OUTPUT_FILENAME', 'north_america_triatomine/google_scholar_raw_US.csv')

    print(f"Starting Google Scholar search with parameters:")
    print(f"  Keywords: '{keywords}'")
    print(f"  Years: {start_year}-{end_year}")
    print(f"  Output File: '{filename}'")

    if setup_proxy():
        results = search_scholar(keywords, start_year, end_year, max_retries=5, max_results=None)
        save_to_csv(results, filename)
    else:
        print("Initial proxy setup failed. Aborting search.")
        sys.exit(1) # Exit with a non-zero code to indicate failure in GitHub Actions
