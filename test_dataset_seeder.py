"""
Test script to verify dataset seeder data structure
Run this after seeding to see how datasets are created
"""
from app import create_app
from app.modules.dataset.models import DataSet, DSDownloadRecord, Author
from app.modules.auth.models import User

app = create_app()

with app.app_context():
    print("=" * 80)
    print("DATASET SEEDER VERIFICATION")
    print("=" * 80)
    
    # Get all datasets
    datasets = DataSet.query.order_by(DataSet.id).all()
    
    print(f"\nTotal Datasets: {len(datasets)}\n")
    
    for ds in datasets:
        print(f"\n{'─' * 80}")
        print(f"Dataset ID: {ds.id}")
        print(f"Title: {ds.ds_meta_data.title}")
        print(f"Created At: {ds.created_at}")
        print(f"Publication Type: {ds.ds_meta_data.publication_type.value}")
        print(f"Tags: {ds.ds_meta_data.tags}")
        
        # Get authors
        authors = Author.query.filter_by(ds_meta_data_id=ds.ds_meta_data_id).all()
        author_names = [a.name for a in authors]
        print(f"Authors: {', '.join(author_names)}")
        
        # Get download count
        download_count = DSDownloadRecord.query.filter_by(dataset_id=ds.id).count()
        print(f"Download Count: {download_count}")
        
        # Get owner
        user = User.query.get(ds.user_id)
        print(f"Owner: {user.email if user else 'Unknown'}")
    
    print(f"\n{'=' * 80}")
    print("\nDOWNLOAD STATISTICS")
    print(f"{'=' * 80}\n")
    
    # Show download distribution
    for ds in datasets:
        download_count = DSDownloadRecord.query.filter_by(dataset_id=ds.id).count()
        print(f"Dataset {ds.id} ({ds.ds_meta_data.title}): {download_count} downloads")
    
    print(f"\n{'=' * 80}")
    print("\nRECOMMENDATION SYSTEM TEST DATA")
    print(f"{'=' * 80}\n")
    
    print("Expected behavior for Dataset 1 recommendations:")
    print("- Should recommend datasets with tags 'tag1' or 'tag2'")
    print("- Should recommend datasets with 'Author 1'")
    print("- Scoring: downloads (3pts) + recency (3pts) + coincidences (4pts)")
    print("\nDatasets with shared attributes:")
    
    # Dataset 1 reference
    ds1 = datasets[0]
    ds1_tags = set(ds1.ds_meta_data.tags.split(", "))
    ds1_authors = {a.name for a in Author.query.filter_by(ds_meta_data_id=ds1.ds_meta_data_id).all()}
    
    print(f"\nDataset 1 tags: {ds1_tags}")
    print(f"Dataset 1 authors: {ds1_authors}\n")
    
    for ds in datasets[1:]:  # Skip dataset 1 itself
        ds_tags = set(ds.ds_meta_data.tags.split(", "))
        ds_authors = {a.name for a in Author.query.filter_by(ds_meta_data_id=ds.ds_meta_data_id).all()}
        
        tag_matches = ds1_tags & ds_tags
        author_matches = ds1_authors & ds_authors
        
        if tag_matches or author_matches:
            download_count = DSDownloadRecord.query.filter_by(dataset_id=ds.id).count()
            print(f"Dataset {ds.id}: {ds.ds_meta_data.title}")
            print(f"  Tag matches: {tag_matches if tag_matches else 'None'}")
            print(f"  Author matches: {author_matches if author_matches else 'None'}")
            print(f"  Downloads: {download_count}")
            print(f"  Created: {ds.created_at}")
            print()
    
    print("=" * 80)
