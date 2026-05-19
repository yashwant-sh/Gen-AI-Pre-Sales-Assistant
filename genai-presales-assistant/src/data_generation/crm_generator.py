"""
Synthetic CRM Data Generator

Generates realistic synthetic CRM data including customers, deals, activities, and products
using LLM-powered data generation with proper constraints and business logic.
"""

import csv
import json
import os
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
from loguru import logger


class CRMDataGenerator:
    """Generates synthetic CRM data using LLM and business rules"""
    
    def __init__(self, llm_client=None):
        """Initialize the CRM data generator"""
        self.llm_client = llm_client
        self.industries = [
            "Technology", "Healthcare", "Finance", "Manufacturing", 
            "Retail", "Education", "Government", "Real Estate",
            "Energy", "Transportation", "Media", "Consulting"
        ]
        
        self.company_sizes = [
            "Startup (1-10)", "Small (11-50)", "Medium (51-200)", 
            "Large (201-1000)", "Enterprise (1000+)"
        ]
        
        self.product_categories = [
            "Software Licenses", "Cloud Services", "Hardware", 
            "Consulting", "Support & Maintenance", "Training"
        ]
        
        self.deal_stages = [
            "Prospecting", "Qualification", "Needs Analysis", 
            "Value Proposition", "Proposal", "Negotiation", 
            "Closed Won", "Closed Lost"
        ]
        
        self.activity_types = [
            "Call", "Email", "Meeting", "Demo", "Proposal Sent", 
            "Follow-up", "Site Visit", "Contract Review"
        ]
    
    def generate_customers(self, num_customers: int = 100) -> List[Dict[str, Any]]:
        """Generate synthetic customer data"""
        logger.info(f"Generating {num_customers} synthetic customers")
        
        customers = []
        for i in range(num_customers):
            customer = {
                "customer_id": f"CUST_{i+1:04d}",
                "company_name": self._generate_company_name(),
                "industry": random.choice(self.industries),
                "company_size": random.choice(self.company_sizes),
                "website": f"www.example{i+1}.com",
                "phone": f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                "email": f"contact@company{i+1}.com",
                "address": f"{random.randint(100, 999)} Main St, City {random.randint(1, 50)}, State {random.randint(1, 50)}",
                "created_date": (datetime.now() - timedelta(days=random.randint(365, 1095))).strftime("%Y-%m-%d"),
                "last_contact_date": (datetime.now() - timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d"),
                "account_owner": f"Sales Rep {random.randint(1, 10)}",
                "annual_revenue": random.choice([
                    random.randint(100000, 1000000),  # Small
                    random.randint(1000000, 10000000),  # Medium
                    random.randint(10000000, 100000000),  # Large
                    random.randint(100000000, 1000000000)  # Enterprise
                ])
            }
            customers.append(customer)
        
        return customers
    
    def generate_products(self, num_products: int = 50) -> List[Dict[str, Any]]:
        """Generate synthetic product data"""
        logger.info(f"Generating {num_products} synthetic products")
        
        products = []
        for i in range(num_products):
            category = random.choice(self.product_categories)
            product = {
                "product_id": f"PROD_{i+1:04d}",
                "product_name": self._generate_product_name(category),
                "category": category,
                "description": f"High-quality {category.lower()} solution for enterprise needs",
                "unit_price": round(random.uniform(100, 50000), 2),
                "cost": round(random.uniform(50, 25000), 2),
                "margin_percent": round(random.uniform(20, 60), 2),
                "created_date": (datetime.now() - timedelta(days=random.randint(180, 730))).strftime("%Y-%m-%d"),
                "is_active": random.choice([True, True, True, False])  # 75% active
            }
            products.append(product)
        
        return products
    
    def generate_deals(self, customers: List[Dict], products: List[Dict], num_deals: int = 200) -> List[Dict[str, Any]]:
        """Generate synthetic deal data"""
        logger.info(f"Generating {num_deals} synthetic deals")
        
        deals = []
        for i in range(num_deals):
            customer = random.choice(customers)
            stage = random.choice(self.deal_stages)
            
            # Calculate deal value based on products
            num_products_in_deal = random.randint(1, 4)
            deal_products = random.sample(products, min(num_products_in_deal, len(products)))
            deal_value = sum(product["unit_price"] * random.randint(1, 10) for product in deal_products)
            
            # Set probability of closing based on stage
            close_probability = {
                "Prospecting": 0.1, "Qualification": 0.2, "Needs Analysis": 0.3,
                "Value Proposition": 0.4, "Proposal": 0.6, "Negotiation": 0.8,
                "Closed Won": 1.0, "Closed Lost": 0.0
            }
            
            deal = {
                "deal_id": f"DEAL_{i+1:04d}",
                "customer_id": customer["customer_id"],
                "deal_name": f"{customer['company_name']} - {random.choice(['Software', 'Hardware', 'Services'])} Deal",
                "stage": stage,
                "value": round(deal_value, 2),
                "currency": "USD",
                "probability": close_probability[stage] * 100,
                "expected_close_date": (datetime.now() + timedelta(days=random.randint(30, 180))).strftime("%Y-%m-%d"),
                "created_date": (datetime.now() - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d"),
                "last_modified_date": (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d"),
                "deal_owner": customer["account_owner"],
                "description": f"Strategic partnership with {customer['company_name']} for {random.choice(['digital transformation', 'cloud migration', 'process optimization', 'cost reduction'])}"
            }
            
            # Add actual close date for closed deals
            if stage in ["Closed Won", "Closed Lost"]:
                deal["actual_close_date"] = (datetime.now() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d")
            
            deals.append(deal)
        
        return deals
    
    def generate_activities(self, customers: List[Dict], deals: List[Dict], num_activities: int = 500) -> List[Dict[str, Any]]:
        """Generate synthetic activity data"""
        logger.info(f"Generating {num_activities} synthetic activities")
        
        activities = []
        for i in range(num_activities):
            customer = random.choice(customers)
            deal = random.choice(deals)
            activity_type = random.choice(self.activity_types)
            
            activity = {
                "activity_id": f"ACT_{i+1:04d}",
                "customer_id": customer["customer_id"],
                "deal_id": deal["deal_id"],
                "activity_type": activity_type,
                "subject": f"{activity_type} with {customer['company_name']}",
                "description": self._generate_activity_description(activity_type, customer["company_name"]),
                "activity_date": (datetime.now() - timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d"),
                "duration_minutes": random.choice([15, 30, 45, 60, 90, 120]),
                "owner": customer["account_owner"],
                "outcome": random.choice(["Positive", "Neutral", "Negative", "Follow-up Required"])
            }
            activities.append(activity)
        
        return activities
    
    def _generate_company_name(self) -> str:
        """Generate realistic company names"""
        prefixes = ["Tech", "Digital", "Global", "Advanced", "Innovate", "Smart", "Next", "Future"]
        suffixes = ["Solutions", "Systems", "Technologies", "Innovations", "Dynamics", "Labs", "Works", "Corp"]
        
        return f"{random.choice(prefixes)} {random.choice(suffixes)}"
    
    def _generate_product_name(self, category: str) -> str:
        """Generate realistic product names based on category"""
        product_names = {
            "Software Licenses": ["Enterprise Suite", "Professional Edition", "Cloud Platform", "Analytics Pro"],
            "Cloud Services": ["Cloud Storage", "Compute Instance", "Managed Database", "CDN Service"],
            "Hardware": ["Server Rack", "Workstation", "Network Switch", "Storage Array"],
            "Consulting": ["Strategy Consulting", "Implementation Service", "Optimization Package", "Migration Service"],
            "Support & Maintenance": ["Premium Support", "24/7 Monitoring", "Maintenance Contract", "SLA Guarantee"],
            "Training": ["Technical Training", "Certification Program", "On-site Workshop", "Online Course"]
        }
        
        return random.choice(product_names.get(category, ["Generic Product"]))
    
    def _generate_activity_description(self, activity_type: str, company_name: str) -> str:
        """Generate realistic activity descriptions"""
        descriptions = {
            "Call": f"Initial discovery call with {company_name} to understand their requirements",
            "Email": f"Follow-up email sent to {company_name} with proposal details",
            "Meeting": f"Product demonstration meeting with {company_name} stakeholders",
            "Demo": f"Live demo session for {company_name} showcasing key features",
            "Proposal Sent": f"Formal proposal submitted to {company_name} for review",
            "Follow-up": f"Follow-up discussion with {company_name} regarding feedback",
            "Site Visit": f"On-site visit to {company_name} for technical assessment",
            "Contract Review": f"Contract terms review with {company_name} legal team"
        }
        
        return descriptions.get(activity_type, f"Activity with {company_name}")
    
    def save_to_csv(self, data: List[Dict[str, Any]], filename: str) -> None:
        """Save data to CSV file"""
        if not data:
            logger.warning(f"No data to save to {filename}")
            return
        
        df = pd.DataFrame(data)
        out_dir = os.path.dirname(os.path.abspath(filename))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        df.to_csv(filename, index=False)
        logger.info(f"Saved {len(data)} records to {filename}")
    
    def generate_all_data(self, 
                         num_customers: int = 100,
                         num_products: int = 50, 
                         num_deals: int = 200,
                         num_activities: int = 500,
                         output_dir: str = "data/raw") -> Dict[str, str]:
        """Generate all CRM data and save to CSV files"""
        
        logger.info("Starting synthetic CRM data generation")
        
        # Generate all data
        customers = self.generate_customers(num_customers)
        products = self.generate_products(num_products)
        deals = self.generate_deals(customers, products, num_deals)
        activities = self.generate_activities(customers, deals, num_activities)
        
        # Save to CSV files
        files_created = {}
        
        customers_file = f"{output_dir}/customers.csv"
        self.save_to_csv(customers, customers_file)
        files_created["customers"] = customers_file
        
        products_file = f"{output_dir}/products.csv"
        self.save_to_csv(products, products_file)
        files_created["products"] = products_file
        
        deals_file = f"{output_dir}/deals.csv"
        self.save_to_csv(deals, deals_file)
        files_created["deals"] = deals_file
        
        activities_file = f"{output_dir}/activities.csv"
        self.save_to_csv(activities, activities_file)
        files_created["activities"] = activities_file
        
        logger.info("CRM data generation completed successfully")
        return files_created


if __name__ == "__main__":
    # Example usage
    generator = CRMDataGenerator()
    files = generator.generate_all_data()
    print("Generated files:", files)
