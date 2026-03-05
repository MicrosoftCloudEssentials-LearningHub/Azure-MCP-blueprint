#!/usr/bin/env python3
"""
Upload industry sample data to Azure Cosmos DB and Azure AI Search
Generates and uploads sample records for the selected industry

Record count defaults to the template configuration:
- `sample_data_size`, or
- `sample_data_config.record_count`
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, cast
from azure.cosmos import CosmosClient, PartitionKey
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField as _SimpleField,  # pyright: ignore[reportUnknownVariableType]
    SearchableField as _SearchableField,  # pyright: ignore[reportUnknownVariableType]
)
from azure.identity import DefaultAzureCredential
from generate_sample_data import SampleDataGenerator

SimpleField: Any = _SimpleField  # pyright: ignore[reportUnknownVariableType]
SearchableField: Any = _SearchableField  # pyright: ignore[reportUnknownVariableType]


def get_sample_record_count(config: dict[str, Any], default: int = 100000) -> int:
    if isinstance(config.get("sample_data_size"), int):
        return int(config["sample_data_size"])
    sample_data_config_any = config.get("sample_data_config")
    if isinstance(sample_data_config_any, dict):
        sample_data_config: dict[str, Any] = cast(dict[str, Any], sample_data_config_any)
        record_count_any = sample_data_config.get("record_count")
        if isinstance(record_count_any, int):
            return int(record_count_any)
    return default

def get_industry_config(industry: str) -> dict[str, Any]:
    """Load industry template configuration"""
    config_path = Path(__file__).parent.parent / "industry-templates" / industry / "schema.json"
    with open(config_path, 'r') as f:
        return json.load(f)

def create_search_index(search_endpoint: str, index_config: dict[str, Any], credential: Any):
    """Create Azure AI Search index based on industry schema"""
    print(f"\nCreating search index: {index_config['name']}")
    
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
    
    fields: list[Any] = []
    for field_def in index_config['fields']:
        if field_def.get('key'):
            fields.append(SimpleField(
                name=field_def['name'],
                type=field_def['type'],
                key=True
            ))
        elif field_def.get('searchable'):
            fields.append(SearchableField(
                name=field_def['name'],
                type=field_def['type'],
                searchable=field_def.get('searchable', False),
                filterable=field_def.get('filterable', False),
                sortable=field_def.get('sortable', False),
                facetable=field_def.get('facetable', False)
            ))
        else:
            fields.append(SimpleField(
                name=field_def['name'],
                type=field_def['type'],
                filterable=field_def.get('filterable', False),
                sortable=field_def.get('sortable', False),
                facetable=field_def.get('facetable', False)
            ))
    
    index = SearchIndex(name=index_config['name'], fields=fields)
    
    try:
        result = index_client.create_or_update_index(index)
        print(f"Search index created: {result.name}")
        return result
    except Exception as e:
        print(f"Failed to create search index: {e}")
        return None

def upload_to_cosmos(
    cosmos_endpoint: str,
    cosmos_key: str,
    db_config: dict[str, Any],
    data: list[dict[str, Any]],
) -> bool:
    """Upload data to Cosmos DB"""
    print(f"\nUploading to Cosmos DB...")
    print(f"  Database: {db_config['database']}")
    print(f"  Container: {db_config['container']}")
    
    client = CosmosClient(cosmos_endpoint, cosmos_key)
    
    # Create database if it doesn't exist
    try:
        database = client.create_database_if_not_exists(id=db_config['database'])
        print(f"Database ready: {db_config['database']}")
    except Exception as e:
        print(f"Database creation failed: {e}")
        return False
    
    # Create container if it doesn't exist
    try:
        container = database.create_container_if_not_exists(
            id=db_config['container'],
            partition_key=PartitionKey(path=db_config['partition_key']),
            offer_throughput=4000
        )
        print(f"Container ready: {db_config['container']}")
    except Exception as e:
        print(f"Container creation failed: {e}")
        return False
    
    # Upload data in batches
    batch_size = 100
    total = len(data)
    success_count = 0
    
    for i in range(0, total, batch_size):
        batch = data[i:i + batch_size]
        for item in batch:
            try:
                container.upsert_item(item)
                success_count += 1
            except Exception as e:
                print(f"Warning: Failed to upload item: {e}")
        
        if (i + batch_size) % 1000 == 0 or (i + batch_size) >= total:
            print(f"  Progress: {min(i + batch_size, total)}/{total} records...")
    
    print(f"Uploaded {success_count}/{total} records to Cosmos DB")
    return success_count == total

def upload_to_search(
    search_endpoint: str,
    index_name: str,
    data: list[dict[str, Any]],
    credential: Any,
) -> bool:
    """Upload data to Azure AI Search"""
    print(f"\nUploading to Azure AI Search index: {index_name}")
    
    search_client: Any = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
    
    # Prepare documents for search (flatten structure if needed)
    search_docs: list[dict[str, Any]] = []
    for item in data:
        # Create search document (may need transformation based on index schema)
        search_doc: dict[str, Any] = {
            k: v for k, v in item.items() 
            if not isinstance(v, (dict, list)) or k in ['id']
        }
        search_docs.append(search_doc)
    
    # Upload in batches
    batch_size = 1000
    total = len(search_docs)
    success_count = 0
    
    for i in range(0, total, batch_size):
        batch = search_docs[i:i + batch_size]
        try:
            result = search_client.upload_documents(documents=batch)
            success_count += len([r for r in result if r.succeeded])
            
            if (i + batch_size) % 5000 == 0 or (i + batch_size) >= total:
                print(f"  Progress: {min(i + batch_size, total)}/{total} documents...")
        except Exception as e:
            print(f"Warning: Batch upload failed: {e}")
    
    print(f"Uploaded {success_count}/{total} documents to Search")
    return success_count == total

def main():
    """Main upload process"""
    # Get configuration from environment or arguments
    industry = os.environ.get("SELECTED_INDUSTRY") or os.environ.get("INDUSTRY") or "healthcare"
    cosmos_endpoint = os.environ.get("COSMOS_ENDPOINT")
    cosmos_key = os.environ.get("COSMOS_KEY")
    search_endpoint = os.environ.get("SEARCH_ENDPOINT")
    search_key = os.environ.get("SEARCH_KEY")
    
    if cosmos_endpoint is None or cosmos_key is None or search_endpoint is None:
        print("Missing required environment variables:")
        print("  - COSMOS_ENDPOINT")
        print("  - COSMOS_KEY")
        print("  - SEARCH_ENDPOINT")
        sys.exit(1)
    
    print(f"\n{'='*70}")
    print(f"UPLOADING SAMPLE DATA FOR: {industry.upper()}")
    print(f"{'='*70}")
    
    # Load industry configuration
    config = get_industry_config(industry)
    print(f"\nConfiguration loaded:")
    print(f"  Industry: {config['display_name']}")
    print(f"  Database: {config['cosmos_db']['database']}")
    print(f"  Container: {config['cosmos_db']['container']}")
    print(f"  Search Index: {config['search_index']['name']}")
    record_count = get_sample_record_count(config)
    print(f"  Sample Size: {record_count:,} records")
    
    # Generate sample data
    print(f"\nGenerating sample data...")
    generator = SampleDataGenerator(industry, count=record_count)
    data = generator.generate()
    
    # Save to file for backup
    backup_file = f"sample-data-{industry}-{len(data)}.json"
    print(f"\nSaving backup to: {backup_file}")
    with open(backup_file, 'w') as f:
        json.dump(data, f)
    
    # Create search index
    # Prefer key-based auth if provided; fall back to AAD.
    credential = AzureKeyCredential(search_key) if search_key else DefaultAzureCredential()
    _ = create_search_index(search_endpoint, config['search_index'], credential)
    
    # Upload to Cosmos DB
    cosmos_success = upload_to_cosmos(
        cosmos_endpoint,
        cosmos_key,
        config['cosmos_db'],
        data
    )
    
    # Upload to Azure AI Search
    search_success = upload_to_search(
        search_endpoint,
        config['search_index']['name'],
        data,
        credential
    )
    
    # Summary
    print(f"\n{'='*70}")
    print(f"UPLOAD SUMMARY")
    print(f"{'='*70}")
    print(f"  Industry: {config['display_name']}")
    print(f"  Records Generated: {len(data):,}")
    print(f"  Cosmos DB Upload: {'Success' if cosmos_success else 'Failed'}")
    print(f"  Search Index Upload: {'Success' if search_success else 'Failed'}")
    print(f"  Backup File: {backup_file}")
    print(f"{'='*70}")
    
    if cosmos_success and search_success:
        print("\nSample data upload completed successfully!")
        return 0
    else:
        print("\nUpload completed with errors. Check logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
