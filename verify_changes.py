
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Setup path
sys.path.append(os.getcwd())

try:
    from FAIRS.server.database.schema import Base, InferenceContext, PredictedGames
    from FAIRS.server.utils.repository.serializer import DataSerializer
    from FAIRS.server.utils.services.importer import DatasetImportService
    from FAIRS.server.utils.constants import INFERENCE_CONTEXT_TABLE, PREDICTED_GAMES_TABLE
    print("Imports success")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def verify_schema():
    print("Verifying schema...")
    tables = [c.__tablename__ for c in Base.__subclasses__()]
    if "INFERENCE_CONTEXT" in tables and "PREDICTED_GAMES" in tables:
        print("Schema tables OK")
        return True
    print(f"Schema tables missing. Found: {tables}")
    return False

def verify_serializer_and_importer():
    print("Verifying serializer and importer...")
    importer = DatasetImportService()
    serializer = DataSerializer()
    
    # Create dummy data
    df = pd.DataFrame({
        "extraction": [1, 2, 3],
        "other_col": ["a", "b", "c"] # Should be ignored
    })
    
    # Test Import
    try:
        count = importer.import_dataframe(df, "INFERENCE_CONTEXT", dataset_name="test_context")
        print(f"Imported {count} rows to INFERENCE_CONTEXT")
    except Exception as e:
        print(f"Import failed: {e}")
        return False

    # Test Load
    try:
        loaded = serializer.load_inference_context("test_context")
        print(f"Loaded {len(loaded)} rows from INFERENCE_CONTEXT")
        if len(loaded) == 3:
            print("Row count matches")
        else:
            print(f"Row count mismatch: {len(loaded)}")
            return False
            
        if "dataset_name" in loaded.columns and "uploaded_at" in loaded.columns:
             print("New columns present")
        else:
             print(f"Columns missing. Found: {loaded.columns}")
             return False
             
    except Exception as e:
        print(f"Load failed: {e}")
        return False
        
    return True

if __name__ == "__main__":
    if verify_schema() and verify_serializer_and_importer():
        print("VERIFICATION SUCCESS")
    else:
        print("VERIFICATION FAILED")
