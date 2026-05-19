"""
Tests for CRM data generation module
"""

import pytest
import os
import pandas as pd
from src.data_generation.crm_generator import CRMDataGenerator


class TestCRMDataGenerator:
    """Test cases for CRMDataGenerator"""
    
    def setup_method(self):
        """Setup test environment"""
        self.generator = CRMDataGenerator()
        self.test_dir = "test_data"
        os.makedirs(self.test_dir, exist_ok=True)
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_generate_customers(self):
        """Test customer generation"""
        customers = self.generator.generate_customers(num_customers=10)
        
        assert len(customers) == 10
        assert all('customer_id' in customer for customer in customers)
        assert all('company_name' in customer for customer in customers)
        assert all('industry' in customer for customer in customers)
        assert all('annual_revenue' in customer for customer in customers)
    
    def test_generate_products(self):
        """Test product generation"""
        products = self.generator.generate_products(num_products=5)
        
        assert len(products) == 5
        assert all('product_id' in product for product in products)
        assert all('product_name' in product for product in products)
        assert all('category' in product for product in products)
        assert all('unit_price' in product for product in products)
    
    def test_generate_deals(self):
        """Test deal generation"""
        customers = self.generator.generate_customers(num_customers=5)
        products = self.generator.generate_products(num_products=5)
        
        deals = self.generator.generate_deals(customers, products, num_deals=10)
        
        assert len(deals) == 10
        assert all('deal_id' in deal for deal in deals)
        assert all('customer_id' in deal for deal in deals)
        assert all('stage' in deal for deal in deals)
        assert all('value' in deal for deal in deals)
    
    def test_generate_activities(self):
        """Test activity generation"""
        customers = self.generator.generate_customers(num_customers=3)
        products = self.generator.generate_products(num_products=3)
        deals = self.generator.generate_deals(customers, products, num_deals=5)
        
        activities = self.generator.generate_activities(customers, deals, num_activities=10)
        
        assert len(activities) == 10
        assert all('activity_id' in activity for activity in activities)
        assert all('customer_id' in activity for activity in activities)
        assert all('activity_type' in activity for activity in activities)
    
    def test_save_to_csv(self):
        """Test CSV saving functionality"""
        customers = self.generator.generate_customers(num_customers=5)
        csv_file = f"{self.test_dir}/test_customers.csv"
        
        self.generator.save_to_csv(customers, csv_file)
        
        assert os.path.exists(csv_file)
        
        # Verify CSV content
        df = pd.read_csv(csv_file)
        assert len(df) == 5
        assert 'customer_id' in df.columns
        assert 'company_name' in df.columns
    
    def test_generate_all_data(self):
        """Test complete data generation"""
        files = self.generator.generate_all_data(
            num_customers=5,
            num_products=3,
            num_deals=10,
            num_activities=15,
            output_dir=self.test_dir
        )
        
        assert len(files) == 4
        assert 'customers' in files
        assert 'products' in files
        assert 'deals' in files
        assert 'activities' in files
        
        # Verify all files exist
        for file_path in files.values():
            assert os.path.exists(file_path)
            
            # Verify CSV content
            df = pd.read_csv(file_path)
            assert len(df) > 0


if __name__ == "__main__":
    pytest.main([__file__])
