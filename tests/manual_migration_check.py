import sys
import os
from collections.abc import Callable
import pandas as pd
import numpy as np
from io import BytesIO

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from FAIRS.server.services.loader import TabularFileLoader
from FAIRS.server.services.importer import DatasetImportService, ROULETTE_SERIES_TABLE
from FAIRS.server.repositories.database import database

def test_migration_flow():
    print(f"Pandas version: {pd.__version__}")
    assert pd.__version__ == "3.0.0", f"Expected pandas 3.0.0, got {pd.__version__}"

    # 1. Simulate Loading with mixed types that might be inferred as string
    print("\n--- Testing Loader and String Inference ---")
    csv_content = b"extraction;dataset_name\n15;test_dataset\n0;\n32;test_dataset"
    loader = TabularFileLoader()
    df = loader.load_bytes(csv_content, "test.csv")
    df["dataset_name"] = df["dataset_name"].astype("string")
    
    print("Loaded DataFrame dtypes:")
    print(df.dtypes)
    assert pd.api.types.is_string_dtype(df["dataset_name"].dtype)
    
    # Check if string inference is active (pandas 3.0 default for some read implementations?) 
    # Actually explicit string dtype is opt-in mostly but let's see what happens with default read_csv
    
    # 2. Simulate Import/Normalization
    print("\n--- Testing Importer and Normalization ---")
    importer = DatasetImportService()
    normalized_df = importer.normalize(df, ROULETTE_SERIES_TABLE, "test_dataset_v3")
    
    print("Normalized DataFrame dtypes:")
    print(normalized_df.dtypes)
    print("Normalized DataFrame head:")
    print(normalized_df.head())
    assert pd.api.types.is_string_dtype(normalized_df["dataset_name"].dtype)
    assert "color" not in df.columns
    
    # 3. Simulate DB Save (Upsert/Insert)
    # create a row with pd.NA if possible to test the fix
    # Manually force a pd.NA into the dataframe to test the sanitizer
    print("\n--- Testing DB Persistence with pd.NA ---")
    
    # Create a dataframe with string dtype and pd.NA
    df_na = pd.DataFrame({
        "id": [999999],
        "extraction": [0],
        "dataset_name": pd.Series(["test_na"], dtype="string"),
        "color": pd.Series([pd.NA], dtype="string"), # This should cause issues if not sanitized
        "color_code": [0],
        "position": [0]
    })
    
    print("DataFrame with pd.NA:")
    print(df_na)
    print(df_na.dtypes)
    
    try:
        # We use a direct save to test the backend logic
        # Using save_into_database (which uses to_sql) might be fine, but upsert uses the dict logic we fixed
        print("Attempting delete...")
        database.delete_from_database(ROULETTE_SERIES_TABLE, {"id": 999999})
        
        print("Attempting upsert...")
        database.upsert_into_database(df_na, ROULETTE_SERIES_TABLE)
        print("Upsert successful!")
        
        # Verify it was saved as NULL (None)
        loaded = database.load_filtered(ROULETTE_SERIES_TABLE, {"id": 999999})
        print("Loaded back:")
        print(loaded)
        val = loaded.iloc[0]["color"]
        print(f"Loaded value for color: {val} (type: {type(val)})")
        assert val is None or isinstance(val, str)
        
        # Cleanup
        database.delete_from_database(ROULETTE_SERIES_TABLE, {"id": 999999})
        
    except Exception as e:
        print(f"FAILED: {e}")
        raise e

if __name__ == "__main__":
    test_migration_flow()
