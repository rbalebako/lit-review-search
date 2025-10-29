from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from collections import defaultdict
from pathlib import Path
from abc import abstractmethod
import csv
import os
from requests import get
from dotenv import load_dotenv
import requests
import re
import html


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

# for opencitation
HTTP_HEADERS = {"authorization": OPENCITATIONS_API_KEY}


class Publication:
    """Base class for publication data with common functionality"""
    
    # Class-level declarations of all attributes
    _doi: Optional[str]
    _eid: Optional[str]
    _data_folder: str
    _pub_directory: str
    _references: List[str]
    _citations: List[str]
    _co_citing_counts: defaultdict
    _co_cited_counts: defaultdict
    _abstract: str
    _title: str
    _pub_year: Optional[int]
    
    def __init__(self, data_folder: str, doi: Optional[str] = None, eid: Optional[str] = None):
        if not doi and not eid:
            raise ValueError("Must provide either DOI or EID")
            
        self._doi = doi
        self._eid = eid.rjust(10, '0') if eid else None
   

        # Initialize common attributes
        self._references = []
        self._citations = []
        self._co_citing_counts = defaultdict(int)
        self._co_cited_counts = defaultdict(int)
        self._abstract = ''
        self._title = ''
        self._pub_year = None
        self._data_folder = data_folder
        self._pub_directory = None  # Will be set in create_pub_directory if it is called.  Otherwise, keep this lightweight
    
    def create_pub_directory(self, data_folder: str) -> str:
        """Create and return path to publication directory using EID or DOI.
        
        Args:
            data_folder: Base directory for storing publication data
            
        Returns:
            String path to publication-specific directory
        """
        # Use EID if available, otherwise DOI, and ensure filename safety using Path
        id_to_use = self._eid if self._eid else self._doi
        safe_id = Path(id_to_use).stem  # Removes unsafe chars and path separators
        pub_directory = str(Path(data_folder) / safe_id)
        
        # Create publication directory if it does not exist
        Path(pub_directory).mkdir(parents=True, exist_ok=True)
        return pub_directory
    
    @property
    def id(self) -> Optional[str]:
        return self._doi if self._doi else self._eid

    @property
    def doi(self) -> Optional[str]:
        return self._doi
        
    @property
    def eid(self) -> Optional[str]:
        return self._eid
    
    @property
    def reference_count(self) -> int:
        """Get reference count, loading references if not already loaded."""
        if not self._references:
            self._references = self.get_references()
        return len(self._references)
    
    @property
    def citation_count(self) -> int:
        """Get citation count, loading citations if not already loaded."""
        if not self._citations:
            self._citations = self.get_citations()
        return len(self._citations)
    
    @property
    def references(self) -> List[str]:
        """Access to publication references with lazy loading."""
        if not self._references:
            self._references = self.get_references()
        return self._references
        
    @property
    def citations(self) -> List[str]:
        """Access to publication citations with lazy loading."""
        if not self._citations:
            self._citations = self.get_citations()
        return self._citations

   
    
    def append_to_csv(self, csv_file_path: str):
        """
        Append publication information to a CSV file.
        
        Creates the file with headers if it doesn't exist.
        Appends a row with id, title, year, abstract, citation_count, reference_count.
        
        Args:
            csv_file_path (str): Path to the CSV file to append to.
        """
        # Determine the ID (use DOI if available, otherwise EID)
        pub_id = self._doi if self._doi else self._eid
        
        # Check if file exists to determine if we need to write headers
        file_exists = os.path.exists(csv_file_path)
        
        try:
            with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['id', 'title', 'year', 'abstract', 'citation_count', 'reference_count']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header if file is new
                if not file_exists:
                    writer.writeheader()
                
                # Write publication data
                writer.writerow({
                    'id': pub_id,
                    'title': self._title,
                    'year': self._pub_year,
                    'abstract': self._abstract,
                    'citation_count': self.citation_count,
                    'reference_count': self.reference_count
                })
                
        except Exception as e:
            print(f"Error appending publication {pub_id} to CSV: {e}")


    def _list_from_opencitations_json(self, field: str, data: dict):
        """Create list of dois from OpenCitations API response"""
        if isinstance(data, list):
            dois = []
            for item in data:
                id_string = item.get(field, '')
                doi = self._extract_doi(id_string=id_string)
                if doi:
                    dois.append(doi)
            return dois
        else:
            print(f"Warning: OpenCitations references API did not return a list.")
            return None


    def _extract_doi(self, id_string: str) -> Optional[str]:
        """Extract DOI from a given identifier string."""
        doi_pattern = re.compile(r'doi:\d{2}.\d{4,9}/[-._;()/:A-Z0-9]+', re.IGNORECASE)
        match = doi_pattern.search(id_string)
        return match.group(0) if match else None
    

    def get_references(self) -> List[str]:
        """
        CrossrefCommons does not have a get reference function, so we use OpenCitations API here.
        https://api.opencitations.net/index/v2

        all the outgoing references to other cited works appearing in the reference list of the bibliographic entity identified 
        """
        api_call = f"https://api.opencitations.net/index/v2/references/doi:{self._doi}?format=json"
        response = get(api_call, headers=HTTP_HEADERS)
        list_of_dois = self._list_from_opencitations_json(field="cited", data=response.json())
        return list_of_dois

    def get_citations(self) -> List[str]:
        """
        constitute the incoming citations of that identified bibliographic entity
        Example: /citations/doi:10.1108/jd-12-2013-0166 
        """
        api_call = f"https://api.opencitations.net/index/v2/citations/doi:{self._doi}?format=json"
        response = get(api_call, headers=HTTP_HEADERS)
        list_of_dois  = self._list_from_opencitations_json(field="citing", data=response.json()) 
        return list_of_dois 
    
    def _scrape_abstract_from_doi(self, doi: str) -> Optional[str]:
        """
        Attempt to fetch and extract an abstract from the DOI landing page or arXiv.

        Strategy:
        - First check if DOI points to arXiv and fetch directly from arXiv API
        - Otherwise GET https://doi.org/{doi} (follow redirects)
        - Look for common meta tags and HTML containers:
            - <meta name="description" content="...">
            - <meta property="og:description" content="...">
            - <meta name="citation_abstract" content="...">
            - <div class="abstract">...</div> (or similar)
        - Strip HTML tags and unescape entities.

        Returns:
            str or None: extracted abstract text or None if not found.
        """
        # Check if this is an arXiv DOI
        arxiv_match = re.search(r'arxiv\.org/abs/(\d+\.\d+)', doi.lower())
        if arxiv_match:
            arxiv_id = arxiv_match.group(1)
            abstract = self._fetch_abstract_from_arxiv(arxiv_id)
            if abstract:
                return abstract
        
        try:
            url = f"https://doi.org/{doi}"
            resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            resp.raise_for_status()
            text = resp.text
            
            # Check if redirected to arXiv
            if 'arxiv.org' in resp.url:
                arxiv_match = re.search(r'arxiv\.org/abs/(\d+\.\d+)', resp.url)
                if arxiv_match:
                    arxiv_id = arxiv_match.group(1)
                    abstract = self._fetch_abstract_from_arxiv(arxiv_id)
                    if abstract:
                        return abstract

            # common meta and container regexes
            patterns = [
                r'<meta\s+name=["\']citation_abstract["\']\s+content=["\'](.*?)["\']',
                r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
                r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']',
                r'<meta\s+name=["\']dc\.description["\']\s+content=["\'](.*?)["\']',
                r'(<div[^>]*(?:class|id)=["\'][^"\']*abstract[^"\']*["\'][^>]*>.*?</div>)',
                r'(<section[^>]*class=["\'][^"\']*abstract[^"\']*["\'][^>]*>.*?</section>)'
            ]

            for pat in patterns:
                m = re.search(pat, text, flags=re.I | re.S)
                if m:
                    candidate = m.group(1)
                    # if whole container matched, strip tags
                    if candidate:
                        # remove HTML tags
                        cleaned = re.sub(r'<[^>]+>', ' ', candidate)
                        cleaned = html.unescape(cleaned)
                        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                        # Heuristic: ignore very short matches
                        if len(cleaned) >= 50:
                            return cleaned

            return None

        except Exception as e:
            # swallow errors, return None to allow fallback
            print(f"Warning: error scraping DOI {doi}: {e}")
            return "Abstract not found {e}"
    
    def _fetch_abstract_from_arxiv(self, arxiv_id: str) -> Optional[str]:
        """
        Fetch abstract directly from arXiv API.
        
        Args:
            arxiv_id (str): arXiv identifier (e.g., "2301.12345")
            
        Returns:
            str or None: Abstract text or None if not found
        """
        try:
            import xml.etree.ElementTree as ET
            
            # arXiv API endpoint
            api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
            resp = requests.get(api_url, timeout=15)
            resp.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(resp.content)
            
            # Find abstract in the entry
            # arXiv API uses Atom namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entry = root.find('atom:entry', ns)
            
            if entry is not None:
                summary = entry.find('atom:summary', ns)
                if summary is not None and summary.text:
                    # Clean up whitespace
                    abstract = re.sub(r'\s+', ' ', summary.text).strip()
                    return abstract
            
            return None
            
        except Exception as e:
            print(f"Warning: error fetching arXiv abstract for {arxiv_id}: {e}")
            return None




