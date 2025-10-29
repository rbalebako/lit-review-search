from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict
import os, json, urllib.request, urllib.error, urllib.parse, time
from typing import Optional, List
import re
import crossref_commons.retrieval
from requests import get
from dotenv import load_dotenv
import requests
from publication import Publication, Citation
import html  # unescape HTML entities


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


class CrossRefPublication(Publication):
    """Represents a publication from CrossRef API with citation network data."""

    def __init__(self, data_folder, doi, download=True):
        super().__init__(data_folder, doi=doi)
        self._metadata = None  # Declare Crossref-specific attribute

        if download:
            self.metadata  # Trigger metadata download

    @property
    def metadata(self):
        if self._metadata is None:
            try:
                self._metadata = crossref_commons.retrieval.get_publication_as_json(self._doi)  # Use parent's _doi
            except requests.exceptions.RequestException as e:
                print(f"Error fetching metadata for {self._doi}: {e}")
                self._metadata = {}
        return self._metadata
    
    #TODO add publisher, created->date-parts, 

    def get_references(self) -> List['CrossRefPublication.Citation']:
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

    def get_citations(self) -> List['CrossRefPublication.Citation']:
        """
        constitute the incoming citations of that identified bibliographic entity
        Example: /citations/doi:10.1108/jd-12-2013-0166 
        """
        api_call = f"https://api.opencitations.net/index/v2/citations/doi:{self._doi}?format=json"
        response = get(api_call, headers=HTTP_HEADERS)
        list_of_dois  = self._list_from_opencitations_json(field="citing", data=response.json()) 
        return list_of_dois 
    

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
        If abstract is missing in CrossRef metadata, attempt to scrape it from the DOI landing page.
        """
        # Ensure metadata is loaded
        if not self._metadata:
            _ = self.metadata

        if not self._metadata:
            return

        # Extract title
        titles = self._metadata.get('title', [])
        if titles:
            self.title_ = titles[0]

        # Extract abstract (if available)
        self.abstract_ = self._metadata.get('abstract', '') or ''
        # If abstract is empty, try scraping from DOI landing page
        if not self.abstract_ and self._doi:
            try:
                scraped = self._scrape_abstract_from_doi(self._doi)
                if scraped:
                    self.abstract_ = scraped
            except Exception as e:
                # don't fail hard on scraping errors
                print(f"Warning: failed to scrape abstract for {self._doi}: {e}")

        # Extract publication year
        pub_date = self._metadata.get('published', {}) or self._metadata.get('created', {})
        if pub_date and 'date-parts' in pub_date:
            date_parts = pub_date['date-parts'][0]
            if date_parts:
                self.pub_year_ = date_parts[0]

    def filter_citations(self, min_year=None, max_year=None):
        """
        Filter citations by year range.

        Args:
            min_year (int, optional): Minimum publication year (inclusive).
            max_year (int, optional): Maximum publication year (inclusive).

        Note: Since we don't have full citation data from CrossRef API
        (requires membership), this is a placeholder for when citation
        data is obtained from other sources (e.g., OpenCitations).
        """
        filtered_citations = []
        for citation in self.citations_:
            cite_year = citation.get('year')

            if cite_year is None:
                continue

            if min_year is not None and cite_year < min_year:
                continue

            if max_year is not None and cite_year > max_year:
                continue

            filtered_citations.append(citation)

        self.citations_ = filtered_citations
        # Note: Co-citing calculation would happen here if we had citation data




    def get_cociting_ids(self):
        """
        Calculate co-citing relationships.

        Note: This requires citation data which is not freely available
        from CrossRef API without Cited-by membership.
        """
        # Placeholder - would need citation data to implement
        pass

    def get_co_cited_ids(self):
        """
        Calculate co-cited relationships.

        Note: This requires analyzing citations of citing papers.
        """
        # Placeholder - would need citation data to implement
        pass

    @property
    def references(self) -> List[Citation]:
        """Lazy-loaded access to references."""
        if not self._references:  # This will check both None and empty array
            self._references = self.get_references()
        return self._references

    @property 
    def citations(self) -> List[Citation]:
        """Lazy-loaded access to citations."""
        if not self._citations:
            self._citations =self.get_citations()
        return self._citations
    
    @classmethod
    def _extract_doi(self, id_string: str) -> Optional[str]:
        """Extract DOI from a given identifier string."""
        doi_pattern = re.compile(r'doi:\d{2}.\d{4,9}/[-._;()/:A-Z0-9]+', re.IGNORECASE)
        match = doi_pattern.search(id_string)
        return match.group(0) if match else None
    
    @classmethod
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
                    pub.metadata_ = item
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
                    pub.metadata_ = item
                    pub.extract_metadata()
                    pub.extract_references()
                    results.append(pub)

            time.sleep(RATE_LIMIT_DELAY)
            return results

        except Exception as e:
            print(f'Error searching for author "{author_name}": {e}')
            return []

    def _scrape_abstract_from_doi(self, doi: str) -> Optional[str]:
        """
        Attempt to fetch and extract an abstract from the DOI landing page.

        Strategy:
          - GET https://doi.org/{doi} (follow redirects)
          - Look for common meta tags and HTML containers:
            - <meta name="description" content="...">
            - <meta property="og:description" content="...">
            - <meta name="citation_abstract" content="...">
            - <div class="abstract">...</div> (or similar)
          - Strip HTML tags and unescape entities.

        Returns:
            str or None: extracted abstract text or None if not found.
        """
        try:
            url = f"https://doi.org/{doi}"
            resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            resp.raise_for_status()
            text = resp.text

            # common meta and container regexes
            patterns = [
                r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
                r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']',
                r'<meta\s+name=["\']citation_abstract["\']\s+content=["\'](.*?)["\']',
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
            return None
