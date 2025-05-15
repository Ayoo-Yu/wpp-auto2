import sys
import os

# Determine the correct path to 'backend-autopredict'
# current_file_dir is ...auto_scripts/scripts/supershort/
current_file_dir = os.path.dirname(os.path.abspath(__file__))
# target_path should be ...backend-autopredict/
# This navigates three levels up from 'supershort' directory to 'backend-autopredict'
path_to_backend_autopredict = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..'))

if path_to_backend_autopredict not in sys.path:
    sys.path.insert(0, path_to_backend_autopredict)
    # Optional: for debugging, you can add a print statement
    # print(f"[DEBUG data_processor_supershort] Added to sys.path: {path_to_backend_autopredict}")

import pandas as pd
import logging
from datetime import datetime # Added for timestamp comparison in CSV update

# Assuming db_session.py and db_models.py are in a location accessible via PYTHONPATH
# or are in the same directory or a parent directory added to sys.path elsewhere.
# For this example, we'll follow the pattern in data_processor_short.py
# and assume they can be imported.

# --- DB Imports Start ---
try:
    from sqlalchemy.orm import Session
    # IMPORTANT: Changed TrainPreSupershort to TrainPreShort as per new requirement
    from db_models import TrainPreShort, ActualPower 
    from db_session import db_session
    DB_ACCESS_AVAILABLE = True
    logging.info("Database modules (TrainPreShort, ActualPower) imported successfully for supershort processing.")
except ImportError as e:
    logging.error(f"Supershort DB related modules import failed (using TrainPreShort): {e}. DB operations will be unavailable.", exc_info=True)
    DB_ACCESS_AVAILABLE = False
# --- DB Imports End ---

