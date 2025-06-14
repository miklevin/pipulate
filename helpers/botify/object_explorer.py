# helpers/botify/object_explorer.py
import os
import json
import httpx
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set
import asyncio

# --- Configuration ---
TOKEN_FILE = 'botify_token.txt'
# Ensure the config file is in the same directory as this script for consistency
CONFIG_FILE = Path(__file__).parent / 'config.json'

class BotifySchemaExplorer:
    """Comprehensive Botify API schema discovery tool."""
    
    def __init__(self, org: str, project: str, analysis: str, api_key: str):
        self.org = org
        self.project = project
        self.analysis = analysis
        self.api_key = api_key
        self.headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
        self.base_url = f"https://api.botify.com/v1/projects/{org}/{project}"
        self.crawl_collection = f"crawl.{analysis}"
        
        # Schema discovery results
        self.discovered_collections = set()
        self.collection_schemas = {}
        self.field_test_results = {}
        
    async def discover_complete_schema(self) -> Dict[str, Any]:
        """Comprehensive schema discovery for the Botify project."""
        print("🔍 Starting comprehensive Botify API schema discovery...")
        print(f"📊 Project: {self.org}/{self.project}")
        print(f"📅 Analysis: {self.analysis}")
        
        schema_inventory = {
            "project_info": {
                "org": self.org,
                "project": self.project,
                "analysis": self.analysis,
                "discovery_timestamp": datetime.now().isoformat()
            },
            "collections": {},
            "field_discovery_log": [],
            "summary": {}
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: Discover available collections
            await self._discover_collections(client, schema_inventory)
            
            # Step 2: Explore each collection's schema
            for collection in self.discovered_collections:
                print(f"\n🔬 Exploring schema for collection: {collection}")
                await self._explore_collection_schema(client, collection, schema_inventory)
            
            # Step 3: Test integration patterns
            await self._test_collection_integrations(client, schema_inventory)
            
            # Step 4: Generate summary
            self._generate_schema_summary(schema_inventory)
        
        return schema_inventory
    
    async def _discover_collections(self, client: httpx.AsyncClient, inventory: Dict):
        """Discover what collections are available."""
        print("\n📋 Phase 1: Collection Discovery")
        
        # Standard collections we know about
        known_collections = [
            self.crawl_collection,
            "search_console", 
            "google_analytics",
            "segments",
            "keywords"
        ]
        
        for collection in known_collections:
            exists = await self._test_collection_exists(client, collection)
            if exists:
                self.discovered_collections.add(collection)
                print(f"  ✅ {collection}")
                inventory["collections"][collection] = {"exists": True, "fields": {}}
            else:
                print(f"  ❌ {collection}")
                inventory["field_discovery_log"].append({
                    "collection": collection,
                    "status": "not_available",
                    "timestamp": datetime.now().isoformat()
                })
    
    async def _test_collection_exists(self, client: httpx.AsyncClient, collection: str) -> bool:
        """Test if a collection exists by trying a minimal query."""
        try:
            # For crawl collections, we need the full collection name
            if collection.startswith("crawl."):
                dimensions = [f"{collection}.url"]
            else:
                # For other collections, try standard fields
                dimensions = []
            
            query = {
                "collections": [collection],
                "query": {
                    "dimensions": dimensions,
                    "metrics": []
                }
            }
            
            # Add periods for time-based collections
            if collection in ["search_console", "google_analytics"]:
                analysis_date = datetime.strptime(self.analysis, '%Y%m%d')
                period_start = (analysis_date - timedelta(days=7)).strftime('%Y-%m-%d')
                period_end = analysis_date.strftime('%Y-%m-%d')
                query["periods"] = [[period_start, period_end]]
            
            response = await client.post(f"{self.base_url}/query", headers=self.headers, json=query)
            return response.status_code == 200
            
        except Exception:
            return False
    
    async def _explore_collection_schema(self, client: httpx.AsyncClient, collection: str, inventory: Dict):
        """Systematically explore a collection's field schema."""
        
        # Field discovery strategies based on collection type
        if collection.startswith("crawl."):
            await self._explore_crawl_schema(client, collection, inventory)
        elif collection == "search_console":
            await self._explore_gsc_schema(client, collection, inventory)
        elif collection == "google_analytics":
            await self._explore_ga_schema(client, collection, inventory)
        else:
            await self._explore_generic_schema(client, collection, inventory)
    
    async def _explore_crawl_schema(self, client: httpx.AsyncClient, collection: str, inventory: Dict):
        """Explore crawl collection schema with systematic field testing."""
        
        # Comprehensive field categories for crawl data
        field_categories = {
            "Basic Info": [
                "url", "domain", "subdomain", "path", "query", "fragment",
                "url_hash", "url_length"
            ],
            "HTTP & Response": [
                "http_code", "status", "status_code", "redirect_type", 
                "redirect_target", "response_time", "content_type", "content_length"
            ],
            "Compliance & Crawling": [
                "compliant.is_compliant", "compliant.main_reason", "compliant.detailed_reason",
                "compliant.rules", "crawl_status", "depth", "visits"
            ],
            "Internal Linking": [
                "inlinks_internal.nb.total", "inlinks_internal.nb.follow", 
                "inlinks_internal.nb.nofollow", "inlinks_internal.nb.unique",
                "outlinks_internal.nb.total", "outlinks_internal.nb.follow"
            ],
            "External Linking": [
                "inlinks_external.nb.total", "outlinks_external.nb.total",
                "inlinks_external.nb.follow", "outlinks_external.nb.nofollow"
            ],
            "Content Analysis": [
                "content.body.word_count", "content.body.text_ratio", 
                "content.body.size", "content.images.nb.total",
                "content.images.nb.internal", "content.images.nb.external"
            ],
            "Metadata": [
                "metadata.title.content", "metadata.title.len", "metadata.title.quality",
                "metadata.description.content", "metadata.description.len",
                "metadata.h1.contents", "metadata.h2.contents", "metadata.h3.contents",
                "metadata.canonical", "metadata.lang", "metadata.hreflang"
            ],
            "Performance": [
                "performance.first_byte", "performance.load_time", 
                "performance.total_time", "performance.size.html",
                "performance.size.css", "performance.size.js", "performance.size.images"
            ],
            "Sitemaps & Structure": [
                "sitemaps.present", "sitemaps.indexed", "breadcrumb.depth",
                "segments.pagetype.depth_1", "segments.pagetype.depth_2"
            ],
            "Technical SEO": [
                "robots.txt.allowed", "meta_robots.index", "meta_robots.follow",
                "schema.org.present", "open_graph.present", "twitter_card.present"
            ]
        }
        
        collection_schema = inventory["collections"][collection]
        
        for category, fields in field_categories.items():
            print(f"  📁 Testing {category} fields...")
            
            # Test fields in small batches
            for i in range(0, len(fields), 3):
                batch = fields[i:i+3]
                await self._test_field_batch(client, collection, batch, category, inventory)
    
    async def _test_field_batch(self, client: httpx.AsyncClient, collection: str, fields: List[str], 
                               category: str, inventory: Dict):
        """Test a batch of fields for existence."""
        
        # Build query with full collection prefixes
        dimensions = [f"{collection}.{field}" for field in fields]
        
        query = {
            "collections": [collection],
            "query": {
                "dimensions": dimensions,
                "metrics": []
            }
        }
        
        try:
            response = await client.post(f"{self.base_url}/query", headers=self.headers, json=query)
            
            if response.status_code == 200:
                # All fields in batch work
                for field in fields:
                    full_field = f"{collection}.{field}"
                    inventory["collections"][collection]["fields"][field] = {
                        "status": "available",
                        "category": category,
                        "full_name": full_field
                    }
                    print(f"    ✅ {field}")
            else:
                # Test individually to identify which fail
                for field in fields:
                    await self._test_individual_field(client, collection, field, category, inventory)
                    
        except Exception as e:
            # Test individually on exception
            for field in fields:
                await self._test_individual_field(client, collection, field, category, inventory)
    
    async def _test_individual_field(self, client: httpx.AsyncClient, collection: str, 
                                   field: str, category: str, inventory: Dict):
        """Test a single field for existence."""
        
        query = {
            "collections": [collection],
            "query": {
                "dimensions": [f"{collection}.{field}"],
                "metrics": []
            }
        }
        
        try:
            response = await client.post(f"{self.base_url}/query", headers=self.headers, json=query)
            
            if response.status_code == 200:
                inventory["collections"][collection]["fields"][field] = {
                    "status": "available",
                    "category": category,
                    "full_name": f"{collection}.{field}"
                }
                print(f"    ✅ {field}")
            else:
                error_msg = "unknown"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "unknown")
                except:
                    pass
                
                inventory["collections"][collection]["fields"][field] = {
                    "status": "not_available",
                    "category": category,
                    "error": error_msg,
                    "http_status": response.status_code
                }
                print(f"    ❌ {field} - {error_msg}")
                
        except Exception as e:
            inventory["collections"][collection]["fields"][field] = {
                "status": "error",
                "category": category,
                "error": str(e)
            }
            print(f"    ❓ {field} - {str(e)}")
    
    async def _explore_gsc_schema(self, client: httpx.AsyncClient, collection: str, inventory: Dict):
        """Explore Google Search Console schema."""
        print(f"  🔍 Exploring GSC metrics...")
        
        gsc_metrics = [
            "search_console.period_0.count_impressions",
            "search_console.period_0.count_clicks", 
            "search_console.period_0.ctr",
            "search_console.period_0.avg_position",
            "search_console.period_0.count_queries",
            "search_console.period_0.count_pages"
        ]
        
        # Test GSC integration with crawl data
        try:
            analysis_date = datetime.strptime(self.analysis, '%Y%m%d')
            period_start = (analysis_date - timedelta(days=30)).strftime('%Y-%m-%d')
            period_end = analysis_date.strftime('%Y-%m-%d')
            
            query = {
                "collections": [self.crawl_collection, collection],
                "query": {
                    "dimensions": [f"{self.crawl_collection}.url"],
                    "metrics": gsc_metrics
                },
                "periods": [[period_start, period_end]]
            }
            
            response = await client.post(f"{self.base_url}/query", headers=self.headers, json=query)
            
            if response.status_code == 200:
                for metric in gsc_metrics:
                    base_metric = metric.split('.')[-1]  # e.g., "count_impressions"
                    inventory["collections"][collection]["fields"][base_metric] = {
                        "status": "available",
                        "category": "GSC Metrics",
                        "full_name": metric
                    }
                    print(f"    ✅ {base_metric}")
            else:
                print(f"    ❌ GSC integration failed: {response.status_code}")
                
        except Exception as e:
            print(f"    ❓ GSC exploration error: {e}")
    
    async def _explore_ga_schema(self, client: httpx.AsyncClient, collection: str, inventory: Dict):
        """Explore Google Analytics schema if available."""
        print(f"  📊 Exploring Google Analytics...")
        
        # Common GA metrics to test
        ga_metrics = [
            "google_analytics.period_0.sessions",
            "google_analytics.period_0.users", 
            "google_analytics.period_0.pageviews",
            "google_analytics.period_0.bounce_rate",
            "google_analytics.period_0.avg_session_duration"
        ]
        
        # Similar approach to GSC but for GA
        # Implementation would follow similar pattern
        inventory["collections"][collection]["fields"]["note"] = {
            "status": "schema_discovery_needed",
            "category": "Analytics",
            "note": "GA schema exploration needs specific implementation"
        }
    
    async def _explore_generic_schema(self, client: httpx.AsyncClient, collection: str, inventory: Dict):
        """Generic schema exploration for unknown collections."""
        print(f"  🔬 Generic exploration for {collection}...")
        
        # Try basic queries to understand collection structure
        inventory["collections"][collection]["fields"]["exploration_needed"] = {
            "status": "manual_exploration_required",
            "category": "Unknown",
            "note": f"Collection {collection} needs manual schema discovery"
        }
    
    async def _test_collection_integrations(self, client: httpx.AsyncClient, inventory: Dict):
        """Test how collections can be joined together."""
        print(f"\n🔗 Phase 3: Testing Collection Integrations")
        
        integrations = []
        
        # Test crawl + GSC integration
        if self.crawl_collection in self.discovered_collections and "search_console" in self.discovered_collections:
            integration_result = await self._test_crawl_gsc_integration(client)
            integrations.append({
                "collections": [self.crawl_collection, "search_console"],
                "status": "available" if integration_result else "failed",
                "note": "Crawl data with Search Console metrics"
            })
        
        inventory["collection_integrations"] = integrations
    
    async def _test_crawl_gsc_integration(self, client: httpx.AsyncClient) -> bool:
        """Test if crawl and GSC data can be joined."""
        try:
            analysis_date = datetime.strptime(self.analysis, '%Y%m%d')
            period_start = (analysis_date - timedelta(days=7)).strftime('%Y-%m-%d')
            period_end = analysis_date.strftime('%Y-%m-%d')
            
            query = {
                "collections": [self.crawl_collection, "search_console"],
                "query": {
                    "dimensions": [f"{self.crawl_collection}.url"],
                    "metrics": ["search_console.period_0.count_impressions"]
                },
                "periods": [[period_start, period_end]]
            }
            
            response = await client.post(f"{self.base_url}/query", headers=self.headers, json=query)
            return response.status_code == 200
            
        except Exception:
            return False
    
    def _generate_schema_summary(self, inventory: Dict):
        """Generate summary statistics for the schema discovery."""
        summary = {
            "total_collections": len(inventory["collections"]),
            "available_collections": len([c for c in inventory["collections"].values() if c.get("exists", False)]),
            "total_fields_tested": 0,
            "available_fields": 0,
            "fields_by_category": {}
        }
        
        for collection_name, collection_data in inventory["collections"].items():
            if "fields" in collection_data:
                for field_name, field_data in collection_data["fields"].items():
                    summary["total_fields_tested"] += 1
                    
                    if field_data.get("status") == "available":
                        summary["available_fields"] += 1
                        
                        category = field_data.get("category", "Uncategorized")
                        if category not in summary["fields_by_category"]:
                            summary["fields_by_category"][category] = 0
                        summary["fields_by_category"][category] += 1
        
        inventory["summary"] = summary
        
        print(f"\n📊 Schema Discovery Summary:")
        print(f"  Collections Available: {summary['available_collections']}/{summary['total_collections']}")
        print(f"  Fields Available: {summary['available_fields']}/{summary['total_fields_tested']}")
        print(f"  Categories Found: {len(summary['fields_by_category'])}")

