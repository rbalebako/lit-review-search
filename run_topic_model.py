"""
Topic Modeling Pipeline for Literature Review

This script processes a set of seed publications to:
1. Build a citation network
2. Find strongly related publications
3. Extract topics from abstracts
4. Cluster documents by topic similarity
5. Filter results by topic relevance

The pipeline combines citation analysis with topic modeling to identify
relevant publications for literature review.
"""

import sys, os, citation_filtering, topic_filtering
from scopus_publication import ScopusPublication

def main():
    # Configuration parameters
    shared = 0.10  # Threshold for determining strong citation relationships
    min_year = 2010  # Minimum publication year to include
    max_year = 2020  # Maximum publication year to include

    # File paths and folders
    review = 'seeds'          # Name of the review project
    studies_folder = ''       # Folder containing seed studies
    data_folder = ''         # Folder for cached Scopus data
    topic_output_folder = '' # Folder for topic modeling outputs
    output_file = 'rake_results.csv'  # Final results file

    print('Getting list of included studies..')
    # Load seed publications from CSV (format: Title,EID)
    seeds = []
    with open(os.path.join(studies_folder, review, 'included.csv')) as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 2:
                # Extract EID (second column), remove quotes if present
                eid = parts[1].strip().strip('"')
                seeds.append(eid)

    print('Getting citation space..')
    # Build citation network from seed publications
    scopus_pubs = {}
    for seed in seeds:
        # Create ScopusPublication object for each seed
        scopus_pubs[seed] = ScopusPublication(data_folder, seed)
        # Filter citations to specified year range
        scopus_pubs[seed].filter_citations(min_year=min_year, max_year=max_year)
        # Calculate co-citation relationships
        scopus_pubs[seed].get_co_cited_eids()

    print('Getting strong citation relationships..')
    # Find publications with strong citation connections
    strong_cite_related_pub_eids = set()
    for seed in seeds:
        # Union of all strongly related publications across seeds
        strong_cite_related_pub_eids = strong_cite_related_pub_eids.union(
            citation_filtering.get_strong_citation_relationship(scopus_pubs[seed], shared)
        )

    # Create publication objects for strongly related papers
    strong_cite_related_pubs = []
    for eid in strong_cite_related_pub_eids:
        strong_cite_related_pubs.append(ScopusPublication(data_folder, eid, False))

    print('Getting topics..')
    # Extract topics from publication abstracts
    topic_filtering.get_topics(topic_output_folder, strong_cite_related_pubs)

    print('Clustering documents..')
    # Group documents by topic similarity
    cluster_documents(topic_output_folder, strong_related_pubs)

    print('Filtering by topic cluster..')
    # Select relevant documents based on topic clusters
    select_topic_clusters(topic_output_folder, strong_related_pubs)        

if __name__ == "__main__":
    main()