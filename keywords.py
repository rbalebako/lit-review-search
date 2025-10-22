"""
Extract keywords from publication abstracts using RAKE (Rapid Automatic Keyword Extraction).

This script:
1. Processes publications from a source folder
2. Extracts keywords from their abstracts using RAKE algorithm
3. Saves keywords to individual files for each publication
"""

from scopus_publication import ScopusPublication
from rake_nltk import Rake
from shutil import copyfile
import os

def extract_keywords(abstract: str) -> list:
    """Extract keywords from text using RAKE algorithm.
    
    Args:
        abstract: Publication abstract text
        
    Returns:
        List of extracted keyword phrases
    """
    r = Rake()
    r.extract_keywords_from_text(abstract)
    return r.get_ranked_phrases()

def process_publication(pub: ScopusPublication, output_folder: str) -> None:
    """Process a single publication to extract and save keywords.
    
    Args:
        pub: ScopusPublication object to process
        output_folder: Folder to save keyword files
    """
    keywords_file = os.path.join(output_folder, pub.eid, 'rake_keywords.txt')
    
    # Skip if keywords already extracted
    if os.path.exists(keywords_file):
        return
        
    # Clean and encode abstract text
    pub.abstract = pub.abstract.encode('ascii', 'ignore').decode('ascii')
    if not pub.abstract:
        return
        
    try:
        keywords = extract_keywords(pub.abstract)
        if keywords:
            with open(keywords_file, 'w') as o:
                for keyword in keywords:
                    o.write(keyword)
                    o.write('\n')
    except Exception as e:
        print(f"Error processing publication {pub.eid}: {e}")

# Configuration paths
source_folder = ''  # Source folder containing publications
output_folder = ''  # Output folder for keyword files
studies_folder = '' # Studies metadata folder

# Process each publication in the output folder
for file in os.listdir(output_folder):
    if file == '.DS_Store':  # Skip macOS system files
        continue
        
    pub = ScopusPublication(output_folder, file)
    process_publication(pub, output_folder)