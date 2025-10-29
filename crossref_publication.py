import os, json, urllib.request, urllib.parse, time
from typing import Optional
import re
import crossref_commons
import crossref_commons.retrieval
from dotenv import load_dotenv
import requests
from publication import Publication
import html  # unescape HTML entities



# CrossRef API configuration
CROSSREF_BASE_URL = 'https://api.crossref.org'
MAILTO = os.getenv('CROSSREF_MAILTO', '')  # Email for polite pool access
if MAILTO:
    print(f"Using CrossRef polite pool with email: {MAILTO}")



# Rate limiting: CrossRef allows 50 req/sec for polite pool, 5 req/sec otherwise
RATE_LIMIT_DELAY = 1.0  # Conservative 1 second between requests


class CrossRefPublication(Publication):
    """Represents a publication from CrossRef API with citation network data."""

    def __init__(self, data_folder, doi, download=True):
        super().__init__(data_folder, doi=doi)
        self._metadata = None  # Declare Crossref-specific attribute

        if download: #TODO check the logic we probably don't want this
            self.metadata  # Trigger metadata download

    @property
    def metadata(self):
        if self._metadata is None:
            try:
                self.extract_metadata()
            except requests.exceptions.RequestException as e:
                print(f"Error fetching metadata from crossref_commons for {self._doi}: {e}")
                self._metadata = {}
        return self._metadata
    
   
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

    def extract_metadata(self):
        """
        Extract title, abstract, and publication year from metadata.
        Also populates references and citations from OpenCitations.
        """
        if not self._metadata:           
            self._metadata = crossref_commons.retrieval.get_publication_as_json(self._doi)  # Use parent's _doi

        # Extract title
        titles = self._metadata.get('title', [])
        if titles:
            self._title = titles[0]

        # Extract abstract (if available)
        self._abstract = self._metadata.get('abstract', '') or ''

        # Extract publication year
        pub_date = self._metadata.get('published', {}) or self._metadata.get('created', {})
        if pub_date and 'date-parts' in pub_date:
            date_parts = pub_date['date-parts'][0]
            if date_parts:
                self._pub_year = date_parts[0]
        
        # Populate references and citations
        try:
            self._references = self.get_references()
            self._citations = self.get_citations()
        except Exception as e:
            print(f"Warning: Could not fetch references/citations for {self._doi}: {e}")


    @staticmethod
    def search_by_title(title, data_folder):
        """
        Search for publications by title using CrossRef API.

        Args:
            title (str): Title to search for
            data_folder (str): Folder for caching data

        Returns:
            list: List of CrossRefPublication objects matching the search
        """
        try:
            # URL encode the title
            encoded_title = urllib.parse.quote(title)
            url = f'{CROSSREF_BASE_URL}/works?query.title={encoded_title}&rows=10'

            headers = {
                'User-Agent': f'LiteratureReviewSearch/1.0 (mailto:{MAILTO})' if MAILTO else 'LiteratureReviewSearch/1.0'
            }

            req = urllib.request.Request(url, headers=headers)
            response = urllib.request.urlopen(req, timeout=30)
            data = json.loads(response.read())

            results = []
            for item in data.get('message', {}).get('items', []):
                doi = item.get('DOI')
                if doi:
                    pub = CrossRefPublication(data_folder, doi, download=False)
                    pub._metadata = item
                    pub.extract_metadata()
                    results.append(pub)

            time.sleep(RATE_LIMIT_DELAY)
            return results

        except Exception as e:
            print(f'Error searching for title "{title}": {e}')
            return []

    @staticmethod
    def search_by_author(author_name, data_folder, max_results=10):
        """
        Search for publications by author name using CrossRef API.

        Args:
            author_name (str): Author name to search for
            data_folder (str): Folder for caching data
            max_results (int): Maximum number of results to return

        Returns:
            list: List of CrossRefPublication objects
        """
        try:
            encoded_author = urllib.parse.quote(author_name)
            url = f'{CROSSREF_BASE_URL}/works?query.author={encoded_author}&rows={max_results}'

            headers = {
                'User-Agent': f'LiteratureReviewSearch/1.0 (mailto:{MAILTO})' if MAILTO else 'LiteratureReviewSearch/1.0'
            }

            req = urllib.request.Request(url, headers=headers)
            response = urllib.request.urlopen(req, timeout=30)
            data = json.loads(response.read())

            results = []
            for item in data.get('message', {}).get('items', []):
                doi = item.get('DOI')
                if doi:
                    pub = CrossRefPublication(data_folder, doi, download=False)
                    pub._metadata = item
                    pub.extract_metadata()
                    pub.extract_references()
                    results.append(pub)

            time.sleep(RATE_LIMIT_DELAY)
            return results

        except Exception as e:
            print(f'Error searching for author "{author_name}": {e}')
            return []

 