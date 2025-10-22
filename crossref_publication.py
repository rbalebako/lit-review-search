from datetime import datetime
from collections import defaultdict
import os, json, urllib.request, urllib.error, urllib.parse, time


class CrossRefPublication():
    """
    Represents a publication from CrossRef API with citation network data.

    Similar to ScopusPublication but uses DOI as identifier and CrossRef API.
    """

    @property
    def doi(self):
        return self.doi_

    @property
    def references(self):
        return self.references_

    @property
    def reference_count(self):
        return len(self.references_)

    @property
    def citations(self):
        return self.citations_

    @property
    def citation_count(self):
        return len(self.citations_)

    @property
    def co_citing_ids(self):
        return list(self.co_citing_counts_.keys())

    @property
    def co_citing_counts(self):
        return self.co_citing_counts_

    @property
    def co_cited_eids(self):
        return list(self.co_cited_counts_.keys())

    @property
    def co_cited_counts(self):
        return self.co_cited_counts_

    @property
    def abstract(self):
        return self.abstract_

    @property
    def pub_year(self):
        return self.pub_year_

    @property
    def title(self):
        return self.title_

    def __init__(self, data_folder, doi, download=True):
        """
        Initialize CrossRefPublication object.

        Args:
            data_folder (str): Path to folder for storing cached data
            doi (str): DOI of the publication (e.g., "10.1037/0003-066X.59.1.29")
            download (bool): If True, download data from API. If False, only load cached data.
        """
        self.doi_ = doi
        # Replace slashes with underscores for safe file names
        self.safe_doi_ = doi.replace('/', '_')
        self.data_folder_ = data_folder
        self.pub_directory_ = os.path.join(data_folder, self.safe_doi_)

        # Create publication directory if it does not exist
        if not os.path.exists(self.pub_directory_):
            os.makedirs(self.pub_directory_)

        self.references_ = []
        self.citations_ = []
        self.co_citing_counts_ = defaultdict(int)
        self.co_cited_counts_ = defaultdict(int)
        self.abstract_ = ''
        self.title_ = ''
        self.pub_year_ = None

        metadata_file = os.path.join(self.pub_directory_, 'metadata.json')

        # Download metadata if it doesn't exist and download=True
        if download and not os.path.exists(metadata_file):
            self.download_metadata(metadata_file)

        # Load metadata from file
        if os.path.exists(metadata_file):
            self.load_metadata(metadata_file)
            self.extract_references()
            self.extract_metadata()

        # Get citations (noted: full citation list requires Cited-by membership)
        # We can get the count but not the full list without membership
        # For now, we'll store the citation count and leave citations_ empty
        # unless we implement OpenCitations integration

    def download_metadata(self, metadata_file):
        """
        Download publication metadata from CrossRef API.

        Args:
            metadata_file (str): Path to save the metadata JSON
        """
        try:
            # Build API URL
            url = f'{CROSSREF_BASE_URL}/works/{self.doi_}'

            # Create request with polite pool headers
            headers = {
                'User-Agent': f'LiteratureReviewSearch/1.0 (mailto:{MAILTO})' if MAILTO else 'LiteratureReviewSearch/1.0'
            }

            req = urllib.request.Request(url, headers=headers)
            response = urllib.request.urlopen(req, timeout=30)
            data = response.read()

            # Save to file
            with open(metadata_file, 'wb') as f:
                f.write(data)

            print(f'Downloaded metadata for DOI: {self.doi_}')

        except urllib.error.HTTPError as e:
            print(f'Error downloading metadata for DOI {self.doi_}: HTTP {e.code}')
        except Exception as e:
            print(f'Error downloading metadata for DOI {self.doi_}: {e}')

        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)

    def load_metadata(self, metadata_file):
        """
        Load metadata from cached JSON file.

        Args:
            metadata_file (str): Path to the metadata JSON file
        """
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.metadata_ = data.get('message', {})
        except Exception as e:
            print(f'Error loading metadata for DOI {self.doi_}: {e}')
            self.metadata_ = {}

    def extract_metadata(self):
        """
        Extract title, abstract, and publication year from metadata.
        """
        if not hasattr(self, 'metadata_'):
            return

        # Extract title
        titles = self.metadata_.get('title', [])
        if titles:
            self.title_ = titles[0]

        # Extract abstract (if available)
        self.abstract_ = self.metadata_.get('abstract', '')

        # Extract publication year
        pub_date = self.metadata_.get('published', {}) or self.metadata_.get('created', {})
        if pub_date and 'date-parts' in pub_date:
            date_parts = pub_date['date-parts'][0]
            if date_parts:
                self.pub_year_ = date_parts[0]

    def extract_references(self):
        """
        Extract references (works cited by this publication) from metadata.
        """
        if not hasattr(self, 'metadata_'):
            return

        references = self.metadata_.get('reference', [])

        for ref in references:
            ref_doi = ref.get('DOI')
            ref_title = ref.get('article-title', '') or ref.get('volume-title', '')

            if ref_doi:
                self.references_.append({
                    'doi': ref_doi,
                    'title': ref_title
                })

    def get_citation_count(self):
        """
        Get the number of citations from metadata.

        Note: CrossRef provides citation count via 'is-referenced-by-count'
        but getting the full list of citing works requires Cited-by membership
        or using external services like OpenCitations.

        Returns:
            int: Number of citations
        """
        if not hasattr(self, 'metadata_'):
            return 0

        return self.metadata_.get('is-referenced-by-count', 0)

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
                    pub.extract_references()
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


def convert_scopus_to_crossref(scopus_title, data_folder):
    """
    Helper function to find CrossRef DOI for a Scopus publication by title.

    Args:
        scopus_title (str): Title of the Scopus publication
        data_folder (str): Folder for caching CrossRef data

    Returns:
        CrossRefPublication or None: Matching publication if found
    """
    results = CrossRefPublication.search_by_title(scopus_title, data_folder)
    if results:
        return results[0]  # Return best match
    return None
