"""Sample data generator for MCP Blueprint industry templates.

This script supports all industries under `industry-templates/<industry>/schema.json`.

- For `healthcare`, `retail`, and `finance`, it uses the existing hand-crafted generators.
- For all other industries, it generates synthetic records from the template's
    `cosmos_db.schema` definition.

Record count defaults to the template configuration:
- `sample_data_size`, or
- `sample_data_config.record_count`
"""

import argparse
import json
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, cast
import uuid
from pathlib import Path


class SampleDataGenerator:
    def __init__(self, industry: str, count: Optional[int] = None):
        self.industry = industry
        self.config = load_industry_config(industry)
        self.count = int(count) if count is not None else get_sample_record_count(self.config)
        self.generated_data: List[Dict[str, Any]] = []
        
    def generate(self) -> List[Dict[str, Any]]:
        """Generate sample data based on industry type"""
        if self.industry == "healthcare":
            return self._generate_healthcare_data()
        elif self.industry == "retail":
            return self._generate_retail_data()
        elif self.industry == "finance":
            return self._generate_finance_data()
        else:
            return self._generate_from_schema()
    
    def _generate_healthcare_data(self) -> List[Dict[str, Any]]:
        """Generate patient records"""
        print(f"Generating {self.count} healthcare patient records...")
        
        first_names = ["John", "Jane", "Michael", "Sarah", "Robert", "Emily", "David", "Jessica", "James", "Emma",
                      "William", "Olivia", "Richard", "Ava", "Joseph", "Sophia", "Thomas", "Isabella", "Charles", "Mia"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                     "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
        blood_types = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
        conditions = ["Diabetes", "Hypertension", "Asthma", "Arthritis", "COPD", "Heart Disease", "Thyroid Disorder"]
        medications = ["Metformin", "Lisinopril", "Atorvastatin", "Amlodipine", "Omeprazole", "Levothyroxine", "Albuterol"]
        allergies = ["Penicillin", "Peanuts", "Latex", "Sulfa drugs", "Shellfish", "None"]
        physicians = ["Dr. Smith", "Dr. Johnson", "Dr. Williams", "Dr. Brown", "Dr. Garcia", "Dr. Martinez"]
        insurance_providers = ["BlueCross BlueShield", "Aetna", "Cigna", "UnitedHealthcare", "Kaiser Permanente", "Humana"]
        cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego"]
        states = ["NY", "CA", "IL", "TX", "AZ", "PA", "TX", "CA"]
        
        data: List[Dict[str, Any]] = []
        for i in range(self.count):
            patient_id = f"PAT-{str(uuid.uuid4())[:8].upper()}"
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            
            # Random date of birth (18-90 years old)
            age_days = random.randint(18*365, 90*365)
            dob = (datetime.now() - timedelta(days=age_days)).strftime("%Y-%m-%d")
            
            # Random last visit (within last year)
            last_visit_days = random.randint(1, 365)
            last_visit = (datetime.now() - timedelta(days=last_visit_days)).strftime("%Y-%m-%d")
            
            city = random.choice(cities)
            state = random.choice(states)
            
            record: Dict[str, Any] = {
                "id": patient_id,  # Required for Cosmos DB
                "patientId": patient_id,
                "firstName": first_name,
                "lastName": last_name,
                "dateOfBirth": dob,
                "gender": random.choice(["Male", "Female"]),
                "bloodType": random.choice(blood_types),
                "allergies": random.sample(allergies, k=random.randint(0, 3)),
                "chronicConditions": random.sample(conditions, k=random.randint(0, 3)),
                "medications": random.sample(medications, k=random.randint(0, 4)),
                "lastVisitDate": last_visit,
                "primaryPhysician": random.choice(physicians),
                "insuranceProvider": random.choice(insurance_providers),
                "contactPhone": f"{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}",
                "address": {
                    "street": f"{random.randint(100,9999)} {random.choice(['Main', 'Oak', 'Elm', 'Maple'])} St",
                    "city": city,
                    "state": state,
                    "zipCode": f"{random.randint(10000,99999)}"
                },
                "emergencyContact": {
                    "name": f"{random.choice(first_names)} {random.choice(last_names)}",
                    "relationship": random.choice(["Spouse", "Parent", "Sibling", "Child", "Friend"]),
                    "phone": f"{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}"
                },
                "medicalHistory": f"Patient history includes routine checkups and treatment for various conditions. Last comprehensive physical exam on {last_visit}.",
                "labResults": [],
                "vaccinations": random.sample(["Flu", "COVID-19", "Tetanus", "Hepatitis B", "MMR"], k=random.randint(2, 5))
            }
            
            data.append(record)
            
            if (i + 1) % 10000 == 0:
                print(f"  Generated {i + 1}/{self.count} records...")
        
        print(f"Generated {len(data)} healthcare records")
        return data
    
    def _generate_retail_data(self) -> List[Dict[str, Any]]:
        """Generate retail transactions"""
        print(f"Generating {self.count} retail transaction records...")
        
        products: List[Dict[str, Any]] = [
            {"name": "Laptop", "category": "Electronics", "price": 999.99},
            {"name": "Smartphone", "category": "Electronics", "price": 699.99},
            {"name": "Tablet", "category": "Electronics", "price": 449.99},
            {"name": "Headphones", "category": "Electronics", "price": 149.99},
            {"name": "Monitor", "category": "Electronics", "price": 299.99},
            {"name": "Running Shoes", "category": "Apparel", "price": 89.99},
            {"name": "T-Shirt", "category": "Apparel", "price": 19.99},
            {"name": "Jeans", "category": "Apparel", "price": 59.99},
            {"name": "Coffee Maker", "category": "Home", "price": 79.99},
            {"name": "Blender", "category": "Home", "price": 49.99},
            {"name": "Vacuum Cleaner", "category": "Home", "price": 199.99},
            {"name": "Desk Chair", "category": "Furniture", "price": 249.99},
            {"name": "Desk Lamp", "category": "Furniture", "price": 39.99},
            {"name": "Book Shelf", "category": "Furniture", "price": 149.99},
        ]
        
        customer_names = ["Alice Johnson", "Bob Smith", "Carol Williams", "David Brown", "Eve Davis", 
                         "Frank Miller", "Grace Wilson", "Henry Moore", "Ivy Taylor", "Jack Anderson"]
        
        stores = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia"]
        channels = ["Online", "In-Store", "Mobile App"]
        payment_methods = ["Credit Card", "Debit Card", "PayPal", "Apple Pay", "Google Pay"]
        statuses = ["Completed", "Pending", "Failed", "Cancelled"]
        promo_codes: List[Optional[str]] = [
            "SAVE10",
            "SAVE20",
            "SUMMER25",
            "WELCOME15",
            None,
            None,
            None,
        ]  # More no-promo transactions
        
        data: List[Dict[str, Any]] = []
        for i in range(self.count):
            customer_id = f"CUST-{random.randint(10000, 99999)}"
            customer_name = random.choice(customer_names)
            customer_email = f"{customer_name.lower().replace(' ', '.')}@email.com"
            
            # Random transaction date (last 6 months)
            trans_days = random.randint(1, 180)
            trans_date = (datetime.now() - timedelta(days=trans_days)).isoformat()
            
            # Random 1-5 items per transaction
            num_items = random.randint(1, 5)
            items: List[Dict[str, Any]] = []
            total_amount: float = 0.0
            
            for _ in range(num_items):
                product: Dict[str, Any] = random.choice(products)
                quantity = random.randint(1, 3)
                discount = random.choice([0, 0, 0, 10, 15, 20])  # Most have no discount
                unit_price = float(product["price"])
                item_total: float = (unit_price * quantity) * (1 - discount / 100)
                total_amount += item_total
                
                items.append({
                    "productId": f"PROD-{random.randint(1000, 9999)}",
                    "productName": product["name"],
                    "category": product["category"],
                    "quantity": quantity,
                    "unitPrice": unit_price,
                    "discount": discount,
                    "sku": f"SKU-{random.randint(100000, 999999)}"
                })
            
            city = random.choice(stores)
            promo = random.choice(promo_codes)
            
            record: Dict[str, Any] = {
                "id": f"TXN-{str(uuid.uuid4())[:8].upper()}",
                "transactionId": f"TXN-{str(uuid.uuid4())[:8].upper()}",
                "customerId": customer_id,
                "customerName": customer_name,
                "customerEmail": customer_email,
                "transactionDate": trans_date,
                "totalAmount": round(total_amount, 2),
                "currency": "USD",
                "paymentMethod": random.choice(payment_methods),
                "status": random.choice(statuses),
                "items": items,
                "shippingAddress": {
                    "street": f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Elm'])} St",
                    "city": city,
                    "state": random.choice(["NY", "CA", "IL", "TX", "AZ", "PA"]),
                    "zipCode": f"{random.randint(10000, 99999)}",
                    "country": "USA"
                },
                "storeLocation": city,
                "salesChannel": random.choice(channels),
                "loyaltyPoints": random.randint(0, 5000),
                "promotionCode": promo
            }
            
            data.append(record)
            
            if (i + 1) % 10000 == 0:
                print(f"  Generated {i + 1}/{self.count} records...")
        
        print(f"Generated {len(data)} retail transaction records")
        return data
    
    def _generate_finance_data(self) -> List[Dict[str, Any]]:
        """Generate financial transactions"""
        print(f"Generating {self.count} financial transaction records...")
        
        transaction_types = ["Deposit", "Withdrawal", "Transfer", "Payment", "Purchase"]
        merchants = ["Amazon", "Walmart", "Target", "Starbucks", "Shell Gas", "McDonald's", "Apple Store", 
                    "Best Buy", "Home Depot", "CVS Pharmacy", "Uber", "Netflix", "Spotify", "Whole Foods"]
        merchant_categories = ["E-commerce", "Retail", "Food & Dining", "Gas & Fuel", "Technology", 
                              "Home Improvement", "Healthcare", "Transportation", "Entertainment", "Groceries"]
        
        cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Seattle", "Boston", "Atlanta"]
        countries = ["USA", "USA", "USA", "USA", "Canada", "UK", "Mexico"]  # Mostly domestic
        
        payment_methods = ["Debit Card", "Credit Card", "ACH Transfer", "Wire Transfer", "Check"]
        
        data: List[Dict[str, Any]] = []
        for i in range(self.count):
            account_id = f"ACC-{random.randint(100000, 999999)}"
            customer_id = f"CUST-{random.randint(10000, 99999)}"
            
            # Random transaction timestamp (last 90 days)
            trans_days = random.randint(0, 90)
            trans_hours = random.randint(0, 23)
            trans_minutes = random.randint(0, 59)
            timestamp = (datetime.now() - timedelta(days=trans_days, hours=trans_hours, minutes=trans_minutes)).isoformat()
            
            trans_type = random.choice(transaction_types)
            amount = round(random.uniform(5.0, 5000.0), 2)
            
            # Larger amounts for certain transaction types
            if trans_type in ["Deposit", "Transfer"]:
                amount = round(random.uniform(100.0, 10000.0), 2)
            
            merchant = random.choice(merchants)
            category = random.choice(merchant_categories)
            city = random.choice(cities)
            country = random.choice(countries)
            is_international = country != "USA"
            
            # Fraud score (most transactions are safe)
            fraud_score = round(random.triangular(0.0, 0.3, 0.1), 2)
            if random.random() < 0.02:  # 2% high-risk transactions
                fraud_score = round(random.uniform(0.7, 0.95), 2)
            
            record: Dict[str, Any] = {
                "id": f"TXN-{str(uuid.uuid4())[:8].upper()}",
                "transactionId": f"TXN-{str(uuid.uuid4())[:8].upper()}",
                "accountId": account_id,
                "customerId": customer_id,
                "customerName": f"Customer {customer_id}",
                "transactionType": trans_type,
                "amount": amount,
                "currency": "USD",
                "timestamp": timestamp,
                "status": random.choice(["Completed", "Completed", "Completed", "Pending", "Declined"]),
                "merchantName": merchant,
                "merchantCategory": category,
                "location": {
                    "city": city,
                    "state": random.choice(["NY", "CA", "IL", "TX", "WA", "MA", "GA"]),
                    "country": country,
                    "coordinates": {
                        "lat": round(random.uniform(25.0, 48.0), 6),
                        "lon": round(random.uniform(-125.0, -70.0), 6)
                    }
                },
                "paymentMethod": random.choice(payment_methods),
                "cardLast4": f"{random.randint(1000, 9999)}",
                "accountBalance": round(random.uniform(1000.0, 50000.0), 2),
                "fraudScore": fraud_score,
                "isInternational": is_international,
                "description": f"{trans_type} at {merchant}",
                "category": category,
                "tags": random.sample(["expense", "income", "recurring", "one-time", "business", "personal"], k=random.randint(1, 3))
            }
            
            data.append(record)
            
            if (i + 1) % 10000 == 0:
                print(f"  Generated {i + 1}/{self.count} records...")
        
        print(f"Generated {len(data)} financial transaction records")
        return data
    
    def save_to_file(self, filename: str):
        """Save generated data to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.generated_data, f, indent=2)
        print(f"Saved data to {filename}")

    def _generate_from_schema(self) -> List[Dict[str, Any]]:
        """Generate records based on the template's Cosmos DB schema."""
        cosmos_db_any = self.config.get("cosmos_db")
        cosmos_db: Dict[str, Any] = cast(Dict[str, Any], cosmos_db_any) if isinstance(cosmos_db_any, dict) else {}

        cosmos_schema_any = cosmos_db.get("schema")
        if not isinstance(cosmos_schema_any, dict):
            raise ValueError(f"Industry '{self.industry}' template missing cosmos_db.schema")

        cosmos_schema: Dict[str, Any] = cast(Dict[str, Any], cosmos_schema_any)

        partition_key_path = str(cosmos_db.get("partition_key", "/id"))
        key_field = partition_key_path.lstrip("/") or "id"

        data: List[Dict[str, Any]] = []
        prefix = _prefix_for_key(key_field)

        print(f"Generating {self.count} {self.industry} records from schema...")
        for i in range(self.count):
            key_value = f"{prefix}{str(uuid.uuid4())[:12].upper()}"
            record = _generate_object_from_schema(cosmos_schema)

            # Ensure a stable id and partition key field exist
            record[key_field] = key_value
            record["id"] = key_value

            data.append(record)

            if (i + 1) % 10000 == 0:
                print(f"  Generated {i + 1}/{self.count} records...")

        print(f"Generated {len(data)} {self.industry} records")
        return data


def repo_root() -> Path:
    return Path(__file__).parent.parent


def list_available_industries() -> List[str]:
    templates_dir = repo_root() / "industry-templates"
    if not templates_dir.exists():
        return ["healthcare", "retail", "finance"]
    industries: List[str] = []
    for industry_dir in templates_dir.iterdir():
        if not industry_dir.is_dir():
            continue
        if (industry_dir / "schema.json").exists():
            industries.append(industry_dir.name)
    return sorted(industries)


def load_industry_config(industry: str) -> Dict[str, Any]:
    config_path = repo_root() / "industry-templates" / industry / "schema.json"
    if not config_path.exists():
        raise ValueError(f"Unknown industry '{industry}'. Expected template at: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_sample_record_count(config: Dict[str, Any], default: int = 100000) -> int:
    if isinstance(config.get("sample_data_size"), int):
        return int(config["sample_data_size"])
    sample_data_config_any = config.get("sample_data_config")
    if isinstance(sample_data_config_any, dict):
        sample_data_config: Dict[str, Any] = cast(Dict[str, Any], sample_data_config_any)
        record_count_any = sample_data_config.get("record_count")
        if isinstance(record_count_any, int):
            return int(record_count_any)
    return default


def _prefix_for_key(key_field: str) -> str:
    cleaned = "".join([c for c in key_field if c.isalnum()]).upper()
    if not cleaned:
        return "ID-"
    return f"{cleaned[:6]}-"


def _generate_object_from_schema(schema_obj: Dict[str, Any], *, depth: int = 0) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for field_name, field_schema in schema_obj.items():
        result[field_name] = _generate_value(field_name, field_schema, depth=depth)
    return result


def _generate_value(field_name: str, field_schema: Any, *, depth: int) -> Any:
    # Prevent runaway nesting
    if depth > 5:
        return None

    if isinstance(field_schema, dict):
        return _generate_object_from_schema(cast(Dict[str, Any], field_schema), depth=depth + 1)

    if field_schema == "string":
        lowered = field_name.lower()
        if "date" in lowered and "update" not in lowered:
            days_ago = random.randint(0, 365 * 5)
            return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        if "time" in lowered or "timestamp" in lowered:
            days_ago = random.randint(0, 365)
            seconds = random.randint(0, 86400)
            return (datetime.now() - timedelta(days=days_ago, seconds=seconds)).isoformat()
        if "email" in lowered:
            return f"user{random.randint(10000, 99999)}@example.com"
        if lowered.endswith("id"):
            return f"{_prefix_for_key(field_name)}{str(uuid.uuid4())[:12].upper()}"
        if "status" in lowered:
            return random.choice(["Active", "Pending", "Closed", "Completed", "In Progress"]) 
        if "state" == lowered:
            return random.choice(["CA", "NY", "TX", "WA", "MA", "IL", "AZ", "PA"])
        if "city" == lowered:
            return random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Seattle", "Boston"])
        return f"{field_name}-{random.randint(1000, 9999)}"

    if field_schema == "number":
        lowered = field_name.lower()
        if "score" in lowered or "rate" in lowered or "efficiency" in lowered:
            return round(random.uniform(0.0, 1.0), 2)
        if "amount" in lowered or "balance" in lowered or "price" in lowered or "cost" in lowered:
            return round(random.uniform(10.0, 10000.0), 2)
        if "rpm" in lowered:
            return random.randint(500, 6000)
        if "temperature" in lowered:
            return round(random.uniform(40.0, 120.0), 1)
        if "pressure" in lowered:
            return round(random.uniform(10.0, 250.0), 1)
        if "floor" in lowered:
            return random.randint(1, 10)
        return round(random.uniform(0.0, 100.0), 2)

    if field_schema == "array":
        # Schema doesn't specify element types; default to strings
        sample_pool = [
            "note", "alert", "document", "tag", "item", "event",
            "high-priority", "low-priority", "review", "approved"
        ]
        length = random.randint(0, 5)
        return random.sample(sample_pool, k=length)

    # Unknown schema type: return None
    return None


def main():
    """Generate sample data for all industries."""
    industries = list_available_industries()
    
    for industry in industries:
        print(f"\n{'='*60}")
        print(f"Generating data for: {industry.upper()}")
        print(f"{'='*60}")
        
        generator = SampleDataGenerator(industry, count=None)
        data = generator.generate()
        generator.generated_data = data
        
        output_file = f"sample-data-{industry}.json"
        generator.save_to_file(output_file)
        
        print(f"\nCompleted {industry} - {len(data)} records")
    
    print(f"\n{'='*60}")
    print("All sample data generated successfully!")
    print(f"{'='*60}")


if __name__ == "__main__":
    available_industries = list_available_industries()
    parser = argparse.ArgumentParser(description="Generate sample data for the selected MCP Blueprint industry")
    parser.add_argument(
        "--industry",
        type=str,
        required=True,
        choices=available_industries,
        help="Industry template to generate data for",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Number of records to generate (defaults to template sample size)",
    )
    
    args = parser.parse_args()
    
    generator = SampleDataGenerator(args.industry, count=args.count)
    print(f"\n{'='*60}")
    print(f"Generating {generator.count} records for: {args.industry.upper()}")
    print(f"{'='*60}\n")
    data = generator.generate()
    
    output_file = f"sample-data-{args.industry}.json"
    generator.save_to_file(output_file)
    
    print(f"\n{'='*60}")
    print(f"Generated {len(data)} {args.industry} records")
    print(f"   Saved to: {output_file}")
    print(f"{'='*60}\n")
