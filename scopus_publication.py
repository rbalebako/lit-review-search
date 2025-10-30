# Module: ScopusPublication
# This module defines the ScopusPublication class which represents a publication from the Scopus API
# It inherits from the Publication base class and includes methods for retrieving publication data,
# references, citations, and co-citation/co-cited information from Scopus.

from lxml import etree
from datetime import datetime
import os, json, urllib.request, urllib.error, time, xml.etree.ElementTree as ET
from dotenv import load_dotenv
from publication import Publication 

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
API_KEY = os.getenv('SCOPUS_API_KEY', '')
if not API_KEY:
    raise ValueError(
        "SCOPUS_API_KEY not found in environment variables. "
        "Please create a .env file with your API key. "
        "See .env.example for template."
    )

# Get current year from environment or use current year
CURRENT_YEAR = int(os.getenv('CURRENT_YEAR', datetime.now().year))

class ScopusPublication(Publication):
    """Represents a publication from Scopus API with citation network data."""
    
    def __init__(self, data_folder, eid):
        super().__init__(data_folder, eid=eid)
        # Don't set eid_ since parent manages _eid
        
        # Initialize Scopus specific attributes
        self.reference_xml = None  # Add proper declaration
        self.citations_folder = os.path.join(self._pub_directory, 'citations')
        
        # Get reference data
        reference_file = os.path.join(self._pub_directory, 'references.xml')
        if not os.path.exists(reference_file):
            self.download_reference_file(reference_file)
        
        self.get_reference_file(reference_file)
        self.get_reference_eids()
        self.get_abstract()
        self.get_year()
        
        # Get citation data
        if not os.path.exists(self.citations_folder):
            self.download_citation_files()
        self.get_citation_eids()

    def get_abstract(self):
        self._abstract = ''  # Use parent's _abstract
        if self.reference_xml:  # Remove underscore from reference_xml_
            abstract_xmls = self.reference_xml.xpath('/ns0:abstracts-retrieval-response/ns0:coredata/dc:description/abstract[@xml:lang="eng"]', \
                namespaces={'ns0':'http://www.elsevier.com/xml/svapi/abstract/dtd', \
                'dc':'http://purl.org/dc/elements/1.1/'})

            for abstract_xml in abstract_xmls:
                paragraph_xmls = abstract_xml.xpath('ns3:para', namespaces={'ns3':'http://www.elsevier.com/xml/ani/common'})
                for paragraph_xml in paragraph_xmls:
                    self._abstract = ' '.join([self._abstract, paragraph_xml.xpath('string(.)')])

    def get_year(self):
        try:
            pub_date = self.reference_xml.xpath('/ns0:abstracts-retrieval-response/ns0:coredata/ns1:coverDate', \
            namespaces={'ns0':'http://www.elsevier.com/xml/svapi/abstract/dtd', \
            'ns1': 'http://prismstandard.org/namespaces/basic/2.0/'})

            self._pub_year = datetime.strptime(pub_date[0].text, '%Y-%m-%d').year  # Use parent's _pub_year
        except Exception as e:
            self._pub_year = 1900

    def download_reference_file(self, reference_file):
        try:
            abstract_url = 'https://api.elsevier.com/content/abstract/scopus_id/{}?apiKey={}'.format(self.eid_, API_KEY)
            
            #change ET to lxml
            xml_file = urllib.request.urlopen(abstract_url, timeout = 1000)
            data = xml_file.read()
            xml_file.close()
            xml = ET.fromstring(data)

            # save xml data to file
            with open(os.path.join(reference_file), 'wb') as f:
                f.write(ET.tostring(xml))

        except Exception as e:
            print('Error getting reference file: ' + self.eid_)
            print(e)
        
        time.sleep(5)

    def get_reference_file(self, reference_file):
        try:
            tree = etree.parse(reference_file)
            self.reference_xml = tree.getroot()  # Update to reference_xml
        except Exception as e:
            self.reference_xml = None

    def get_reference_eids(self):
        if self.reference_xml != None:
            references = self.reference_xml.xpath('/ns0:abstracts-retrieval-response/item/bibrecord/tail/bibliography/reference', \
                namespaces={'ns0':'http://www.elsevier.com/xml/svapi/abstract/dtd'})

            for reference in references:
                title = reference.xpath('ref-info/ref-title/ref-titletext')
                ref_eid = reference.xpath('ref-info/refd-itemidlist/itemid[@idtype="SGR"]')[0].text

                if ref_eid not in self._references:  # Update to _references
                    if len(title) > 0:
                        self._references.append({'eid' : ref_eid, 'title' : title[0].text})
                    else:
                        self._references.append({'eid' : ref_eid, 'title' : None})

    def get_citation_eids(self):
        if os.path.exists(self.citations_folder_):
            for file in os.listdir(self.citations_folder_):
                if '.json' in file:
                    with open(os.path.join(self.citations_folder_, file), 'r') as f:
                        json_data = json.load(f)

                        if 'entry' in json_data['search-results']:
                            for result in json_data['search-results']['entry']:
                                if 'eid' in result:
                                    cit_eid = result['eid'].replace('2-s2.0-', '')

                                    if 'dc:title' in result:
                                        title = result['dc:title'].replace('<inf>', '').replace('</inf>', '').replace('<sup>', '').replace('</sup>', '')
                                    else:
                                        title = ''

                                    try:
                                        year = datetime.strptime(result['prism:coverDate'], '%Y-%m-%d').year
                                    except:
                                        year = None

                                    #add year
                                    self._citations.append({'eid': cit_eid, 'title': title, 'year': year})  # Update to _citations

    def download_citation_files(self):
        try:         
            if not os.path.exists(self.citations_folder_):
                os.makedirs(self.citations_folder_)

            current_year = 2018
            count_results = 0

            year = 1900 #start from 1900 because some publication years are wrong
            while year <= current_year:
                page_count = 0
                while True:
                    json_file = urllib.request.urlopen('https://api.elsevier.com/content/search/scopus?' + \
                        'query=refeid(2-s2.0-{})&apiKey={}&date={}&count=200&start={}'.format(self.eid_, API_KEY, year, page_count * 200))
                    data = json_file.read()

                    json_data = json.loads(data)
                    results = int(json_data['search-results']['opensearch:totalResults'])

                    if page_count == 0 and results > 5000:
                        print('More than 5000: ' + self.eid_)
                        print('Year: ' + str(year))

                    if results == 0 or 'entry' not in json_data['search-results']:
                        break

                    count_results += len(json_data['search-results']['entry'])

                    #save citations to file
                    with open(os.path.join(self.citations_folder_, str(year) + '-' + str(page_count) + '.json'),'wb') as f:
                        f.write(data)

                    page_count += 1

                    if page_count * 200 > results:
                        break

                year += 1
        except urllib.error.HTTPError:
            print('Error getting citations: ' + self.eid_)

        # second delay for each request to Scopus
        time.sleep(5)


    @staticmethod
    def search_by_title(title: str, data_folder: str):
        """
        Search for a publication by title using Scopus API.
        
        Args:
            title (str): Title to search for
            data_folder (str): Folder for storing publication data
            
        Returns:
            ScopusPublication or None: First matching publication or None if not found
        """
        try:
            import urllib.parse
            
            # URL encode the title for the search query
            encoded_title = urllib.parse.quote(title)
            search_url = f'https://api.elsevier.com/content/search/scopus?query=TITLE({encoded_title})&count=1&apiKey={API_KEY}'
            
            # Make the API request
            response = urllib.request.urlopen(search_url, timeout=30)
            data = json.loads(response.read())
            
            # Parse the response
            if 'search-results' in data and 'entry' in data['search-results']:
                entries = data['search-results']['entry']
                if entries and len(entries) > 0:
                    first_result = entries[0]
                    
                    # Extract EID from the result
                    if 'eid' in first_result:
                        eid = first_result['eid'].replace('2-s2.0-', '')
                        
                        # Create and return ScopusPublication object
                        pub = ScopusPublication(data_folder, eid)
                        return pub
            
            print(f"No results found in Scopus for title: {title}")
            return None
            
        except Exception as e:
            print(f"Error searching Scopus for title '{title}': {e}")
            return None