def load_and_merge_data_from_db(days_to_load: int = None):
    """
    Loads feature data from TrainPreShort and actual power from ActualPower,
    merges them, and returns a pandas DataFrame.
    (This function might be less used if training always reads from an updated CSV)

    Args:
        days_to_load (int, optional): Number of past days of data to load. 
                                      If None, loads all available data. Defaults to None.
    Returns:
        pd.DataFrame: Merged DataFrame with features and actual power, or an empty
                      DataFrame if an error occurs or no data is found.
    """
    if not DB_ACCESS_AVAILABLE:
        logging.error("Database modules not available. Cannot load data directly for supershort model.")
        return pd.DataFrame()

    logging.info("Starting to load data directly from database for supershort model (using TrainPreShort)...")

    features_df = pd.DataFrame()
    actual_df = pd.DataFrame()

    try:
        with db_session() as session:
            # Query changed to TrainPreShort
            logging.info("Querying TrainPreShort table...")
            query_features = session.query(TrainPreShort)
            # Optional: Filter by date if days_to_load is specified
            # from datetime import timedelta # Ensure datetime is imported
            # if days_to_load is not None and hasattr(TrainPreShort, 'Timestamp'):
            #     cutoff_date = datetime.utcnow() - timedelta(days=days_to_load)
            #     query_features = query_features.filter(TrainPreShort.Timestamp >= cutoff_date)
            
            features_df = pd.read_sql(query_features.statement, session.bind)
            if 'timestamp' in features_df.columns and 'Timestamp' not in features_df.columns:
                features_df.rename(columns={'timestamp': 'Timestamp'}, inplace=True)
            logging.info(f"Retrieved {len(features_df)} records from TrainPreShort.")

            logging.info("Querying ActualPower table...")
            query_actual = session.query(ActualPower.timestamp, ActualPower.wp_true)
            # Optional: Filter by date
            # if days_to_load is not None and hasattr(ActualPower, 'timestamp'):
            #     cutoff_date_actual = datetime.utcnow() - timedelta(days=days_to_load)
            #     query_actual = query_actual.filter(ActualPower.timestamp >= cutoff_date_actual)

            actual_df = pd.read_sql(query_actual.statement, session.bind)
            if 'timestamp' in actual_df.columns and 'Timestamp' not in actual_df.columns:
                actual_df.rename(columns={'timestamp': 'Timestamp'}, inplace=True)
            elif 'Timestamp' not in actual_df.columns and not actual_df.empty:
                 logging.warning("ActualPower query result missing 'Timestamp' column after potential rename. Trying to rename first column if it exists.")
                 if actual_df.columns.any():
                     actual_df.rename(columns={actual_df.columns[0]: 'Timestamp'}, inplace=True)
            logging.info(f"Retrieved {len(actual_df)} records from ActualPower.")

    except Exception as e:
        logging.error(f"Error querying database for supershort data (using TrainPreShort): {e}", exc_info=True)
        return pd.DataFrame()

    if features_df.empty and actual_df.empty:
        logging.warning("No data retrieved from either TrainPreShort or ActualPower.")
        return pd.DataFrame()
    if features_df.empty:
        logging.warning("No data retrieved from TrainPreShort. Cannot create training set.")
        return pd.DataFrame()
    if actual_df.empty:
        logging.warning("No data retrieved from ActualPower (wp_true). Cannot create training set.")
        return pd.DataFrame()

    logging.info("Merging data from TrainPreShort and ActualPower...")
    try:
        if 'Timestamp' not in features_df.columns:
            logging.error("Features DataFrame (TrainPreShort) is missing 'Timestamp' column for merge.")
            return pd.DataFrame()
        if 'Timestamp' not in actual_df.columns:
            logging.error("Actual power DataFrame (ActualPower) is missing 'Timestamp' column for merge.")
            return pd.DataFrame()

        features_df['Timestamp'] = pd.to_datetime(features_df['Timestamp'])
        actual_df['Timestamp'] = pd.to_datetime(actual_df['Timestamp'])
        merged_df = pd.merge(features_df, actual_df, on='Timestamp', how='inner')
        logging.info(f"Successfully merged data. Resulting DataFrame has {len(merged_df)} records.")

        if merged_df.empty:
            logging.warning("Merged DataFrame is empty. Check timestamp alignment and data availability in both tables.")
            return pd.DataFrame()

        for col_name in ['record_id', 'record_id_x', 'record_id_y']:
            if col_name in merged_df.columns:
                logging.info(f"Dropping '{col_name}' column from merged supershort data.")
                merged_df.drop(columns=[col_name], inplace=True)
        
        merged_df.sort_values(by='Timestamp', inplace=True)
        merged_df.reset_index(drop=True, inplace=True)
        return merged_df
    except Exception as e:
        logging.error(f"Error merging or post-processing supershort data (from TrainPreShort): {e}", exc_info=True)
        return pd.DataFrame()