async def main():
    """Main function to run comprehensive schema discovery."""
    try:
        # Load configuration
        api_key = open(TOKEN_FILE).read().strip().splitlines()[0]
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        org, project, analysis = config['org'], config['project'], config['analysis']
        
        # Create explorer instance
        explorer = BotifySchemaExplorer(org, project, analysis, api_key)
        
        # Discover complete schema
        schema_inventory = await explorer.discover_complete_schema()
        
        # Save comprehensive results in current directory
        # Save detailed JSON schema
        schema_file = Path(f"{project}_{analysis}_complete_schema.json")
        with open(schema_file, 'w') as f:
            json.dump(schema_inventory, f, indent=2, default=str)
        
        print(f"\n✅ Complete schema inventory saved to:")
        print(f"   {schema_file.resolve()}")
        
        # Save available fields CSV for easy browsing
        available_fields = []
        for collection_name, collection_data in schema_inventory["collections"].items():
            if "fields" in collection_data:
                for field_name, field_data in collection_data["fields"].items():
                    if field_data.get("status") == "available":
                        available_fields.append({
                            "collection": collection_name,
                            "field": field_name,
                            "full_name": field_data.get("full_name"),
                            "category": field_data.get("category")
                        })
        
        if available_fields:
            df = pd.DataFrame(available_fields)
            csv_file = Path(f"{project}_{analysis}_available_fields.csv")
            df.to_csv(csv_file, index=False)
            print(f"   {csv_file.resolve()}")
            
            print(f"\n📋 Available Fields by Collection:")
            for collection in df['collection'].unique():
                count = len(df[df['collection'] == collection])
                print(f"   {collection}: {count} fields")
        
    except Exception as e:
        print(f"❌ Schema discovery failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())