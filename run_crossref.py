import sys, os, math, time
import crossref_commons.retrieval
from dotenv import load_dotenv
from requests import get
import requests.exceptions
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import re

from dotenv import load_dotenv
from scopus_publication import ScopusPublication


# Load environment variables from .env file
load_dotenv()

# Get OpenCitations API key from environment variable
OPENCITATIONS_API_KEY = os.getenv('OPENCITATIONS_API_KEY', '')
if not OPENCITATIONS_API_KEY:
    raise ValueError(
        "OPENCITATIONS_API_KEY not found in environment variables. "
        "Please create a .env file with your API key. "
        "See .env.example for template."
    )

# CrossRef API configuration
CROSSREF_BASE_URL = 'https://api.crossref.org'
MAILTO = os.getenv('CROSSREF_MAILTO', '')  # Email for polite pool access
if MAILTO:
    print(f"Using CrossRef polite pool with email: {MAILTO}")



# Rate limiting: CrossRef allows 50 req/sec for polite pool, 5 req/sec otherwise
RATE_LIMIT_DELAY = 1.0  # Conservative 1 second between requests

# for opencitation
HTTP_HEADERS = {"authorization": OPENCITATIONS_API_KEY}

@dataclass
class Citation:
    doi: str
    year: Optional[int] = None
    
    @classmethod
    def extract_doi(cls, id_string: str) -> Optional[str]:
        """Extract DOI from a given identifier string."""
        doi_pattern = re.compile(r'10.\d{4,9}/[-._;()/:A-Z0-9]+', re.IGNORECASE)
        match = doi_pattern.search(id_string)
        return match.group(0) if match else None
    
    @classmethod
    def from_opencitations_json(cls, field: str, data: dict):
        """Create Citation from OpenCitations API response"""
        id_string = data.get(field, '')
        doi = cls.extract_doi(id_string= id_string)
        if not doi:
            return None
            
        date_parts = data.get('creation', {}).split('-')
        year = int(date_parts[0]) if date_parts else None
        return cls(doi=doi, year=year)



def get_references(doi) -> List[Citation]:
    """
    CrossrefCommons does bnot have a get reference function, so we use OpenCitations API here.
    https://api.opencitations.net/index/v2

    all the outgoing references to other cited works appearing in the reference list of the bibliographic entity identified 

    """
    api_call = f"https://api.opencitations.net/index/v2/references/doi:{doi}?format=json"
    #print("calling references with " + api_call)
    response = get(api_call, headers=HTTP_HEADERS)
    return [Citation.from_opencitations_json(field="cited", data=item) for item in response.json()]

def get_citations(doi) -> List[Citation]:
    """
    constitute the incoming citations of that identified bibliographic entity
    Example: /citations/doi:10.1108/jd-12-2013-0166 
    """
    api_call = f"https://api.opencitations.net/index/v2/citations/doi:{doi}?format=json"
   # print("calling citations with " + api_call)
    response = get(api_call, headers=HTTP_HEADERS)
    # TODO time is all the same ignore this for citations
    return [Citation.from_opencitations_json(field="citing", data=item) for item in response.json()]


def get_strong_co_citing(crossref_pub, shared):
    """
    Return DOIs of publications that are strongly co-citing with the given publication.

    Args:
        crossref_pub: CrossRefPublication object whose co-citing counts are examined.
        shared: float fraction used to compute the minimum shared reference threshold.

    Returns:
        List of DOI strings for publications with co-citing counts >= threshold.
    """
    min_count = math.ceil(crossref_pub.reference_count * shared)

    dois = []
    for doi, count in list(crossref_pub.co_citing_counts.items()):
        if count >= min_count:
            dois.append(doi)

    return dois

def get_strong_co_cited(crossref_pub, shared):
    """
    Return DOIs of publications that are strongly co-cited with the given publication.

    Args:
        crossref_pub: CrossRefPublication object whose co-cited counts are examined.
        shared: float fraction used to compute the minimum shared citation threshold.

    Returns:
        List of DOI strings for publications with co-cited counts >= threshold.
    """
    min_count = math.ceil(crossref_pub.citation_count * shared)

    dois = []
    for doi, count in list(crossref_pub.co_cited_counts.items()):
        if count >= min_count:
            dois.append(doi)

    return dois

def get_strong_citation_relationship(crossref_pub, shared):
    """
    Populate crossref_pub.strong_cit_pubs with DOIs representing strong citation relationships.

    This function:
      - Initializes crossref_pub.strong_cit_pubs as a set.
      - Adds direct references' and citations' DOIs.
      - Unions in DOIs from strongly co-citing and strongly co-cited publications.

    Args:
        crossref_pub: CrossRefPublication object to update.
        shared: float fraction used by co-citing/co-cited threshold calculations.

    Returns:
        set: Set of DOIs representing strong related publications.
    """
    strong_related_pub_dois = set()

    # Add direct references
    for reference in crossref_pub.references:
        strong_related_pub_dois.add(reference['doi'])

    # Add direct citations
    for citation in crossref_pub.citations:
        strong_related_pub_dois.add(citation.get('doi', citation.get('DOI')))

    # Add strongly co-citing publications
    strong_related_pub_dois = strong_related_pub_dois.union(get_strong_co_citing(crossref_pub, shared))

    # Add strongly co-cited publications
    strong_related_pub_dois = strong_related_pub_dois.union(get_strong_co_cited(crossref_pub, shared))

    return strong_related_pub_dois