# New function similar to data_processor_short.py's update_training_csv_from_db
def update_supershort_training_csv_from_db(csv_file_path: str):
    """
    Updates the local supershort training CSV file from the database (TrainPreShort and ActualPower).
    Fetches new data based on the latest timestamp in the CSV.
    Creates the CSV if it doesn't exist.

    Args:
        csv_file_path (str): Path to the supershort training CSV file.

    Returns:
        bool: True if update/creation was successful or no new data was needed, False otherwise.
    """
    if not DB_ACCESS_AVAILABLE:
        logging.error("Database modules not available. Cannot update/create supershort training CSV.")
        return False

    logging.info(f"Starting to check and update supershort training CSV: {csv_file_path}")
    latest_timestamp_in_csv = None
    existing_df = pd.DataFrame()
    file_exists = os.path.exists(csv_file_path)
    initial_creation = not file_exists

    if file_exists:
        try:
            existing_df = pd.read_csv(csv_file_path)
            ts_col = None
            for col in existing_df.columns: # Find timestamp column case-insensitively
                if col.lower() == 'timestamp':
                    ts_col = col
                    break
            
            if not existing_df.empty and ts_col:
                if ts_col != 'Timestamp': # Standardize to 'Timestamp'
                    logging.info(f"Renaming CSV column '{ts_col}' to 'Timestamp' for supershort data.")
                    existing_df.rename(columns={ts_col: 'Timestamp'}, inplace=True)
                existing_df['Timestamp'] = pd.to_datetime(existing_df['Timestamp'])
                latest_timestamp_in_csv = existing_df['Timestamp'].max()
                logging.info(f"Latest timestamp in existing supershort CSV '{csv_file_path}': {latest_timestamp_in_csv}")
            else:
                logging.warning(f"Supershort CSV '{csv_file_path}' is empty or missing 'Timestamp' column. Will treat as initial creation.")
                initial_creation = True
        except Exception as e:
            logging.error(f"Error reading existing supershort CSV '{csv_file_path}': {e}. Aborting update.", exc_info=True)
            return False
    else:
        logging.info(f"Supershort CSV file '{csv_file_path}' not found. Will attempt to create it from database.")

    # Query database for new data
    features_new_df = pd.DataFrame()
    actual_new_df = pd.DataFrame()
    try:
        with db_session() as session:
            logging.info("Querying TrainPreShort for new supershort data...")
            query_features = session.query(TrainPreShort)
            if latest_timestamp_in_csv is not None:
                # Ensure TrainPreShort.Timestamp is the correct attribute name
                query_features = query_features.filter(TrainPreShort.Timestamp > latest_timestamp_in_csv)
            
            features_new_df = pd.read_sql(query_features.statement, session.bind)
            if 'timestamp' in features_new_df.columns and 'Timestamp' not in features_new_df.columns:
                 features_new_df.rename(columns={'timestamp': 'Timestamp'}, inplace=True)
            logging.info(f"Retrieved {len(features_new_df)} new records from TrainPreShort for supershort CSV.")

            logging.info("Querying ActualPower for new supershort data...")
            # Assuming ActualPower.timestamp is the correct attribute name
            query_actual = session.query(ActualPower.timestamp, ActualPower.wp_true)
            if latest_timestamp_in_csv is not None:
                query_actual = query_actual.filter(ActualPower.timestamp > latest_timestamp_in_csv)
            
            actual_new_df = pd.read_sql(query_actual.statement, session.bind)
            if 'timestamp' in actual_new_df.columns and 'Timestamp' not in actual_new_df.columns:
                 actual_new_df.rename(columns={'timestamp': 'Timestamp'}, inplace=True)
            elif 'Timestamp' not in actual_new_df.columns and not actual_new_df.empty and actual_new_df.columns.any():
                 actual_new_df.rename(columns={actual_new_df.columns[0]: 'Timestamp'}, inplace=True)
            logging.info(f"Retrieved {len(actual_new_df)} new records from ActualPower for supershort CSV.")

    except Exception as e:
        logging.error(f"Error querying database for new supershort data: {e}", exc_info=True)
        return False

    if features_new_df.empty or actual_new_df.empty:
        if initial_creation and features_new_df.empty and actual_new_df.empty:
            logging.warning("Database has no data from TrainPreShort or ActualPower to create initial supershort CSV.")
        else:
            logging.info("No new data found in database to add to supershort CSV (or one table was empty).")
        # If initial creation and no data, still return True as it's not an error state unless file MUST be created.
        # If file must exist, an empty df could be written or return False. For now, True.
        if initial_creation and not os.path.exists(csv_file_path):
             logging.warning(f"Initial CSV creation for {csv_file_path} attempted, but DB had no data. File will not be created.")
        return True 

    logging.info("Merging new data for supershort CSV...")
    try:
        if 'Timestamp' not in features_new_df.columns:
             logging.error("New features data (TrainPreShort) is missing 'Timestamp' for supershort CSV merge.")
             return False
        if 'Timestamp' not in actual_new_df.columns:
             logging.error("New actual power data (ActualPower) is missing 'Timestamp' for supershort CSV merge.")
             return False

        features_new_df['Timestamp'] = pd.to_datetime(features_new_df['Timestamp'])
        actual_new_df['Timestamp'] = pd.to_datetime(actual_new_df['Timestamp'])
        
        merged_new_data = pd.merge(features_new_df, actual_new_df, on='Timestamp', how='inner')
        logging.info(f"Merged new data for supershort CSV, {len(merged_new_data)} new records obtained.")

        if 'record_id' in merged_new_data.columns: # Drop record_id from merged new data
            merged_new_data.drop(columns=['record_id'], inplace=True)
        # Also check for _x, _y suffixes if merge creates them due to overlapping non-key columns
        for col_name_suffix in ['_x', '_y']:
            cols_to_drop = [col for col in merged_new_data.columns if col.startswith('record_id') and col.endswith(col_name_suffix)]
            if cols_to_drop:
                merged_new_data.drop(columns=cols_to_drop, inplace=True)
        
        if merged_new_data.empty:
            logging.info("No new records after merging (possibly due to timestamp mismatches or data cleaning). Supershort CSV not updated.")
            return True

        # Clean NaNs from new data - simple dropna on features, mean fill for wp_true
        if 'wp_true' in merged_new_data.columns:
            merged_new_data['wp_true'].fillna(merged_new_data['wp_true'].mean(), inplace=True)
        merged_new_data.dropna(subset=[col for col in merged_new_data.columns if col not in ['Timestamp', 'wp_true']], inplace=True)
        
        merged_new_data.sort_values(by='Timestamp', inplace=True)

    except Exception as e:
        logging.error(f"Error merging or cleaning new supershort data: {e}", exc_info=True)
        return False

    if merged_new_data.empty: # Check again after cleaning
        logging.info("New data became empty after cleaning. Supershort CSV not updated.")
        return True
        
    logging.info(f"Writing/Appending {len(merged_new_data)} new records to supershort CSV: {csv_file_path}")
    try:
        if initial_creation:
            merged_new_data.to_csv(csv_file_path, index=False, header=True)
            logging.info(f"Created new supershort CSV '{csv_file_path}' with {len(merged_new_data)} records.")
        else:
            # Ensure columns match existing CSV if appending
            if not existing_df.empty:
                existing_cols = existing_df.columns.tolist()
                try:
                    merged_new_data = merged_new_data[existing_cols]
                except KeyError as ke:
                    logging.error(f"Column mismatch: New supershort data columns {merged_new_data.columns.tolist()} do not match existing CSV columns {existing_cols}. Missing: {ke}. Cannot append.")
                    return False
            merged_new_data.to_csv(csv_file_path, mode='a', index=False, header=False)
            logging.info(f"Appended {len(merged_new_data)} new records to existing supershort CSV '{csv_file_path}'.")
        return True
    except Exception as e:
        logging.error(f"Error writing to supershort CSV '{csv_file_path}': {e}", exc_info=True)
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Example for load_and_merge_data_from_db
    # print("\nAttempting to load supershort data directly from DB (using TrainPreShort)...")
    # if DB_ACCESS_AVAILABLE:
    #     all_data = load_and_merge_data_from_db()
    #     if not all_data.empty:
    #         print(f"Successfully loaded {len(all_data)} records directly.")
    #         print(all_data.head())
    #     else:
    #         print("Failed to load data directly or data is empty.")
    # else:
    #     print("DB_ACCESS_AVAILABLE is False. Cannot run direct load example.")

    # Example for update_supershort_training_csv_from_db
    print("\nAttempting to update/create 'training_data_supershort_example.csv'...")
    if DB_ACCESS_AVAILABLE:
        # Make sure current dir is where you want the CSV or provide full path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        example_csv_path = os.path.join(script_dir, 'training_data_supershort_example.csv')
        
        # To test incremental, run once, then potentially add new data to DB and run again.
        # To test creation, delete the example CSV before running.
        if os.path.exists(example_csv_path):
            print(f"Example CSV '{example_csv_path}' exists. Update will be attempted.")
        else:
            print(f"Example CSV '{example_csv_path}' does not exist. Creation will be attempted.")

        success = update_supershort_training_csv_from_db(example_csv_path)
        if success:
            print(f"Update/Create process for '{example_csv_path}' completed.")
            if os.path.exists(example_csv_path):
                 df_check = pd.read_csv(example_csv_path)
                 print(f"CSV now contains {len(df_check)} records. Last 5 rows:")
                 print(df_check.tail())
            else:
                 print(f"CSV {example_csv_path} was not created (likely no data in DB for initial creation).")

        else:
            print(f"Update/Create process for '{example_csv_path}' failed. Check logs.")
    else:
        print("DB_ACCESS_AVAILABLE is False. Cannot run CSV update example.") 