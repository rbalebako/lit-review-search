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
        return len(self._references)
    
    @property
    def citation_count(self) -> int:
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


    def get_references(self) -> List[str]:
        """
        CrossrefCommons does not have a get reference function, so we use OpenCitations API here.
        https://api.opencitations.net/index/v2

        all the outgoing references to other cited works appearing in the reference list of the bibliographic entity identified 
        """
        api_call = f"https://api.opencitations.net/index/v2/references/doi:{self._doi}?format=json"
        response = get(api_call, headers=HTTP_HEADERS)
        print(f"Calling {api_call} for references")
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
    