class CrossRefCommonsPublication:
    """Wrapper for Crossref Commons API access with caching."""
    
    def __init__(self, data_folder, doi):
        self.doi = doi
        self.data_folder = data_folder
        self._metadata = None
        self._references = None
        self._citations = None
        
        # Create cache directory
        os.makedirs(data_folder, exist_ok=True)
        
    @property
    def metadata(self):
        if self._metadata is None:
            try:
                self._metadata = crossref_commons.retrieval.get_publication_as_json(self.doi)
            except requests.exceptions.RequestException as e:
                print(f"Error fetching metadata for {self.doi}: {e}")
                self._metadata = {}
        return self._metadata
    
    @property
    def references(self) -> List[Citation]:
        if self._references is None:
            try:
                self._references = get_references(self.doi)
            except requests.exceptions.RequestException as e:
                print(f"Error fetching references for {self.doi}: {e}")
                self._references = []
        return self._references
    
    @property
    def citations(self) -> List[Citation]:
        if self._citations is None:
            try:
                self._citations = get_citations(self.doi)
            except requests.exceptions.RequestException as e:
                print(f"Error fetching citations for {self.doi}: {e}")
                self._citations = []
        return self._citations
    
    @property
    def title(self):
        return self.metadata.get('title', [None])[0]
    
    @property
    def pub_year(self):
        date_parts = self.metadata.get('published-print', {}).get('date-parts', [[None]])[0]
        return date_parts[0] if date_parts else None
    
    @property
    def reference_count(self):
        return len(self.references)
    
    def get_citation_count(self):
        return self.metadata.get('is-referenced-by-count', 0)

def check_publication_data(pub, identifier: str, service_name: str):
    """Helper to check if a publication has valid citation data"""
    try:
        if hasattr(pub, 'metadata') and pub.metadata:  # Check metadata if exists
            ref_count = len(pub.references)
            cite_count = len(pub.citations)
            if ref_count > 0 and cite_count > 0:
                print(f"Using {service_name} for {identifier} (refs: {ref_count}, cites: {cite_count})")
                return pub
            print(f"{service_name} missing citations/references for {identifier}")
    except Exception as e:
        print(f"Error accessing {service_name} data for {identifier}: {e}")
    return None

def create_publication(data_folder, identifier):
    """Factory function that tries to create a CrossRef publication first,
    falls back to Scopus if that fails or if CrossRef has no references/citations."""
    
    # Try CrossRef first
    try:
        pub = CrossRefCommonsPublication(data_folder, identifier)
        if result := check_publication_data(pub, identifier, "CrossRef"):
            return result
    except Exception as e:
        print(f"Failed to create CrossRef publication for {identifier}: {e}")
    
    # Try Scopus as fallback
    try:
        pub = ScopusPublication(data_folder, identifier)
        if result := check_publication_data(pub, identifier, "Scopus"):
            return result
    except Exception as e:
        print(f"Failed to create Scopus publication for {identifier}: {e}")
    
    print(f"No valid publication data found for {identifier}")
    return None

def main():
    """
    Main entry point using Crossref Commons library.
    """
    shared = 0.10
    # TODO either get these values from .env or here, but don't have them in bothe placese
    min_year = 2022
    max_year = 2025

    # Create date bounds for filtering
    min_date = datetime(min_year, 1, 1)
    max_date = datetime(max_year, 12, 31)

    # TODO find a more obvious place or prompt the user for this
    review = 'firsttry'
    studies_folder = 'data/included-studies'
    output_folder = 'data/crossref-download'

    print('Getting list of included studies...')
    seeds = []
    input_file = os.path.join(studies_folder, review, 'included.csv')

    if not os.path.exists(input_file):
        print(f'ERROR: Input file not found: {input_file}')
        return

    with open(input_file) as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 3:
                doi = parts[2].strip().strip('"')
                if doi:
                    seeds.append(doi)

    print(f'Found {len(seeds)} seed publications')
    
    print('Getting citation space...')
    publications = {}
    for seed_doi in seeds:
        print(f"  Processing: {seed_doi}")
        pub = create_publication(output_folder, seed_doi)
        if pub:
            publications[seed_doi] = pub
            
            # Display basic info
            print(f"    Title: {pub.title}")
            print(f"    Year: {pub.pub_year}")
            print(f"    References: {pub.reference_count}")
            print(f"    Citation count: {pub.get_citation_count()}")
            
            time.sleep(1)  # Rate limiting
    
    all_related_dois = set()
    for seed_doi, pub in publications.items():
        related_dois = set()
        
        # Add references within year range
        for ref in pub.references:
            if ref and isinstance(ref, Citation):
                if ref.year and min_year <= ref.year <= max_year:
                    related_dois.add(ref.doi)

        
        # Add citations within year range
        for cite in pub.citations:
            if cite and isinstance(cite, Citation):
                related_dois.add(cite.doi)

        all_related_dois.update(related_dois)
        print(f'  {seed_doi}: {len(related_dois)} related publications')

    print(f'\nTotal unique related publications: {len(all_related_dois)}')

    # Save results
    output_file = os.path.join('data', 'crossref_related_dois.txt')
    os.makedirs('data', exist_ok=True)

    with open(output_file, 'w') as f:
        for doi in all_related_dois:
            f.write(f'{doi}\n')
        print(f'\nResults saved to: {output_file}')

if __name__ == "__main__":   
    main()

