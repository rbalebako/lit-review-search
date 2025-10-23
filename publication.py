from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from collections import defaultdict
from pathlib import Path
from abc import abstractmethod

@dataclass
class Citation:
    id: str  # DOI or EID depending on implementation
    year: Optional[int] = None

class Publication:
    """Base class for publication data with common functionality"""
    
    # Class-level declarations of all attributes
    _doi: Optional[str]
    _eid: Optional[str]
    _data_folder: str
    _pub_directory: str
    _references: List[Citation]
    _citations: List[Citation]
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
    @abstractmethod
    def references(self) -> List[Citation]:
        """Access to publication references. Child classes must implement loading logic."""
        pass
        
    @property
    @abstractmethod
    def citations(self) -> List[Citation]:
        """Access to publication citations. Child classes must implement loading logic."""
        pass
    
    def filter_citations(self, min_year=None, max_year=None):
        """Filter citations by year range."""
        filtered_citations = []
        for citation in self._citations:
            cite_year = citation.year
            
            if cite_year is None:
                continue
                
            if min_year is not None and cite_year < min_year:
                continue
                
            if max_year is not None and cite_year > max_year:
                continue
                
            filtered_citations.append(citation)
            
        self._citations = filtered_citations


