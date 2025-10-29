import os, json, urllib.request, urllib.parse, time
from typing import Optional
import re
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
                self._metadata = crossref_commons.retrieval.get_publication_as_json(self._doi)  # Use parent's _doi
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
        If abstract is missing in CrossRef metadata, attempt to scrape it from the DOI landing page.
        Also populates references and citations from OpenCitations.
        """
        # Ensure metadata is loaded
        if not self._metadata:
            _ = self.metadata

        if not self._metadata:
            return

        # Extract title
        titles = self._metadata.get('title', [])
        if titles:
            self._title = titles[0]

        # Extract abstract (if available)
        self._abstract = self._metadata.get('abstract', '') or ''
        # If abstract is empty, try scraping from DOI landing page
        if not self._abstract and self._doi:
            try:
                scraped = self._scrape_abstract_from_doi(self._doi)
                if scraped:
                    self._abstract = scraped
            except Exception as e:
                # don't fail hard on scraping errors
                print(f"Warning: failed to scrape abstract for {self._doi}: {e}")

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
