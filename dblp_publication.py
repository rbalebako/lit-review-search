"""
DBLP Publication Module

This module defines the DBLPPublication class which represents a publication from the DBLP API.
DBLP (Digital Bibliography & Library Project) specializes in computer science publications.
"""

from datetime import datetime
from typing import Optional, List
import re
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import os
from publication import Publication

# Load environment variables
load_dotenv()

# DBLP API configuration
DBLP_BASE_URL = 'https://dblp.org/search/publ/api'
DBLP_REC_URL = 'https://dblp.org/rec'
RATE_LIMIT_DELAY = 1.0  # Conservative rate limiting

class DBLPPublication(Publication):
    """Represents a publication from DBLP API with citation network data."""
    
    def __init__(self, data_folder, dblp_key, download=True):
        """
        Initialize DBLPPublication object.
        
        Args:
            data_folder (str): Path to folder for storing cached data
            dblp_key (str): DBLP key of the publication (e.g., "conf/icse/SmithJ20")
            download (bool): If True, download data from API. If False, only load cached data.
        """
        # DBLP uses keys instead of DOIs, store in DOI field for compatibility
        super().__init__(data_folder, doi=dblp_key)
        self._metadata = None
        self.dblp_key = dblp_key
        
        if download:
            self.metadata  # Trigger metadata download
    
    @property
    def metadata(self):
        """
        Lazy-loaded access to DBLP metadata.
        
        Fetches metadata from DBLP API on first access and caches the result.
        Extracts metadata fields using extract_metadata() method.
        
        Returns:
            dict: Publication metadata from DBLP, or empty dict if fetch fails.
        """
        if self._metadata is None:
            try:
                self._metadata = self._fetch_metadata_from_dblp()
                self.extract_metadata()
            except requests.exceptions.RequestException as e:
                print(f"Error fetching metadata from DBLP for {self.dblp_key}: {e}")
                self._metadata = {}
        return self._metadata
    
    def _fetch_metadata_from_dblp(self):
        """
        Fetch publication metadata from DBLP API.
        
        Retrieves the XML record for the publication from DBLP and parses
        common fields like title, year, authors, venue, DOI, etc.
        
        Returns:
            dict: Publication metadata from DBLP containing fields:
                  - type: Publication type (article, inproceedings, etc.)
                  - key: DBLP key
                  - title: Publication title
                  - year: Publication year
                  - authors: List of author names
                  - venue: Journal or conference name
                  - doi: DOI (from 'ee' field)
                  - url: DBLP URL
                  - pages: Page range
                  - volume: Volume number
                  - number: Issue number
        """
        try:
            # Construct API URL for specific record
            url = f"{DBLP_REC_URL}/{self.dblp_key}.xml"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            
            # Extract metadata from XML
            metadata = {}
            
            # Find the publication element (could be article, inproceedings, etc.)
            pub_elem = root.find('.//*[@key]')
            if pub_elem is not None:
                metadata['type'] = pub_elem.tag
                metadata['key'] = pub_elem.get('key')
                
                # Extract common fields
                metadata['title'] = self._get_text(pub_elem, 'title')
                metadata['year'] = self._get_text(pub_elem, 'year')
                metadata['authors'] = [self._get_text(author, '.') 
                                      for author in pub_elem.findall('author')]
                metadata['venue'] = (self._get_text(pub_elem, 'journal') or 
                                   self._get_text(pub_elem, 'booktitle'))
                
                # Extract DOI from 'ee' field which contains URL like 'https://doi.org/10.1145/3576915.3623157'
                ee_url = self._get_text(pub_elem, 'ee')
                if ee_url:
                    # Extract just the DOI part after '.org/'
                    doi_match = re.search(r'\.org/(.+)$', ee_url)
                    if doi_match:
                        metadata['doi'] = doi_match.group(1)  # Get captured group (the DOI)
                        self._doi = metadata['doi']
                    else:
                        # If pattern doesn't match, store the full URL as fallback
                        metadata['doi'] = ee_url
                        self._doi = ee_url

            return metadata
            
        except Exception as e:
            print(f"Error parsing DBLP XML for {self.dblp_key}: {e}")
            return {}
    
    def _get_text(self, element, tag):
        """
        Helper to safely extract text from XML element.
        
        Args:
            element: XML element to extract from
            tag: Tag name to find, or '.' for element's own text
            
        Returns:
            str or None: Text content of the tag, or None if not found
        """
        if tag == '.':
            return element.text
        child = element.find(tag)
        return child.text if child is not None else None
    
    def extract_metadata(self):
        """
        Extract title, year, and other fields from DBLP metadata.
        
        Populates internal fields (_title, _pub_year, _abstract) from
        the metadata dictionary. Attempts to fetch abstract from DOI
        if available, since DBLP typically doesn't include abstracts.
        Also populates references and citations if available.
        """
        if not self._metadata:
            return
        
        # Extract title
        self._title = self._metadata.get('title', '')
        
        # Extract year
        year_str = self._metadata.get('year', '')
        if year_str and year_str.isdigit():
            self._pub_year = int(year_str)
        
    
        # Populate references and citations
        try:
            self._references = self.get_references()
            self._citations = self.get_citations()
        except Exception as e:
            print(f"Warning: Could not fetch references/citations for {self.dblp_key}: {e}")


    @property
    def title(self):
        """
        Get publication title.
        
        Lazily loads from metadata if not already set.
        
        Returns:
            str: Publication title
        """
        if not self._title and self.metadata:
            self._title = self.metadata.get('title', '')
        return self._title
    
    @property
    def pub_year(self):
        """
        Get publication year.
        
        Lazily loads from metadata if not already set.
        
        Returns:
            int or None: Publication year as integer, or None if not available
        """
        if not self._pub_year and self.metadata:
            year_str = self.metadata.get('year', '')
            if year_str and year_str.isdigit():
                self._pub_year = int(year_str)
        return self._pub_year
    
    def get_citation_count(self):
        """
        Get citation count for this publication.
        
        Note: DBLP doesn't provide citation counts directly.
        
        Returns:
            int: Always returns 0 (DBLP limitation)
        """
        return 0
    
    @staticmethod
    def search_by_title(title: str, data_folder: str, max_results: int = 10):
        """
        Search for publications by title using DBLP search API.
        
        Queries the DBLP search API with the given title and returns
        DBLPPublication objects for matching results.
        
        Args:
            title (str): Title keywords to search for
            data_folder (str): Folder for caching publication data
            max_results (int): Maximum number of results to return (default: 10)
            
        Returns:
            list: List of DBLPPublication objects matching the search,
                  or empty list if search fails
        """
        try:
            # DBLP search API
            params = {
                'q': title,
                'format': 'xml',
                'h': max_results
            }
            
            response = requests.get(DBLP_BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            results = []
            
            # Parse search results
            for hit in root.findall('.//hit'):
                info = hit.find('info')
                if info is not None:
                    key = info.find('key')
                    if key is not None and key.text:
                        pub = DBLPPublication(data_folder, key.text, download=False)
                        results.append(pub)
            
            return results
            
        except Exception as e:
            print(f'Error searching DBLP for title "{title}": {e}')
            return []
    
    @staticmethod
    def search_by_author(author_name: str, data_folder: str, max_results: int = 10):
        """
        Search for publications by author using DBLP search API.
        
        Queries the DBLP search API with the given author name and returns
        DBLPPublication objects for matching results.
        
        Args:
            author_name (str): Author name to search for
            data_folder (str): Folder for caching publication data
            max_results (int): Maximum number of results to return (default: 10)
            
        Returns:
            list: List of DBLPPublication objects by the author,
                  or empty list if search fails
        """
        try:
            # DBLP author search
            params = {
                'q': f'author:{author_name}',
                'format': 'xml',
                'h': max_results
            }
            
            response = requests.get(DBLP_BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            results = []
            
            for hit in root.findall('.//hit'):
                info = hit.find('info')
                if info is not None:
                    key = info.find('key')
                    if key is not None and key.text:
                        pub = DBLPPublication(data_folder, key.text, download=False)
                        results.append(pub)
            
            return results
            
        except Exception as e:
            print(f'Error searching DBLP for author "{author_name}": {e}')
            return []
