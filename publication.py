from typing import Optional, List
from pathlib import Path
import csv
import os
from requests import get
from dotenv import load_dotenv
import re
import requests
import xml.etree.ElementTree as ET


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
    _dblp: Optional[str]
    _references: List[str]
    _citations: List[str]
    _abstract: str
    _title: str
    _pub_year: Optional[int] # to keep the method lightweieght, only set and create folder if needed.

    
    def __init__(self, doi: Optional[str] = None, eid: Optional[str] = None, dblp:  Optional[str] = None):
            
        self._doi = doi if doi else None
        self._eid = eid.rjust(10, '0') if eid else None
        self._dblp = dblp if dblp else None
   
        # Initialize common attributes
        self._references = []
        self._citations = []
        self._abstract = ''
        self._title = ''
        self._pub_year = None

    
    def create_pub_directory(self, data_folder: str) -> str:
        """Create and return path to publication directory using EID or DOI.
        
        Args:
            data_folder: Base directory for storing publication data
            
        Returns:create_pub_directory
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
    def dblp(self) -> Optional[str]:
        return self._dblp
    
    @property
    def abstract(self) -> Optional[str]:
        return self._abstract
    
    @property
    def title(self) -> Optional[str]:
        return self._title
    
    @property
    def pub_year(self) -> Optional[str]:
        return self._pub_year
    
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

   
    @property
    def abstract(self) -> Optional[str]:
        if not self._abstract:
            self._abstract = self._fetch_abstract_from_arxiv_by_title()
        return self._abstract
   
    
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
                fieldnames = ['title', 'doi', 'eid', 'dblp',  'year',  'citation_count', 'reference_count', 'url', 'abstract']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header if file is new
                if not file_exists:
                    writer.writeheader()
                
                # Write publication data
                writer.writerow({
                    'title': self.title,
                    'doi': self.doi,
                    'eid': self.eid,
                    'dblp': self.dblp,
                    'year': self.pub_year,
                    'citation_count': self.citation_count,
                    'reference_count': self.reference_count,
                    'url': f"https://doi.org/{self.doi}",
                    'abstract': self.abstract,
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
        # TODO the id being used here is not the doi. 
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
    
    
    
    def _fetch_abstract_from_arxiv(self, arxiv_id: str) -> Optional[str]:
        """
        Fetch abstract directly from arXiv API using arXiv ID.
        
        Args:
            arxiv_id (str): arXiv identifier (e.g., "2301.12345")
            
        Returns:
            str or None: Abstract text or None if not found
        """
        try:
            # arXiv API endpoint
            api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
            resp = requests.get(api_url, timeout=15)
            resp.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(resp.content)
            
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
            print(f"Warning: error fetching arXiv abstract for ID {arxiv_id}: {e}")
            return None
    
    def _fetch_abstract_from_arxiv_by_title(self) -> Optional[str]:
        """
        Fetch abstract from arXiv by searching for the paper title.
        
        Uses the arXiv API search endpoint to find papers matching the title,
        then retrieves the abstract from the first matching result.
            
        Returns:
            str or None: Abstract text or None if not found
        """
        try:
            # Clean title for search query
            search_query = self.title.strip()
            
            # arXiv API search endpoint
            api_url = f"http://export.arxiv.org/api/query?search_query=ti:{requests.utils.quote(search_query)}&max_results=1"
            resp = requests.get(api_url, timeout=15)
            resp.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(resp.content)
            
            # arXiv API uses Atom namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entry = root.find('atom:entry', ns)
            
            if entry is not None:
                # Verify title matches (case-insensitive partial match)
                entry_title = entry.find('atom:title', ns)
                if entry_title is not None and entry_title.text:
                    entry_title_text = entry_title.text.strip().lower()
                    search_title_lower = self.title.strip().lower()
                    
                    # Check if titles match (allow partial matching)
                    if search_title_lower in entry_title_text or entry_title_text in search_title_lower:
                        summary = entry.find('atom:summary', ns)
                        if summary is not None and summary.text:
                            # Clean up whitespace
                            abstract = re.sub(r'\s+', ' ', summary.text).strip()
                            return abstract
            
            return None
            
        except Exception as e:
            print(f"Warning: error fetching arXiv abstract by title '{self.title}': {e}")
            return None




